
import os
import json
import random
import re
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import config
from themes import get_theme


def hex_to_rgba(hex_color, alpha=255):
    """Convert hex color to RGBA tuple."""
    if not hex_color or hex_color == '':
        return (0, 0, 0, alpha)
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    if len(hex_color) != 6:
        return (0, 0, 0, alpha)
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b, alpha)
    except:
        return (0, 0, 0, alpha)


def get_font(weight, size):
    """Get font with robust fallback chain supporting Cyrillic."""
    font_map = {
        'title': [
            config.DEFAULT_FONTS.get('title'),
            config.DEFAULT_FONTS.get('title_fallback'),
            config.DEFAULT_FONTS.get('subtitle'),
            config.DEFAULT_FONTS.get('subtitle_fallback'),
        ],
        'subtitle': [
            config.DEFAULT_FONTS.get('subtitle'),
            config.DEFAULT_FONTS.get('subtitle_fallback'),
            config.DEFAULT_FONTS.get('title'),
            config.DEFAULT_FONTS.get('title_fallback'),
        ],
        'body': [
            config.DEFAULT_FONTS.get('body'),
            config.DEFAULT_FONTS.get('body_fallback'),
            config.DEFAULT_FONTS.get('regular'),
            config.DEFAULT_FONTS.get('regular_fallback'),
        ],
        'regular': [
            config.DEFAULT_FONTS.get('regular'),
            config.DEFAULT_FONTS.get('regular_fallback'),
            config.DEFAULT_FONTS.get('body'),
            config.DEFAULT_FONTS.get('body_fallback'),
        ],
        'bold': [
            config.DEFAULT_FONTS.get('title'),
            config.DEFAULT_FONTS.get('title_fallback'),
            config.DEFAULT_FONTS.get('subtitle'),
            config.DEFAULT_FONTS.get('subtitle_fallback'),
        ],
        'medium': [
            config.DEFAULT_FONTS.get('subtitle'),
            config.DEFAULT_FONTS.get('subtitle_fallback'),
            config.DEFAULT_FONTS.get('body'),
            config.DEFAULT_FONTS.get('body_fallback'),
        ]
    }

    for path in font_map.get(weight, font_map['regular']):
        if path and os.path.exists(path):
            try:
                font = ImageFont.truetype(path, max(8, size))
                return font
            except Exception as e:
                print(f"[FONT] Failed to load font {path}: {e}")
                continue

    system_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]

    for path in system_fallbacks:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, max(8, size))
            except:
                continue

    print("[FONT] WARNING: Using default font - may not support Cyrillic!")
    return ImageFont.load_default()


def draw_gradient(draw, width, height, color, position, depth_percent):
    """Draw a smooth gradient overlay."""
    color_rgba = hex_to_rgba(color, 255)
    if position in ('bottom', 'top'):
        depth = max(1, int(height * depth_percent / 100))
    else:
        depth = max(1, int(width * depth_percent / 100))

    if position == 'bottom':
        for y in range(max(0, height - depth), height):
            alpha = int(255 * (y - (height - depth)) / depth) if depth > 0 else 255
            alpha = min(255, max(0, alpha))
            draw.line([(0, y), (width, y)], fill=(*color_rgba[:3], alpha))
    elif position == 'top':
        for y in range(0, min(depth, height)):
            alpha = int(255 * (depth - y) / depth) if depth > 0 else 255
            alpha = min(255, max(0, alpha))
            draw.line([(0, y), (width, y)], fill=(*color_rgba[:3], alpha))
    elif position == 'left':
        for x in range(0, min(depth, width)):
            alpha = int(255 * (depth - x) / depth) if depth > 0 else 255
            alpha = min(255, max(0, alpha))
            draw.line([(x, 0), (x, height)], fill=(*color_rgba[:3], alpha))
    elif position == 'right':
        for x in range(max(0, width - depth), width):
            alpha = int(255 * (x - (width - depth)) / depth) if depth > 0 else 255
            alpha = min(255, max(0, alpha))
            draw.line([(x, 0), (x, height)], fill=(*color_rgba[:3], alpha))


