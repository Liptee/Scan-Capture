# Развёртывание

## 1. Платформы

| Платформа | Камера (IC4) | HSI (build_csi) | Web UI |
|---|---|---|---|
| Windows 10/11 x64 | ✅ | ✅ (ожидается) | ✅ |
| Linux x64 (Ubuntu 20.04+) | ✅ | ✅ (ожидается) | ✅ |
| Linux ARM64 | ✅ | ✅ (ожидается) | ✅ |
| macOS | ❌ IC4 | ⚠️ зависит от build_csi | ✅ UI only |

**macOS:** frontend и API работают; capture — через удалённый agent на Windows/Linux или mock.

---

## 2. Системные зависимости

### 2.1. Камера

1. [IC Imaging Control 4 SDK](https://www.theimagingsource.com/en-us/support/download/)
2. GenTL USB3 Vision driver (серия 37U)
3. Python 3.10+

### 2.2. HSI

1. `build_csi` из Dev-ветки
2. Зависимости библиотеки (numpy, возможно GDAL для GeoTIFF)

### 2.3. Backend

```
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.0
python-multipart
websockets
pillow
numpy
imagingcontrol4; sys_platform == "win32" or sys_platform == "linux"
```

### 2.4. Frontend

```
node >= 18
npm или pnpm
```

---

## 3. Локальная разработка

### 3.1. Backend

```bash
cd Baumer_App
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # fastapi, uvicorn, ...

cp config/settings.example.yaml config/settings.yaml
mkdir -p data/{recordings,hsi,exports,calibration,jobs}

uvicorn services.web_api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2. Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173, proxy → :8000
```

### 3.3. Переменные окружения

```bash
# .env
HSI_BACKEND=mock          # mock | native
DATA_DIR=./data
CALIBRATION_PROFILE=default
CAPTURE_MOCK=false        # true на macOS без камеры
CORS_ORIGINS=http://localhost:5173
```

---

## 4. Docker (опционально)

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - /dev/bus/usb:/dev/bus/usb    # Linux: доступ к камере
    privileged: true                  # только если нужен USB
    environment:
      - HSI_BACKEND=native

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [api]
```

> USB passthrough в Docker на Windows/macOS ограничен. Для production на Windows — запуск API нативно.

---

## 5. Production

1. `npm run build` → static в `frontend/dist/`
2. FastAPI раздаёт `dist/` через `StaticFiles`
3. Systemd / Windows Service для `uvicorn`
4. Nginx reverse proxy (опционально)

---

## 6. Структура config

`config/settings.example.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000

paths:
  data_dir: data
  recordings_dir: data/recordings
  hsi_dir: data/hsi
  exports_dir: data/exports
  calibration_dir: data/calibration
  jobs_dir: data/jobs

capture:
  default_pixel_format: mono16
  preview_max_fps: 15
  jpeg_quality: 80

hsi:
  backend: mock
  default_calibration_profile: default
  worker_processes: 1

cors:
  origins:
    - http://localhost:5173
```

---

## 7. Проверка установки

```bash
# Камера
python list_modes.py

# API
curl http://localhost:8000/api/v1/camera/status

# HSI mock
curl -X POST http://localhost:8000/api/v1/hsi/build -H "Content-Type: application/json" -d '{...}'
```
