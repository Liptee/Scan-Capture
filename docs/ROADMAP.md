# Roadmap реализации

## Фаза 0. Текущее состояние ✅

- [x] Модуль `tis_camera/` — IC4, RAW-захват
- [x] CLI: `capture_raw.py`, `list_modes.py`, `read_raw.py`
- [x] Архитектурная документация

---

## Фаза 1. Backend foundation (2–3 недели)

| Задача | Приоритет |
|---|---|
| `pyproject.toml`, `requirements-dev.txt` | P0 |
| `shared/schemas/` — Pydantic модели | P0 |
| `shared/contracts/` — Protocol интерфейсы | P0 |
| `services/web_api/` — FastAPI skeleton + `/camera/status` | P0 |
| `services/capture/manager.py` — обёртка над `tis_camera` | P0 |
| `config/settings.yaml` | P1 |
| Базовые тесты API | P1 |

**Результат:** API connect/disconnect/status, без preview.

---

## Фаза 2. Capture + Stream (2–3 недели)

| Задача | Приоритет |
|---|---|
| `PreviewStream` — QueueSink + JPEG | P0 |
| WebSocket `/ws/stream` | P0 |
| `PropertyController` — live exposure/gain | P0 |
| `RecordingController` — Start/Stop + timer | P0 |
| REST recording endpoints | P0 |
| Unit-тесты recorder | P1 |

**Результат:** Вкладки Подключение, Поток, Съёмка работают через API.

---

## Фаза 3. Frontend MVP (2–3 недели)

| Задача | Приоритет |
|---|---|
| Vite + React + TypeScript scaffold | P0 |
| ConnectionPage | P0 |
| StreamPage + WebSocket | P0 |
| CapturePage | P0 |
| API client + TanStack Query | P0 |
| Общие компоненты (status, sliders) | P1 |

**Результат:** Полный цикл подключение → поток → запись.

---

## Фаза 4. HSI integration (зависит от build_csi)

| Задача | Приоритет |
|---|---|
| Submodule `build_csi` | P0 |
| Документировать фактический API | P0 |
| `HSIBuilderAdapter` | P0 |
| `BuildWorker` + progress WebSocket | P0 |
| `CalibrationLoader` | P0 |
| REST `/hsi/*` | P0 |
| BuildPage UI | P0 |
| Конвертер TIS RAW → вход buildHSI (если нужен) | P1 |

**Результат:** Запись → сборка HSI → файл на диске.

---

## Фаза 5. HSI Viewer + Export (2 недели)

| Задача | Приоритет |
|---|---|
| Band viewer API | P0 |
| Spectrum at point | P0 |
| RGB synthesis (ComplexData / simplified) | P0 |
| ViewerPage — zoom/pan | P0 |
| Export dialog (GeoTIFF, MAT, NPY, ...) | P0 |
| File download API | P1 |

**Результат:** Полное соответствие ТЗ v1.

---

## Фаза 6. Hardening (1–2 недели)

| Задача | Приоритет |
|---|---|
| E2E тесты | P1 |
| Docker compose | P2 |
| Логирование (structlog) | P1 |
| Обработка ошибок IC4 / build_csi | P0 |
| Документация OpenAPI | P1 |

---

## Вне scope v1 (архитектурно заложено)

| Функция | Интерфейс | Версия |
|---|---|---|
| Управление подвижкой | `IStageController` | v2 |
| Синхронизация скорости линии | `CaptureService.set_line_rate()` | v2 |
| Моторизованная платформа | `StageController` + hardware driver | v2 |
| Доп. алгоритмы обработки | плагины к `IHsiBuildService` | v2+ |
| gRPC между сервисами | `shared/proto/` | v2 |
| Аутентификация | middleware JWT | v2 |
| Удалённый capture-agent (macOS) | отдельный бинарник | v2 |

---

## Риски

| Риск | Митигация |
|---|---|
| `build_csi` недоступен | Mock adapter, параллельная разработка UI |
| TIS RAW не совместим с buildHSI | Конвертер-упаковщик, согласовать формат |
| IC4 не на macOS | UI dev на Mac, capture на Windows/Linux |
| USB2 вместо USB3 | Предупреждение в UI, ограничение FPS |
| Длительная сборка блокирует UI | Async worker + WebSocket progress |

---

## Критерии приёмки v1

1. Подключение камеры и отображение статуса
2. Live preview с настройкой exposure/gain
3. Запись Start/Stop с опциональным таймером
4. Сборка HSI из записи с progress bar
5. Просмотр каналов и спектра в точке
6. Цветосинтез через библиотеку
7. Экспорт минимум в 3 формата (HSI, TIFF, NPY)
8. Работа на Windows и Linux
