# Интеграция с fw-monitor / HSBuilder

## 1. Расположение библиотеки

| Компонент | Путь |
|---|---|
| Библиотека | `fw-monitor/` |
| Сборщик | `fw-monitor/hs/build_hsi/hsi_builder.py` → `HSBuilder` |
| Параметры | `fw-monitor/hs/build_hsi/builder_params.py` → `BuildParams` |
| Куб HSI | `fw-monitor/hs/core/hs_image.py` → `HSImage` |
| ComplexData | `fw-monitor/hs/data_complex/complexed_data.py` → `ComplexedData` |
| Цветосинтез | `fw-monitor/hs/viewer/color_synthesis.py` → `hsi_to_rgb` |

Сохранённый scope: [fw-monitor/SCOPE.md](../fw-monitor/SCOPE.md).

```bash
pip install -r fw-monitor/requirements.txt
export PYTHONPATH="${PYTHONPATH}:$(pwd)/fw-monitor"
```

---

## 2. Архитектурный принцип

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────┐
│  HSI Build       │     │  HSIBuilderAdapter  │     │  build_csi   │
│  Service         │────▶│  (наш код, ~100 LOC)│────▶│  HSIBuilder  │
│  worker.py       │     │  adapter.py         │     │  buildHSI()  │
└──────────────────┘     └─────────────────────┘     └──────────────┘
```

**Запрещено:** копировать алгоритмы реконструкции, декодирования, калибровки из `build_csi`.

**Разрешено:** обёртка, валидация входов, прогресс-колбэк, пути файлов, сериализация job status.

---

## 3. Фактический API

### 3.1. Инициализация

```python
from hs import HSBuilder, load_build_metadata

build_params = load_build_metadata("data/calibration/default/build_params.json")

builder = HSBuilder(
    path_to_hs_source="data/recordings/scan.avi",  # или каталог PNG/JPEG
    source_data_type="video",                       # "images" | "video"
    path_to_gps=None,                               # опционально, v2 UAV
    build_params=build_params,
    dark_current=None,
)
```

### 3.2. Сборка

```python
builder.build_hsi()           # опционально: build_uav_type="knn"|"triangle"
hsi = builder.get_hsi()
```

Прогресс: внутри `HSBuilder` используется `tqdm` на этапе preprocessing.  
Для WebSocket — обернуть цикл в адаптере или патчить callback в `services/hsi/worker.py`.

### 3.3. Сохранение / экспорт

```python
from hs import save_hsi, save_hsi_to_geotiff, save_hsi_to_envi

hsi.save("data/hsi/result.tiff")                    # + *_metadata.json
save_hsi_to_geotiff(hsi, "data/exports/result.tif")
save_hsi_to_envi(hsi, "data/exports/result")      # ENVI .hdr + .dat

# Форматы save_hsi: .mat, .npy, .tiff
# Чтение: load_hsi(path, path_to_metadata=..., key=...)
# ENVI/SPECIM: load_hsi(.dat, path_to_hdr=.hdr)
```

### 3.4. Калибровка

```python
from hs.build_hsi.postprocessing import calibrate_hsi

hsi_calibrated = calibrate_hsi(hsi, white_point, "data/calibration/coefficients.json")
```

`BuildParams.hyper_device_params` содержит `roi`, `wavelengths`, `frame_orientation`, `rotation_angle`.

### 3.5. Цветосинтез

```python
from hs import hsi_to_rgb

rgb = hsi_to_rgb(hsi, awb="simplified")  # или "grey-world", "grey-edge"
```

---

## 4. Адаптер (наша реализация)

`services/hsi/adapter.py`:

```python
class HSIBuilderAdapter:
    def __init__(self, calibration_dir: Path):
        self._calibration_dir = calibration_dir
        self._builder: HSIBuilder | None = None

    def _ensure_builder(self, profile: str) -> HSIBuilder:
        if self._builder is None:
            profile_path = self._calibration_dir / profile
            config = load_profile(profile_path)
            self._builder = HSIBuilder(
                calibration_path=str(profile_path),
                config=config.hsi_builder_config,
            )
        return self._builder

    def build(self, params: BuildParams, on_progress: ProgressCallback) -> HsiResult:
        try:
            from hs import HSBuilder
        except ImportError as exc:
            raise HsiLibraryNotAvailableError(
                "fw-monitor not on PYTHONPATH. See docs/INTEGRATION_HSI.md"
            ) from exc

        builder = HSBuilder(
            path_to_hs_source=str(params.source_path),
            source_data_type=params.data_source,
            build_params=self._load_build_params(params),
        )
        builder.build_hsi()
        hsi = builder.get_hsi()
```

---

## 5. Маппинг UI → buildHSI

| Поле UI (BuildPage) | Параметр buildHSI |
|---|---|
| Исходный файл | `source_path` |
| Build mode | `build_mode` |
| Data source | `data_source` |
| Reconstruction | `reconstruction_params` |
| ROI x,y,w,h | `roi` |
| Wavelengths | `wavelengths_nm` или из калибровки |
| Calibration profile | `calibration_coefficients` + init config |

---

## 6. Mock-режим (до подключения build_csi)

Для разработки UI и API без библиотеки:

```python
class MockHSIBuilderAdapter(HSIBuilderAdapter):
    def build(self, params, on_progress):
        for i in range(101):
            on_progress(BuildProgress("mock", i / 100, f"step {i}"))
            time.sleep(0.05)
        return HsiResult.mock(params.output_path)
```

Переключение: `HSI_BACKEND=mock` в `.env`.

---

## 7. Чеклист интеграции

- [ ] Получить URL Dev-ветки и документацию
- [ ] Добавить submodule / pip dependency
- [ ] Зафиксировать фактические сигнатуры в этом документе
- [ ] Положить файлы калибровки в `data/calibration/default/`
- [ ] Проверить совместимость формата записи (TIS RAW) с `data_source`
- [ ] Реализовать `HSIBuilderAdapter` без mock
- [ ] Подключить экспорт всех форматов через библиотеку
- [ ] E2E тест: запись → build → viewer

---

## 8. Конвертация TIS RAW → вход buildHSI

Если `HSIBuilder` не принимает TIS RAW напрямую, добавить тонкий конвертер в `services/hsi/converters/raw_to_lines.py`:

- Читает `.raw` + `.raw.json`
- Формирует входной формат библиотеки (ENVI stack, TIFF sequence, etc.)
- **Не** выполняет спектральную реконструкцию — только упаковка данных

Формат конвертации — по требованию Dev-документации.
