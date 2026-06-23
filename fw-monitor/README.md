# fw-monitor (HSI subset)

Урезанная библиотека формирования и просмотра ГСИ для проекта **Baumer_App**.

Полное описание сохранённого функционала: [SCOPE.md](./SCOPE.md).

## Установка

```bash
cd fw-monitor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Основные классы

- `HSBuilder` — сборка гиперспектрального куба из video/images
- `BuildParams` / `load_build_metadata` — ROI, wavelengths, калибровка
- `HSImage` — хранение куба, экспорт MAT/NPY/TIFF/GeoTIFF/ENVI/DAT+HDR
- `ComplexedData` — комплекс HSI + RGB
- `hsi_to_rgb` — цветосинтез для просмотра

## Интеграция с Baumer_App

Сервис HSI (`services/hsi/`) оборачивает `HSBuilder` без изменения алгоритмов.  
См. `../docs/INTEGRATION_HSI.md`.
