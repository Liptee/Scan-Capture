# Модели данных и форматы файлов

## 1. Запись с камеры (TIS RAW)

Реализовано в `tis_camera/raw_writer.py`.

### 1.1. Бинарный файл `.raw`

| Смещение | Размер | Поле |
|---|---|---|
| 0 | 8 | Magic `TISRAW\x01` |
| 8 | 4 | width (uint32) |
| 12 | 4 | height (uint32) |
| 16 | 4 | bits_per_pixel (uint32) |
| 20 | 4 | frame_count (uint32) |
| 24 | 4 | frame_size_bytes (uint32) |
| 28 | 8 | fps (float64) |
| 36 | 8 | exposure_us (float64) |
| 44 | 4 | pixel_format_len (uint32) |
| 48 | N | pixel_format (UTF-8) |
| 48+N | frame_count × frame_size | payload |

Кадры идут последовательно без разделителей.

### 1.2. Sidecar `.raw.json`

```json
{
  "device_model": "DMM 37UX252-ML",
  "device_serial": "02524135",
  "mode": "2048x1536@60",
  "width": 2048,
  "height": 1536,
  "fps": 60.0,
  "duration_s": 47.3,
  "exposure_us": 10000.0,
  "pixel_format": "Mono16",
  "bits_per_pixel": 16,
  "frame_count": 2838,
  "frame_size_bytes": 6291456,
  "pitch_bytes": 4096,
  "created_at_utc": "2025-06-23T12:00:00+00:00",
  "frame_timestamps_ns": [0, 16666666, "..."],
  "frame_numbers": [1, 2, "..."]
}
```

### 1.3. Роль в pipeline

TIS RAW — **внутренний формат** capture-сервиса. Перед `buildHSI` может потребоваться конвертация в формат, ожидаемый `HSIBuilder` (уточняется в Dev-документации `build_csi`).

---

## 2. HSI-куб (результат сборки)

Формат определяется библиотекой `build_csi`. Адаптер сохраняет native `.hsi` и предоставляет метаданные для API.

### 2.1. Логическая модель

```python
@dataclass
class HsiCube:
    id: str
    path: Path
    width: int           # пространственное разрешение (lines)
    height: int          # поперечное (pixels across slit)
    bands: int           # число спектральных каналов
    wavelengths_nm: list[float]
    data_type: str       # float32, uint16, ...
    interleave: str      # BIP, BSQ, BIL
```

### 2.2. Экспорт (ТЗ §4)

| Формат | Расширение | Sidecars |
|---|---|---|
| GeoTIFF | `.tif` / `.tiff` | `.hdr`, геопривязка |
| TIFF | `.tif` | опционально |
| MATLAB | `.mat` | — |
| NumPy | `.npy` / `.npz` | — |
| ENVI DAT | `.dat` | `.hdr` |
| Native HSI | `.hsi` | `.jsl` и др. по библиотеке |

Экспорт выполняется **только** через методы `build_csi`, не собственной реализацией.

---

## 3. Калибровка

Каталог: `data/calibration/{profile_name}/`

### 3.1. `roi.json`

```json
{
  "x": 0,
  "y": 100,
  "width": 2048,
  "height": 200,
  "description": "Spatial ROI on sensor"
}
```

### 3.2. `wavelengths.json`

```json
{
  "unit": "nm",
  "count": 224,
  "values": [400.0, 402.5, 405.0]
}
```

или ссылка на бинарный файл:

```json
{
  "source_file": "wavelengths.bin",
  "count": 224,
  "unit": "nm"
}
```

### 3.3. `coefficients/`

Файлы от разработчиков библиотеки (формат — по Dev-документации):

```
coefficients/
├── spectral_response.csv
├── geometric_calibration.json
└── ...
```

### 3.4. `profile.json`

```json
{
  "name": "default",
  "description": "Factory calibration 2025-06",
  "roi": "roi.json",
  "wavelengths": "wavelengths.json",
  "coefficients_dir": "coefficients/",
  "hsi_builder_config": {}
}
```

`hsi_builder_config` — произвольный JSON, передаваемый в `HSIBuilder` без изменений.

---

## 4. Задачи сборки (jobs)

`data/jobs/{job_id}.json`:

```json
{
  "job_id": "build_20250623_001",
  "type": "hsi_build",
  "status": "running",
  "progress": 0.42,
  "stage": "reconstruction",
  "message": "line 850/2048",
  "created_at": "2025-06-23T12:05:00Z",
  "updated_at": "2025-06-23T12:06:30Z",
  "params": { },
  "result": null,
  "error": null
}
```

---

## 5. Pydantic-схемы (shared/schemas/)

Основные модели для API:

| Модель | Файл |
|---|---|
| `CameraStatus` | `shared/schemas/camera.py` |
| `CaptureModeInfo` | `shared/schemas/camera.py` |
| `CameraProperty` | `shared/schemas/camera.py` |
| `RecordingConfig` | `shared/schemas/recording.py` |
| `RecordingStatus` | `shared/schemas/recording.py` |
| `BuildParams` | `shared/schemas/hsi.py` |
| `BuildJobStatus` | `shared/schemas/hsi.py` |
| `HsiInfo` | `shared/schemas/hsi.py` |
| `ExportRequest` | `shared/schemas/hsi.py` |
| `CalibrationProfile` | `shared/schemas/hsi.py` |

---

## 6. ComplexData и цветосинтез

Реализация — в `build_csi`. Web-сервис:

1. Принимает параметры RGB-синтеза от UI
2. Вызывает API библиотеки (`ComplexData` или simplified mode)
3. Возвращает PNG для отображения

Не дублировать алгоритм декодирования в frontend/backend.

---

## 7. Хранение и именование

| Тип | Шаблон пути |
|---|---|
| Запись | `data/recordings/{name}_{timestamp}.raw` |
| HSI | `data/hsi/{name}_{timestamp}.hsi` |
| Экспорт | `data/exports/{hsi_id}/{format}/` |

`data/` в `.gitignore`, кроме `data/calibration/.gitkeep`.