def get_text_width(draw, text, font, letter_spacing=0):
    """Get text width accounting for letter spacing."""
    if not text:
        return 0
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        base_width = bbox[2] - bbox[0]
    except:
        base_width = len(text) * (font.size if hasattr(font, 'size') else 32) * 0.6

    if letter_spacing != 0 and len(text) > 1:
        base_width += letter_spacing * (font.size if hasattr(font, 'size') else 32) * (len(text) - 1)

    return base_width


def wrap_text(text, font, max_width, draw, letter_spacing=0):
    """
    Wrap text to fit within max_width, accounting for letter spacing.
    """
    if not text:
        return []

    lines = []
    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        words = paragraph.split(' ')
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word]) if current_line else word
            text_width = get_text_width(draw, test_line, font, letter_spacing)

            if text_width <= max_width:
                current_line.append(word)
            else:
                if not current_line:
                    char_line = ""
                    for char in word:
                        test_char_line = char_line + char
                        char_width = get_text_width(draw, test_char_line, font, letter_spacing)
                        if char_width <= max_width:
                            char_line = test_char_line
                        else:
                            if char_line:
                                lines.append(char_line)
                            char_line = char
                    if char_line:
                        current_line = [char_line]
                    else:
                        current_line = []
                else:
                    lines.append(' '.join(current_line))
                    word_width = get_text_width(draw, word, font, letter_spacing)
                    if word_width <= max_width:
                        current_line = [word]
                    else:
                        char_line = ""
                        for char in word:
                            test_char_line = char_line + char
                            char_width = get_text_width(draw, test_char_line, font, letter_spacing)
                            if char_width <= max_width:
                                char_line = test_char_line
                            else:
                                if char_line:
                                    lines.append(char_line)
                                char_line = char
                        if char_line:
                            current_line = [char_line]
                        else:
                            current_line = []

        if current_line:
            lines.append(' '.join(current_line))

    return lines


# ==================== HIGHLIGHT RENDERING ====================

def split_highlight_segments(segments):
    """
    Process segments to ensure:
    - Highlight segments have NO leading/trailing spaces
    - Spaces are separate non-highlight segments
    - Consecutive highlight segments are merged into one
    """
    if not segments:
        return []

    result = []
    current_hl_text = None

    for seg in segments:
        text = seg['text']
        is_hl = seg.get('highlight', False)

        if not text:
            continue

        if is_hl:
            stripped = text.strip(' ')
            if stripped:
                if current_hl_text is None:
                    current_hl_text = stripped
                else:
                    current_hl_text += stripped
        else:
            if current_hl_text is not None:
                result.append({'text': current_hl_text, 'highlight': True})
                current_hl_text = None
            result.append(seg)

    if current_hl_text is not None:
        result.append({'text': current_hl_text, 'highlight': True})

    return result


