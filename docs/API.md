# REST и WebSocket API

Базовый URL: `http://localhost:8000/api/v1`

WebSocket: `ws://localhost:8000/ws`

Все ответы — JSON. Ошибки: `{ "detail": "..." }` (FastAPI standard).

---

## 1. Камера (Вкладка «Подключение» + «Поток»)

### GET `/camera/status`

Статус подключения и информация об устройстве.

**Response 200:**
```json
{
  "connected": true,
  "model": "DMM 37UX252-ML",
  "serial": "02524135",
  "vendor": "The Imaging Source Europe GmbH",
  "usb_speed": "high_speed",
  "preview_active": false,
  "recording_active": false
}
```

### POST `/camera/connect`

Подключить камеру.

**Body (optional):**
```json
{
  "serial": "02524135"
}
```

**Response 200:** `CameraStatus` (как выше, `connected: true`)

**Response 503:** камера не найдена / драйвер не установлен

### POST `/camera/disconnect`

Отключить камеру. Останавливает preview и запись.

**Response 200:** `{ "connected": false }`

### GET `/camera/modes`

Список режимов съёмки.

**Response 200:**
```json
{
  "modes": [
    {
      "id": "2048x1536@60",
      "width": 2048,
      "height": 1536,
      "fps": 60.0,
      "pixel_formats": ["Mono8", "Mono16"]
    }
  ]
}
```

### GET `/camera/properties`

Текущие настраиваемые параметры камеры (GenICam).

**Response 200:**
```json
{
  "properties": [
    {
      "id": "ExposureTime",
      "type": "float",
      "value": 10000.0,
      "min": 1.0,
      "max": 4000000.0,
      "unit": "us",
      "writable": true
    },
    {
      "id": "Gain",
      "type": "float",
      "value": 0.0,
      "min": 0.0,
      "max": 48.0,
      "unit": "dB",
      "writable": true
    }
  ]
}
```

### PATCH `/camera/properties`

Применить параметры без перезапуска (live).

**Body:**
```json
{
  "properties": {
    "ExposureTime": 5000.0,
    "Gain": 3.0
  }
}
```

**Response 200:** обновлённый список properties

---

## 2. Видеопоток (Вкладка «Просмотр»)

### POST `/camera/preview/start`

Запуск preview-потока.

**Body (optional):**
```json
{
  "mode": "2048x1536@30",
  "pixel_format": "mono8"
}
```

### POST `/camera/preview/stop`

Остановка preview.

### WebSocket `/ws/stream`

**Client → Server:**
```json
{ "action": "subscribe", "quality": 80, "max_fps": 15 }
```

**Server → Client (binary):** JPEG-кадры

**Server → Client (text):**
```json
{
  "type": "frame_meta",
  "frame_number": 1024,
  "timestamp_ns": 123456789,
  "width": 2048,
  "height": 1536
}
```

---

## 3. Съёмка (Вкладка «Съёмка»)

### POST `/recording/start`

Унифицированный режим: Start + опциональный таймер.

**Body:**
```json
{
  "mode": "2048x1536@60",
  "pixel_format": "mono16",
  "exposure_us": 10000.0,
  "max_duration_s": 300.0,
  "output_name": "scan_001"
}
```

| Поле | Описание |
|---|---|
| `max_duration_s` | `null` — только ручной Stop; число — автоостановка |
| `output_name` | Имя без расширения; файл → `data/recordings/{name}.raw` |

**Response 202:**
```json
{
  "recording_id": "rec_20250623_001",
  "status": "recording",
  "started_at": "2025-06-23T12:00:00Z",
  "file_path": "data/recordings/scan_001.raw"
}
```

### POST `/recording/{recording_id}/stop`

Ручная остановка.

**Response 200:**
```json
{
  "recording_id": "rec_20250623_001",
  "status": "completed",
  "duration_s": 47.3,
  "frame_count": 2838,
  "file_path": "data/recordings/scan_001.raw",
  "metadata_path": "data/recordings/scan_001.raw.json"
}
```

