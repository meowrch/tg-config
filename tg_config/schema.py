"""
Static schema constants — DBI block IDs, descriptions, aliases, APP_SCHEMA.
The actual runtime schema is loaded dynamically via schema_loader.load_schema().
"""

# Populated at runtime by __main__ after load_schema()
DBI_SCHEMA: dict[int, tuple[str, str]] = {}

# Human-readable descriptions for --verbose mode
DBI_DESCRIPTION: dict[str, str] = {
    'AutoStart':            'Запуск с системой (0=выкл, 1=вкл)',
    'StartMinimized':       'Запуск свёрнутым в трей (0/1)',
    'SoundNotify':          'Звук уведомлений (0/1)',
    'WorkMode':             'Режим трея (0=окно, 1=трей, 2=окно+трей)',
    'SeenTrayTooltip':      'Подсказка о трее была показана (0/1)',
    'DesktopNotify':        'Десктопные уведомления (0/1)',
    'AutoUpdate':           'Автообновление (0/1)',
    'LastUpdateCheck':      'Unix-время последней проверки обновлений',
    'AskDownloadPath':      'Спрашивать путь при скачивании (0/1)',
    'SendToMenu':           'Пункт "Отправить в Telegram" в контекстном меню (0/1)',
    'CompressPastedImage':  'Сжимать вставленные изображения (0/1)',
    'NotifyView':           'Вид уведомлений (0=с текстом, 1=только имя, 2=ничего)',
    'BackgroundKey':        'Ключи файлов обоев {day, night}',
    'SavedGifsLimit':       'Лимит сохранённых GIF',
    'DownloadPath':         'Путь к папке загрузок',
    'DialogLastPath':       'Последняя папка в диалоге выбора файла',
    'TileBackground':       'Тайлить обои {day, night} (0/1)',
    'AutoPlayGif':          'Авто-воспроизведение GIF (0/1)',
    'StickersRecentLimit':  'Лимит недавних стикеров',
    'StickersFavedLimit':   'Лимит избранных стикеров',
    'AnimationsDisabled':   'Отключить анимации UI (0/1)',
    'ScalePercent':         'Масштаб UI: 0=авто, 100, 125, 150, 200, 300',
    'LangPackKey':          'Ключ файла языкового пакета',
    'LanguagesKey':         'Ключ файла списка языков',
    'ApplicationSettings':  'Основные настройки (Core::Settings blob)',
    'PowerSaving':          'Флаги энергосбережения (bitmask)',
    'ThemeKey':             'Ключи файлов тем {day, night, night_mode}',
    'ConnectionType':       'Настройки прокси (blob)',
    'DcOptions':            'MTP DC-опции (blob)',
}

POWER_SAVING_FLAGS: dict[int, str] = {
    0x001: 'AnimationsInChats',
    0x002: 'VideoInChats',
    0x004: 'AnimatedEmoji',
    0x008: 'AnimatedStickers',
    0x010: 'AnimatedBackground',
    0x020: 'AllAnimations',
}

# Sub-field aliases for --set
ALIASES: dict[str, tuple[str, str]] = {
    'NightMode':            ('ThemeKey',        'night_mode'),
    'ThemeKeyDay':          ('ThemeKey',        'day'),
    'ThemeKeyNight':        ('ThemeKey',        'night'),
    'TileBackgroundDay':    ('TileBackground',  'day'),
    'TileBackgroundNight':  ('TileBackground',  'night'),
}

