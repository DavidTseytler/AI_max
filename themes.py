# # themes.py - Theme definitions with highlight/accent colors
#
# THEMES = {
#     'Ocean': {
#         'light': {
#             'background': '#F0F4F8',
#             'title': '#0A1428',
#             'subtitle': '#1D3461',
#             'body': '#4A5568',
#             'highlight': '#3B82F6',  # Blue accent
#         },
#         'dark': {
#             'background': '#0A1428',
#             'title': '#FFFFFF',
#             'subtitle': '#93C5FD',
#             'body': '#CBD5E1',
#             'highlight': '#3B82F6',  # Blue accent
#         }
#     },
#     'Sunset': {
#         'light': {
#             'background': '#FFF5F0',
#             'title': '#2D1810',
#             'subtitle': '#9A3412',
#             'body': '#78716C',
#             'highlight': '#F97316',  # Orange accent
#         },
#         'dark': {
#             'background': '#1C1917',
#             'title': '#FFFFFF',
#             'subtitle': '#FDBA74',
#             'body': '#D6D3D1',
#             'highlight': '#F97316',  # Orange accent
#         }
#     },
#     'Forest': {
#         'light': {
#             'background': '#F0FDF4',
#             'title': '#052E16',
#             'subtitle': '#166534',
#             'body': '#57534E',
#             'highlight': '#22C55E',  # Green accent
#         },
#         'dark': {
#             'background': '#052E16',
#             'title': '#FFFFFF',
#             'subtitle': '#86EFAC',
#             'body': '#D6D3D1',
#             'highlight': '#22C55E',  # Green accent
#         }
#     },
#     'Berry': {
#         'light': {
#             'background': '#FDF2F8',
#             'title': '#500724',
#             'subtitle': '#BE185D',
#             'body': '#78716C',
#             'highlight': '#EC4899',  # Pink accent
#         },
#         'dark': {
#             'background': '#500724',
#             'title': '#FFFFFF',
#             'subtitle': '#F9A8D4',
#             'body': '#D6D3D1',
#             'highlight': '#EC4899',  # Pink accent
#         }
#     },
#     'Gold': {
#         'light': {
#             'background': '#FFFBEB',
#             'title': '#451A03',
#             'subtitle': '#B45309',
#             'body': '#78716C',
#             'highlight': '#EAB308',  # Yellow accent
#         },
#         'dark': {
#             'background': '#451A03',
#             'title': '#FFFFFF',
#             'subtitle': '#FCD34D',
#             'body': '#D6D3D1',
#             'highlight': '#EAB308',  # Yellow accent
#         }
#     },
#     'Cobalt': {
#         'light': {
#             'background': '#F8FAFD',
#             'title': '#0A1428',
#             'subtitle': '#1D4ED8',
#             'body': '#4B5563',
#             'highlight': '#1D4ED8',  # Deep blue accent (like competitor)
#         },
#         'dark': {
#             'background': '#0A1428',
#             'title': '#F8FAFD',
#             'subtitle': '#60A5FA',
#             'body': '#9CA3AF',
#             'highlight': '#3B82F6',  # Blue accent
#         }
#     },
#     'Mint': {
#         'light': {
#             'background': '#F0FDFA',
#             'title': '#042F2E',
#             'subtitle': '#0F766E',
#             'body': '#57534E',
#             'highlight': '#14B8A6',  # Teal accent
#         },
#         'dark': {
#             'background': '#042F2E',
#             'title': '#FFFFFF',
#             'subtitle': '#5EEAD4',
#             'body': '#D6D3D1',
#             'highlight': '#14B8A6',  # Teal accent
#         }
#     },
#     'Lavender': {
#         'light': {
#             'background': '#FAF5FF',
#             'title': '#3B0764',
#             'subtitle': '#7C3AED',
#             'body': '#78716C',
#             'highlight': '#8B5CF6',  # Purple accent
#         },
#         'dark': {
#             'background': '#3B0764',
#             'title': '#FFFFFF',
#             'subtitle': '#C4B5FD',
#             'body': '#D6D3D1',
#             'highlight': '#8B5CF6',  # Purple accent
#         }
#     },
# }
#
#
# def get_theme(name):
#     """Get theme by name, return Ocean as default."""
#     return THEMES.get(name, THEMES['Ocean'])
# themes.py
# Структура тем для каруселей
# Каждая тема имеет light и dark режимы
# Поля:
#   title       — Основной цвет (заголовок)
#   subtitle    — Цвет подзаголовка
#   body        — Цвет основного текста
#   background  — Фон слайда
#   highlight   — Доп. цвет (выделение триггерных слов)

THEMES = {
    "Ocean": {
        "light": {
            "title": "#0A1428",
            "subtitle": "#1E3A5F",
            "body": "#111111",
            "background": "#F8FAFD",
            "highlight": "#1D4ED8",
        },
        "dark": {
            "title": "#F8FAFD",
            "subtitle": "#BFDBFE",
            "body": "#FFFFFF",
            "background": "#0A1428",
            "highlight": "#60A5FA",
        }
    },
    "Sunset": {
        "light": {
            "title": "#7C2D12",
            "subtitle": "#9A3412",
            "body": "#111111",
            "background": "#FFF7ED",
            "highlight": "#EA580C",
        },
        "dark": {
            "title": "#FFF7ED",
            "subtitle": "#FDBA74",
            "body": "#FFFFFF",
            "background": "#7C2D12",
            "highlight": "#FB923C",
        }
    },
    "Forest": {
        "light": {
            "title": "#064E3B",
            "subtitle": "#065F46",
            "body": "#111111",
            "background": "#ECFDF5",
            "highlight": "#059669",
        },
        "dark": {
            "title": "#ECFDF5",
            "subtitle": "#A7F3D0",
            "body": "#FFFFFF",
            "background": "#064E3B",
            "highlight": "#34D399",
        }
    },
    "Berry": {
        "light": {
            "title": "#581C87",
            "subtitle": "#6B21A8",
            "body": "#111111",
            "background": "#FAF5FF",
            "highlight": "#9333EA",
        },
        "dark": {
            "title": "#FAF5FF",
            "subtitle": "#E9D5FF",
            "body": "#FFFFFF",
            "background": "#581C87",
            "highlight": "#C084FC",
        }
    },
    "Monochrome": {
        "light": {
            "title": "#111111",
            "subtitle": "#333333",
            "body": "#111111",
            "background": "#F5F5F5",
            "highlight": "#2563EB",
        },
        "dark": {
            "title": "#F5F5F5",
            "subtitle": "#D4D4D4",
            "body": "#FFFFFF",
            "background": "#111111",
            "highlight": "#60A5FA",
        }
    },
    "Gold": {
        "light": {
            "title": "#422006",
            "subtitle": "#713F12",
            "body": "#111111",
            "background": "#FFFBEB",
            "highlight": "#B45309",
        },
        "dark": {
            "title": "#FFFBEB",
            "subtitle": "#FDE68A",
            "body": "#FFFFFF",
            "background": "#422006",
            "highlight": "#FBBF24",
        }
    },
}


def get_theme(name):
    """Возвращает тему по имени. Если не найдена — возвращает Ocean."""
    return THEMES.get(name, THEMES["Ocean"])


def get_theme_names():
    """Возвращает список имён тем."""
    return list(THEMES.keys())