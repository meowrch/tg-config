"""
Theme management — apply .tdesktop-theme files.
Based on the proven method from tdesktop-theme-apply-v6.py
"""

import secrets
import shutil
import struct
import subprocess
from pathlib import Path

from .crypto import decrypt_local, derive_key, encrypt_local
from .tdf import _qt_ba, _qt_str, _read_qt_ba, _read_qt_str, read_tdf, write_tdf


def _to_file_part(key: int) -> str:
    """Convert 64-bit key to hex filename (16 chars, reversed nibbles)."""
    result = []
    for _ in range(16):
        v = key & 0x0F
        result.append(chr(ord("0") + v) if v < 10 else chr(ord("A") + v - 10))
        key >>= 4
    return "".join(result)


def _generate_key(tdata: Path) -> int:
    """Generate a new unique theme file key."""
    while True:
        key = secrets.randbits(64)
        if not key:
            continue
        if not any(
            Path(str(tdata / _to_file_part(key)) + s).exists() for s in ["s", "0", "1"]
        ):
            return key


def _read_theme_file_raw(tdata: Path, key: int, auth_key: bytes) -> bytes | None:
    """Read existing theme file and return raw inner bytes."""
    fname = Path(str(tdata / _to_file_part(key)) + "s")
    if not fname.exists():
        return None
    raw = fname.read_bytes()
    if raw[:4] != b"TDF$":
        return None
    payload = raw[8:-16]
    enc, _ = _read_qt_ba(payload, 0)
    try:
        return decrypt_local(enc, auth_key)
    except Exception:
        return None


def _write_theme_file(
    tdata: Path,
    key: int,
    content: bytes,
    path_abs: str,
    path_rel: str,
    auth_key: bytes,
    version: int,
):
    """Write theme file, preserving existing suffix data if available."""
    # Read existing inner to preserve fields after path_rel
    old_inner = _read_theme_file_raw(tdata, key, auth_key)

    suffix_bytes = b""
    if old_inner:
        # Parse old inner and take everything after path_rel
        p = 0
        _, p = _read_qt_ba(old_inner, p)  # content — skip
        _, p = _read_qt_str(old_inner, p)  # tag
        _, p = _read_qt_str(old_inner, p)  # path_abs
        _, p = _read_qt_str(old_inner, p)  # path_rel
        suffix_bytes = old_inner[p:]  # ← copy all the rest as-is!
        print(f"[*] Preserved suffix from old file: {len(suffix_bytes)}B")
    else:
        # No old file — write zeros (first time)
        suffix_bytes = struct.pack(">QQ", 0, 0)  # bg ids
        suffix_bytes += _qt_str("")  # bg slug 1
        suffix_bytes += _qt_str("")  # bg slug 2
        suffix_bytes += struct.pack(">Q", 0)
        suffix_bytes += struct.pack(">i", 0)
        suffix_bytes += struct.pack(">ii", 0, 0)
        suffix_bytes += _qt_ba(None)
        suffix_bytes += _qt_ba(None)
        suffix_bytes += struct.pack(">I", 0)

    inner = _qt_ba(content)
    inner += _qt_str("special://new_tag")
    inner += _qt_str(path_abs)
    inner += _qt_str(path_rel)
    inner += suffix_bytes  # ← preserve original fields

    encrypted = _qt_ba(encrypt_local(inner, auth_key))
    write_tdf(tdata / _to_file_part(key), encrypted, version)
    print(
        f"[✓] Theme file written: {_to_file_part(key)}s ({len(inner)}B inner)"
    )


def apply_theme(theme_path: Path, tdata: Path, night: bool = False) -> bool:
    """Apply a .tdesktop-theme file by overwriting the existing theme file.

    This is the ONLY method that reliably works without user interaction.
    It reads the current theme key from settings and overwrites that file.

    Args:
        theme_path: Path to .tdesktop-theme file
        tdata: Path to Telegram Desktop tdata directory
        night: If True, apply as night theme; otherwise day theme

    Returns:
        True if successful
    """
    if not theme_path.exists():
        print(f"[!] Theme file not found: {theme_path}")
        return False

    if theme_path.suffix != ".tdesktop-theme":
        print(f"[!] Theme file must have .tdesktop-theme extension: {theme_path}")
        return False

    if not tdata.exists():
        print(f"[!] tdata not found: {tdata}")
        return False

    # Check if Telegram Desktop is running
    if subprocess.run(
        ["pgrep", "-xi", "telegram-desktop"], capture_output=True
    ).returncode == 0:
        print("[!] Close Telegram Desktop before applying theme")
        return False

    # ── Read settings ─────────────────────────────────────────────────────
    try:
        payload, version = read_tdf(tdata / "settings")
        salt, pos = _read_qt_ba(payload, 0)
        enc_raw, _ = _read_qt_ba(payload, pos)
        auth_key = derive_key(salt)

        print(f"[*] TDF version: {version}")
        print(f"[*] Salt: {salt[:8].hex()}...")

        data = decrypt_local(enc_raw, auth_key)
        print(f"[✓] Decrypted settings: {len(data)} bytes")
    except Exception as e:
        print(f"[!] Failed to read settings: {e}")
        return False

    # ── Read current dbiThemeKey ──────────────────────────────────────────
    dbi_theme_key = 0x54
    off = data.find(struct.pack(">I", dbi_theme_key))
    kd = kn = 0
    nm = False
    if off != -1:
        kd, kn = struct.unpack_from(">QQ", data, off + 4)
        nm = bool(struct.unpack_from(">I", data, off + 20)[0])
        print(f"[*] day=0x{kd:016X}  night=0x{kn:016X}  night_mode={nm}")
    else:
        print("[!] dbiThemeKey not found in settings — theme was never applied")

    # ── Determine target key ──────────────────────────────────────────────
    # v6: DO NOT create new key — overwrite existing file
    # Telegram manages keys in settings; we only need to update the file
    target_key = kn if nm else kd

    if target_key == 0:
        # No key yet — create new one and write to settings
        target_key = _generate_key(tdata)
        print(f"[*] Key not found, creating new: 0x{target_key:016X}")
        new_kd = target_key if not nm else kd
        new_kn = target_key if nm else kn
        # Patch settings
        buf = bytearray(data)
        if off != -1:
            struct.pack_into(">Q", buf, off + 4, new_kd)
            struct.pack_into(">Q", buf, off + 12, new_kn)
        else:
            extra = struct.pack(">I", dbi_theme_key)
            extra += struct.pack(">QQ", new_kd, new_kn)
            extra += struct.pack(">I", 1 if nm else 0)
            buf += extra
        # Backup settings
        for s in ["s", "0", "1"]:
            p = tdata / f"settings{s}"
            if p.exists():
                shutil.copy2(p, tdata / f"settings.bak.{s}")
        enc2 = encrypt_local(bytes(buf), auth_key)
        write_tdf(tdata / "settings", _qt_ba(salt) + _qt_ba(enc2), version)
        print("[✓] settings updated")
    else:
        print(
            f"[*] Overwriting existing key: 0x{target_key:016X} → {_to_file_part(target_key)}s"
        )

    # ── Write theme file ──────────────────────────────────────────────────
    content = theme_path.read_bytes()
    path_abs = str(theme_path.resolve())
    path_rel = str(theme_path)

    _write_theme_file(tdata, target_key, content, path_abs, path_rel, auth_key, version)

    print(f"\n[✓] Done! Launch Telegram Desktop.")
    print(f"    Theme: {theme_path.name}")
    print(f"    Key: 0x{target_key:016X} ({'night' if nm else 'day'})")

    return True
