
import os
import json
import uuid
import zipfile
import random
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename

import config
from image_processor import render_slide, export_project
from text_generator import generate_carousel_text
from themes import THEMES

BASE_DIR = config.BASE_DIR

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.secret_key = 'carousel-maker-secret-key'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def get_project(project_id):
    project_path = os.path.join(config.PROJECTS_FOLDER, f"{project_id}.json")
    if os.path.exists(project_path):
        with open(project_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_project(project):
    project_path = os.path.join(config.PROJECTS_FOLDER, f"{project['id']}.json")
    with open(project_path, 'w', encoding='utf-8') as f:
        json.dump(project, f, ensure_ascii=False, indent=2)


def get_random_theme_mode():
    return random.choice(['dark', 'light'])


def get_gradient_for_mode(mode):
    return config.GRADIENT_PRESETS.get(mode, config.GRADIENT_PRESETS['dark'])


def create_default_slide(order=0):
    theme_mode = get_random_theme_mode()
    gradient = get_gradient_for_mode(theme_mode)

    return {
        'id': str(uuid.uuid4()),
        'order': order,
        'title': '',
        'subtitle': '',
        'body': '',
        'text_color': '',
        'title_color': '',
        'subtitle_color': '',
        'body_color': '',
        'text_position': 'bottom',
        'text_align': 'left',
        'title_size': 96,
        'subtitle_size': 52,
        'body_size': 32,
        'line_height': 1.25,
        'letter_spacing': -0.02,
        'paragraph_spacing': 1.2,
        'title_gap': 0.55,
        'subtitle_gap': 0.45,
        'background_image': '',
        'bg_opacity': 100,
        'bg_offset_x': 50,
        'bg_offset_y': 50,
        'bg_scale': 100,
        'gradient_enabled': True,
        'gradient_color': gradient['gradient_color'],
        'gradient_opacity': gradient['gradient_opacity'],
        'gradient_position': gradient['gradient_position'],
        'gradient_depth': gradient['gradient_depth'],
        'theme': 'Ocean',
        'theme_mode': theme_mode,
        'text_offset_y': -100,
        # === NEW: Highlight fields ===
        'highlight_color': '#3B82F6',
        'highlight_enabled': True,
        'title_segments': [],
        'subtitle_segments': [],
        'body_segments': [],
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create_project', methods=['POST'])
def create_project():
    topic = request.form.get('topic', 'Новый проект')
    article_text = request.form.get('article_text', '')
    num_slides = int(request.form.get('num_slides', 5))

    project_id = str(uuid.uuid4())
    generated = generate_carousel_text(article_text, num_slides)

    slides = []
    for i in range(num_slides):
        slide = create_default_slide(order=i)
        if i < len(generated):
            # Strip == markers from plain text fields
            slide['title'] = generated[i].get('title', '').replace('==', '')
            slide['subtitle'] = generated[i].get('subtitle', '').replace('==', '')
            slide['body'] = generated[i].get('body', '').replace('==', '')
            # Store highlight segments separately
            slide['title_segments'] = generated[i].get('title_segments', [])
            slide['subtitle_segments'] = generated[i].get('subtitle_segments', [])
            slide['body_segments'] = generated[i].get('body_segments', [])
        slides.append(slide)

    project = {
        'id': project_id,
        'topic': topic,
        'created_at': str(uuid.uuid1()),
        'slides': slides,
        'settings': {
            'aspect_ratio': '4:5',
            'slide_number': {
                'show': True,
                'position': 'bottom-right',
            },
            'watermark': {
                'text': '',
                'position': 'bottom-left',
            }
        }
    }

    save_project(project)
    return redirect(url_for('project', project_id=project_id))


@app.route('/project/<project_id>')
def project(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return redirect(url_for('index'))
    return render_template('project.html', project=project_data, themes=THEMES)


@app.route('/update_slide/<project_id>', methods=['POST'])
def update_slide(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    data = request.get_json()
    slide_id = data.get('slide_id')

    slide = next((s for s in project_data['slides'] if s['id'] == slide_id), None)
    if not slide:
        return jsonify({'success': False, 'error': 'Slide not found'})

    updatable_fields = ['title', 'subtitle', 'body', 'text_color', 'title_color', 'subtitle_color', 'body_color',
                'text_position', 'text_align',
                'title_size', 'subtitle_size', 'body_size', 'line_height',
                'letter_spacing', 'paragraph_spacing', 'title_gap', 'subtitle_gap', 'bg_opacity',
                'bg_offset_x', 'bg_offset_y', 'bg_scale',
                'gradient_enabled', 'gradient_color', 'gradient_opacity',
                'gradient_position', 'gradient_depth', 'theme', 'theme_mode',
                'text_offset_y',
                # === NEW: Highlight fields ===
                'highlight_color', 'highlight_enabled',
                'title_segments', 'subtitle_segments', 'body_segments']

    for key in updatable_fields:
        if key in data:
            slide[key] = data[key]

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/update_settings/<project_id>', methods=['POST'])
def update_settings(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    data = request.get_json()

    if 'aspect_ratio' in data:
        project_data['settings']['aspect_ratio'] = data['aspect_ratio']

    if 'slide_number' in data:
        sn = data['slide_number']
        project_data['settings']['slide_number']['show'] = sn.get('show', False)
        project_data['settings']['slide_number']['position'] = sn.get('position', 'bottom-right')

    if 'watermark' in data:
        wm = data['watermark']
        project_data['settings']['watermark']['text'] = wm.get('text', '')
        project_data['settings']['watermark']['position'] = wm.get('position', 'bottom-left')

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/apply_theme/<project_id>', methods=['POST'])
def apply_theme(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    data = request.get_json()
    theme_name = data.get('theme')

    if theme_name not in THEMES:
        return jsonify({'success': False, 'error': 'Theme not found'})

    for slide in project_data['slides']:
        slide['theme'] = theme_name
        slide['title_color'] = ''
        slide['subtitle_color'] = ''
        slide['body_color'] = ''
        slide['text_color'] = ''

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/apply_bg_to_all/<project_id>', methods=['POST'])
def apply_bg_to_all(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    data = request.get_json()
    source_slide_id = data.get('slide_id')

    source_slide = next((s for s in project_data['slides'] if s['id'] == source_slide_id), None)
    if not source_slide:
        return jsonify({'success': False, 'error': 'Source slide not found'})

    bg_fields = ['background_image', 'bg_opacity', 'bg_offset_x', 'bg_offset_y', 'bg_scale',
                 'gradient_enabled', 'gradient_color', 'gradient_opacity',
                 'gradient_position', 'gradient_depth']

    for slide in project_data['slides']:
        for field in bg_fields:
            slide[field] = source_slide[field]

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/add_slide/<project_id>', methods=['POST'])
def add_slide(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    new_slide = create_default_slide(order=len(project_data['slides']))
    project_data['slides'].append(new_slide)
    save_project(project_data)
    return jsonify({'success': True, 'slide': new_slide})


@app.route('/delete_slide/<project_id>/<slide_id>', methods=['POST'])
def delete_slide(project_id, slide_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    if len(project_data['slides']) <= 1:
        return jsonify({'success': False, 'error': 'Cannot delete the last slide'})

    project_data['slides'] = [s for s in project_data['slides'] if s['id'] != slide_id]
    for i, slide in enumerate(project_data['slides']):
        slide['order'] = i

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/duplicate_slide/<project_id>/<slide_id>', methods=['POST'])
def duplicate_slide(project_id, slide_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    source = next((s for s in project_data['slides'] if s['id'] == slide_id), None)
    if not source:
        return jsonify({'success': False, 'error': 'Slide not found'})

    new_slide = dict(source)
    new_slide['id'] = str(uuid.uuid4())
    new_slide['order'] = len(project_data['slides'])

    project_data['slides'].append(new_slide)
    save_project(project_data)
    return jsonify({'success': True, 'slide': new_slide})


@app.route('/reorder_slide/<project_id>', methods=['POST'])
def reorder_slide(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    data = request.get_json()
    slide_id = data.get('slide_id')
    direction = data.get('direction')

    slides = project_data['slides']
    idx = next((i for i, s in enumerate(slides) if s['id'] == slide_id), -1)

    if idx == -1:
        return jsonify({'success': False, 'error': 'Slide not found'})

    if direction == 'up' and idx > 0:
        slides[idx], slides[idx - 1] = slides[idx - 1], slides[idx]
    elif direction == 'down' and idx < len(slides) - 1:
        slides[idx], slides[idx + 1] = slides[idx + 1], slides[idx]

    for i, slide in enumerate(slides):
        slide['order'] = i

    save_project(project_data)
    return jsonify({'success': True})


@app.route('/toggle_theme_mode/<project_id>/<slide_id>', methods=['POST'])
def toggle_theme_mode(project_id, slide_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    slide = next((s for s in project_data['slides'] if s['id'] == slide_id), None)
    if not slide:
        return jsonify({'success': False, 'error': 'Slide not found'})

    old_mode = slide.get('theme_mode', 'dark')
    new_mode = 'light' if old_mode == 'dark' else 'dark'
    slide['theme_mode'] = new_mode

    gradient = get_gradient_for_mode(new_mode)
    slide['gradient_color'] = gradient['gradient_color']
    slide['gradient_opacity'] = gradient['gradient_opacity']
    slide['gradient_position'] = gradient['gradient_position']
    slide['gradient_depth'] = gradient['gradient_depth']

    save_project(project_data)
    return jsonify({'success': True, 'theme_mode': new_mode})


@app.route('/upload_background/<project_id>/<slide_id>', methods=['POST'])
def upload_background(project_id, slide_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if file and allowed_file(file.filename):
        filename = f"{project_id}_{slide_id}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        slide = next((s for s in project_data['slides'] if s['id'] == slide_id), None)
        if slide:
            slide['background_image'] = filepath
            save_project(project_data)

        rel_path = os.path.relpath(filepath, BASE_DIR).replace('\\', '/')
        return jsonify({'success': True, 'path': rel_path})

    return jsonify({'success': False, 'error': 'Invalid file type'})


@app.route('/remove_background/<project_id>/<slide_id>', methods=['POST'])
def remove_background(project_id, slide_id):
    project_data = get_project(project_id)
    if not project_data:
        return jsonify({'success': False, 'error': 'Project not found'})

    slide = next((s for s in project_data['slides'] if s['id'] == slide_id), None)
    if slide:
        if slide.get('background_image') and os.path.exists(slide['background_image']):
            try:
                os.remove(slide['background_image'])
            except:
                pass
        slide['background_image'] = ''
        save_project(project_data)

    return jsonify({'success': True})


@app.route('/render/<project_id>/<slide_id>')
def render(project_id, slide_id):
    try:
        img = render_slide(project_id, slide_id, preview=True)
        if not img:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (432, 540), (240, 240, 240))
            draw = ImageDraw.Draw(img)

            font = None
            small_font = None
            font_paths = [
                os.path.join(config.FONTS_FOLDER, 'Inter-Bold.ttf'),
                os.path.join(config.FONTS_FOLDER, 'OpenSans-Regular.ttf'),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]

            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, 20)
                        small_font = ImageFont.truetype(path, 14)
                        break
                    except:
                        continue

            if not font:
                font = ImageFont.load_default()
                small_font = font

            draw.text((216, 250), "Ошибка рендеринга", fill=(150, 150, 150), font=font, anchor="mm")
            draw.text((216, 280), "Проверьте шрифты и перезапустите", fill=(180, 180, 180), font=small_font, anchor="mm")
            draw.text((216, 300), "Убедитесь что есть шрифты в static/fonts/", fill=(180, 180, 180), font=small_font, anchor="mm")

        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        response = send_file(img_io, mimetype='image/png')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Render error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/export/<project_id>')
def export(project_id):
    project_data = get_project(project_id)
    if not project_data:
        return redirect(url_for('index'))

    output_files = export_project(project_id)

    if not output_files:
        return jsonify({'success': False, 'error': 'Nothing to export'})

    zip_io = BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filepath in output_files:
            arcname = os.path.basename(filepath)
            zf.write(filepath, arcname)

    zip_io.seek(0)
    return send_file(zip_io, mimetype='application/zip',
                     download_name=f"carousel_{project_id[:8]}.zip",
                     as_attachment=True)


@app.route('/projects')
def list_projects():
    projects = []
    if os.path.exists(config.PROJECTS_FOLDER):
        for filename in os.listdir(config.PROJECTS_FOLDER):
            if filename.endswith('.json'):
                project_id = filename[:-5]
                project_data = get_project(project_id)
                if project_data:
                    projects.append({
                        'id': project_id,
                        'topic': project_data.get('topic', 'Без названия'),
                        'slides_count': len(project_data.get('slides', [])),
                        'created_at': project_data.get('created_at', '')
                    })

    return render_template('projects_list.html', projects=projects)


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_file(os.path.join(config.UPLOAD_FOLDER, filename))


if __name__ == '__main__':
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(config.PROJECTS_FOLDER, exist_ok=True)

    # Запускаем бота MAX в отдельном потоке
    import threading
    from max_bot import main as bot_main
    bot_thread = threading.Thread(target=bot_main, daemon=True)
    bot_thread.start()

    app.run(debug=True, host='0.0.0.0', port=5000)

    import threading
    from max_bot import main as bot_main


    def start_bot():
        bot_thread = threading.Thread(target=bot_main, daemon=True)
        bot_thread.start()


    start_bot()
