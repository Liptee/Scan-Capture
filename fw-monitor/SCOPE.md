# fw-monitor — scope for HSI Web System

Урезанная копия [fw-monitor](.) для интеграции с веб-системой (`Baumer_App`).  
Сохранён только функционал, нужный по ТЗ; ML/разметка/аугментация удалены.

## Сохранено

| Модуль | Назначение | ТЗ |
|---|---|---|
| `hs/build_hsi/` | `HSBuilder`, чтение video/images, ROI, сборка куба | §2.2, §5 |
| `hs/build_hsi/builder_params.py` | `BuildParams`, калибровка, wavelengths, metadata JSON/TOML | §4, §5 |
| `hs/build_hsi/postprocessing.py` | `calibrate_hsi`, пост-нормализация/фильтрация | §5 |
| `hs/core/hs_image.py` | `HSImage`, load/save MAT/NPY/TIFF/DAT+HDR, GeoTIFF/ENVI | §4 |
| `hs/core/hs_mask.py` | Маски (для `ComplexedData`, опционально) | — |
| `hs/core/utils.py` | I/O утилиты | §4 |
| `hs/data_complex/complexed_data.py` | `ComplexedData` — HSI + RGB + metadata | §3 вкладка 5 |
| `hs/viewer/color_synthesis.py` | `hsi_to_rgb` (simplified / AWB) | §3 вкладка 5 |

## Удалено

| Модуль | Причина |
|---|---|
| `hs/classifiers/` | Обучение/инференс НС — вне scope v1 |
| `hs/synthesis/` | RGB→HSI нейросеть — не в ТЗ |
| `hs/statistical_analysis/` | Индексный анализ — не в ТЗ v1 |
| `hs/augment/` | Аугментация для обучения |
| `hs/hsirs/` | Desktop-разметка, matching, denoising |
| `hs/data_complex/complex.py`, fusion/* | Fusion/CNMF — не в ТЗ v1 |
| `rgb/`, `hsi_painter.py`, `demo_trainer.py` | Демо и RGB-inference |
| `nn_trainer.py`, `nn_inference.py`, `dl_loggers.py` | PyTorch training stack |

## API сборки

```python
from hs import HSBuilder, load_build_metadata

params = load_build_metadata("calibration/build_params.json")
builder = HSBuilder(
    path_to_hs_source="data/recordings/scan.avi",
    source_data_type="video",
    build_params=params,
)
builder.build_hsi()
hsi = builder.get_hsi()
hsi.save("data/hsi/result.tiff")
```

## Зависимости

См. `requirements.txt` — без PyTorch, PyQt, wandb, SAM2.

GDAL на macOS: `brew install gdal`, затем pip install GDAL (см. оригинальный README).

## Тесты

```bash
pip install -r requirements.txt
pytest tests/ -k "builder or hs_image"
```

Тесты builder требуют `test_data/` из полного репозитория fw-monitor (не включены).