### GET `/recording/{recording_id}`

Текущий статус записи.

**Response 200:**
```json
{
  "recording_id": "rec_20250623_001",
  "status": "recording",
  "elapsed_s": 12.5,
  "frame_count": 750,
  "file_path": "data/recordings/scan_001.raw"
}
```

### GET `/recordings`

Список завершённых записей.

---

## 4. Сборка HSI (Вкладка «Сборка»)

### GET `/hsi/presets`

Доступные пресеты сборки из `build_csi`.

### GET `/hsi/calibration`

Текущая калибровка (ROI, wavelengths).

### POST `/hsi/build`

Запуск сборки (асинхронно).

**Body:**
```json
{
  "source_path": "data/recordings/scan_001.raw",
  "build_mode": "push_broom",
  "data_source": "raw",
  "reconstruction": {
    "method": "default"
  },
  "roi": {
    "x": 0,
    "y": 0,
    "width": 2048,
    "height": 200
  },
  "wavelengths_nm": [400, 410, 420],
  "calibration_profile": "default",
  "output_name": "hsi_001"
}
```

**Response 202:**
```json
{
  "job_id": "build_20250623_001",
  "status": "queued"
}
```

### GET `/hsi/build/{job_id}`

Статус задачи.

**Response 200:**
```json
{
  "job_id": "build_20250623_001",
  "status": "running",
  "progress": 0.42,
  "stage": "reconstruction",
  "message": "Processing line 850/2048"
}
```

### POST `/hsi/build/{job_id}/cancel`

Отмена сборки.

### GET `/hsi/build/{job_id}/result`

Результат после `status: completed`.

```json
{
  "job_id": "build_20250623_001",
  "hsi_path": "data/hsi/hsi_001.hsi",
  "bands": 224,
  "width": 2048,
  "height": 1500,
  "wavelengths_nm": [400.0, 402.5, "..."]
}
```

### WebSocket `/ws/jobs/{job_id}`

Стрим прогресса сборки.

```json
{
  "type": "progress",
  "progress": 0.65,
  "stage": "export",
  "message": "..."
}
```

---

## 5. Просмотр HSI (Вкладка «Просмотр»)

### GET `/hsi/{hsi_id}/info`

Метаданные куба.

### GET `/hsi/{hsi_id}/band/{index}`

Один спектральный канал (PNG/JPEG для отображения).

**Query:** `?format=png&normalize=true`

### GET `/hsi/{hsi_id}/spectrum`

Спектр в точке.

**Query:** `?x=512&y=256`

**Response:**
```json
{
  "x": 512,
  "y": 256,
  "wavelengths_nm": [400, 402, "..."],
  "values": [0.12, 0.15, "..."]
}
```

### POST `/hsi/{hsi_id}/rgb`

Цветосинтез (через библиотеку ComplexData / simplified).

**Body:**
```json
{
  "mode": "simplified",
  "r_band": 650,
  "g_band": 550,
  "b_band": 450
}
```

**Response:** URL или base64 PNG

### POST `/hsi/{hsi_id}/export`

Экспорт на диск.

**Body:**
```json
{
  "format": "geotiff",
  "include_sidecars": true,
  "bands": "all"
}
```

**Поддерживаемые `format`:** `geotiff`, `tiff`, `mat`, `npy`, `dat`, `hsi`

---

## 6. Файлы

### GET `/files/recordings`

### GET `/files/hsi`

### GET `/files/download?path=...`

Скачивание с проверкой sandbox (только `data/`).

---

## 7. Коды ошибок

| HTTP | Ситуация |
|---|---|
| 400 | Невалидные параметры |
| 404 | Запись / job / файл не найден |
| 409 | Камера занята (идёт запись) |
| 503 | Камера не подключена / build_csi недоступен |
| 500 | Внутренняя ошибка |

---

## 8. OpenAPI

Автогенерация: `http://localhost:8000/docs` (Swagger UI) после запуска FastAPI.

Pydantic-модели — в `shared/schemas/`.
