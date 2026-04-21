# tg-config

> **Manage Telegram Desktop settings via config files instead of the GUI!**

A utility for reading and writing **Telegram Desktop** settings directly into the `tdata/settings` binary format.

## Why do you need this?

### 🎨 For Ricers and Dotfiles Enthusiasts

- **Declarative Configuration** — keep all your Telegram settings in a single TOML file, just like the rest of your dotfiles.
- **Git Versioning** — store and sync your Telegram config along with your system configurations.
- **Automation** — apply settings automatically every time you launch Telegram.
- **Theming** — automatically apply `.tdesktop-theme` files.
- **Reproducibility** — quickly restore your preferred settings on a fresh OS installation.

### 💡 Use Cases

- Configure UI scale, auto-start, and "minimize to tray" behavior.
- Enable experimental features (e.g., showing Peer IDs).
- Apply custom themes on system startup.
- Sync settings between multiple machines via a dotfiles repository.
- Quickly toggle between light/dark modes using a script.

## Installation

### Arch Linux (AUR)

```bash
yay -S tg-config
# or
paru -S tg-config
```

After installation, Telegram will automatically run through a wrapper that applies settings from `~/.config/tg-config/config.toml` before each launch.

### From Source

```bash
# via uv (recommended)
uv sync
uv run tg-config

# or standard pip
pip install -e .
python -m tg_config
```

**For AUR package:** Settings are applied automatically when you start Telegram.  
**For manual installation:** Run `tg-config` manually or add it to your startup scripts.

## Usage

```bash
# List all settings
uv run tg-config

# List with descriptions
uv run tg-config -v

# Change a setting
uv run tg-config --set ScalePercent=150
uv run tg-config --set NightMode=1
uv run tg-config --set AutoStart=1 --set StartMinimized=1
uv run tg-config --set "PowerSaving+=AllAnimations"
uv run tg-config --set "PowerSaving-=AnimatedStickers"

# Experimental options (tdata/experimental_options.json)
uv run tg-config --set-exp show-peer-id-below-about=1
uv run tg-config --set-exp webview-debug-enabled=true
uv run tg-config --unset-exp webview-debug-enabled
uv run tg-config --exp-list

# Backup / Restore
uv run tg-config --export backup.json
uv run tg-config --import-file backup.json

# Diagnostics
uv run tg-config --dump-tail
uv run tg-config --deep-scan
uv run tg-config --schema-info

# Custom tdata path
uv run tg-config --tdata /path/to/tdata

# Offline mode (skips GitHub API requests)
uv run tg-config --offline
```

## Configuration

On startup, the utility looks for a TOML configuration file:

- Default location: `${XDG_CONFIG_HOME:-$HOME/.config}/tg-config/config.toml`
- Override path using the `--config /path/to/config.toml` flag.

Settings from the config file are applied first, followed by command-line arguments. This means CLI arguments always take priority.

### Supported `config.toml` Keys:

- `tdata` — String path to the Telegram Desktop `tdata` directory.
- `[settings]` — Section where each key maps to a setting name, and the value is a number/bool/string (equivalent to `--set Name=VALUE`).
- `[experimental]` — Section for experimental options (equivalent to `--set-exp key=BOOL`).
- `[theme]` — Section with a `path` key for auto-applying a `.tdesktop-theme` file.
  *Alternative short syntax:* `theme = "path/to/theme"`.
  **IMPORTANT:** Telegram Desktop must be closed when applying a theme!

### Example `~/.config/tg-config/config.toml`:

```toml
tdata = "/home/user/.local/share/TelegramDesktop/tdata"

[settings]
ScalePercent = 150
AutoStart = 0

[experimental]
show-peer-id-below-about = 1
webview-debug-enabled = true

[theme]
path = "~/themes/my-theme.tdesktop-theme"
```

*For a full commented example, see `config.example.toml`.*

## Project Structure

```text
tg_config/
├── __init__.py
├── __main__.py       # Entry point, argparse
├── crypto.py         # AES-IGE encrypt/decrypt
├── tdf.py            # TDF$ format + Qt serialization
├── schema.py         # Constants: DBI_SCHEMA, APP_SCHEMA, descriptions
├── schema_loader.py  # TG version detection, GitHub API, caching
├── scanner.py        # Binary stream scanner, raw_read/patch
├── formatter.py      # Value formatting, dump_all, diagnostics
├── editor.py         # apply_set, export/import JSON
├── experimental.py   # experimental_options.json handler
├── theme.py          # apply .tdesktop-theme files
└── io.py             # load/save tdata/settings
```

## Schema

The DBI-block schema is loaded dynamically from the Telegram Desktop source code for your specific version. It is cached in `~/.cache/tg-settings/schema_<version>.json`. If there is no internet connection, a built-in fallback is used.
