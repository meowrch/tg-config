"""
Динамическая загрузка DBI-схемы из исходников tdesktop
для конкретной версии Telegram Desktop.
"""

import re
import struct
import hashlib
import urllib.request
import urllib.error
import json
import os
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / '.cache' / 'tg-settings'


# ── Cache ────────────────────────────────────────────────────────────────

def _cache_path(version_str: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f'schema_{version_str}.json'


def _load_cache(version_str: str) -> Optional[dict]:
    p = _cache_path(version_str)
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(version_str: str, schema: dict):
    try:
        with open(_cache_path(version_str), 'w') as f:
            json.dump(schema, f, indent=2)
    except Exception:
        pass


# ── Version detection ────────────────────────────────────────────────────

def _find_telegram_binary() -> Optional[Path]:
    candidates = [
        Path('/usr/bin/telegram-desktop'),
        Path('/usr/local/bin/telegram-desktop'),
        Path.home() / '.local/bin/Telegram',
        Path.home() / '.local/share/TelegramDesktop/Telegram',
        Path('/opt/telegram/Telegram'),
        Path('/opt/Telegram/Telegram'),
        Path.home() / '.var/app/org.telegram.desktop/data/TelegramDesktop/Telegram',
    ]
    for p in candidates:
        if p.exists() and os.access(p, os.X_OK):
            return p
    import shutil
    for name in ('Telegram', 'telegram-desktop'):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def get_tg_version_from_binary(binary: Optional[Path] = None) -> Optional[str]:
    if binary is None:
        binary = _find_telegram_binary()
    if binary is None:
        return None
    try:
        data = binary.read_bytes()
        pattern = rb'(\d+\.\d+\.\d+(?:\.\d+)?)\x00'
        matches = re.findall(pattern, data)
        valid = []
        for m in matches:
            parts = m.decode().split('.')
            try:
                major = int(parts[0])
                if 1 <= major <= 19 and len(parts) in (3, 4):
                    valid.append(m.decode())
            except ValueError:
                continue
        if not valid:
            return None
        from collections import Counter
        return Counter(valid).most_common(1)[0][0]
    except Exception:
        return None


def get_tg_version_from_tdata(tdata: Path) -> Optional[str]:
    for suffix in ['s', '0', '1']:
        f = tdata / f'settings{suffix}'
        if not f.exists():
            continue
        try:
            raw = f.read_bytes()
            if raw[:4] != b'TDF$':
                continue
            ver_int = struct.unpack_from('<I', raw, 4)[0]
            if ver_int > 1000000:
                major = ver_int // 1000000
                rest  = ver_int % 1000000
                minor = rest // 1000
                patch = rest % 1000
                return f'{major}.{minor}.{patch}'
        except Exception:
            continue
    return None


# ── GitHub API ───────────────────────────────────────────────────────────

GITHUB_API = 'https://api.github.com'
REPO = 'telegramdesktop/tdesktop'


def _gh_get(url: str) -> Optional[dict | list]:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'tdesktop-settings-tool/1.0',
            'Accept': 'application/vnd.github.v3+json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print('[!] GitHub rate limit exceeded. Используем fallback схему.')
        return None
    except Exception as e:
        print(f'[!] GitHub API ошибка: {e}')
        return None


def find_git_tag(version_str: str) -> Optional[str]:
    for tag_fmt in [f'v{version_str}', version_str]:
        url = f'{GITHUB_API}/repos/{REPO}/git/refs/tags/{tag_fmt}'
        data = _gh_get(url)
        if data and 'ref' in data:
            return tag_fmt

    url = f'{GITHUB_API}/repos/{REPO}/tags?per_page=50'
    tags = _gh_get(url)
    if not tags:
        return None

    version_clean = version_str.lstrip('v')
    for tag in tags:
        name = tag.get('name', '').lstrip('v')
        if name == version_clean:
            return tag['name']

    parts = version_clean.split('.')
    if len(parts) >= 2:
        prefix = f"v{parts[0]}.{parts[1]}."
        for tag in tags:
            if tag.get('name', '').startswith(prefix):
                print(f'[~] Точный тег не найден, используем ближайший: {tag["name"]}')
                return tag['name']

    return None


def fetch_scheme_header(tag: str) -> Optional[str]:
    path = 'Telegram/SourceFiles/storage/details/storage_settings_scheme.h'
    url  = f'https://raw.githubusercontent.com/{REPO}/{tag}/{path}'
    req  = urllib.request.Request(url, headers={'User-Agent': 'tdesktop-settings-tool/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f'[!] Не удалось скачать схему: {e}')
        return None


# ── Enum parser ──────────────────────────────────────────────────────────

_NAME_TO_FMT_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'Key$'),             'u64'),
    (re.compile(r'Keys?$'),           'u64'),
    (re.compile(r'Authorization$'),   'ba'),
    (re.compile(r'Settings$'),        'ba'),
    (re.compile(r'Config$'),          'ba'),
    (re.compile(r'Options$'),         'ba'),
    (re.compile(r'Path$'),            'str'),
    (re.compile(r'ThemeKey$'),        'theme_key'),
    (re.compile(r'TileBackground$'),  'two_i32'),
    (re.compile(r'BackgroundKey$'),   'two_u64'),
    (re.compile(r'Percent$'),         'i32'),
    (re.compile(r'Volume$'),          'i32'),
    (re.compile(r'Speed$'),           'i32'),
    (re.compile(r'Saving$'),          'i32'),
    (re.compile(r'CacheSettings'),    'ba'),
]