def draw_text_with_highlight(draw, x, y, text_segments, font, text_color_rgba,
                             highlight_color='#3B82F6',
                             letter_spacing=0, scale=1.0, line_height=1.25,
                             bg_color_rgba=None):
    """
    Draw text with subtle highlight background.
    """
    if not text_segments:
        return x, y, 0

    segments = split_highlight_segments(text_segments)
    font_size = font.size if hasattr(font, 'size') else 32

    if bg_color_rgba is None:
        hl_r, hl_g, hl_b, _ = hex_to_rgba(highlight_color, 255)
        brightness = (hl_r * 299 + hl_g * 587 + hl_b * 114) / 1000
        if brightness > 128:
            highlight_text_color = (0, 0, 0, 255)
        else:
            highlight_text_color = (255, 255, 255, 255)
    else:
        highlight_text_color = bg_color_rgba

    corner_r = max(4, min(8, int(font_size * 0.08 * scale)))
    h_pad = max(3, int(font_size * 0.06 * scale))
    v_pad = max(2, int(font_size * 0.10 * scale))
    hl_height = font_size + 2 * v_pad

    segment_data = []
    current_x = x

    for segment in segments:
        seg_text = segment['text']
        is_highlight = segment.get('highlight', False)

        if not seg_text:
            continue

        seg_w = get_text_width(draw, seg_text, font, letter_spacing)

        try:
            bbox = draw.textbbox((current_x, y), seg_text, font=font)
            text_top = bbox[1]
            text_bottom = bbox[3]
            text_height = text_bottom - text_top
        except:
            text_top = y
            text_bottom = y + font_size
            text_height = font_size

        segment_data.append({
            'text': seg_text,
            'highlight': is_highlight,
            'x': current_x,
            'width': seg_w,
            'text_top': text_top,
            'text_bottom': text_bottom,
            'text_height': text_height,
        })

        current_x += seg_w

    if not segment_data:
        return x, y, 0

    min_text_top = min(s['text_top'] for s in segment_data)
    max_text_bottom = max(s['text_bottom'] for s in segment_data)
    line_center_y = (min_text_top + max_text_bottom) // 2

    highlight_rgba = hex_to_rgba(highlight_color, 255)

    for seg_data in segment_data:
        if seg_data['highlight'] and seg_data['text'].strip():
            rect_top = line_center_y - hl_height // 2
            rect_bottom = rect_top + hl_height
            rect_left = seg_data['x'] - h_pad
            rect_right = seg_data['x'] + seg_data['width'] + h_pad

            seg_width = rect_right - rect_left
            min_width = corner_r * 2 + 4
            if seg_width < min_width:
                extra = (min_width - seg_width) // 2
                rect_left -= extra
                rect_right += extra

            rect_left = max(0, rect_left)
            rect_top = max(0, rect_top)

            draw.rounded_rectangle(
                [(rect_left, rect_top), (rect_right, rect_bottom)],
                radius=corner_r,
                fill=highlight_rgba
            )

    for seg_data in segment_data:
        seg_text = seg_data['text']
        seg_x = seg_data['x']

        if seg_data['highlight']:
            seg_color = highlight_text_color
        else:
            seg_color = text_color_rgba

        if letter_spacing != 0:
            char_x = seg_x
            for char in seg_text:
                draw.text((char_x, y), char, font=font, fill=seg_color)
                char_w = get_text_width(draw, char, font, 0)
                char_x += char_w + letter_spacing * font_size
        else:
            draw.text((seg_x, y), seg_text, font=font, fill=seg_color)

    try:
        full_text = ''.join([s['text'] for s in text_segments])
        full_bbox = draw.textbbox((x, y), full_text, font=font)
        line_h = (full_bbox[3] - full_bbox[1]) * line_height
    except:
        line_h = font_size * line_height

    return current_x, y, line_h


def parse_highlight_segments(text, segments_data=None):
    """
    Parse text into segments with highlight info.
    If segments_data provided (from generator), use it.
    Otherwise parse ==text== markers from raw text.
    """
    if segments_data:
        return segments_data

    segments = []
    pattern = r'==(.*?)=='
    last_end = 0

    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            segments.append({'text': text[last_end:match.start()], 'highlight': False})
        segments.append({'text': match.group(1), 'highlight': True})
        last_end = match.end()

    if last_end < len(text):
        segments.append({'text': text[last_end:], 'highlight': False})

    if not segments:
        segments = [{'text': text, 'highlight': False}]

    return segments


def find_line_segments(line_text, full_text, segments):
    """
    FIXED: Find which segments from full_text appear in this line.
    Uses character-by-character matching instead of string.find() which fails on duplicates.
    """
    if not segments:
        return [{'text': line_text, 'highlight': False}]

    built_text = ''.join([s['text'] for s in segments])

    if built_text.strip() != full_text.strip():
        return [{'text': line_text, 'highlight': False}]

    char_list = []
    for seg in segments:
        for ch in seg['text']:
            char_list.append({'char': ch, 'highlight': seg.get('highlight', False)})

    line_start = full_text.find(line_text)
    if line_start == -1:
        stripped_line = line_text.strip()
        line_start = full_text.find(stripped_line)
        if line_start == -1:
            return [{'text': line_text, 'highlight': False}]

    line_end = line_start + len(line_text)
    line_chars = char_list[line_start:line_end]

    result = []
    if not line_chars:
        return [{'text': line_text, 'highlight': False}]

    current_group = {'text': line_chars[0]['char'], 'highlight': line_chars[0]['highlight']}

    for ch_info in line_chars[1:]:
        if ch_info['highlight'] == current_group['highlight']:
            current_group['text'] += ch_info['char']
        else:
            result.append(current_group)
            current_group = {'text': ch_info['char'], 'highlight': ch_info['highlight']}

    result.append(current_group)
    result = [r for r in result if r['text']]

    if not result:
        return [{'text': line_text, 'highlight': False}]

    return result


