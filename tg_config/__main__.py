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
from .experimental import (
    experimental_path,
    parse_bool,
    load_experimental,
    save_experimental,
    dump_experimental,
)


def main():
    ap = argparse.ArgumentParser(
        description='Telegram Desktop settings reader/writer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # show all known settings
  %(prog)s -v                           # include field descriptions
  %(prog)s --dump-tail                  # inspect unparsed tail in stream
  %(prog)s --deep-scan                  # find all known IDs via bytes.find
  %(prog)s --set ScalePercent=150
  %(prog)s --set AutoStart=1 --set StartMinimized=1
  %(prog)s --set NightMode=1
  %(prog)s --set AnimationsDisabled=1
  %(prog)s --set "PowerSaving+=AllAnimations"
  %(prog)s --set "PowerSaving-=AnimatedStickers"
  %(prog)s --set-exp show-peer-id-below-about=1
  %(prog)s --unset-exp webview-debug-enabled
  %(prog)s --exp-list
  %(prog)s --app-settings
  %(prog)s --export backup.json
  %(prog)s --import-file backup.json
""")
    ap.add_argument('--tdata',          default=None,
                    help='path to Telegram Desktop tdata directory')
    ap.add_argument('--set',            action='append', metavar='KEY=VALUE',
                    help='set DBI setting value (can be used multiple times)')
    ap.add_argument('--set-exp',        action='append', metavar='KEY=BOOL',
                    help='set experimental option in experimental_options.json')
    ap.add_argument('--unset-exp',      action='append', metavar='KEY',
                    help='remove key from experimental_options.json')
    ap.add_argument('--exp-list',       action='store_true',
                    help='print known experimental options and current values')
    ap.add_argument('--export',         metavar='FILE',
                    help='export current known DBI settings to JSON')
    ap.add_argument('--import-file',    metavar='FILE', dest='import_file',
                    help='import DBI settings from JSON')
    ap.add_argument('--dump-tail',      action='store_true',
                    help='show parser stop offset and tail diagnostics')
    ap.add_argument('--deep-scan',      action='store_true',
                    help='scan for all known block IDs across full stream')
    ap.add_argument('--app-settings',   action='store_true',
                    help='decode and print ApplicationSettings blob')
    ap.add_argument('-v', '--verbose',  action='store_true',
                    help='include human-readable descriptions')
    ap.add_argument('--offline',        action='store_true',
                    help='skip GitHub schema fetch, use offline inference')
    ap.add_argument('--schema-version', default=None,
                    help='force Telegram version for schema lookup (e.g. 5.9.1)')
    ap.add_argument('--schema-info',    action='store_true',
                    help='print loaded DBI schema and exit')
    args = ap.parse_args()

    tdata = Path(args.tdata) if args.tdata else Path(
        os.environ.get('TDATA_PATH',
                       Path.home() / '.local/share/TelegramDesktop/tdata'))

    if not tdata.exists():
        print(f'[!] tdata не найдена: {tdata}')
        sys.exit(1)
    exp_modified = False
    exp_data: dict[str, bool] = {}
    exp_requested = bool(args.set_exp or args.unset_exp or args.exp_list)
    if exp_requested:
        exp_file = experimental_path(tdata)
        exp_data = load_experimental(exp_file)

        if args.set_exp:
            for kv in args.set_exp:
                if '=' not in kv:
                    print(f'[!] Формат --set-exp: KEY=BOOL (получено: {kv!r})')
                    continue
                key, raw_value = kv.split('=', 1)
                key = key.strip()
                parsed = parse_bool(raw_value)
                if parsed is None:
                    print(f'[!] {key}: BOOL должен быть 0/1/true/false/on/off/yes/no')
                    continue
                if key not in _schema.EXPERIMENTAL_OPTIONS:
                    print(f'[~] {key}: ключ не в известном списке, но будет сохранён')
                old = exp_data.get(key, None)
                exp_data[key] = parsed
                if old != parsed:
                    exp_modified = True
                print(f'[✓] experimental {key} = {str(parsed).lower()}')

        if args.unset_exp:
            for key in args.unset_exp:
                key = key.strip()
                if key in exp_data:
                    del exp_data[key]
                    exp_modified = True
                    print(f'[✓] experimental {key} удалён')
                else:
                    print(f'[~] experimental {key} отсутствует')

        if exp_modified:
            save_experimental(exp_file, exp_data)

        if args.exp_list:
            dump_experimental(exp_data)

    only_exp_actions = exp_requested and not any([
        args.set,
        args.export,
        args.import_file,
        args.dump_tail,
        args.deep_scan,
        args.app_settings,
        args.schema_info,
    ])
    if only_exp_actions:
        return

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
