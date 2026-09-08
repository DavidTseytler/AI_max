




import os
import json
import uuid
import time
import requests
import threading
import urllib3
from io import BytesIO
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import config
from app import create_default_slide, get_project, save_project, get_gradient_for_mode
from text_generator import generate_carousel_text
from image_processor import export_project, parse_highlight_segments
from themes import THEMES

BOT_TOKEN = "f9LHodD0cOJ5Y170mb_MDuaNdg_1Lym3jCxEaO4RmTEkp40DmQwTU1XxflJQgBsbaRrfnT0lF4Scp8GwA24g"
CHANNEL_ID = "-77622185813470"
BASE_URL = "https://platform-api2.max.ru"

HEADERS = {
    "Authorization": BOT_TOKEN,
    "Content-Type": "application/json"
}

ADMIN_IDS = [33347466, 117716446]
SCHEDULED_POSTS_FILE = os.path.join(os.path.dirname(config.PROJECTS_FOLDER), "scheduled_posts.json")
PUBLISHED_POSTS_FILE = os.path.join(os.path.dirname(config.PROJECTS_FOLDER), "published_posts.json")
SCHEDULER_INTERVAL = 600

WATERMARKS_FILE = os.path.join(os.path.dirname(config.PROJECTS_FOLDER), "user_watermarks.json")


def _load_watermarks():
    if os.path.exists(WATERMARKS_FILE):
        try:
            with open(WATERMARKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def _save_watermarks(data):
    os.makedirs(os.path.dirname(WATERMARKS_FILE), exist_ok=True)
    with open(WATERMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_user_watermark(user_id):
    return _load_watermarks().get(str(user_id), {})


def _set_user_watermark(user_id, text, position):
    data = _load_watermarks()
    data[str(user_id)] = {"text": text, "position": position}
    _save_watermarks(data)


def _load_scheduled_posts():
    if os.path.exists(SCHEDULED_POSTS_FILE):
        try:
            with open(SCHEDULED_POSTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"posts": []}
    return {"posts": []}


def _save_scheduled_posts(data):
    os.makedirs(os.path.dirname(SCHEDULED_POSTS_FILE), exist_ok=True)
    with open(SCHEDULED_POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_published_posts():
    if os.path.exists(PUBLISHED_POSTS_FILE):
        try:
            with open(PUBLISHED_POSTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"posts": []}
    return {"posts": []}


def _save_published_posts(data):
    os.makedirs(os.path.dirname(PUBLISHED_POSTS_FILE), exist_ok=True)
    with open(PUBLISHED_POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_bot_username():
    try:
        resp = requests.get(
            f"{BASE_URL}/me",
            headers={"Authorization": BOT_TOKEN},
            verify=False, timeout=10
        )
        print(f"[get_bot_username] HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            username = data.get("username")
            print(f"[get_bot_username] username: {username}")
            return username
        else:
            print(f"[get_bot_username] Response: {resp.text[:300]}")
    except Exception as e:
        print(f"[get_bot_username] Error: {e}")
    return None


BOT_USERNAME = get_bot_username()
if not BOT_USERNAME:
    print("❌ Не удалось получить username бота. Проверьте BOT_TOKEN.")
    exit(1)

print(f"✅ Bot username: @{BOT_USERNAME}")
print("🔧 ВЕРСИЯ max_bot.py: NAVIGATION + THEME + BACKGROUND v3")

_last_send_time = {}
_send_lock = threading.Lock()


def _rate_limited_send(chat_id):
    with _send_lock:
        now = time.time()
        last = _last_send_time.get(chat_id, 0)
        wait = max(0, 0.55 - (now - last))
        if wait > 0:
            time.sleep(wait)
        _last_send_time[chat_id] = time.time()


def send_message(user_id, text, buttons=None, attachments=None):
    _rate_limited_send(user_id)
    url = f"{BASE_URL}/messages?user_id={user_id}"
    payload = {"text": text}
    if buttons:
        payload["attachments"] = [{
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        }]
    if attachments:
        if "attachments" not in payload:
            payload["attachments"] = []
        payload["attachments"].extend(attachments)
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, verify=False, timeout=30)
        print(f"[send_message] HTTP {resp.status_code}: {resp.text[:200] if resp.status_code != 200 else 'OK'}")
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"[send_message] Error: {e}")
        return None


def send_channel_message(text, buttons=None, attachments=None):
    _rate_limited_send(CHANNEL_ID)
    url = f"{BASE_URL}/messages?chat_id={CHANNEL_ID}"
    payload = {"text": text}
    if buttons:
        payload["attachments"] = [{
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        }]
    if attachments:
        if "attachments" not in payload:
            payload["attachments"] = []
        payload["attachments"].extend(attachments)
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, verify=False, timeout=30)
        print(f"[send_channel_message] HTTP {resp.status_code}: {resp.text[:200] if resp.status_code != 200 else 'OK'}")
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"[send_channel_message] Error: {e}")
        return None


def answer_callback(callback_id, text, buttons=None):
    _rate_limited_send(f"cb_{callback_id}")
    url = f"{BASE_URL}/answers?callback_id={callback_id}"
    message = {"text": text}
    if buttons:
        message["attachments"] = [{
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        }]
    try:
        resp = requests.post(url, headers=HEADERS, json={"message": message}, verify=False, timeout=30)
        print(f"[answer_callback] HTTP {resp.status_code}: {resp.text[:200] if resp.status_code != 200 else 'OK'}")
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"[answer_callback] Error: {e}")
        return None


def bot_deeplink(payload):
    return f"https://max.ru/{BOT_USERNAME}?start={payload}"


def send_post_to_channel():
    url = f"{BASE_URL}/messages?chat_id={CHANNEL_ID}"
    payload = {
        "text": "👋 Генератор контента для Instagram\n\nВыберите действие 👇",
        "attachments": [{
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {
                            "type": "link",
                            "text": "🏠 Главное меню",
                            "url": bot_deeplink("main_menu")
                        },
                        {
                            "type": "link",
                            "text": "🎠 Карусель",
                            "url": bot_deeplink("carousel")
                        }
                    ]
                ]
            }
        }]
    }
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, verify=False, timeout=30)
        print(f"📤 Пост в канал: {resp.status_code}")
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"[send_post_to_channel] Error: {e}")
        return None


def upload_and_send_image(user_id, image_path, caption=""):
    _rate_limited_send(user_id)
    try:
        upload_resp = requests.post(
            f"{BASE_URL}/uploads?type=image",
            headers={"Authorization": BOT_TOKEN},
            verify=False, timeout=30
        )
        if upload_resp.status_code != 200:
            return False
        upload_data = upload_resp.json()
        upload_url = upload_data.get("url")
        if not upload_url:
            return False

        with open(image_path, "rb") as f:
            files = {"data": (os.path.basename(image_path), f, "image/png")}
            cdn_resp = requests.post(upload_url, files=files, verify=False, timeout=60)

        token = None
        try:
            cdn_json = cdn_resp.json()
            photos = cdn_json.get("photos", {})
            if photos:
                first_photo = list(photos.values())[0]
                token = first_photo.get("token")
            else:
                token = cdn_json.get("token")
        except Exception:
            pass

        if not token:
            return False

        time.sleep(1.5)

        payload = {
            "text": caption,
            "attachments": [{
                "type": "image",
                "payload": {"token": token}
            }]
        }
        resp = requests.post(
            f"{BASE_URL}/messages?user_id={user_id}",
            headers=HEADERS, json=payload, verify=False, timeout=30
        )
        if resp.status_code != 200 and ("attachment.not.ready" in resp.text or "not.processed" in resp.text):
            time.sleep(3)
            resp = requests.post(
                f"{BASE_URL}/messages?user_id={user_id}",
                headers=HEADERS, json=payload, verify=False, timeout=30
            )
        return resp.status_code == 200
    except Exception as e:
        print(f"[upload_and_send_image] Error: {e}")
        return False


def upload_media_get_token(file_path, media_type="image"):
    try:
        upload_resp = requests.post(
            f"{BASE_URL}/uploads?type={media_type}",
            headers={"Authorization": BOT_TOKEN},
            verify=False, timeout=30
        )
        if upload_resp.status_code != 200:
            return None
        upload_data = upload_resp.json()
        upload_url = upload_data.get("url")
        if not upload_url:
            return None

        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        ext = os.path.splitext(file_path)[1].lower()
        mime = mime_types.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            files = {"data": (os.path.basename(file_path), f, mime)}
            cdn_resp = requests.post(upload_url, files=files, verify=False, timeout=60)

        token = None
        try:
            cdn_json = cdn_resp.json()
            if "photos" in cdn_json:
                photos = cdn_json.get("photos", {})
                if photos:
                    first_photo = list(photos.values())[0]
                    token = first_photo.get("token")
            elif "token" in cdn_json:
                token = cdn_json.get("token")
            else:
                token = cdn_json.get("token")
        except Exception:
            pass
        return token
    except Exception as e:
        print(f"[upload_media_get_token] Error: {e}")
        return None


def get_updates(marker=None):
    url = f"{BASE_URL}/updates"
    params = {"limit": 100, "timeout": 30, "types": "message_callback,message_created,bot_started"}
    if marker is not None:
        params["marker"] = marker
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=35, verify=False)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ get_updates HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ get_updates connection error: {e}")
    return {"updates": [], "marker": marker}


# ==================== FSM & NAVIGATION ====================
user_states = {}
_state_lock = threading.Lock()

