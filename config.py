import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Используем /tmp для хранения временных файлов (uploads, outputs, projects)
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
PROJECTS_FOLDER = '/tmp/projects'
FONTS_FOLDER = os.path.join(BASE_DIR, 'static', 'fonts')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Slide aspect ratios (width, height)
ASPECT_RATIOS = {
    '4:5': (1080, 1350),
    '1:1': (1080, 1080),
    '9:16': (1080, 1920)
}

# ==================== GRADIENT SETTINGS BY THEME MODE ====================
GRADIENT_PRESETS = {
    'dark': {
        'gradient_color': '#000000',
        'gradient_opacity': 92,
        'gradient_depth': 90,
        'gradient_position': 'bottom',
    },
    'light': {
        'gradient_color': '#ffffff',
        'gradient_opacity': 88,
        'gradient_depth': 85,
        'gradient_position': 'bottom',
    }
}

# ==================== FONT CONFIGURATION ====================
DEFAULT_FONTS = {
    'title': os.path.join(FONTS_FOLDER, 'Montserrat-Bold.ttf'),
    'title_fallback': os.path.join(FONTS_FOLDER, 'Inter-Bold.ttf'),
    'subtitle': os.path.join(FONTS_FOLDER, 'Montserrat-SemiBold.ttf'),
    'subtitle_fallback': os.path.join(FONTS_FOLDER, 'Inter-Bold.ttf'),
    'body': os.path.join(FONTS_FOLDER, 'Montserrat-Medium.ttf'),
    'body_fallback': os.path.join(FONTS_FOLDER, 'OpenSans-Regular.ttf'),
    'regular': os.path.join(FONTS_FOLDER, 'Montserrat-Regular.ttf'),
    'regular_fallback': os.path.join(FONTS_FOLDER, 'OpenSans-Regular.ttf'),
}

# Preview scale
PREVIEW_SCALE = 0.4

# Default slide settings
DEFAULT_SETTINGS = {
    'text_position': 'bottom',
    'text_align': 'left',
    'theme_mode': 'dark',
    'gradient_enabled': True,
    'title_size': 96,
    'subtitle_size': 52,
    'body_size': 32,
    'line_height': 1.25,
    'letter_spacing': -0.02,
    'paragraph_spacing': 1.2,
    'title_gap': 0.55,      # Gap between title and subtitle (as ratio of title_size)
    'subtitle_gap': 0.45,   # Gap between subtitle and body (as ratio of subtitle_size)
    'bg_opacity': 100,
    'bg_offset_x': 50,
    'bg_offset_y': 50,
    'bg_scale': 100,
    'text_offset_y': -100,
}