def calculate_text_block_height(title_lines, subtitle_lines, body_lines,
                                  title_font, subtitle_font, body_font,
                                  title_size, subtitle_size, body_size,
                                  line_height, paragraph_spacing,
                                  title_gap_ratio, subtitle_gap_ratio,
                                  draw, letter_spacing=0):
    """
    Calculate total text block height accurately.
    """
    def get_uniform_line_height(font, size, line_height_mult):
        font_size = font.size if hasattr(font, 'size') else size
        return font_size * line_height_mult

    title_line_h = get_uniform_line_height(title_font, title_size, line_height)
    subtitle_line_h = get_uniform_line_height(subtitle_font, subtitle_size, line_height)
    body_line_h = get_uniform_line_height(body_font, body_size, line_height)

    title_heights = [title_line_h] * len(title_lines)
    subtitle_heights = [subtitle_line_h] * len(subtitle_lines)
    body_heights = [body_line_h] * len(body_lines)

    total_height = sum(title_heights) + sum(subtitle_heights) + sum(body_heights)

    if title_lines and subtitle_lines:
        total_height += title_size * title_gap_ratio
    if (title_lines or subtitle_lines) and body_lines:
        total_height += subtitle_size * subtitle_gap_ratio * paragraph_spacing

    return total_height, title_heights, subtitle_heights, body_heights