# Schema for ApplicationSettings blob (Core::Settings)
APP_SCHEMA: dict[int, tuple[str, str]] = {
    0x01: ('DesktopNotify',             'i32'),
    0x02: ('NotifyView',                'i32'),
    0x03: ('NativeNotifications',       'i32'),
    0x04: ('NotificationsCount',        'i32'),
    0x05: ('NotificationsCorner',       'i32'),
    0x06: ('SoundNotify',               'i32'),
    0x07: ('IncludeMuted',              'i32'),
    0x08: ('CountUnreadMessages',       'i32'),
    0x0a: ('AutoDownloadPhoto',         'i32'),
    0x0b: ('AutoDownloadAudio',         'i32'),
    0x0c: ('AutoDownloadGif',           'i32'),
    0x0d: ('AutoPlayGif',               'i32'),
    0x0f: ('DialogsMode',               'i32'),
    0x11: ('SongVolume',                'i32'),
    0x12: ('VideoVolume',               'i32'),
    0x13: ('AskDownloadPath',           'i32'),
    0x14: ('DownloadPath',              'str'),
    0x15: ('CompressPastedImage',       'i32'),
    0x16: ('StickersFavedLimit',        'i32'),
    0x17: ('DialogLastPath',            'str'),
    0x1a: ('SendFilesWay',              'i32'),
    0x20: ('ThirdColumnWidth',          'i32'),
    0x21: ('ThirdSectionInfoEnabled',   'i32'),
    0x22: ('SmallDialogsList',          'i32'),
    0x23: ('ForwardQuoted',             'i32'),
    0x26: ('GroupCallPushToTalk',       'i32'),
    0x28: ('GroupCallPushToTalkDelay',  'i32'),
    0x2b: ('VoicePlaybackSpeed',        'i32'),
    0x30: ('TabbedPanelShowOnHover',    'i32'),
    0x33: ('DialogFilters',             'ba'),
    0x34: ('DialogFiltersEnabled',      'i32'),
    0x36: ('VoiceRecordBitrateKbps',    'i32'),
    0x37: ('VideoMessageQuality',       'i32'),
}

# Known keys from Telegram Desktop experimental_options.json
# (settings/settings_experimental.cpp + referenced option ids)
EXPERIMENTAL_OPTIONS: dict[str, str] = {
    'tabbed-panel-show-on-click':               'Показывать панель эмодзи/стикеров по клику',
    'forum-hide-chats-list':                    'Скрывать список чатов в форумах',
    'fractional-scaling-enabled':               'Точный fractional scaling',
    'high-dpi-downscale':                       'Альтернативный High-DPI downscale',
    'view-profile-in-chats-list-context-menu':  'Пункт “View Profile” в контекстном меню списка чатов',
    'show-peer-id-below-about':                 'Показывать Peer ID в профиле',
    'show-channel-joined-below-about':          'Показывать дату вступления в канал',
    'use-small-msg-bubble-radius':              'Малый радиус пузырей сообщений',
    'disable-autoplay-next':                    'Отключить autoplay следующего трека',
    'send-large-photos':                        'Отправлять фото с увеличенным лимитом стороны',
    'webview-debug-enabled':                    'Включить debug webview',
    'webview-legacy-edge':                      'Использовать legacy Edge webview',
    'auto-scroll-inactive-chat':                'Автопрокрутка/прочтение неактивного чата',
    'hide-reply-button':                        'Скрыть кнопку Reply в уведомлениях',
    'custom-notification':                      'Форсировать доступность non-native notifications',
    'gnotification':                            'Форсировать GLib GNotification',
    'freetype':                                 'Использовать FreeType font engine',
    'skip-url-scheme-register':                 'Пропустить регистрацию tg:// при обновлении',
    'deadlock-detector':                        'Включить детектор deadlock',
    'external-media-viewer':                    'Использовать внешний media viewer',
    'new-windows-size-as-first':                'Новые окна с размером первого окна',
    'prefer-ipv6':                              'Предпочитать IPv6',
    'fast-buttons-mode':                        'Режим быстрых кнопок (1-9)',
    'touchbar-disabled':                        'Отключить Touch Bar (macOS)',
    'alternative-scroll-processing':            'Legacy-обработка скролла в профилях',
    'moderate-common-groups':                   'Модерация сразу в нескольких группах',
    'force-compose-search-one-column':          'Форсировать встроенный поиск в one-column',
    'unlimited-recent-stickers':                'Безлимит недавних стикеров',
}
