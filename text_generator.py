
import os
import sys
import asyncio
import random
import json
import re
import time
import traceback
from typing import List, Dict, Optional, Tuple
import g4f

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ==================== НАСТРОЙКИ ====================
MODELS = [
    "command-a",
]

PROXY_LIST = [
    "http://LLxeax:1FuUet@186.65.117.79:9180",
    # ... остальные прокси
]

REQUEST_TIMEOUT = 60
MAX_RETRIES = 2

REQUESTS_PER_PROXY_PER_HOUR = 200
MIN_PROXY_REST_TIME = 1800
ERROR_THRESHOLD_FOR_PAUSE = 8
ERROR_THRESHOLD_FOR_MODEL_SWITCH = 3
MIN_PAUSE_DURATION = 300
MAX_PAUSE_DURATION = 3600


# ==================== SMART PROXY MANAGER ====================
class SmartProxyManager:
    """Умный менеджер прокси с раздельной статистикой по моделям"""

    def __init__(self, proxy_list: List[str], models: List[str]):
        self.all_proxies = proxy_list
        self.models = models
        self.model_proxy_stats: Dict[str, Dict[str, Dict]] = {}
        self._init_model_proxy_stats()
        print(f"[SmartProxy] Инициализировано {len(self.all_proxies)} прокси для {len(self.models)} моделей")

    def _init_model_proxy_stats(self):
        for model in self.models:
            self.model_proxy_stats[model] = {}
            for proxy in self.all_proxies:
                self.model_proxy_stats[model][proxy] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'consecutive_fails': 0,
                    'last_used': None,
                    'last_success': None,
                    'hourly_requests': 0,
                    'hour_start_time': time.time(),
                    'is_active': True,
                    'rest_until': None,
                    'rest_count': 0
                }

    def get_available_proxy(self, model: str) -> Optional[str]:
        current_time = time.time()
        if model not in self.model_proxy_stats:
            return None

        model_stats = self.model_proxy_stats[model]
        available_proxies = []

        for proxy, stats in model_stats.items():
            if not stats['is_active']:
                continue
            if stats['rest_until'] and current_time < stats['rest_until']:
                continue
            if current_time - stats['hour_start_time'] > 3600:
                stats['hourly_requests'] = 0
                stats['hour_start_time'] = current_time
                stats['consecutive_fails'] = 0
            if stats['hourly_requests'] < REQUESTS_PER_PROXY_PER_HOUR:
                available_proxies.append(proxy)

        if not available_proxies:
            for proxy, stats in model_stats.items():
                if stats['is_active']:
                    available_proxies.append(proxy)

        if not available_proxies:
            return None

        proxy = min(available_proxies, key=lambda p: model_stats[p]['hourly_requests'])
        stats = model_stats[proxy]
        stats['hourly_requests'] += 1
        stats['total_requests'] += 1
        stats['last_used'] = current_time
        return proxy

    def mark_proxy_success(self, proxy: str, model: str):
        if model in self.model_proxy_stats and proxy in self.model_proxy_stats[model]:
            stats = self.model_proxy_stats[model][proxy]
            stats['successful_requests'] += 1
            stats['last_success'] = time.time()
            stats['consecutive_fails'] = 0
            stats['rest_count'] = 0

    def mark_proxy_failed(self, proxy: str, model: str, reason: str = ""):
        if model in self.model_proxy_stats and proxy in self.model_proxy_stats[model]:
            stats = self.model_proxy_stats[model][proxy]
            stats['failed_requests'] += 1
            stats['consecutive_fails'] += 1
            if stats['consecutive_fails'] >= 3:
                stats['is_active'] = False
                stats['rest_count'] += 1
                base_rest_time = MIN_PROXY_REST_TIME
                dynamic_rest_time = base_rest_time * (stats['rest_count'] ** 0.5)
                stats['rest_until'] = time.time() + min(dynamic_rest_time, MAX_PAUSE_DURATION)
                print(
                    f"[SmartProxy] Прокси {proxy.split('@')[-1]} для модели {model} на отдыхе {dynamic_rest_time / 60:.1f} мин. Причина: {reason}")

    def reactivate_rested_proxies(self, model: str) -> int:
        current_time = time.time()
        reactivated = 0
        if model not in self.model_proxy_stats:
            return 0
        model_stats = self.model_proxy_stats[model]
        for proxy, stats in model_stats.items():
            if not stats['is_active'] and stats['rest_until'] and current_time >= stats['rest_until']:
                stats['is_active'] = True
                stats['rest_until'] = None
                stats['consecutive_fails'] = 0
                stats['hourly_requests'] = 0
                stats['hour_start_time'] = current_time
                reactivated += 1
        return reactivated

    def get_working_proxies_count(self, model: str) -> int:
        if model not in self.model_proxy_stats:
            return 0
        current_time = time.time()
        model_stats = self.model_proxy_stats[model]
        return sum(1 for stats in model_stats.values()
                   if stats['is_active'] and (not stats['rest_until'] or current_time >= stats['rest_until']))

    def reset_model_proxy_stats(self, old_model: str, new_model: str):
        if old_model in self.model_proxy_stats:
            for proxy_stats in self.model_proxy_stats[old_model].values():
                proxy_stats['consecutive_fails'] = max(0, proxy_stats['consecutive_fails'] - 1)