def render_slide(project_id, slide_id, preview=False):
    """Render a single slide to an image."""
    print(f"[RENDER] project_id={project_id}, slide_id={slide_id}, preview={preview}")

    try:
        project_path = os.path.join(config.PROJECTS_FOLDER, f"{project_id}.json")

        if not os.path.exists(project_path):
            print(f"[RENDER] Project not found: {project_path}")
            return None

        with open(project_path, 'r', encoding='utf-8') as f:
            project = json.load(f)

        slides = project.get('slides', [])
        slide = next((s for s in slides if s.get('id') == slide_id), None)
        if not slide:
            print(f"[RENDER] Slide {slide_id} not found in project")
            return None

        print(f"[RENDER] Slide data: title=\"{slide.get('title', '')[:50]}...\" subtitle=\"{slide.get('subtitle', '')[:50]}...\" body=\"{slide.get('body', '')[:50]}...\"")

        settings = project.get('settings', {})
        aspect = settings.get('aspect_ratio', '4:5')

        if preview:
            scale = config.PREVIEW_SCALE
        else:
            scale = 1.0

        width, height = config.ASPECT_RATIOS.get(aspect, (1080, 1350))
        width = int(width * scale)
        height = int(height * scale)

        theme_mode = slide.get('theme_mode', 'dark')
        theme_name = slide.get('theme', 'Ocean')
        theme = get_theme(theme_name)
        colors = theme.get(theme_mode, theme.get('light'))

        bg_color = hex_to_rgba(colors['background'], 255)
        img = Image.new('RGBA', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # ==================== BACKGROUND IMAGE ====================
        bg_image_path = slide.get('background_image', '')
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                bg = Image.open(bg_image_path).convert('RGBA')

                bg_ratio = bg.width / bg.height
                target_ratio = width / height

                if bg_ratio > target_ratio:
                    new_height = bg.height
                    new_width = int(new_height * target_ratio)
                    left = (bg.width - new_width) // 2
                    bg = bg.crop((left, 0, left + new_width, new_height))
                else:
                    new_width = bg.width
                    new_height = int(new_width / target_ratio)
                    top = (bg.height - new_height) // 2
                    bg = bg.crop((0, top, new_width, top + new_height))

                bg = bg.resize((width, height), Image.LANCZOS)

                opacity = slide.get('bg_opacity', 100)
                if opacity < 100:
                    alpha = Image.new('L', (width, height), int(255 * opacity / 100))
                    bg.putalpha(alpha)

                img = Image.alpha_composite(img, bg)
                draw = ImageDraw.Draw(img)
                print(f"[RENDER] Background image loaded: {bg_image_path}")
            except Exception as e:
                print(f"[RENDER] Error loading background: {e}")

        # ==================== GRADIENT ====================
        if slide.get('gradient_enabled', True):
            gradient_preset = config.GRADIENT_PRESETS.get(theme_mode, config.GRADIENT_PRESETS['dark'])

            gradient_color = slide.get('gradient_color', '')
            if not gradient_color or gradient_color == '':
                gradient_color = gradient_preset['gradient_color']

            gradient_alpha = slide.get('gradient_opacity', -1)
            if gradient_alpha < 0:
                gradient_alpha = gradient_preset['gradient_opacity']

            gradient_pos = slide.get('gradient_position', '')
            if not gradient_pos:
                gradient_pos = gradient_preset['gradient_position']

            gradient_depth = slide.get('gradient_depth', -1)
            if gradient_depth < 0:
                gradient_depth = gradient_preset['gradient_depth']

            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            draw_gradient(overlay_draw, width, height, gradient_color, gradient_pos, gradient_depth)

            if gradient_alpha < 100:
                r, g, b, a = overlay.split()
                a = a.point(lambda x: int(x * gradient_alpha / 100))
                overlay = Image.merge('RGBA', (r, g, b, a))

            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

        # ==================== TEXT AREA ====================
        padding_x = int(width * 0.08)
        padding_y = int(height * 0.06)
        text_max_width = width - (padding_x * 2)
        text_max_width = int(text_max_width * 0.96)
        text_offset_y = int(slide.get('text_offset_y', 0) * scale)

        title_color = slide.get('title_color', '') or colors['title']
        subtitle_color = slide.get('subtitle_color', '') or colors['subtitle']
        body_color = slide.get('body_color', '') or colors['body']

        title_color_rgba = hex_to_rgba(title_color, 255)
        subtitle_color_rgba = hex_to_rgba(subtitle_color, 255)
        body_color_rgba = hex_to_rgba(body_color, 255)

        bg_color_rgba = hex_to_rgba(colors['background'], 255)

        title = slide.get('title', '')
        subtitle = slide.get('subtitle', '')
        body = slide.get('body', '')

        title_size = int(slide.get('title_size', 82) * scale)
        subtitle_size = int(slide.get('subtitle_size', 52) * scale)
        body_size = int(slide.get('body_size', 32) * scale)
        line_height = slide.get('line_height', 1.35)
        letter_spacing = slide.get('letter_spacing', -0.02)
        paragraph_spacing = slide.get('paragraph_spacing', 1.2)

        title_font = get_font('title', max(8, title_size))
        subtitle_font = get_font('subtitle', max(8, subtitle_size))
        body_font = get_font('body', max(8, body_size))

        highlight_color = slide.get('highlight_color', '') or colors.get('highlight', '#3B82F6')
        highlight_enabled = slide.get('highlight_enabled', True)

        title_segments = slide.get('title_segments', [])
        subtitle_segments = slide.get('subtitle_segments', [])
        body_segments = slide.get('body_segments', [])

        if not title_segments:
            title_segments = parse_highlight_segments(title)
        if not subtitle_segments:
            subtitle_segments = parse_highlight_segments(subtitle)
        if not body_segments:
            body_segments = parse_highlight_segments(body)

        title_lines = wrap_text(title, title_font, text_max_width, draw, letter_spacing)
        subtitle_lines = wrap_text(subtitle, subtitle_font, text_max_width, draw, letter_spacing)
        body_lines = wrap_text(body, body_font, text_max_width, draw, letter_spacing)

        print(f"[RENDER] Lines: title={len(title_lines)}, subtitle={len(subtitle_lines)}, body={len(body_lines)}")

        total_text_height, title_heights, subtitle_heights, body_heights = calculate_text_block_height(
            title_lines, subtitle_lines, body_lines,
            title_font, subtitle_font, body_font,
            title_size, subtitle_size, body_size,
            line_height, paragraph_spacing,
            slide.get('title_gap', 0.55), slide.get('subtitle_gap', 0.45),
            draw, letter_spacing
        )

        text_position = slide.get('text_position', 'bottom')

        if text_position == 'center':
            current_y = (height - total_text_height) // 2 + text_offset_y
        elif text_position == 'top':
            current_y = padding_y + text_offset_y
        else:
            current_y = height - total_text_height - padding_y + text_offset_y

        current_y = max(padding_y, current_y)
        if current_y + total_text_height > height - padding_y:
            current_y = height - padding_y - total_text_height
            current_y = max(padding_y, current_y)

        # ==================== DRAW TEXT ====================
        text_align = slide.get('text_align', 'left')

        def get_x(text_width, align, max_w, pad_x):
            if align == 'center':
                return (max_w - text_width) // 2 + pad_x
            elif align == 'right':
                return max_w - text_width - pad_x
            else:
                return pad_x

        # Draw title
        for i, line in enumerate(title_lines):
            line_h = title_heights[i]

            try:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_w = bbox[2] - bbox[0]
            except:
                text_w = len(line) * title_size * 0.6

            x = get_x(text_w, text_align, width, padding_x)

            if highlight_enabled and title_segments:
                line_segments = find_line_segments(line, title, title_segments)
                draw_text_with_highlight(
                    draw, x, current_y, line_segments, title_font,
                    title_color_rgba, highlight_color,
                    letter_spacing=letter_spacing, scale=scale,
                    line_height=line_height,
                    bg_color_rgba=bg_color_rgba
                )
            else:
                if letter_spacing != 0:
                    x_offset = 0
                    for char in line:
                        draw.text((x + x_offset, current_y), char, font=title_font, fill=title_color_rgba)
                        char_w = get_text_width(draw, char, title_font, 0)
                        x_offset += char_w + letter_spacing * title_size
                else:
                    draw.text((x, current_y), line, font=title_font, fill=title_color_rgba)

            current_y += line_h

        title_gap_ratio = slide.get('title_gap', 0.55)
        if title_lines and subtitle_lines:
            current_y += title_size * title_gap_ratio

        # Draw subtitle
        for i, line in enumerate(subtitle_lines):
            line_h = subtitle_heights[i]

            try:
                bbox = draw.textbbox((0, 0), line, font=subtitle_font)
                text_w = bbox[2] - bbox[0]
            except:
                text_w = len(line) * subtitle_size * 0.6

            x = get_x(text_w, text_align, width, padding_x)

            if highlight_enabled and subtitle_segments:
                line_segments = find_line_segments(line, subtitle, subtitle_segments)
                draw_text_with_highlight(
                    draw, x, current_y, line_segments, subtitle_font,
                    subtitle_color_rgba, highlight_color,
                    letter_spacing=letter_spacing, scale=scale,
                    line_height=line_height,
                    bg_color_rgba=bg_color_rgba
                )
            else:
                if letter_spacing != 0:
                    x_offset = 0
                    for char in line:
                        draw.text((x + x_offset, current_y), char, font=subtitle_font, fill=subtitle_color_rgba)
                        char_w = get_text_width(draw, char, subtitle_font, 0)
                        x_offset += char_w + letter_spacing * subtitle_size
                else:
                    draw.text((x, current_y), line, font=subtitle_font, fill=subtitle_color_rgba)

            current_y += line_h

        subtitle_gap_ratio = slide.get('subtitle_gap', 0.45)
        if (title_lines or subtitle_lines) and body_lines:
            current_y += subtitle_size * subtitle_gap_ratio * paragraph_spacing

        # Draw body
        for i, line in enumerate(body_lines):
            line_h = body_heights[i]

            try:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                text_w = bbox[2] - bbox[0]
            except:
                text_w = len(line) * body_size * 0.6

            x = get_x(text_w, text_align, width, padding_x)

            if highlight_enabled and body_segments:
                line_segments = find_line_segments(line, body, body_segments)
                draw_text_with_highlight(
                    draw, x, current_y, line_segments, body_font,
                    body_color_rgba, highlight_color,
                    letter_spacing=letter_spacing, scale=scale,
                    line_height=line_height,
                    bg_color_rgba=bg_color_rgba
                )
            else:
                if letter_spacing != 0:
                    x_offset = 0
                    for char in line:
                        draw.text((x + x_offset, current_y), char, font=body_font, fill=body_color_rgba)
                        char_w = get_text_width(draw, char, body_font, 0)
                        x_offset += char_w + letter_spacing * body_size
                else:
                    # BUGFIX: было draw.text((x, current_y), line, line, font=body_font, fill=body_color_rgba)
                    draw.text((x, current_y), line, font=body_font, fill=body_color_rgba)

            current_y += line_h

        # ==================== WATERMARK & SLIDE NUMBER ====================
        slide_settings = settings.get('slide_number', {})
        watermark = settings.get('watermark', {})

        linked_font_weight = 'subtitle'
        linked_font_size = max(8, int(subtitle_size * 0.55))
        linked_color = subtitle_color

        # --- Slide Number ---
        num_text = ""
        num_w, num_h = 0, 0
        num_font = None
        num_color_rgba = None

        if slide_settings.get('show', False):
            slide_num = slide.get('order', 0) + 1
            num_text = f"{slide_num}"
            num_font = get_font(linked_font_weight, max(8, linked_font_size))
            num_color_rgba = hex_to_rgba(linked_color, 255)

            try:
                bbox = draw.textbbox((0, 0), num_text, font=num_font)
                num_w = bbox[2] - bbox[0]
                num_h = bbox[3] - bbox[1]
            except:
                num_w = len(num_text) * linked_font_size * 0.6
                num_h = linked_font_size

        # --- Watermark ---
        wm_text = watermark.get('text', '')
        wm_w, wm_h = 0, 0
        wm_font = None
        wm_color_rgba = None

        if wm_text:
            wm_font = get_font(linked_font_weight, max(8, linked_font_size))
            wm_color_rgba = hex_to_rgba(linked_color, 200)

            try:
                bbox = draw.textbbox((0, 0), wm_text, font=wm_font)
                wm_w = bbox[2] - bbox[0]
                wm_h = bbox[3] - bbox[1]
            except:
                wm_w = len(wm_text) * linked_font_size * 0.6
                wm_h = linked_font_size

        # Same padding for both elements (same offset as slide number)
        num_pos = slide_settings.get('position', 'bottom-right')
        wm_pos = watermark.get('position', 'bottom-left')

        # Y coordinates: same baseline for elements on same vertical side
        bottom_y = height - padding_y - max(num_h, wm_h)
        top_y = padding_y

        def get_element_x(position, content_w):
            if 'left' in position:
                return padding_x
            else:  # right
                return width - padding_x - content_w

        def get_element_y(position):
            if 'bottom' in position:
                return bottom_y
            else:  # top
                return top_y

        # Draw watermark
        if wm_text:
            wm_x = get_element_x(wm_pos, wm_w)
            wm_y = get_element_y(wm_pos)
            draw.text((wm_x, wm_y), wm_text, font=wm_font, fill=wm_color_rgba)

        # Draw slide number
        if num_text:
            num_x = get_element_x(num_pos, num_w)
            num_y = get_element_y(num_pos)
            draw.text((num_x, num_y), num_text, font=num_font, fill=num_color_rgba)

        final_img = Image.new('RGB', (width, height), (255, 255, 255))
        final_img.paste(img, mask=img.split()[3])

        print(f"[RENDER] Слайд отрендерен успешно: {width}x{height}")
        return final_img

    except Exception as e:
        print(f"[RENDER] CRITICAL ERROR in render_slide: {e}")
        traceback.print_exc()
        return None


def export_project(project_id):
    """Export all slides as PNG images."""
    print(f"[EXPORT] Начинаю экспорт проекта: {project_id}")
    project_path = os.path.join(config.PROJECTS_FOLDER, f"{project_id}.json")

    if not os.path.exists(project_path):
        print(f"[EXPORT] Проект не найден: {project_path}")
        return []

    with open(project_path, 'r', encoding='utf-8') as f:
        project = json.load(f)

    output_files = []
    slides = project.get('slides', [])
    print(f"[EXPORT] В проекте {len(slides)} слайдов")

    for slide in slides:
        print(f"[EXPORT] Рендерю слайд {slide.get('order', 0)+1}, id={slide.get('id')}")
        img = render_slide(project_id, slide['id'], preview=False)
        if img:
            output_path = os.path.join(config.OUTPUT_FOLDER, f"{project_id}_slide_{slide['order'] + 1}.png")
            img.save(output_path, 'PNG', quality=95)
            output_files.append(output_path)
            print(f"[EXPORT] Сохранён: {output_path}")
        else:
            print(f"[EXPORT] ОШИБКА рендеринга слайда {slide.get('order', 0)+1}")

    print(f"[EXPORT] Итого экспортировано: {len(output_files)}/{len(slides)}")
    return output_files