# Карта переходов Назад: текущее -> (предыдущее, ключи для сохранения)
BACK_MAP = {
    "waiting_slide_count": ("waiting_text", ["article_text"]),
    "waiting_theme": ("waiting_slide_count", ["article_text", "num_slides"]),
    "waiting_watermark_text": ("waiting_theme", ["article_text", "num_slides", "theme"]),
    "waiting_watermark_position": ("waiting_watermark_text", ["article_text", "num_slides", "theme", "watermark_text"]),
    "waiting_watermark_confirm": ("waiting_theme", ["article_text", "num_slides", "theme"]),
    "waiting_photo_slide_num": ("waiting_regenerate", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position"]),
    "waiting_photo_upload": ("waiting_photo_slide_num", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position", "current_slide"]),
    "waiting_edit_slide": ("waiting_regenerate", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position"]),
    "waiting_edit_field": ("waiting_edit_slide", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position", "edit_slide"]),
    "waiting_edit_text": ("waiting_edit_field", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position", "edit_slide", "edit_field"]),
    "generated": ("waiting_regenerate", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position"]),
    "waiting_slide_theme_select": ("generated", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position"]),
    "waiting_slide_bg_select": ("generated", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position"]),
    "waiting_bg_upload": ("waiting_slide_bg_select", ["project_id", "generated", "photos", "num_slides", "theme", "article_text", "watermark_text", "watermark_position", "bg_slide_num"]),
}


def _set_state(user_id, state, data_update=None):
    with _state_lock:
        if user_id not in user_states:
            user_states[user_id] = {"state": state, "data": {}}
        else:
            old_state = user_states[user_id]["state"]
            if old_state != state and state != "confirm_main_menu":
                user_states[user_id]["data"]["__prev_state"] = old_state
            user_states[user_id]["state"] = state
        if data_update:
            user_states[user_id]["data"].update(data_update)
        print(f"[STATE] user={user_id} -> {state} | data_keys={list(user_states[user_id]['data'].keys())}")


def _get_state(user_id):
    with _state_lock:
        return user_states.get(user_id, {"state": "idle", "data": {}})


def _go_back(user_id):
    st = _get_state(user_id)
    state = st["state"]
    data = st["data"]

    if state == "confirm_main_menu":
        prev = data.get("__prev_state", "idle")
        _set_state(user_id, prev, data)
        _restore_ui(user_id, prev, data)
        return True

    if state in BACK_MAP:
        prev_state, keys_to_keep = BACK_MAP[state]
        new_data = {}
        for k in keys_to_keep:
            if k in data:
                new_data[k] = data[k]
        new_data["__prev_state"] = data.get("__prev_state")
        _set_state(user_id, prev_state, new_data)
        _restore_ui(user_id, prev_state, new_data)
        return True

    show_main_menu(user_id)
    return True


def _restore_ui(user_id, state, data):
    if state == "waiting_text":
        send_message(user_id, "🎠 *Создание карусели*\n\nВведите текст статьи, которую нужно превратить в слайды:")
    elif state == "waiting_slide_count":
        send_message(user_id, "📊 Выберите количество слайдов:", buttons=kb_slide_counts())
    elif state == "waiting_theme":
        send_message(user_id, "🎨 Выберите тему оформления:", buttons=kb_themes())
    elif state == "waiting_watermark_text":
        send_message(user_id,
            "✍️ Введите подпись для слайдов (ник, телефон, @instagram и т.д.), или нажмите «Пропустить»:",
            buttons=kb_watermark_text())
    elif state == "waiting_watermark_position":
        send_message(user_id, "📍 Выберите позицию подписи:", buttons=kb_watermark_positions())
    elif state == "waiting_watermark_confirm":
        saved = _get_user_watermark(user_id)
        if saved and saved.get("text"):
            send_message(user_id,
                f"💾 У вас сохранена подпись:\n\n'{saved['text']}'\n\nОставить её?",
                buttons=kb_watermark_confirm(saved["text"], saved.get("position", "bottom-left")))
        else:
            _set_state(user_id, "waiting_watermark_text", data)
            send_message(user_id,
                "✍️ Введите подпись для слайдов (ник, телефон, @instagram и т.д.), или нажмите «Пропустить»:",
                buttons=kb_watermark_text())
    elif state == "waiting_regenerate":
        generated = data.get("generated", [])
        preview = _format_preview(generated)
        send_message(user_id, preview, buttons=kb_regenerate())
    elif state == "waiting_photo_slide_num":
        project = get_project(data.get("project_id")) if data.get("project_id") else None
        count = len(project["slides"]) if project else data.get("num_slides", 5)
        photos = data.get("photos", {})
        filled = list(photos.keys())
        send_message(user_id,
            f"📤 Выберите слайд (1–{count}), на который загрузить фото,\nили нажмите «Готово».",
            buttons=kb_slide_numbers(count, exclude=filled))
    elif state == "waiting_edit_slide":
        generated = data.get("generated", [])
        count = len(generated)
        send_message(user_id, "✏️ Выберите слайд:", buttons=kb_edit_slides(count))
    elif state == "waiting_edit_field":
        sn = data.get("edit_slide", 1)
        generated = data.get("generated", [])
        if 1 <= sn <= len(generated):
            current = generated[sn - 1]
            send_message(user_id,
                f"✏️ *Слайд {sn}*\n\n"
                f"📝 Заголовок: {current['title']}\n"
                f"📝 Подзаголовок: {current['subtitle']}\n"
                f"📝 Текст: {current['body'][:100]}...\n\n"
                f"Что хотите изменить?",
                buttons=kb_edit_fields())
    elif state == "generated":
        project_id = data.get("project_id")
        if project_id:
            send_message(user_id,
                "✅ Карусель готова!\n\nВыберите действие:",
                buttons=kb_post_generate(project_id))
    elif state == "idle":
        show_main_menu(user_id)
    else:
        show_main_menu(user_id)


def _ask_main_menu_confirm(user_id):
    st = _get_state(user_id)
    state = st["state"]
    if state == "idle":
        show_main_menu(user_id)
        return
    _set_state(user_id, "confirm_main_menu", {"__prev_state": state, **st["data"]})
    send_message(user_id,
        "⚠️ *Отменить создание карусели и выйти в главное меню?*\n\nВсе несохранённые данные будут потеряны.",
        buttons=[
            [{"type": "callback", "text": "✅ Да, выйти", "payload": "confirm_main_menu_yes"}],
            [{"type": "callback", "text": "❌ Нет, продолжить", "payload": "confirm_main_menu_no"}],
        ])


def _add_nav(buttons, show_back=True, show_home=True):
    nav_row = []
    if show_back:
        nav_row.append({"type": "callback", "text": "⬅️ Назад", "payload": "nav_back"})
    if show_home:
        nav_row.append({"type": "callback", "text": "🏠 Главное меню", "payload": "nav_main_menu"})
    if nav_row:
        buttons.append(nav_row)
    return buttons


# ==================== ПРОВЕРКА АДМИНА ====================
def is_admin(user_id):
    return int(user_id) in ADMIN_IDS


# ==================== КЛАВИАТУРЫ ====================

def kb_main_menu():
    return [
        [{"type": "callback", "text": "🎠 Карусель", "payload": "menu_carousel"}],
        [{"type": "callback", "text": "🖼 Нейрофото", "payload": "menu_neurophoto"}],
        [{"type": "callback", "text": "🏡 Хоумстейджинг", "payload": "menu_homestaging"}],
        [{"type": "callback", "text": "⭐ Подписка", "payload": "menu_subscription"}],
    ]


def kb_admin_menu():
    buttons = [
        [{"type": "callback", "text": "📝 Создать пост", "payload": "admin_create_post"}],
        [{"type": "callback", "text": "📅 Запланированные", "payload": "admin_list_scheduled"}],
        [{"type": "callback", "text": "✏️ Редактировать пост", "payload": "admin_edit_select"}],
        [{"type": "callback", "text": "🗑 Удалить пост", "payload": "admin_delete_select"}],
    ]
    return _add_nav(buttons, show_back=False, show_home=True)


def kb_admin_post_actions():
    buttons = [
        [{"type": "callback", "text": "📤 Опубликовать сейчас", "payload": "admin_publish_now"}],
        [{"type": "callback", "text": "📅 Запланировать", "payload": "admin_schedule"}],
        [{"type": "callback", "text": "✏️ Изменить текст", "payload": "admin_edit_text"}],
        [{"type": "callback", "text": "🖼 Изменить медиа", "payload": "admin_edit_media"}],
        [{"type": "callback", "text": "🔘 Изменить кнопки", "payload": "admin_edit_buttons"}],
        [{"type": "callback", "text": "❌ Отменить", "payload": "admin_cancel"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_media_choice():
    buttons = [
        [{"type": "callback", "text": "📸 Добавить фото", "payload": "media_photo"}],
        [{"type": "callback", "text": "🎬 Добавить видео", "payload": "media_video"}],
        [{"type": "callback", "text": "📎 Добавить документ", "payload": "media_doc"}],
        [{"type": "callback", "text": "⏭ Пропустить", "payload": "media_skip"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_button_types(selected=None):
    selected = selected or []
    buttons = []
    opts = [
        ("🏠 Главное меню", "btn_main_menu"),
        ("🎠 Карусель", "btn_carousel"),
        ("🖼 Нейрофото", "btn_neurophoto"),
        ("🏡 Хоумстейджинг", "btn_homestaging"),
    ]
    for label, payload in opts:
        mark = "✅ " if payload in selected else ""
        buttons.append([{"type": "callback", "text": f"{mark}{label}", "payload": f"toggle_{payload}"}])
    buttons.append([{"type": "callback", "text": "✅ Готово", "payload": "buttons_done"}])
    buttons.append([{"type": "callback", "text": "⏭ Без кнопок", "payload": "buttons_skip"}])
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_calendar():
    buttons = []
    today = datetime.now()
    row = []
    months_ru = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    for i in range(14):
        date = today + timedelta(days=i)
        label = f"{date.day} {months_ru[date.month]}"
        payload = f"date_{date.strftime('%Y-%m-%d')}"
        row.append({"type": "callback", "text": label, "payload": payload})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_hours():
    buttons = []
    for h in range(0, 24, 4):
        row = []
        for i in range(4):
            if h + i < 24:
                row.append({"type": "callback", "text": f"{h+i:02d}", "payload": f"hour_{h+i:02d}"})
        buttons.append(row)
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_minutes():
    buttons = [
        [{"type": "callback", "text": "00", "payload": "min_00"},
         {"type": "callback", "text": "15", "payload": "min_15"},
         {"type": "callback", "text": "30", "payload": "min_30"},
         {"type": "callback", "text": "45", "payload": "min_45"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_slide_counts():
    buttons = [
        [{"type": "callback", "text": "3 слайда", "payload": "slides_3"}],
        [{"type": "callback", "text": "5 слайдов", "payload": "slides_5"}],
        [{"type": "callback", "text": "7 слайдов", "payload": "slides_7"}]
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_themes():
    themes = list(THEMES.keys())
    buttons = []
    row = []
    for t in themes:
        row.append({"type": "callback", "text": t, "payload": f"theme_{t}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_photo_choice():
    buttons = [
        [{"type": "callback", "text": "📸 С фото", "payload": "with_photo"}],
        [{"type": "callback", "text": "🚫 Без фото", "payload": "without_photo"}]
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_slide_numbers(max_slides, exclude=None):
    buttons = []
    for i in range(1, max_slides + 1):
        if exclude and i in exclude:
            label = f"✅ Слайд {i}"
        else:
            label = f"Слайд {i}"
        buttons.append([{"type": "callback", "text": label, "payload": f"slide_num_{i}"}])
    buttons.append([{"type": "callback", "text": "✅ Готово", "payload": "photos_done"}])
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_regenerate():
    buttons = [
        [{"type": "callback", "text": "🔄 Перегенерировать", "payload": "regenerate"}],
        [{"type": "callback", "text": "✏️ Редактировать текст", "payload": "edit_slides"}],
        [{"type": "callback", "text": "📸 Добавить фото", "payload": "add_photos"}],
        [{"type": "callback", "text": "✅ Сгенерировать финал", "payload": "generate_final"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_final(project_id):
    buttons = [
        [{"type": "callback", "text": "🖼 Получить в боте", "payload": f"get_images_{project_id}"}],
        [{"type": "link", "text": "🔗 Открыть на сервере", "url": f"http://127.0.0.1:5000/project/{project_id}"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


# === НОВАЯ КЛАВИАТУРА: после получения готовых слайдов ===
def kb_post_generate(project_id):
    buttons = [
        [{"type": "callback", "text": "🌗 Сменить тему слайда", "payload": "postgen_theme"}],
        [{"type": "callback", "text": "📸 Фон слайда (добавить/убрать)", "payload": "postgen_bg"}],
        [{"type": "callback", "text": "✏️ Редактировать текст", "payload": "postgen_edit_text"}],
        [{"type": "callback", "text": "🔄 Перегенерировать всё", "payload": "postgen_regenerate"}],
        [{"type": "callback", "text": "🖼 Получить слайды снова", "payload": f"get_images_{project_id}"}],
        [{"type": "link", "text": "🔗 Открыть на сервере", "url": f"http://127.0.0.1:5000/project/{project_id}"}],
    ]
    return _add_nav(buttons, show_back=False, show_home=True)


def kb_slide_theme_select(max_slides):
    buttons = []
    for i in range(1, max_slides + 1):
        buttons.append([{"type": "callback", "text": f"🌗 Слайд {i}", "payload": f"theme_slide_{i}"}])
    buttons.append([{"type": "callback", "text": "⬅️ Назад", "payload": "nav_back"}])
    return buttons


def kb_slide_bg_select(max_slides):
    buttons = []
    for i in range(1, max_slides + 1):
        buttons.append([{"type": "callback", "text": f"📸 Слайд {i}", "payload": f"bg_slide_{i}"}])
    buttons.append([{"type": "callback", "text": "⬅️ Назад", "payload": "nav_back"}])
    return buttons


def kb_slide_actions():
    return [
        [{"type": "callback", "text": "📸 Загрузить фото", "payload": "bg_add_photo"}],
        [{"type": "callback", "text": "🗑 Удалить фон", "payload": "bg_remove"}],
        [{"type": "callback", "text": "⬅️ Назад", "payload": "nav_back"}],
    ]


def kb_watermark_confirm(saved_text, saved_pos):
    pos_labels = {
        "bottom-left": "↙️ слева снизу",
        "bottom-right": "↘️ справа снизу",
        "top-left": "↖️ слева сверху",
        "top-right": "↗️ справа сверху",
    }
    pos_label = pos_labels.get(saved_pos, saved_pos)
    buttons = [
        [{"type": "callback", "text": f"✅ Да, оставить '{saved_text}' ({pos_label})", "payload": "watermark_keep"}],
        [{"type": "callback", "text": "✏️ Нет, новая подпись", "payload": "watermark_new"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_watermark_text():
    buttons = [
        [{"type": "callback", "text": "⏭ Пропустить подпись", "payload": "watermark_skip"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_watermark_positions():
    buttons = [
        [{"type": "callback", "text": "↙️ Слева снизу", "payload": "wm_pos_bottom-left"}],
        [{"type": "callback", "text": "↘️ Справа снизу", "payload": "wm_pos_bottom-right"}],
        [{"type": "callback", "text": "↖️ Слева сверху", "payload": "wm_pos_top-left"}],
        [{"type": "callback", "text": "↗️ Справа сверху", "payload": "wm_pos_top-right"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_edit_slides(max_slides):
    buttons = []
    for i in range(1, max_slides + 1):
        buttons.append([{"type": "callback", "text": f"✏️ Слайд {i}", "payload": f"edit_slide_{i}"}])
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_edit_fields():
    buttons = [
        [{"type": "callback", "text": "📝 Заголовок (title)", "payload": "edit_field_title"}],
        [{"type": "callback", "text": "📝 Подзаголовок (subtitle)", "payload": "edit_field_subtitle"}],
        [{"type": "callback", "text": "📝 Основной текст (body)", "payload": "edit_field_body"}],
    ]
    return _add_nav(buttons, show_back=True, show_home=True)


def kb_post_list(posts, action_prefix):
    buttons = []
    for p in posts:
        post_id = p["id"]
        text_preview = p.get("text", "")[:30] + "..." if len(p.get("text", "")) > 30 else p.get("text", "Без текста")
        status = p.get("status", "unknown")
        if status == "scheduled":
            when = p.get("scheduled_time", "неизвестно")
            label = f"📅 {text_preview} ({when})"
        else:
            label = f"✅ {text_preview}"
        buttons.append([{"type": "callback", "text": label, "payload": f"{action_prefix}_{post_id}"}])
    return _add_nav(buttons, show_back=True, show_home=True)


# ==================== ЛОГИКА АДМИН-ПАНЕЛИ ====================

def show_admin_menu(user_id):
    text = (
        "🔐 *Админ-панель*\n\n"
        "Управление контентом канала:"
    )
    send_message(user_id, text, buttons=kb_admin_menu())


def _build_post_buttons(post_data):
    selected = post_data.get("buttons", [])
    post_id = post_data.get("id", str(uuid.uuid4()))
    buttons_row = []

    if "btn_main_menu" in selected:
        buttons_row.append({
            "type": "link",
            "text": "🏠 Главное меню",
            "url": bot_deeplink("main_menu")
        })

    if "btn_carousel" in selected:
        buttons_row.append({
            "type": "link",
            "text": "🎠 Карусель",
            "url": bot_deeplink(f"carousel_post_{post_id}")
        })

    if "btn_neurophoto" in selected:
        buttons_row.append({
            "type": "link",
            "text": "🖼 Нейрофото",
            "url": bot_deeplink("neurophoto")
        })

    if "btn_homestaging" in selected:
        buttons_row.append({
            "type": "link",
            "text": "🏡 Хоумстейджинг",
            "url": bot_deeplink("homestaging")
        })

    if buttons_row:
        return [buttons_row]
    return None


def _save_post_for_carousel(post_id, text):
    data = _load_published_posts()
    data["posts"] = [p for p in data.get("posts", []) if p["id"] != post_id]
    data["posts"].append({
        "id": post_id,
        "text": text,
        "saved_at": datetime.now().isoformat()
    })
    _save_published_posts(data)


def _get_post_text_for_carousel(post_id):
    data = _load_published_posts()
    for p in data.get("posts", []):
        if p["id"] == post_id:
            return p.get("text", "")
    return ""


def _publish_post_to_channel(post_data):
    text = post_data.get("text", "")
    media = post_data.get("media", [])
    buttons = _build_post_buttons(post_data)
    post_id = post_data.get("id")

    if "btn_carousel" in post_data.get("buttons", []) and post_id:
        _save_post_for_carousel(post_id, text)

    attachments = []
    for m in media:
        if m.get("token"):
            attachments.append({
                "type": m.get("type", "image"),
                "payload": {"token": m["token"]}
            })

    url = f"{BASE_URL}/messages?chat_id={CHANNEL_ID}"
    payload = {"text": text}
    if attachments:
        payload["attachments"] = attachments
    if buttons:
        if "attachments" not in payload:
            payload["attachments"] = []
        payload["attachments"].append({
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        })

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, verify=False, timeout=30)
        print(f"[_publish_post_to_channel] HTTP {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            msg_id = result.get("message_id") or result.get("id")
            return msg_id or True
    except Exception as e:
        print(f"[_publish_post_to_channel] Error: {e}")
    return None


def _show_post_preview(user_id, post_data, edit_mode=False):
    text = post_data.get("text", "(без текста)")
    media_count = len(post_data.get("media", []))
    buttons = post_data.get("buttons", [])

    preview_text = (
        "👁 *Предпросмотр поста:*\n\n"
        f"{text}\n\n"
        f"📎 Медиа: {media_count}\n"
        f"🔘 Кнопки: {', '.join(buttons) if buttons else 'нет'}"
    )

    media = post_data.get("media", [])
    if media and media[0].get("token"):
        m = media[0]
        media_payload = {
            "text": preview_text,
            "attachments": [{
                "type": m.get("type", "image"),
                "payload": {"token": m["token"]}
            }]
        }
        if edit_mode:
            media_payload["attachments"].append({
                "type": "inline_keyboard",
                "payload": {"buttons": kb_admin_post_actions()}
            })
        requests.post(
            f"{BASE_URL}/messages?user_id={user_id}",
            headers=HEADERS, json=media_payload, verify=False, timeout=30
        )
    else:
        if edit_mode:
            send_message(user_id, preview_text, buttons=kb_admin_post_actions())
        else:
            send_message(user_id, preview_text)


# ==================== ПЛАНИРОВЩИК ====================
def scheduler_loop():
    print("📅 Планировщик запущен (проверка каждые 10 мин)")
    while True:
        try:
            now = datetime.now()
            data = _load_scheduled_posts()
            updated = False

            for post in data.get("posts", []):
                if post.get("status") == "scheduled":
                    try:
                        scheduled_time = datetime.fromisoformat(post["scheduled_time"])
                        if scheduled_time <= now:
                            print(f"📅 Публикуем запланированный пост {post['id']}")
                            msg_id = _publish_post_to_channel(post)
                            if msg_id:
                                post["status"] = "published"
                                post["published_at"] = now.isoformat()
                                post["channel_message_id"] = msg_id
                                updated = True
                                print(f"✅ Пост {post['id']} опубликован")
                            else:
                                print(f"❌ Ошибка публикации поста {post['id']}")
                    except Exception as e:
                        print(f"[scheduler] Ошибка обработки поста {post['id']}: {e}")

            if updated:
                _save_scheduled_posts(data)

        except Exception as e:
            print(f"[scheduler] Ошибка цикла: {e}")

        time.sleep(SCHEDULER_INTERVAL)


# ==================== ЛОГИКА ГЕНЕРАЦИИ ====================
def _create_project_direct(article_text, num_slides, theme_name, watermark_text="", watermark_position="bottom-left"):
    print(f"[_create_project_direct] article_text='{article_text[:100]}...' len={len(article_text)} num_slides={num_slides} theme={theme_name}")

    if not article_text or not article_text.strip():
        print("[_create_project_direct] ОШИБКА: article_text пустой!")
        return None, None

    project_id = str(uuid.uuid4())
    generated = generate_carousel_text(article_text, num_slides)

    print(f"[_create_project_direct] generate_carousel_text вернул {len(generated)} слайдов")

    if not generated:
        print("[_create_project_direct] ОШИБКА: генерация вернула пустой список!")
        return None, None

    import random
    slides = []
    for i in range(num_slides):
        theme_mode = random.choice(["dark", "light"])
        print(f"[_create_project_direct] Слайд {i+1}: режим={theme_mode}")

        slide = create_default_slide(order=i)
        slide["theme"] = theme_name
        slide["theme_mode"] = theme_mode
        gradient = get_gradient_for_mode(theme_mode)
        slide["gradient_color"] = gradient["gradient_color"]
        slide["gradient_opacity"] = gradient["gradient_opacity"]
        slide["gradient_position"] = gradient["gradient_position"]
        slide["gradient_depth"] = gradient["gradient_depth"]
        slide["highlight_color"] = THEMES[theme_name][theme_mode]["highlight"]

        if i < len(generated):
            slide["title"] = generated[i].get("title", "").replace("==", "")
            slide["subtitle"] = generated[i].get("subtitle", "").replace("==", "")
            slide["body"] = generated[i].get("body", "").replace("==", "")
            slide["title_segments"] = generated[i].get("title_segments", [])
            slide["subtitle_segments"] = generated[i].get("subtitle_segments", [])
            slide["body_segments"] = generated[i].get("body_segments", [])
            print(f"[_create_project_direct] Слайд {i+1}: title='{slide['title'][:50]}...' subtitle='{slide['subtitle'][:50]}...' body='{slide['body'][:50]}...'")
        else:
            print(f"[_create_project_direct] ВНИМАНИЕ: слайд {i+1} не заполнен (generated короче num_slides)")
        slides.append(slide)

    project = {
        "id": project_id,
        "topic": article_text[:60],
        "created_at": str(uuid.uuid1()),
        "slides": slides,
        "settings": {
            "aspect_ratio": "4:5",
            "slide_number": {"show": True, "position": "bottom-right"},
            "watermark": {"text": watermark_text, "position": watermark_position}
        }
    }
    save_project(project)
    print(f"[_create_project_direct] Проект сохранён: {project_id}")
    return project_id, generated


def _format_preview(generated):
    text = "📝 *Текст слайдов:*\n\n"
    for i, s in enumerate(generated, 1):
        text += f"*{i}.* {s['title']}\n"
        text += f"_{s['subtitle']}_\n"
        text += f"{s['body']}\n\n"
    return text


def _update_slide_field(project_id, slide_order, field, new_text):
    project = get_project(project_id)
    if not project:
        return None
    for slide in project["slides"]:
        if slide.get("order") == slide_order - 1:
            segments = parse_highlight_segments(new_text)
            clean_text = "".join([s["text"] for s in segments])
            slide[field] = clean_text
            slide[f"{field}_segments"] = segments
            save_project(project)
            break
    generated = []
    for s in sorted(project["slides"], key=lambda x: x.get("order", 0)):
        generated.append({
            "title": s.get("title", ""),
            "subtitle": s.get("subtitle", ""),
            "body": s.get("body", ""),
        })
    return generated


def _show_edit_preview(user_id, generated, project_id):
    _set_state(user_id, "waiting_regenerate", {
        "project_id": project_id,
        "generated": generated
    })
    preview = _format_preview(generated)
    send_message(user_id, preview, buttons=kb_regenerate())


def _do_generate(user_id):
    st = _get_state(user_id)
    data = st["data"]
    article = data.get("article_text", "")
    count = data.get("num_slides", 5)
    theme = data.get("theme", "Ocean")
    photos = data.get("photos", {})
    watermark_text = data.get("watermark_text", "")
    watermark_position = data.get("watermark_position", "bottom-left")

    print(f"[_do_generate] user_id={user_id} article='{article[:100]}...' len={len(article)} count={count} theme={theme}")
    print(f"[_do_generate] data keys: {list(data.keys())}")

    if not article or not article.strip():
        print(f"[_do_generate] ОШИБКА: article_text пустой! data={data}")
        send_message(user_id,
            "❌ *Ошибка*\n\n"
            "Текст статьи не сохранился. Пожалуйста, начните заново: нажмите 🎠 Карусель и введите текст.")
        _set_state(user_id, "idle")
        return

    send_message(user_id, "⏳ Генерирую текст слайдов... Это может занять 10–30 сек.")

    project_id, generated = _create_project_direct(article, count, theme, watermark_text, watermark_position)

    if not project_id or not generated:
        print(f"[_do_generate] ГЕНЕРАЦИЯ ПРОВАЛИЛАСЬ для user_id={user_id}")
        send_message(user_id,
            "❌ *Ошибка генерации*\n\n"
            "Не удалось сгенерировать текст слайдов. Возможные причины:\n"
            "• Проблемы с API генерации\n"
            "• Пустой или слишком короткий текст\n"
            "• Проблемы с прокси\n\n"
            "Попробуйте ещё раз или напишите другой текст.",
            buttons=[[{"type": "callback", "text": "🔄 Попробовать снова", "payload": "regenerate"}]])
        _set_state(user_id, "waiting_regenerate", {"failed": True})
        return

    if photos:
        project = get_project(project_id)
        for slide in project["slides"]:
            sn = slide["order"] + 1
            path = photos.get(sn)
            if path and os.path.exists(path):
                slide["background_image"] = path
        save_project(project)

    _set_state(user_id, "waiting_regenerate", {
        "project_id": project_id,
        "generated": generated
    })

    preview = _format_preview(generated)
    send_message(user_id, preview, buttons=kb_regenerate())


# === НОВЫЕ ФУНКЦИИ: смена темы и фона на финальном этапе ===

def _toggle_slide_theme(project_id, slide_order):
    project = get_project(project_id)
    if not project:
        return None, None
    slide = None
    for s in project["slides"]:
        if s.get("order") == slide_order - 1:
            slide = s
            break
    if not slide:
        return None, None

    current_mode = slide.get("theme_mode", "dark")
    new_mode = "light" if current_mode == "dark" else "dark"
    theme_name = slide.get("theme", "Ocean")

    slide["theme_mode"] = new_mode
    gradient = get_gradient_for_mode(new_mode)
    slide["gradient_color"] = gradient["gradient_color"]
    slide["gradient_opacity"] = gradient["gradient_opacity"]
    slide["gradient_position"] = gradient["gradient_position"]
    slide["gradient_depth"] = gradient["gradient_depth"]
    slide["highlight_color"] = THEMES[theme_name][new_mode]["highlight"]

    save_project(project)

    files = export_project(project_id)
    if files and slide_order <= len(files):
        return files[slide_order - 1], new_mode
    return None, new_mode


def _remove_slide_background(project_id, slide_order):
    project = get_project(project_id)
    if not project:
        return None
    for slide in project["slides"]:
        if slide.get("order") == slide_order - 1:
            if "background_image" in slide:
                del slide["background_image"]
            save_project(project)
            break
    files = export_project(project_id)
    if files and slide_order <= len(files):
        return files[slide_order - 1]
    return None


def _set_slide_background(project_id, slide_order, image_path):
    project = get_project(project_id)
    if not project:
        return None
    for slide in project["slides"]:
        if slide.get("order") == slide_order - 1:
            slide["background_image"] = image_path
            save_project(project)
            break
    files = export_project(project_id)
    if files and slide_order <= len(files):
        return files[slide_order - 1]
    return None


def _send_project_slides(user_id, project_id):
    send_message(user_id, "⏳ Рендерю слайды в PNG...")
    files = export_project(project_id)
    if not files:
        send_message(user_id, "❌ Ошибка рендеринга. Проверьте проект на сервере.")
        return False

    success_count = 0
    for fp in files:
        ok = upload_and_send_image(user_id, fp, caption=f"Слайд {os.path.basename(fp)}")
        if ok:
            success_count += 1
        else:
            send_message(user_id, f"❌ Не удалось отправить {os.path.basename(fp)}")

    send_message(user_id, f"✅ Отправлено {success_count}/{len(files)} слайдов!")
    return True


# ==================== ОБРАБОТЧИКИ ====================
def _extract_user_id(upd):
    cb = upd.get("callback", {})
    user = cb.get("user") or upd.get("user")
    if user:
        uid = user.get("user_id") or user.get("id")
        if uid:
            return int(uid)

    msg = upd.get("message", {})
    sender = msg.get("sender", {})
    uid = sender.get("user_id") or sender.get("id")
    if uid:
        return int(uid)

    frm = upd.get("from") or msg.get("from")
    if frm:
        uid = frm.get("user_id") or frm.get("id")
        if uid:
            return int(uid)

    chat = msg.get("chat", {})
    uid = chat.get("user_id") or chat.get("id")
    if uid:
        return int(uid)

    return None


def show_main_menu(user_id):
    text = (
        "👋 *Главное меню*\n\n"
        "Выберите, что хотите создать:"
    )
    send_message(user_id, text, buttons=kb_main_menu())


def start_carousel_flow(user_id):
    _set_state(user_id, "waiting_text", {})
    send_message(user_id, "🎠 *Создание карусели*\n\nВведите текст статьи, которую нужно превратить в слайды:")


def start_carousel_flow_with_text(user_id, article_text):
    if not article_text or not article_text.strip():
        send_message(user_id, "❌ Текст статьи пустой. Начните с главного меню.")
        show_main_menu(user_id)
        return
    _set_state(user_id, "waiting_slide_count", {"article_text": article_text})
    send_message(user_id, f"🎠 *Создание карусели*\n\nТекст получен из поста!\n\n📊 Выберите количество слайдов:", buttons=kb_slide_counts())


def handle_bot_started(upd):
    user = upd.get("user", {})
    user_id = user.get("user_id") or user.get("id")
    if not user_id:
        return
    user_id = int(user_id)

    payload = upd.get("payload", "") or ""

    print(f"🚀 [{user_id}] bot_started with payload: {payload}")

    if payload.startswith("carousel_post_"):
        post_id = payload.replace("carousel_post_", "")
        article_text = _get_post_text_for_carousel(post_id)
        if article_text:
            send_message(user_id, f"🎠 Создаём карусель из поста...")
            start_carousel_flow_with_text(user_id, article_text)
        else:
            send_message(user_id, "❌ Текст поста не найден. Введите текст вручную:")
            start_carousel_flow(user_id)
        return
    elif payload == "carousel":
        start_carousel_flow(user_id)
    elif payload == "neurophoto":
        send_message(user_id, "🖼 *Нейрофото*\n\nЭтот раздел в разработке. Скоро будет доступен!")
    elif payload == "homestaging":
        send_message(user_id, "🏡 *Хоумстейджинг*\n\nЭтот раздел в разработке. Скоро будет доступен!")
    elif payload == "main_menu":
        show_main_menu(user_id)
    else:
        show_main_menu(user_id)


def handle_callback(upd, callback_id, payload):
    user_id = _extract_user_id(upd)
    if not user_id:
        print(f"⚠️ Не удалось определить user_id в callback: {json.dumps(upd, ensure_ascii=False)[:500]}")
        return

    st = _get_state(user_id)
    state = st["state"]
    print(f"👆 [{user_id}] callback: {payload} | state: {state}")

    # ====== ГЛОБАЛЬНАЯ НАВИГАЦИЯ ======
    if payload == "nav_back":
        _go_back(user_id)
        return

    if payload == "nav_main_menu":
        _ask_main_menu_confirm(user_id)
        return

    if payload == "confirm_main_menu_yes":
        _set_state(user_id, "idle", {})
        show_main_menu(user_id)
        return

    if payload == "confirm_main_menu_no":
        _go_back(user_id)
        return

    # ====== АДМИН-КОЛЛБЭКИ ======
    if is_admin(user_id):
        if payload == "admin_menu" or payload == "admin_back_menu":
            _set_state(user_id, "admin_idle")
            show_admin_menu(user_id)
            return

        if payload == "admin_create_post":
            _set_state(user_id, "admin_enter_text", {"post_data": {"id": str(uuid.uuid4()), "buttons": [], "media": []}})
            send_message(user_id, "📝 *Создание поста*\n\nВведите текст поста:")
            return

        if payload == "admin_list_scheduled":
            data = _load_scheduled_posts()
            scheduled = [p for p in data.get("posts", []) if p.get("status") == "scheduled"]
            if not scheduled:
                send_message(user_id, "📅 Нет запланированных постов.", buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_back_menu"}]])
            else:
                send_message(user_id, "📅 *Запланированные посты:*", buttons=kb_post_list(scheduled, "admin_view"))
            return

        if payload == "admin_edit_select":
            data = _load_scheduled_posts()
            scheduled = [p for p in data.get("posts", []) if p.get("status") == "scheduled"]
            if not scheduled:
                send_message(user_id, "✏️ Нет запланированных постов для редактирования.", buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_back_menu"}]])
            else:
                send_message(user_id, "✏️ Выберите пост для редактирования:", buttons=kb_post_list(scheduled, "admin_edit"))
            return

        if payload == "admin_delete_select":
            data = _load_scheduled_posts()
            scheduled = [p for p in data.get("posts", []) if p.get("status") == "scheduled"]
            if not scheduled:
                send_message(user_id, "🗑 Нет запланированных постов для удаления.", buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_back_menu"}]])
            else:
                send_message(user_id, "🗑 Выберите пост для удаления:", buttons=kb_post_list(scheduled, "admin_delete"))
            return

        if payload.startswith("admin_view_"):
            post_id = payload.replace("admin_view_", "")
            data = _load_scheduled_posts()
            post = None
            for p in data.get("posts", []):
                if p["id"] == post_id:
                    post = p
                    break
            if post:
                text = (
                    f"📅 *Запланировано на:* {post.get('scheduled_time', 'неизвестно')}\n\n"
                    f"{post.get('text', '')}"
                )
                send_message(user_id, text, buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_list_scheduled"}]])
            return

        if payload.startswith("admin_edit_"):
            post_id = payload.replace("admin_edit_", "")
            data = _load_scheduled_posts()
            post = None
            for p in data.get("posts", []):
                if p["id"] == post_id:
                    post = p
                    break
            if post:
                _set_state(user_id, "admin_preview", {"post_data": post, "edit_post_id": post_id})
                _show_post_preview(user_id, post, edit_mode=True)
            return

        if payload.startswith("admin_delete_"):
            post_id = payload.replace("admin_delete_", "")
            data = _load_scheduled_posts()
            original_len = len(data.get("posts", []))
            data["posts"] = [p for p in data.get("posts", []) if p["id"] != post_id]
            if len(data["posts"]) < original_len:
                _save_scheduled_posts(data)
                send_message(user_id, "✅ Пост удалён.", buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_back_menu"}]])
            else:
                send_message(user_id, "❌ Пост не найден.", buttons=[[{"type": "callback", "text": "⬅️ Назад", "payload": "admin_back_menu"}]])
            return

        if state == "admin_preview":
            post_data = st["data"].get("post_data", {})
            edit_post_id = st["data"].get("edit_post_id")

            if payload == "admin_publish_now":
                msg_id = _publish_post_to_channel(post_data)
                if msg_id:
                    if edit_post_id:
                        data = _load_scheduled_posts()
                        data["posts"] = [p for p in data.get("posts", []) if p["id"] != edit_post_id]
                        _save_scheduled_posts(data)
                    send_message(user_id, f"✅ Пост опубликован в канале!", buttons=kb_admin_menu())
                else:
                    send_message(user_id, "❌ Ошибка публикации. Попробуйте снова.", buttons=kb_admin_menu())
                _set_state(user_id, "admin_idle")
                return

            if payload == "admin_schedule":
                _set_state(user_id, "admin_schedule_date", {})
                send_message(user_id, "📅 Выберите дату публикации:", buttons=kb_calendar())
                return

            if payload == "admin_edit_text":
                _set_state(user_id, "admin_edit_text", {})
                current = post_data.get("text", "")
                send_message(user_id, f"✏️ *Редактирование текста*\n\nТекущий текст:\n{current}\n\nВведите новый текст:")
                return

            if payload == "admin_edit_media":
                _set_state(user_id, "admin_add_media", {})
                send_message(user_id, "🖼 Загрузите новое медиа (фото/видео/документ):", buttons=[[{"type": "callback", "text": "🗑 Удалить медиа", "payload": "media_clear"}]])
                return

            if payload == "admin_edit_buttons":
                _set_state(user_id, "admin_choose_buttons", {})
                send_message(user_id, "🔘 Выберите кнопки для поста:", buttons=kb_button_types(post_data.get("buttons", [])))
                return

            if payload == "admin_cancel":
                _set_state(user_id, "admin_idle")
                send_message(user_id, "❌ Создание поста отменено.", buttons=kb_admin_menu())
                return

        if state == "admin_schedule_date" and payload.startswith("date_"):
            date_str = payload.replace("date_", "")
            _set_state(user_id, "admin_schedule_time", {"schedule_date": date_str})
            send_message(user_id, f"📅 Дата: {date_str}\n\n⏰ Выберите час:", buttons=kb_hours())
            return

        if payload == "schedule_cancel":
            _set_state(user_id, "admin_preview")
            post_data = st["data"].get("post_data", {})
            _show_post_preview(user_id, post_data, edit_mode=True)
            return

        if state == "admin_schedule_time" and payload.startswith("hour_"):
            hour = payload.replace("hour_", "")
            _set_state(user_id, "admin_schedule_minute", {"schedule_hour": hour})
            send_message(user_id, f"⏰ Час: {hour}\n\nВыберите минуты:", buttons=kb_minutes())
            return

        if state == "admin_schedule_minute" and payload.startswith("min_"):
            minute = payload.replace("min_", "")
            date_str = st["data"].get("schedule_date")
            hour = st["data"].get("schedule_hour")
            post_data = st["data"].get("post_data", {})
            edit_post_id = st["data"].get("edit_post_id")

            scheduled_time = f"{date_str}T{hour}:{minute}:00"
            post_data["scheduled_time"] = scheduled_time
            post_data["status"] = "scheduled"
            post_data["created_by"] = user_id
            post_data["created_at"] = datetime.now().isoformat()

            data = _load_scheduled_posts()
            if edit_post_id:
                data["posts"] = [p for p in data.get("posts", []) if p["id"] != edit_post_id]
            else:
                data["posts"] = [p for p in data.get("posts", []) if p["id"] != post_data["id"]]
            data["posts"].append(post_data)
            _save_scheduled_posts(data)

            _set_state(user_id, "admin_idle")
            send_message(user_id, f"✅ Пост запланирован на {scheduled_time}!")
            show_admin_menu(user_id)
            return

        if state == "admin_add_media":
            if payload == "media_clear":
                st_data = st["data"]
                if "post_data" in st_data:
                    st_data["post_data"]["media"] = []
                _set_state(user_id, "admin_preview", st_data)
                post_data = st_data.get("post_data", {})
                _show_post_preview(user_id, post_data, edit_mode=True)
                return
            if payload == "media_photo":
                _set_state(user_id, "admin_upload_media", {"media_type": "image"})
                send_message(user_id, "📸 Пришлите фото:")
                return
            if payload == "media_video":
                _set_state(user_id, "admin_upload_media", {"media_type": "video"})
                send_message(user_id, "🎬 Пришлите видео:")
                return
            if payload == "media_doc":
                _set_state(user_id, "admin_upload_media", {"media_type": "file"})
                send_message(user_id, "📎 Пришлите документ:")
                return
            if payload == "media_skip":
                _set_state(user_id, "admin_choose_buttons", {})
                send_message(user_id, "🔘 Выберите кнопки для поста:", buttons=kb_button_types())
                return

        if state == "admin_choose_buttons":
            if payload.startswith("toggle_"):
                btn = payload.replace("toggle_", "")
                post_data = st["data"].get("post_data", {})
                buttons = post_data.get("buttons", [])
                if btn in buttons:
                    buttons.remove(btn)
                else:
                    buttons.append(btn)
                post_data["buttons"] = buttons
                _set_state(user_id, "admin_choose_buttons", {"post_data": post_data})
                send_message(user_id, "🔘 Выберите кнопки:", buttons=kb_button_types(buttons))
                return
            if payload == "buttons_done" or payload == "buttons_skip":
                post_data = st["data"].get("post_data", {})
                if payload == "buttons_skip":
                    post_data["buttons"] = []
                _set_state(user_id, "admin_preview", {"post_data": post_data})
                _show_post_preview(user_id, post_data, edit_mode=True)
                return

        if payload == "admin_back_main":
            _set_state(user_id, "idle")
            show_main_menu(user_id)
            return

    # ====== ОБЫЧНЫЕ КОЛЛБЭКИ ======
    if payload == "menu_carousel":
        start_carousel_flow(user_id)
        return
    elif payload == "menu_neurophoto":
        send_message(user_id, "🖼 *Нейрофото*\n\nЭтот раздел в разработке. Скоро будет доступен!")
        return
    elif payload == "menu_homestaging":
        send_message(user_id, "🏡 *Хоумстейджинг*\n\nЭтот раздел в разработке. Скоро будет доступен!")
        return
    elif payload == "menu_subscription":
        send_message(user_id, "⭐ *Подписка*\n\nЭтот раздел в разработке. Скоро будет доступен!")
        return

    if payload.startswith("get_images_"):
        project_id = payload.split("_", 2)[2]
        _send_project_slides(user_id, project_id)
        # После отправки слайдов показываем меню пост-генерации
        _set_state(user_id, "generated", {**st["data"], "project_id": project_id})
        send_message(user_id, "👇 Что делаем дальше?", buttons=kb_post_generate(project_id))
        return

    if state == "waiting_slide_count" and payload.startswith("slides_"):
        count = int(payload.split("_")[1])
        _set_state(user_id, "waiting_theme", {"num_slides": count})
        send_message(user_id, "🎨 Выберите тему оформления:", buttons=kb_themes())
        return

    if state == "waiting_theme" and payload.startswith("theme_"):
        theme = payload.split("_", 1)[1]
        _set_state(user_id, "waiting_theme", {"theme": theme})
        _ask_watermark(user_id)
        return

    if state == "waiting_photo_slide_num":
        if payload.startswith("slide_num_"):
            sn = int(payload.split("_")[2])
            _set_state(user_id, "waiting_photo_upload", {
                "current_slide": sn,
                "project_id": st["data"].get("project_id"),
                "generated": st["data"].get("generated", []),
                "photos": st["data"].get("photos", {})
            })
            send_message(user_id, f"📤 Пришлите фото для *слайда {sn}*")
            return
        elif payload == "photos_done":
            project_id = st["data"].get("project_id")
            generated = st["data"].get("generated", [])
            _set_state(user_id, "waiting_regenerate", {
                "project_id": project_id,
                "generated": generated
            })
            preview = _format_preview(generated)
            send_message(user_id, preview, buttons=kb_regenerate())
            return

    if state == "waiting_watermark_confirm":
        if payload == "watermark_keep":
            saved = _get_user_watermark(user_id)
            _set_state(user_id, "generating", {
                "watermark_text": saved.get("text", ""),
                "watermark_position": saved.get("position", "bottom-left")
            })
            _do_generate(user_id)
            return
        elif payload == "watermark_new":
            _set_state(user_id, "waiting_watermark_text", {})
            send_message(user_id,
                "✍️ Введите новую подпись для слайдов (ник, телефон, @instagram и т.д.), или нажмите «Пропустить»:",
                buttons=kb_watermark_text())
            return

    if state == "waiting_watermark_text":
        if payload == "watermark_skip":
            _set_state(user_id, "waiting_watermark_position", {"watermark_text": ""})
            send_message(user_id, "📍 Выберите позицию подписи:", buttons=kb_watermark_positions())
            return

    if state == "waiting_watermark_position" and payload.startswith("wm_pos_"):
        pos = payload.split("_", 1)[1]
        st_data = st["data"]
        wm_text = st_data.get("watermark_text", "")
        _set_user_watermark(user_id, wm_text, pos)
        _set_state(user_id, "generating", {"watermark_position": pos, "watermark_text": wm_text})
        _do_generate(user_id)
        return

    if state == "waiting_regenerate" and payload == "edit_slides":
        generated = st["data"].get("generated", [])
        count = len(generated)
        _set_state(user_id, "waiting_edit_slide", {})
        send_message(user_id, "✏️ *Редактирование*\n\nВыберите слайд:", buttons=kb_edit_slides(count))
        return

    if state == "waiting_edit_slide":
        if payload == "back_to_preview":
            generated = st["data"].get("generated", [])
            project_id = st["data"].get("project_id")
            _show_edit_preview(user_id, generated, project_id)
            return
        if payload.startswith("edit_slide_"):
            sn = int(payload.split("_")[2])
            generated = st["data"].get("generated", [])
            if 1 <= sn <= len(generated):
                current = generated[sn - 1]
                _set_state(user_id, "waiting_edit_field", {"edit_slide": sn})
                send_message(user_id,
                    f"✏️ *Слайд {sn}*\n\n"
                    f"📝 Заголовок: {current['title']}\n"
                    f"📝 Подзаголовок: {current['subtitle']}\n"
                    f"📝 Текст: {current['body'][:100]}...\n\n"
                    f"Что хотите изменить?",
                    buttons=kb_edit_fields())
            return

    if state == "waiting_edit_text" and payload == "edit_keep":
        generated = st["data"].get("generated", [])
        project_id = st["data"].get("project_id")
        _show_edit_preview(user_id, generated, project_id)
        return

    if state == "waiting_edit_field":
        if payload == "edit_slides":
            generated = st["data"].get("generated", [])
            count = len(generated)
            _set_state(user_id, "waiting_edit_slide", {})
            send_message(user_id, "✏️ Выберите слайд:", buttons=kb_edit_slides(count))
            return
        if payload.startswith("edit_field_"):
            field = payload.split("_", 2)[2]
            sn = st["data"].get("edit_slide", 1)
            generated = st["data"].get("generated", [])
            current_text = generated[sn - 1].get(field, "")
            _set_state(user_id, "waiting_edit_text", {"edit_field": field, "edit_slide": sn})
            send_message(user_id,
                f"✏️ *Слайд {sn} — {field}*\n\n"
                f"Текущий текст:\n{current_text}\n\n"
                f"Пришлите исправленный текст целиком.\n"
                f"(или «-» чтобы очистить поле)",
                buttons=[[{"type": "callback", "text": "⏭ Оставить как есть", "payload": "edit_keep"}]])
            return

    if state == "waiting_regenerate":
        if payload == "regenerate":
            _set_state(user_id, "generating")
            _do_generate(user_id)
            return
        elif payload == "add_photos":
            project_id = st["data"].get("project_id")
            project = get_project(project_id)
            count = len(project["slides"]) if project else st["data"].get("num_slides", 5)
            _set_state(user_id, "waiting_photo_slide_num", {
                "photos": {},
                "project_id": project_id,
                "generated": st["data"].get("generated", [])
            })
            send_message(user_id,
                f"📤 Выберите слайд (1–{count}), на который загрузить фото,\n"
                f"или нажмите «Готово», если фото не нужны.",
                buttons=kb_slide_numbers(count))
            return
        elif payload == "generate_final":
            project_id = st["data"]["project_id"]
            _set_state(user_id, "generated", st["data"])
            send_message(user_id,
                f"✅ Карусель готова!\n\n"
                f"Можете скачать слайды здесь или отредактировать на сервере.",
                buttons=kb_final(project_id))
            return

    # ====== ПОСТ-ГЕНЕРАЦИЯ: тема, фон, текст ======
    if state == "generated":
        project_id = st["data"].get("project_id")
        if not project_id:
            send_message(user_id, "❌ Ошибка: проект не найден. Начните заново.")
            show_main_menu(user_id)
            return

        if payload == "postgen_theme":
            project = get_project(project_id)
            count = len(project["slides"]) if project else st["data"].get("num_slides", 5)
            _set_state(user_id, "waiting_slide_theme_select", st["data"])
            send_message(user_id, "🌗 Выберите слайд для смены темы:", buttons=kb_slide_theme_select(count))
            return

        if payload == "postgen_bg":
            project = get_project(project_id)
            count = len(project["slides"]) if project else st["data"].get("num_slides", 5)
            _set_state(user_id, "waiting_slide_bg_select", st["data"])
            send_message(user_id, "📸 Выберите слайд для работы с фоном:", buttons=kb_slide_bg_select(count))
            return

        if payload == "postgen_edit_text":
            generated = st["data"].get("generated", [])
            count = len(generated)
            _set_state(user_id, "waiting_edit_slide", st["data"])
            send_message(user_id, "✏️ Выберите слайд для редактирования текста:", buttons=kb_edit_slides(count))
            return

        if payload == "postgen_regenerate":
            _set_state(user_id, "generating", st["data"])
            _do_generate(user_id)
            return

    if state == "waiting_slide_theme_select":
        if payload.startswith("theme_slide_"):
            sn = int(payload.split("_")[2])
            project_id = st["data"].get("project_id")
            new_path, new_mode = _toggle_slide_theme(project_id, sn)
            if new_path and os.path.exists(new_path):
                ok = upload_and_send_image(user_id, new_path, caption=f"🌗 Слайд {sn} — тема: {new_mode}")
                if ok:
                    send_message(user_id, f"✅ Слайд {sn} перерендерен в режиме *{new_mode}*!")
                else:
                    send_message(user_id, f"⚠️ Слайд {sn} сохранён, но не удалось отправить. Попробуйте «Получить слайды снова».")
            else:
                send_message(user_id, f"⚠️ Не удалось перерендерить слайд {sn}. Попробуйте ещё раз.")
            # Возвращаемся в меню пост-генерации
            _set_state(user_id, "generated", st["data"])
            send_message(user_id, "👇 Что делаем дальше?", buttons=kb_post_generate(project_id))
            return

    if state == "waiting_slide_bg_select":
        if payload.startswith("bg_slide_"):
            sn = int(payload.split("_")[2])
            _set_state(user_id, "waiting_bg_actions", {**st["data"], "bg_slide_num": sn})
            send_message(user_id, f"📸 Слайд {sn} — выберите действие:", buttons=kb_slide_actions())
            return

    if state == "waiting_bg_actions":
        sn = st["data"].get("bg_slide_num", 1)
        project_id = st["data"].get("project_id")

        if payload == "bg_add_photo":
            _set_state(user_id, "waiting_bg_upload", st["data"])
            send_message(user_id, f"📤 Пришлите фото для *слайда {sn}* (будет использовано как фон):")
            return

        if payload == "bg_remove":
            new_path = _remove_slide_background(project_id, sn)
            if new_path and os.path.exists(new_path):
                ok = upload_and_send_image(user_id, new_path, caption=f"🗑 Слайд {sn} — фон удалён")
                if ok:
                    send_message(user_id, f"✅ Фон слайда {sn} удалён!")
                else:
                    send_message(user_id, f"⚠️ Фон удалён, но не удалось отправить слайд.")
            else:
                send_message(user_id, f"⚠️ Не удалось перерендерить слайд {sn}.")
            _set_state(user_id, "generated", st["data"])
            send_message(user_id, "👇 Что делаем дальше?", buttons=kb_post_generate(project_id))
            return

    print(f"⚠️ Необработанный callback: {payload} в state {state}")


def _ask_watermark(user_id):
    saved = _get_user_watermark(user_id)
    if saved and saved.get("text"):
        _set_state(user_id, "waiting_watermark_confirm", {})
        send_message(user_id,
            f"💾 У вас сохранена подпись:\n\n"
            f"'{saved['text']}'\n\n"
            f"Оставить её?",
            buttons=kb_watermark_confirm(saved["text"], saved.get("position", "bottom-left")))
    else:
        _set_state(user_id, "waiting_watermark_text", {})
        send_message(user_id,
            "✍️ Введите подпись для слайдов (ник, телефон, @instagram и т.д.), или нажмите «Пропустить»:",
            buttons=kb_watermark_text())


def handle_message(upd, user_id, text, attachments):
    st = _get_state(user_id)
    state = st["state"]
    print(f"💬 [{user_id}] msg: '{text[:80]}...' len={len(text)} | state: {state}")

    # Команда /start — показываем главное меню
    if text and text.strip() == "/start":
        show_main_menu(user_id)
        return

    # Команда /admin — вход в админ-панель
    if text and text.strip() == "/admin":
        if is_admin(user_id):
            _set_state(user_id, "admin_idle")
            show_admin_menu(user_id)
        else:
            send_message(user_id, "⛔ У вас нет доступа к админ-панели.")
        return

    # ==================== АДМИН-СООБЩЕНИЯ ====================
    if is_admin(user_id):
        if state == "admin_enter_text":
            if not text or not text.strip():
                send_message(user_id, "❌ Текст не может быть пустым. Введите текст поста:")
                return
            post_data = st["data"].get("post_data", {})
            post_data["text"] = text.strip()
            _set_state(user_id, "admin_add_media", {"post_data": post_data})
            send_message(user_id, "🖼 Добавить медиа к посту?", buttons=kb_media_choice())
            return

        if state == "admin_upload_media":
            media_type = st["data"].get("media_type", "image")
            media_url = None
            file_token = None

            for att in (attachments or []):
                att_type = att.get("type", "")
                pld = att.get("payload", {})

                if att_type == "image" and media_type == "image":
                    media_url = pld.get("url") or pld.get("src")
                    file_token = pld.get("token")
                elif att_type == "video" and media_type == "video":
                    media_url = pld.get("url") or pld.get("src")
                    file_token = pld.get("token")
                elif att_type in ["file", "document"] and media_type == "file":
                    media_url = pld.get("url") or pld.get("src")
                    file_token = pld.get("token")

                if not media_url and file_token:
                    media_url = f"{BASE_URL}/images/{file_token}"

                if media_url:
                    break

            if not media_url:
                send_message(user_id, "❌ Не вижу медиа. Прикрепите файл и отправьте.")
                return

            try:
                resp = requests.get(media_url, verify=False, timeout=30)
                if resp.status_code != 200:
                    send_message(user_id, "❌ Не удалось скачать файл. Попробуйте ещё раз.")
                    return

                os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
                ext = ".jpg"
                if ".png" in media_url.lower():
                    ext = ".png"
                elif ".webp" in media_url.lower():
                    ext = ".webp"
                elif ".mp4" in media_url.lower():
                    ext = ".mp4"
                elif ".pdf" in media_url.lower():
                    ext = ".pdf"

                filename = f"admin_{user_id}_{uuid.uuid4().hex[:8]}{ext}"
                filepath = os.path.join(config.UPLOAD_FOLDER, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)

                token = upload_media_get_token(filepath, media_type)
                if not token:
                    send_message(user_id, "❌ Ошибка загрузки медиа на сервер. Попробуйте ещё раз.")
                    return

                post_data = st["data"].get("post_data", {})
                if "media" not in post_data:
                    post_data["media"] = []
                post_data["media"].append({
                    "type": media_type,
                    "token": token,
                    "local_path": filepath
                })

                _set_state(user_id, "admin_add_media", {"post_data": post_data})
                send_message(user_id,
                    f"✅ Медиа добавлено!\n\n"
                    f"Добавить ещё или продолжить?",
                    buttons=kb_media_choice())
            except Exception as e:
                print(f"[admin_upload_media] Error: {e}")
                import traceback
                traceback.print_exc()
                send_message(user_id, "❌ Ошибка обработки медиа. Попробуйте ещё раз.")
            return

        if state == "admin_edit_text":
            if not text:
                send_message(user_id, "❌ Текст не может быть пустым. Введите новый текст:")
                return
            post_data = st["data"].get("post_data", {})
            post_data["text"] = text.strip()
            _set_state(user_id, "admin_preview", {"post_data": post_data})
            _show_post_preview(user_id, post_data, edit_mode=True)
            return

    # ==================== ОБЫЧНЫЕ СООБЩЕНИЯ ====================
    if state == "waiting_text":
        if not text or not text.strip():
            print(f"[handle_message] Пустой текст от {user_id}, прошу повторить")
            send_message(user_id, "❌ Текст не получен. Пожалуйста, введите текст статьи:")
            return

        print(f"[handle_message] Получен текст статьи от {user_id}: '{text[:200]}...' len={len(text)}")
        _set_state(user_id, "waiting_slide_count", {"article_text": text})
        send_message(user_id, "📊 Выберите количество слайдов:", buttons=kb_slide_counts())
        return

    if state == "waiting_photo_upload":
        image_url = None
        for att in (attachments or []):
            if att.get("type") == "image":
                pld = att.get("payload", {})
                image_url = pld.get("url") or pld.get("src")
                if not image_url and "token" in pld:
                    image_url = f"{BASE_URL}/images/{pld['token']}"
                break

        if not image_url:
            send_message(user_id, "❌ Не вижу фото. Прикрепите изображение через скрепку и отправьте.")
            return

        try:
            img_resp = requests.get(image_url, verify=False, timeout=30)
            if img_resp.status_code != 200:
                send_message(user_id, "❌ Не удалось скачать фото с сервера. Попробуйте ещё раз.")
                return

            os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
            sn = st["data"]["current_slide"]
            ext = ".jpg"
            if ".png" in image_url.lower():
                ext = ".png"
            elif ".webp" in image_url.lower():
                ext = ".webp"
            filename = f"user_{user_id}_slide_{sn}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(config.UPLOAD_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            photos = st["data"].get("photos", {})
            photos[sn] = filepath

            project_id = st["data"].get("project_id")
            if project_id:
                project = get_project(project_id)
                if project:
                    for slide in project["slides"]:
                        if slide.get("order") == sn - 1:
                            slide["background_image"] = filepath
                    save_project(project)

            project = get_project(project_id) if project_id else None
            count = len(project["slides"]) if project else st["data"].get("num_slides", 5)
            _set_state(user_id, "waiting_photo_slide_num", {
                "photos": photos,
                "project_id": project_id,
                "generated": st["data"].get("generated", [])
            })

            filled = list(photos.keys())
            send_message(user_id,
                f"✅ Фото для слайда {sn} сохранено!\n\n"
                f"Выберите следующий слайд или нажмите «Готово».",
                buttons=kb_slide_numbers(count, exclude=filled))
        except Exception as e:
            print(f"[handle_message] photo error: {e}")
            import traceback
            traceback.print_exc()
            send_message(user_id, "❌ Ошибка обработки фото. Попробуйте ещё раз.")
        return

    if state == "waiting_watermark_text":
        if not text or not text.strip():
            send_message(user_id, "❌ Введите текст подписи или нажмите «Пропустить»:", buttons=kb_watermark_text())
            return
        _set_state(user_id, "waiting_watermark_position", {"watermark_text": text.strip()})
        send_message(user_id, "📍 Выберите позицию подписи:", buttons=kb_watermark_positions())
        return

    if state == "waiting_edit_text":
        if not text:
            send_message(user_id, "❌ Введите новый текст или отправьте «-» чтобы очистить поле.")
            return
        new_text = "" if text.strip() == "-" else text.strip()
        field = st["data"].get("edit_field")
        sn = st["data"].get("edit_slide", 1)
        project_id = st["data"].get("project_id")

        if not field or not project_id:
            send_message(user_id, "❌ Ошибка: не найден проект. Начните заново.")
            _set_state(user_id, "idle")
            return

        updated_generated = _update_slide_field(project_id, sn, field, new_text)
        if updated_generated is None:
            send_message(user_id, "❌ Ошибка обновления слайда.")
            return

        _set_state(user_id, "waiting_regenerate", {
            "project_id": project_id,
            "generated": updated_generated
        })

        send_message(user_id, f"✅ *Слайд {sn} обновлён!*\n\n{field}: {new_text or '(пусто)'}\n\nПоказываю обновлённое превью...")
        preview = _format_preview(updated_generated)
        send_message(user_id, preview, buttons=kb_regenerate())
        return

    # === НОВОЕ: загрузка фона на финальном этапе ===
    if state == "waiting_bg_upload":
        image_url = None
        for att in (attachments or []):
            if att.get("type") == "image":
                pld = att.get("payload", {})
                image_url = pld.get("url") or pld.get("src")
                if not image_url and "token" in pld:
                    image_url = f"{BASE_URL}/images/{pld['token']}"
                break

        if not image_url:
            send_message(user_id, "❌ Не вижу фото. Прикрепите изображение и отправьте.")
            return

        try:
            img_resp = requests.get(image_url, verify=False, timeout=30)
            if img_resp.status_code != 200:
                send_message(user_id, "❌ Не удалось скачать фото. Попробуйте ещё раз.")
                return

            os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
            sn = st["data"]["bg_slide_num"]
            ext = ".jpg"
            if ".png" in image_url.lower():
                ext = ".png"
            elif ".webp" in image_url.lower():
                ext = ".webp"
            filename = f"user_{user_id}_bg_slide_{sn}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(config.UPLOAD_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            project_id = st["data"].get("project_id")
            new_path = _set_slide_background(project_id, sn, filepath)

            if new_path and os.path.exists(new_path):
                ok = upload_and_send_image(user_id, new_path, caption=f"📸 Слайд {sn} — фон обновлён")
                if ok:
                    send_message(user_id, f"✅ Фон для слайда {sn} установлен!")
                else:
                    send_message(user_id, f"⚠️ Фон сохранён, но не удалось отправить слайд.")
            else:
                send_message(user_id, f"⚠️ Не удалось перерендерить слайд {sn}.")

            _set_state(user_id, "generated", st["data"])
            send_message(user_id, "👇 Что делаем дальше?", buttons=kb_post_generate(project_id))
        except Exception as e:
            print(f"[handle_message] bg upload error: {e}")
            import traceback
            traceback.print_exc()
            send_message(user_id, "❌ Ошибка обработки фона. Попробуйте ещё раз.")
        return

    if state == "idle":
        show_main_menu(user_id)


# ==================== ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ MAX API ====================
def extract_message_text(msg):
    text = msg.get("text")
    if text:
        return text

    body = msg.get("body", {})
    if isinstance(body, dict):
        text = body.get("text")
        if text:
            return text
    elif isinstance(body, str):
        return body

    content = msg.get("content", {})
    if isinstance(content, dict):
        text = content.get("text")
        if text:
            return text

    msg_str = json.dumps(msg, ensure_ascii=False)
    if '"text"' in msg_str:
        try:
            import re
            texts = re.findall(r'"text"\s*:\s*"([^"]+)"', msg_str)
            for t in texts:
                if len(t) > 5:
                    return t
        except:
            pass

    return ""


def extract_message_attachments(msg):
    atts = msg.get("attachments")
    if atts:
        return atts

    body = msg.get("body", {})
    if isinstance(body, dict):
        atts = body.get("attachments")
        if atts:
            return atts

    return []


# ==================== ГЛАВНЫЙ ЦИКЛ ====================
def main():
    print("🚀 MAX Carousel Bot запущен!")
    print("=" * 50)
    print("\n1️⃣ Отправляю пост с кнопками в канал...")
    send_post_to_channel()

    print("\n2️⃣ Запускаю планировщик постов...")
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    print("\n3️⃣ Слушаю обновления (bot_started, callback, сообщения)...")
    print("   • Нажмите 🏠 или 🎠 в канале MAX")
    print("   • Админы: отправьте /admin для входа в панель")
    print("   • Ctrl+C — остановить\n")

    current_marker = None
    while True:
        data = get_updates(current_marker)
        updates = data.get("updates", [])
        current_marker = data.get("marker", current_marker)

        for upd in updates:
            utype = upd.get("update_type")

            if utype == "bot_started":
                handle_bot_started(upd)

            elif utype == "message_callback":
                cb = upd.get("callback", {})
                cb_id = cb.get("callback_id") or upd.get("callback_id")
                payload = cb.get("payload") or upd.get("payload")
                if cb_id and payload:
                    handle_callback(upd, cb_id, payload)

            elif utype == "message_created":
                msg = upd.get("message", {})
                text = extract_message_text(msg)
                attachments = extract_message_attachments(msg)

                if not text:
                    print(f"[DEBUG] message_created structure: {json.dumps(msg, ensure_ascii=False, indent=2)[:800]}")

                user_id = _extract_user_id(upd)
                if user_id:
                    handle_message(upd, user_id, text, attachments)

        time.sleep(1)


if __name__ == "__main__":
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(config.PROJECTS_FOLDER, exist_ok=True)
    main()