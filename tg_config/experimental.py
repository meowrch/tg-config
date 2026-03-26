"""
Helpers for Telegram Desktop experimental options JSON.
"""

import json
from pathlib import Path

from . import schema as _schema

_TRUE_VALUES  = {'1', 'true', 'yes', 'on', 'y'}
_FALSE_VALUES = {'0', 'false', 'no', 'off', 'n'}


def experimental_path(tdata: Path) -> Path:
    return tdata / 'experimental_options.json'


def parse_bool(text: str):
    value = text.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return None


def load_experimental(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            obj = json.load(f)
    except Exception as e:
        print(f'[!] Не удалось прочитать {path}: {e}')
        return {}

    if not isinstance(obj, dict):
        print(f'[!] {path}: ожидается JSON-объект')
        return {}

    result: dict[str, bool] = {}
    for key, value in obj.items():
        if isinstance(value, bool):
            result[key] = value
        elif isinstance(value, int) and value in (0, 1):
            result[key] = bool(value)
        else:
            print(f'[~] {key}: не-bool значение, пропущено')
    return result


def save_experimental(path: Path, options: dict[str, bool]):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: options[k] for k in sorted(options)}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
        f.write('\n')
    print(f'[✓] experimental options сохранены: {path}')


def dump_experimental(options: dict[str, bool]):
    print('\n experimental_options.json')
    print(f' {"Ключ":<45} {"Значение":<10} Статус')
    print(f' {"─"*45} {"─"*10} {"─"*20}')
    for key in _schema.EXPERIMENTAL_OPTIONS:
        if key in options:
            val = 'true' if options[key] else 'false'
            status = 'явно задано'
        else:
            val = 'false'
            status = 'по умолчанию'
        print(f' {key:<45} {val:<10} {status}')

    extras = sorted(k for k in options if k not in _schema.EXPERIMENTAL_OPTIONS)
    if extras:
        print('\n Доп. ключи (не из списка settings_experimental.cpp):')
        for key in extras:
            val = 'true' if options[key] else 'false'
            print(f'   {key} = {val}')