def _guess_fmt(name: str) -> str:
    for pattern, fmt in _NAME_TO_FMT_HINTS:
        if pattern.search(name):
            return fmt
    return 'i32'


def parse_dbi_enum(header_src: str) -> dict[int, tuple[str, str]]:
    SKIP = {'dbiEncryptedWithSalt', 'dbiEncrypted', 'dbiVersion', 'dbiKey', 'dbiUser'}
    SKIP_SUFFIX = 'Old'

    enum_match = re.search(r'\benum\s*\{([^}]+)\}', header_src, re.DOTALL)
    if not enum_match:
        return {}

    enum_body = enum_match.group(1)
    schema: dict[int, tuple[str, str]] = {}
    current_val = 0

    for line in enum_body.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        line = re.sub(r'//.*', '', line).strip().rstrip(',').strip()
        if not line:
            continue

        m = re.match(r'(dbi\w+)\s*(?:=\s*(0[xX][0-9a-fA-F]+|\d+))?', line)
        if not m:
            continue

        raw_name = m.group(1)
        val_str  = m.group(2)

        if val_str is not None:
            current_val = int(val_str, 0)

        if raw_name in SKIP or raw_name.endswith(SKIP_SUFFIX):
            current_val += 1
            continue

        name = raw_name[3:]
        schema[current_val] = (name, _guess_fmt(name))
        current_val += 1

    return schema


# ── Fallback ─────────────────────────────────────────────────────────────

FALLBACK_SCHEMA: dict[int, tuple[str, str]] = {
    0x06: ('AutoStart',                'i32'),
    0x07: ('StartMinimized',           'i32'),
    0x0a: ('SeenTrayTooltip',          'i32'),
    0x0c: ('AutoUpdate',               'i32'),
    0x0d: ('LastUpdateCheck',          'i32'),
    0x1d: ('SendToMenu',               'i32'),
    0x23: ('DialogLastPath',           'str'),
    0x4b: ('MtpAuthorization',         'ba'),
    0x4d: ('SessionSettings',          'ba'),
    0x4e: ('LangPackKey',              'u64'),
    0x54: ('ThemeKey',                 'theme_key'),
    0x55: ('TileBackground',           'two_i32'),
    0x57: ('PowerSaving',              'i32'),
    0x58: ('ScalePercent',             'i32'),
    0x5a: ('LanguagesKey',             'u64'),
    0x5c: ('CacheSettings',            'ba'),
    0x5e: ('ApplicationSettings',      'ba'),
    0x60: ('FallbackProductionConfig', 'ba'),
    0x61: ('BackgroundKey',            'two_u64'),
}


# ── Public API ───────────────────────────────────────────────────────────

def load_schema(
    tdata: Optional[Path] = None,
    binary: Optional[Path] = None,
    force_version: Optional[str] = None,
    offline: bool = False,
) -> tuple[dict[int, tuple[str, str]], str]:
    """
    Загружает актуальную DBI-схему для установленной версии TG.
    Возвращает (schema_dict, version_str).
    """
    version = force_version

    if not version and tdata:
        version = get_tg_version_from_tdata(tdata)

    if not version:
        version = get_tg_version_from_binary(binary)

    if not version:
        print('[~] Версия TG не определена, используется fallback-схема')
        return FALLBACK_SCHEMA.copy(), 'unknown'

    print(f'[*] Версия TG: {version}')

    cached = _load_cache(version)
    if cached:
        schema = {int(k): tuple(v) for k, v in cached.items()}
        print(f'[*] Схема загружена из кэша ({len(schema)} блоков)')
        return schema, version

    if offline:
        print('[~] Offline режим, используется fallback-схема')
        return FALLBACK_SCHEMA.copy(), version

    print(f'[*] Загружаем схему с GitHub для v{version}...')
    tag = find_git_tag(version)
    if not tag:
        print(f'[!] Тег для v{version} не найден, используется fallback-схема')
        return FALLBACK_SCHEMA.copy(), version

    print(f'[*] Тег: {tag}')
    header_src = fetch_scheme_header(tag)
    if not header_src:
        print('[!] Не удалось скачать схему, используется fallback')
        return FALLBACK_SCHEMA.copy(), version

    schema = parse_dbi_enum(header_src)
    if not schema:
        print('[!] Не удалось распарсить enum, используется fallback')
        return FALLBACK_SCHEMA.copy(), version

    _save_cache(version, {str(k): list(v) for k, v in schema.items()})
    print(f'[✓] Схема загружена с GitHub: {len(schema)} блоков, кэш сохранён')
    return schema, version
