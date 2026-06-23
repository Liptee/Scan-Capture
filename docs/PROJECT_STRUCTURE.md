# Структура проекта

Целевая структура репозитория после реализации ТЗ.

```
Baumer_App/
│
├── docs/                          # Документация (этот каталог)
│
├── frontend/                      # React SPA
│   ├── src/
│   │   ├── app/                   # Router, layout, providers
│   │   ├── pages/
│   │   │   ├── ConnectionPage/    # Вкладка 1: Подключение
│   │   │   ├── StreamPage/        # Вкладка 2: Видеопоток
│   │   │   ├── CapturePage/       # Вкладка 3: Съёмка
│   │   │   ├── BuildPage/         # Вкладка 4: Сборка HSI
│   │   │   └── ViewerPage/        # Вкладка 5: Просмотр HSI
│   │   ├── components/            # UI-kit: ProgressBar, CameraControls, HsiCanvas
│   │   ├── api/                   # HTTP + WebSocket клиенты
│   │   ├── hooks/                 # useCamera, useStream, useBuildJob
│   │   └── types/                 # TypeScript типы (зеркало Pydantic models)
│   ├── package.json
│   └── vite.config.ts
│
├── services/
│   ├── web_api/                   # FastAPI gateway
│   │   ├── main.py                # Точка входа uvicorn
│   │   ├── app.py                 # create_app()
│   │   ├── routers/
│   │   │   ├── camera.py          # /api/v1/camera/*
│   │   │   ├── recording.py       # /api/v1/recording/*
│   │   │   ├── hsi.py             # /api/v1/hsi/*
│   │   │   ├── files.py           # /api/v1/files/*
│   │   │   └── ws.py              # /ws/stream, /ws/jobs/{id}
│   │   ├── dependencies.py        # DI: get_capture_service, get_hsi_service
│   │   └── middleware.py
│   │
│   ├── capture/                   # Сервис съёмки
│   │   ├── manager.py             # CameraManager (connect/disconnect)
│   │   ├── preview.py             # PreviewStream (QueueSink loop)
│   │   ├── recorder.py            # RecordingController (start/stop/timer)
│   │   ├── properties.py          # GenICam property map wrapper
│   │   └── models.py              # Pydantic: CameraStatus, RecordingStatus
│   │
│   └── hsi/                       # Сервис сборки HSI
│       ├── adapter.py             # HSIBuilderAdapter → build_csi.HSIBuilder
│       ├── worker.py              # Фоновый worker + progress
│       ├── exporter.py            # Обёртка экспорта форматов библиотеки
│       ├── calibration.py         # Загрузка ROI / wavelengths / coeffs
│       └── models.py              # BuildParams, BuildJob, HsiResult
│
├── shared/
│   ├── contracts/                 # Абстрактные интерфейсы сервисов
│   │   ├── capture.py             # ICaptureService (Protocol)
│   │   ├── hsi.py                 # IHsiBuildService (Protocol)
│   │   └── stage.py               # IStageController (заглушка v2)
│   ├── schemas/                   # Общие Pydantic-модели для API
│   │   ├── camera.py
│   │   ├── recording.py
│   │   └── hsi.py
│   └── proto/                     # gRPC (опционально, v2)
│       ├── capture.proto
│       └── hsi.proto
│
├── tis_camera/                    # ✅ Существующий модуль камеры (IC4)
│   ├── ic4_backend.py
│   ├── device_info.py
│   ├── modes.py
│   └── raw_writer.py
│
├── fw-monitor/                    # ✅ HSI-библиотека (урезанный subset)
│   └── hs/                        # HSBuilder, HSImage, ComplexedData, viewer
│
├── config/
│   ├── settings.yaml              # Пути data/, порты, лимиты
│   └── settings.example.yaml
│
├── data/                          # Runtime data (gitignored)
│   ├── recordings/
│   ├── hsi/
│   ├── exports/
│   ├── calibration/
│   └── jobs/
│
├── scripts/
│   ├── run_dev.sh                 # Запуск API + frontend dev
│   └── install_drivers.md         # Ссылка на IC4 / build_csi install
│
├── tests/
│   ├── test_api/
│   ├── test_capture/
│   └── test_hsi/
│
├── capture_raw.py                 # ✅ CLI (сохраняется для отладки)
├── list_modes.py
├── read_raw.py
│
├── pyproject.toml                 # Единый Python-проект
├── requirements.txt
├── docker-compose.yml
└── .env.example
```

## Принципы организации

1. **`tis_camera/`** — низкоуровневый драйвер, не знает про HTTP.
2. **`services/capture/`** — бизнес-логика съёмки, использует `tis_camera`.
3. **`services/hsi/`** — только адаптация `build_csi`, без собственных алгоритмов.
4. **`services/web_api/`** — тонкие роутеры, делегируют в сервисы.
5. **`shared/`** — контракты и схемы, общие для API и сервисов.
6. **`frontend/`** — только UI, вся логика на backend.

## Submodule `build_csi`

```bash
git submodule add <dev-branch-url> build_csi
```

До подключения submodule сервис HSI работает в режиме **mock** (`HSIBuilderAdapter` с `NotImplementedError` или тестовыми данными).
