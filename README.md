# tg-config

Чтение и запись настроек **Telegram Desktop** напрямую в бинарный формат `tdata/settings`.

## Установка

```bash
# через uv (рекомендуется)
uv sync
uv run tg-config

# или обычный pip
pip install -e .
python -m tg_config
```

## Использование

```bash
# Показать все настройки
uv run tg-config

# С описаниями
uv run tg-config -v

# Изменить настройку
uv run tg-config --set ScalePercent=150
uv run tg-config --set NightMode=1
uv run tg-config --set AutoStart=1 --set StartMinimized=1
uv run tg-config --set "PowerSaving+=AllAnimations"
uv run tg-config --set "PowerSaving-=AnimatedStickers"

# Бэкап / восстановление
uv run tg-config --export backup.json
uv run tg-config --import-file backup.json

# Диагностика
uv run tg-config --dump-tail
uv run tg-config --deep-scan
uv run tg-config --schema-info

# Кастомный путь к tdata
uv run tg-config --tdata /path/to/tdata

# Offline режим (без запросов к GitHub)
uv run tg-config --offline
```

## Структура проекта

```
tg_config/
├── __init__.py
├── __main__.py       # точка входа, argparse
├── crypto.py         # AES-IGE encrypt/decrypt
├── tdf.py            # TDF$ формат + Qt-сериализация
├── schema.py         # константы: DBI_SCHEMA, APP_SCHEMA, описания
├── schema_loader.py  # детект версии TG, GitHub API, кэш
├── scanner.py        # бинарный сканер потока, raw_read/patch
├── formatter.py      # fmt_value, dump_all, диагностика
├── editor.py         # apply_set, export/import JSON
└── io.py             # load/save tdata/settings
```

## Схема

Схема DBI-блоков загружается динамически из исходников tdesktop для конкретной версии TG.
Кэшируется в `~/.cache/tg-settings/schema_<version>.json`.
При отсутствии сети используется встроенный fallback.
