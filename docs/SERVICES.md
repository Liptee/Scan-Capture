# Сервисы: детальное описание

## 1. Capture Service (`services/capture/`)

### 1.1. CameraManager

Управляет жизненным циклом IC4.

```python
class CameraManager:
    async def connect(self, serial: str | None = None) -> CameraStatus: ...
    async def disconnect(self) -> None: ...
    def get_status(self) -> CameraStatus: ...
    def list_modes(self) -> list[CaptureModeInfo]: ...
```

**Состояния:** `disconnected` → `connected` → (`previewing` | `recording`)

Потокобезопасность: IC4 — blocking API; все вызовы через `asyncio.to_thread()` или dedicated `ThreadPoolExecutor(max_workers=1)`.

### 1.2. PropertyController

Обёртка над `grabber.device_property_map`.

| Свойство (GenICam) | UI-вкладка | Примечание |
|---|---|---|
| `ExposureTime` | Поток, Съёмка | µs |
| `ExposureAuto` | Поток | Off для ручного режима |
| `Gain` / `GainAuto` | Поток | dB |
| `Focus` / `FocusAuto` | Поток | если поддерживается устройством |
| `Width`, `Height` | Съёмка | через mode |
| `AcquisitionFrameRate` | Съёмка | FPS |
| `PixelFormat` | Съёмка | Mono8 / Mono16 |

`set_properties()` применяет batch без перезапуска preview (если IC4 позволяет на лету).

### 1.3. PreviewStream

Непрерывный поток для вкладки «Просмотр».

**Алгоритм:**
1. `grabber.stream_setup(QueueSink, ACQUISITION_START)`
2. Цикл: `sink.pop_output_buffer()` → конвертация в numpy → JPEG (Pillow/OpenCV)
3. Кадры в `asyncio.Queue` → WebSocket broadcaster
4. `stop()`: `stream_stop()`, join thread

**Параметры throttle:** `max_fps` для WebSocket (не обязательно = camera FPS).

### 1.4. RecordingController

Объединяет режимы «по времени» и «Start/Stop».

```python
class RecordingController:
    async def start(
        self,
        mode: CaptureMode,
        exposure_us: float,
        pixel_format: str,
        max_duration_s: float | None,
        output_path: Path,
    ) -> RecordingStatus: ...

    async def stop(self) -> RecordingStatus: ...
```

**Логика:**
- `start()` — запускает запись в фоновый thread
- Если `max_duration_s` задан — `asyncio.sleep` + auto `stop()`
- Каждый кадр пишется в `.raw` (формат `tis_camera/raw_writer.py`)
- `stop()` — финализирует JSON-метаданные

**Совместимость с HSI:** запись = последовательность line-scan кадров; `HSIBuilder` принимает путь к исходнику согласно Dev-документации.

### 1.5. Входы / выходы (ТЗ §2.1)

| Вход | Источник |
|---|---|
| Параметры съёмки | REST `POST /recording/start`, UI |
| Команда start/stop | REST |

| Выход | Формат |
|---|---|
| Путь к файлу | `data/recordings/*.raw` |
| Длительность | `duration_s` в статусе |
| Статус | `recording` / `completed` / `failed` |

---

## 2. HSI Build Service (`services/hsi/`)

### 2.1. HSIBuilderAdapter

Тонкая обёртка — **единственная точка** вызова `build_csi`.

```python
class HSIBuilderAdapter:
    def __init__(self, calibration_dir: Path): ...

    def list_presets(self) -> list[BuildPreset]: ...

    def validate_params(self, params: BuildParams) -> list[str]: ...

    def build(
        self,
        params: BuildParams,
        progress_callback: Callable[[BuildProgress], None],
    ) -> HsiResult: ...
```

Внутри:
```python
from build_csi import HSIBuilder  # Dev branch

builder = HSIBuilder(config=...)
hsi = builder.buildHSI(
    source=...,
    roi=...,
    wavelengths=...,
    calibration=...,
    progress=progress_callback,
)
```

Точная сигнатура — см. [INTEGRATION_HSI.md](./INTEGRATION_HSI.md).

### 2.2. BuildWorker

```python
class BuildWorker:
  async def submit(self, params: BuildParams) -> str:  # job_id
  def get_status(self, job_id: str) -> BuildJobStatus: ...
  async def cancel(self, job_id: str) -> None: ...
```

- Задачи в `data/jobs/{job_id}.json`
- Выполнение в `ProcessPoolExecutor` (native lib)
- Progress → WebSocket через pub/sub в памяти

### 2.3. HSIExporter

Делегирует экспорт в `build_csi` — не реализует конвертацию самостоятельно.

| Формат | Метод библиотеки (ожидаемый) |
|---|---|
| GeoTIFF | `hsi.export_geotiff(...)` |
| TIFF | `hsi.export_tiff(...)` |
| MAT | `hsi.export_mat(...)` |
| NPY | `hsi.export_npy(...)` |
| DAT | `hsi.export_dat(...)` |
| HSI | native save |
| HDR, JSL | sidecars при `include_sidecars=true` |

### 2.4. CalibrationLoader

```python
class CalibrationLoader:
    def load_profile(self, name: str) -> CalibrationProfile: ...
```

**CalibrationProfile:**
```python
@dataclass
class CalibrationProfile:
    roi: Roi
    wavelengths_nm: list[float]
    coefficients_path: Path
    metadata: dict
```

Файлы: `data/calibration/{profile}/`

### 2.5. Входы / выходы (ТЗ §2.2)

| Вход | Описание |
|---|---|
| Путь к записи | `.raw` или формат из библиотеки |
| Build params | mode, reconstruction, ROI, λ |

| Выход | Описание |
|---|---|
| HSI object | in-memory до экспорта |
| Progress | 0.0–1.0 + stage |
| Файл на диске | `data/hsi/` |

---

## 3. Web API (`services/web_api/`)

### 3.1. Dependency Injection

```python
def get_capture_service() -> ICaptureService:
    return app.state.capture_service

def get_hsi_service() -> IHsiBuildService:
    return app.state.hsi_service
```

### 3.2. Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.capture_service = CaptureService()
    app.state.hsi_service = HsiBuildService(calibration_dir=...)
    yield
    await app.state.capture_service.disconnect()
```

### 3.3. CORS

Разрешить origin frontend dev-сервера (`localhost:5173`) и production static.

---

## 4. Интерфейсы (`shared/contracts/`)

Позволяют вынести сервисы в отдельные процессы без смены API.

```python
# shared/contracts/capture.py
class ICaptureService(Protocol):
    async def connect(self, serial: str | None = None) -> CameraStatus: ...
    async def start_preview(self, config: PreviewConfig) -> None: ...
    async def start_recording(self, config: RecordingConfig) -> RecordingStatus: ...
    ...
```

```python
# shared/contracts/hsi.py
class IHsiBuildService(Protocol):
    async def start_build(self, params: BuildParams) -> str: ...
    def get_job_status(self, job_id: str) -> BuildJobStatus: ...
    ...
```

```python
# shared/contracts/stage.py  (v2 stub)
class IStageController(Protocol):
    async def get_position(self) -> float: ...
    async def move_to(self, position: float, speed: float) -> None: ...
```
