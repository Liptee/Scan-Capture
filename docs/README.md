# Документация проекта HSI Web

Веб-интерфейс управления гиперспектральной системой съёмки и обработки.

## Содержание

| Документ | Описание |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Общая архитектура системы, сервисы, потоки данных |
| [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) | Структура каталогов и модулей репозитория |
| [API.md](./API.md) | REST / WebSocket API веб-сервиса |
| [SERVICES.md](./SERVICES.md) | Детальное описание сервисов съёмки и сборки HSI |
| [FRONTEND.md](./FRONTEND.md) | Вкладки UI, состояния, взаимодействие с API |
| [DATA_MODELS.md](./DATA_MODELS.md) | Форматы файлов, хранение, калибровка |
| [INTEGRATION_HSI.md](./INTEGRATION_HSI.md) | Интеграция с `build_csi` / `HSIBuilder` |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Развёртывание, зависимости, платформы |
| [ROADMAP.md](./ROADMAP.md) | Этапы реализации и будущие расширения |

## Текущее состояние репозитория

| Компонент | Статус |
|---|---|
| Модуль камеры `tis_camera/` | Реализован (CLI, RAW-захват) |
| Сервис съёмки | Запланирован |
| Сервис сборки HSI | Запланирован (требует `build_csi`) |
| Веб-API (FastAPI) | Запланирован |
| Frontend | Запланирован |

## Быстрый старт (только камера, CLI)

```bash
python list_modes.py --offline
python capture_raw.py --mode 2048x1536@30 --duration 5 --exposure 10000 --output data/recordings/test.raw
```

Полный веб-стек описан в [DEPLOYMENT.md](./DEPLOYMENT.md).