# ==================== ПРОМПТ ====================
CAROUSEL_PROMPT_TEMPLATE = """Ты — профессиональный копирайтер-нейромаркетолог, специалист по вирусному контенту для Instagram.

Твоя задача — превратить исходный текст статьи в цепляющую карусель слайдов. Каждый слайд должен выглядеть как на профессиональных референсах: крупный заголовок сверху, подзаголовок другим цветом, основной текст снизу — всё на фоне фотографии с тёмным/светлым градиентом снизу.

### СТИЛЬ КАЖДОГО СЛАЙДА:
1. Заголовок — крупный, цепляющий. До 6 слов. Шок, цифры, вопросы, факты.
2. Подзаголовок — уточняет заголовок. До 10 слов.
3. Основной текст — конкретика, факты, цифры. 1-2 коротких предложения.

### ВЫДЕЛЕНИЕ ТРИГГЕРНЫХ СЛОВ (КРИТИЧЕСКИ ВАЖНО):
На КАЖДОМ слайде выдели 1-2 ключевых слова, которые требуют внимания.
Используй синтаксис: ==выделенный текст==

Примеры:
- "Есть ==проблемные объекты==, риски при покупке которых слишком высоки"
- "==Невидимые жильцы== — люди, отказавшиеся от приватизации"
- "==Семейные проблемы== — продажа без согласия супруга"
- "==Сделки под угрозой== — собственники-должники на грани банкротства"
- "==Напишите мне== — защитим ваши сбережения"

Правила выделения:
- Выделяй только самые важные, эмоционально заряженные слова/фразы
- Не выделяй больше 3 слов на слайд
- Выделение должно быть естественным — как будто маркером подчеркнули главное
- Можно выделять в заголовке, подзаголовке или основном тексте

### ПРИНЦИПЫ:
- Эмоциональный якорь на каждом слайде
- Простота, конкретика, цифры, сравнения
- Контраст: "было/стало", "мнение толпы / инсайд"
- Призыв к действию на последнем слайде

### ФОРМАТ ОТВЕТА (строго):
Для КАЖДОГО слайда выведи ТОЛЬКО:
TITLE: [заголовок с ==выделениями==]
SUBTITLE: [подзаголовок с ==выделениями==]
BODY: [основной текст]

Ничего лишнего. Только слайды.
Не используй emoji и лишние символы в тексте.
TITLE SUBTITLE BODY должны быть связаны по смыслу у каждого слайда, так как каждый слайд в целом это смысл.

Исходный текст:
{article_text}

Количество слайдов: {slide_count}

Сгенерируй:"""


