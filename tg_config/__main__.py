#!/usr/bin/env python3
"""
tg-config — Telegram Desktop settings reader/writer.
Entry point (uv run tg-config  /  python -m tg_config).
"""

import sys
import os
import argparse
from pathlib import Path

from . import schema as _schema
from .schema_loader import load_schema
from .scanner import get_positions, raw_read
from .formatter import dump_all, dump_app_settings, dump_tail_info, deep_scan_diagnostic
from .editor import apply_set, export_json, import_json
from .io import load, save


def main():
    ap = argparse.ArgumentParser(
        description='Telegram Desktop settings reader/writer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                              # показать все настройки
  %(prog)s -v                           # с описаниями
  %(prog)s --dump-tail                  # диагностика хвоста
  %(prog)s --deep-scan                  # все вхождения через bytes.find
  %(prog)s --set ScalePercent=150
  %(prog)s --set AutoStart=1 --set StartMinimized=1
  %(prog)s --set NightMode=1
  %(prog)s --set AnimationsDisabled=1
  %(prog)s --set "PowerSaving+=AllAnimations"
  %(prog)s --set "PowerSaving-=AnimatedStickers"
  %(prog)s --app-settings
  %(prog)s --export backup.json
  %(prog)s --import-file backup.json
""")
    ap.add_argument('--tdata',          default=None)
    ap.add_argument('--set',            action='append', metavar='KEY=VALUE')
    ap.add_argument('--export',         metavar='FILE')
    ap.add_argument('--import-file',    metavar='FILE', dest='import_file')
    ap.add_argument('--dump-tail',      action='store_true')
    ap.add_argument('--deep-scan',      action='store_true')
    ap.add_argument('--app-settings',   action='store_true')
    ap.add_argument('-v', '--verbose',  action='store_true')
    ap.add_argument('--offline',        action='store_true',
                    help='не обращаться к GitHub, использовать fallback-схему')
    ap.add_argument('--schema-version', default=None,
                    help='принудительно задать версию TG (напр. 5.9.1)')
    ap.add_argument('--schema-info',    action='store_true',
                    help='показать загруженную схему и выйти')
    args = ap.parse_args()

    tdata = Path(args.tdata) if args.tdata else Path(
        os.environ.get('TDATA_PATH',
                       Path.home() / '.local/share/TelegramDesktop/tdata'))

    if not tdata.exists():
        print(f'[!] tdata не найдена: {tdata}')
        sys.exit(1)

    # ── Load schema ──────────────────────────────────────────────────────
    _schema.DBI_SCHEMA, tg_version = load_schema(
        tdata=tdata,
        force_version=args.schema_version,
        offline=args.offline,
    )

    if args.schema_info:
        print(f'\n Схема для TG v{tg_version} ({len(_schema.DBI_SCHEMA)} блоков)\n')
        for bid, (name, fmt) in sorted(_schema.DBI_SCHEMA.items()):
            print(f'  0x{bid:04X}  {name:<35} {fmt}')
        return

    # ── Read settings ─────────────────────────────────────────────────────
    print(f'[*] tdata: {tdata}')
    raw_data, salt, auth_key, version = load(tdata)
    seq_pos = get_positions(raw_data)
    print(f'[*] TG версия: {tg_version} | TDF версия: {version} | Salt: {salt[:8].hex()}...')
    print(f'[*] Sequential: {len(seq_pos)} блоков | Размер потока: {len(raw_data)} байт')

    if args.deep_scan:
        deep_scan_diagnostic(raw_data)
        return

    if args.dump_tail:
        dump_tail_info(raw_data)
        return

    modified = False

    if args.import_file:
        ip = Path(args.import_file)
        if not ip.exists():
            print(f'[!] Файл не найден: {ip}')
            sys.exit(1)
        raw_data = import_json(raw_data, ip)
        modified = True

    if args.set:
        for kv in args.set:
            if '+=' in kv or ('-=' in kv and not kv.startswith('-')):
                k, v = kv, ''
            elif '=' not in kv:
                print(f'[!] Формат: KEY=VALUE (получено: {kv!r})')
                continue
            else:
                k, v = kv.split('=', 1)
                k, v = k.strip(), v.strip()
            prev     = raw_data
            raw_data = apply_set(raw_data, k, v)
            if raw_data is not prev:
                modified = True

    if modified:
        save(tdata, raw_data, salt, auth_key, version)

    if args.export:
        export_json(raw_data, Path(args.export))

    dump_all(raw_data, verbose=args.verbose)

    if args.app_settings:
        blob = raw_read(raw_data, _schema.DBI_SCHEMA.get(
            next((k for k, v in _schema.DBI_SCHEMA.items() if v[0] == 'ApplicationSettings'), None)
        ))
        if blob:
            dump_app_settings(blob, verbose=args.verbose)
        else:
            print('[*] ApplicationSettings не найден')


if __name__ == '__main__':
    main()