# ==================== ПАРСЕР С ЛОГИРОВАНИЕМ ====================
def parse_highlighted_text(text: str) -> List[Dict]:
    """
    Parse text with ==highlight== markers into segments.
    Returns list of dicts: {'text': str, 'highlight': bool}
    """
    segments = []
    pattern = r'==(.*?)=='
    last_end = 0

    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            segments.append({
                'text': text[last_end:match.start()],
                'highlight': False
            })
        segments.append({
            'text': match.group(1),
            'highlight': True
        })
        last_end = match.end()

    if last_end < len(text):
        segments.append({
            'text': text[last_end:],
            'highlight': False
        })

    return segments


def parse_generated_carousel(text: str, num_slides: int) -> List[Dict[str, str]]:
    """Парсит ответ LLM в структуру слайдов. Подробное логирование каждого этапа."""

    print(f"[PARSE] Начинаю парсинг. Длина ответа: {len(text)} символов")
    print(f"[PARSE] Первые 800 символов ответа:\n{text[:800]}\n[PARSE] ...конец превью")

    slides = []

    # === Формат **СЛАЙД N** или **SLIDE N** (с markdown-звёздочками) ===
    slide_blocks = re.split(r'\*\*\s*(?:СЛАЙД|SLIDE)\s*(\d+)\s*\*\*', text, flags=re.IGNORECASE)
    print(f"[PARSE] Попытка 1 (markdown **СЛАЙД N**): найдено {len(slide_blocks)} блоков")

    for i in range(1, len(slide_blocks), 2):
        if i + 1 < len(slide_blocks):
            content = slide_blocks[i + 1].strip()
            title = subtitle = body = ""
            title_match = re.search(r'TITLE:\s*(.*?)(?=\nSUBTITLE:|\nBODY:|$)', content, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip().replace("—"," - ")
            subtitle_match = re.search(r'SUBTITLE:\s*(.*?)(?=\nBODY:|$)', content, re.DOTALL)
            if subtitle_match:
                subtitle = subtitle_match.group(1).strip().replace("—"," - ")
            body_match = re.search(r'BODY:\s*(.*?)(?=\n\*\*\s*(?:СЛАЙД|SLIDE)|$)', content, re.DOTALL)
            if body_match:
                body = body_match.group(1).strip().replace("—"," - ")

            print(f"[PARSE] Слайд {len(slides)+1}: title=\"{title[:60]}...\" subtitle=\"{subtitle[:60]}...\" body=\"{body[:60]}...\"")

            slides.append({
                'title': title,
                'subtitle': subtitle,
                'body': body,
                'title_segments': parse_highlighted_text(title),
                'subtitle_segments': parse_highlighted_text(subtitle),
                'body_segments': parse_highlighted_text(body)
            })

    # === Формат SLIDE_N (без звёздочек, английский) ===
    if not slides:
        print("[PARSE] Попытка 1 не сработала. Пробую формат SLIDE_N")
        slide_blocks = re.split(r'SLIDE_(\d+)', text)
        print(f"[PARSE] Попытка 2 (SLIDE_N): найдено {len(slide_blocks)} блоков")

        for i in range(1, len(slide_blocks), 2):
            if i + 1 < len(slide_blocks):
                content = slide_blocks[i + 1].strip()
                title = subtitle = body = ""
                title_match = re.search(r'TITLE:\s*(.*?)(?=\nSUBTITLE:|\nBODY:|$)', content, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                subtitle_match = re.search(r'SUBTITLE:\s*(.*?)(?=\nBODY:|$)', content, re.DOTALL)
                if subtitle_match:
                    subtitle = subtitle_match.group(1).strip()
                body_match = re.search(r'BODY:\s*(.*?)(?=\nSLIDE_|$)', content, re.DOTALL)
                if body_match:
                    body = body_match.group(1).strip()

                print(f"[PARSE] Слайд {len(slides)+1}: title=\"{title[:60]}...\" subtitle=\"{subtitle[:60]}...\" body=\"{body[:60]}...\"")

                slides.append({
                    'title': title,
                    'subtitle': subtitle,
                    'body': body,
                    'title_segments': parse_highlighted_text(title),
                    'subtitle_segments': parse_highlighted_text(subtitle),
                    'body_segments': parse_highlighted_text(body)
                })

    # === Альтернативный формат (русские метки: Слайд, Заголовок, Подзаголовок) ===
    if not slides:
        print("[PARSE] Попытка 2 не сработала. Пробую русские метки")
        blocks = re.split(r'[-=]{3,}\s*Слайд\s*\d+.*?(?=[-=]{3,}\s*Слайд|$)', text, flags=re.IGNORECASE)
        print(f"[PARSE] Попытка 3 (русские метки): найдено {len(blocks)} блоков")

        for block in blocks[1:]:
            title_match = re.search(r'Заголовок:\s*(.*?)(?=\nПодзаголовок:|\nОсновной текст:|$)', block,
                                    re.DOTALL | re.IGNORECASE)
            subtitle_match = re.search(r'Подзаголовок:\s*(.*?)(?=\nОсновной текст:|$)', block,
                                       re.DOTALL | re.IGNORECASE)
            body_match = re.search(r'Основной текст:\s*(.*?)(?=\nТриггеры:|\nКлиффхэнгер:|$)', block,
                                   re.DOTALL | re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            subtitle = subtitle_match.group(1).strip() if subtitle_match else ""
            body = body_match.group(1).strip() if body_match else ""

            print(f"[PARSE] Слайд {len(slides)+1}: title=\"{title[:60]}...\" subtitle=\"{subtitle[:60]}...\" body=\"{body[:60]}...\"")

            if title or body:
                slides.append({
                    'title': title,
                    'subtitle': subtitle,
                    'body': body,
                    'title_segments': parse_highlighted_text(title),
                    'subtitle_segments': parse_highlighted_text(subtitle),
                    'body_segments': parse_highlighted_text(body)
                })

    # === Fallback: просто ищем TITLE/SUBTITLE/BODY без разделителей слайдов ===
    if not slides:
        print("[PARSE] Все попытки с разделителями провалились. Пробую fallback — поиск TITLE/SUBTITLE/BODY")

        # Находим все TITLE
        titles = re.findall(r'TITLE:\s*(.*?)(?=\nSUBTITLE:|\nBODY:|\nTITLE:|$)', text, re.DOTALL)
        subtitles = re.findall(r'SUBTITLE:\s*(.*?)(?=\nBODY:|\nTITLE:|$)', text, re.DOTALL)
        bodies = re.findall(r'BODY:\s*(.*?)(?=\nTITLE:|$)', text, re.DOTALL)

        print(f"[PARSE] Fallback: найдено {len(titles)} TITLE, {len(subtitles)} SUBTITLE, {len(bodies)} BODY")

        count = min(len(titles), num_slides)
        for i in range(count):
            title = titles[i].strip().replace("—"," - ") if i < len(titles) else ""
            subtitle = subtitles[i].strip().replace("—"," - ") if i < len(subtitles) else ""
            body = bodies[i].strip().replace("—"," - ") if i < len(bodies) else ""

            print(f"[PARSE] Слайд {i+1}: title=\"{title[:60]}...\" subtitle=\"{subtitle[:60]}...\" body=\"{body[:60]}...\"")

            slides.append({
                'title': title,
                'subtitle': subtitle,
                'body': body,
                'title_segments': parse_highlighted_text(title),
                'subtitle_segments': parse_highlighted_text(subtitle),
                'body_segments': parse_highlighted_text(body)
            })

    print(f"[PARSE] ИТОГО: распарсено {len(slides)} слайдов из {num_slides} запрошенных")

    if not slides:
        print("[PARSE] ВНИМАНИЕ: слайды не распарсились! Весь ответ для отладки:")
        print("=" * 60)
        print(text)
        print("=" * 60)
        return []

    return slides[:num_slides]


# ==================== ГЕНЕРАТОР С РОТАЦИЕЙ ====================
class CarouselGenerator:
    def __init__(self):
        self.proxy_manager = SmartProxyManager(PROXY_LIST, MODELS)
        self.models = MODELS
        self.current_model_index = 0
        self.current_model = self.models[0]
        self.model_failures = {model: 0 for model in self.models}
        self.consecutive_errors = 0

    def _switch_model(self):
        old_model = self.current_model
        self.model_failures[old_model] += 1
        available = [m for m in self.models if m != old_model]
        if available:
            self.current_model = min(available, key=lambda m: self.model_failures[m])
        else:
            self.current_model_index = (self.current_model_index + 1) % len(self.models)
            self.current_model = self.models[self.current_model_index]
        self.proxy_manager.reset_model_proxy_stats(old_model, self.current_model)
        self.consecutive_errors = 0
        print(f"[CarouselGenerator] Смена модели: {old_model} -> {self.current_model}")

    async def make_g4f_request(self, prompt: str, proxy: str) -> Optional[str]:
        print(f"[G4F] Отправка запроса. Модель: {self.current_model}, прокси: {proxy.split('@')[-1]}")
        print(f"[G4F] Длина промпта: {len(prompt)} символов")

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    g4f.ChatCompletion.create,
                    model=self.current_model,
                    messages=[{"role": "user", "content": prompt}],
                    proxy=proxy,
                ),
                timeout=REQUEST_TIMEOUT
            )

            print(f"[G4F] Тип ответа: {type(response)}")

            # Отладка: показываем первые 1000 символов
            raw_preview = str(response)[:1000] if response else "(пустой ответ)"
            print(f"[G4F] Сырой ответ (первые 1000 символов):\n{raw_preview}")

            # Обработка ответа
            if isinstance(response, str):
                answer = response.strip()
            elif hasattr(response, 'choices') and response.choices:
                answer = response.choices[0].message.content.strip()
            else:
                if isinstance(response, dict) and 'choices' in response:
                    answer = response['choices'][0]['message']['content'].strip()
                else:
                    answer = None

            if answer and len(answer) > 10:
                print(f"[G4F] Ответ получен, длина: {len(answer)} символов")
                return answer
            else:
                print(f"[G4F] Ответ слишком короткий или пустой: {repr(answer)}")
                return None

        except Exception as e:
            print(f"[G4F Error] {type(e).__name__}: {e}")
            traceback.print_exc()
            return None

    async def generate_single(self, article_text: str, num_slides: int = 5) -> List[Dict[str, str]]:
        print(f"[GENERATE] Старт генерации. Слайдов: {num_slides}, текст: {article_text[:100]}...")

        if not article_text or not article_text.strip():
            print("[GENERATE] ОШИБКА: пустой текст статьи!")
            return []

        prompt = CAROUSEL_PROMPT_TEMPLATE.format(
            article_text=article_text.strip(),
            slide_count=num_slides
        )

        print(f"[GENERATE] Промпт сформирован, длина: {len(prompt)} символов")

        for attempt in range(MAX_RETRIES):
            proxy = self.proxy_manager.get_available_proxy(self.current_model)
            if not proxy:
                print("[CarouselGenerator] Нет доступных прокси!")
                self.consecutive_errors += 1
                if self.consecutive_errors >= ERROR_THRESHOLD_FOR_MODEL_SWITCH:
                    self._switch_model()
                await asyncio.sleep(5)
                continue

            proxy_info = proxy.split('@')[-1]
            print(f"[CarouselGenerator] Попытка {attempt + 1}/{MAX_RETRIES}, модель: {self.current_model}, прокси: {proxy_info}")

            result = await self.make_g4f_request(prompt, proxy)

            if result:
                slides = parse_generated_carousel(result, num_slides)
                if slides:
                    self.proxy_manager.mark_proxy_success(proxy, self.current_model)
                    self.consecutive_errors = 0
                    print(f"[GENERATE] УСПЕХ: сгенерировано {len(slides)} слайдов")
                    return slides
                else:
                    print("[CarouselGenerator] Парсинг вернул пустой список")
                    self.proxy_manager.mark_proxy_failed(proxy, self.current_model, "parse_failed")
            else:
                print("[CarouselGenerator] Пустой ответ от API")
                self.proxy_manager.mark_proxy_failed(proxy, self.current_model, "empty_response")
                self.consecutive_errors += 1

                if self.consecutive_errors >= ERROR_THRESHOLD_FOR_MODEL_SWITCH:
                    self._switch_model()

            if attempt < MAX_RETRIES - 1:
                delay = (2 ** attempt) + random.uniform(2.0, 5.0)
                print(f"[CarouselGenerator] Жду {delay:.1f} сек перед следующей попыткой...")
                await asyncio.sleep(delay)

        print("[CarouselGenerator] Все попытки исчерпаны, возвращаем пустой список")
        return []


# ==================== СИНХРОННАЯ ОБЁРТКА ДЛЯ FLASK ====================
_generator = None


def _get_generator():
    global _generator
    if _generator is None:
        _generator = CarouselGenerator()
    return _generator


def generate_carousel_text(article_text: str, num_slides: int = 5) -> List[Dict[str, str]]:
    """Синхронная обёртка для Flask (вызывается из app.py create_project)"""
    print(f"[generate_carousel_text] Вызов. Текст: {article_text[:80]}... | Слайдов: {num_slides}")

    if not article_text or not article_text.strip():
        print("[generate_carousel_text] ОШИБКА: пустой текст!")
        return []

    try:
        generator = _get_generator()

        # Проверяем, есть ли уже запущенный event loop
        try:
            loop = asyncio.get_running_loop()
            print(f"[generate_carousel_text] Обнаружен running event loop: {loop}")
            # Если loop уже запущен — используем run_coroutine_threadsafe или создаём новый в отдельном потоке
            # Но проще: проверим, не в главном потоке ли мы
            import threading
            if threading.current_thread() is threading.main_thread():
                print("[generate_carousel_text] Главный поток, пробуем new_event_loop")
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(generator.generate_single(article_text, num_slides))
                new_loop.close()
            else:
                print("[generate_carousel_text] Не главный поток, используем get_running_loop")
                future = asyncio.run_coroutine_threadsafe(
                    generator.generate_single(article_text, num_slides), loop
                )
                result = future.result(timeout=120)
        except RuntimeError:
            print("[generate_carousel_text] Нет running loop, создаём новый")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(generator.generate_single(article_text, num_slides))
            loop.close()

        print(f"[generate_carousel_text] Результат: {len(result)} слайдов")
        return result

    except Exception as e:
        print(f"[generate_carousel_text] Ошибка: {e}")
        traceback.print_exc()
        return []


# ==================== ТЕСТ ====================
if __name__ == "__main__":
    test_text = """ЖК «Тигры» — это новый жилой комплекс во Владивостоке.
Застройщик СЗ «ДВ Кристалл» входит в группу компаний «Столица».
В комплексе будет ледовый дворец Тигр-Арена, медицинский центр,
две школы и детский сад. Двор без машин, входные двери с усиленной
шумоизоляцией. Ремонт можно включить в ипотеку."""

    result = generate_carousel_text(test_text, 5)
    if result:
        for i, slide in enumerate(result, 1):
            print(f"\n--- Слайд {i} ---")
            print(f"TITLE: {slide['title']}")
            print(f"SUBTITLE: {slide['subtitle']}")
            print(f"BODY: {slide['body']}")
            print(f"TITLE_SEGMENTS: {slide.get('title_segments', [])}")
    else:
        print("Не удалось сгенерировать слайды (пустой ответ).")


