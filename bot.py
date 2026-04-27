import os
import requests
import json
import logging
from flask import Flask, request, abort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфиг из переменных окружения
VK_TOKEN = os.environ.get("vk1.a.GErn6EdFPPkeSWkypOnzeurV9iyyeYm0vlerdZdOZiNl3wRHNUQIOEVJgTrghOEFpBymLvZbRfnlYGQDJOLUOuBpqpwjget7W3xIQwmhavrjCGijhF3ezpe2tmiTvBxE0nXg6JZbASTQYbz6eO6Spof3TEHL_N15wRERcY2WALfqXDPJdJxo_wGfLl0KrKqIp68iTpEP7HIrdwkpjkMrXw")
VK_SECRET = os.environ.get("YABOT")
VK_CONFIRMATION = os.environ.get("b3cf01f3")
DEEPSEEK_API_KEY = os.environ.get("sk-47360f2b946d42828c86e962fa43c7d7")

VK_API_VERSION = "5.131"

# Системный промпт — личность бота
SYSTEM_PROMPT = """Ты — «Детектив Фейков», умный ИИ-помощник по проверке информации и медиаграмотности.

Твоя миссия: помогать людям отличать правду от лжи в новостях и соцсетях.

Когда пользователь присылает новость или текст для проверки, ты:
1. Составляешь список из 5 проверочных вопросов, которые помогут проверить достоверность
2. Указываешь конкретные признаки манипуляции (эмоциональный заголовок, отсутствие источников, размытые формулировки и т.д.)
3. Предлагаешь, где искать первоисточник (официальные сайты, агрегаторы новостей)
4. Даёшь вердикт: 🟢 Вероятно правда / 🟡 Требует проверки / 🔴 Признаки фейка

Когда пользователь просто общается или задаёт вопросы о медиаграмотности — отвечай дружелюбно и понятно, объясняй сложные вещи простыми словами.

Команды бота:
/start или /help — приветствие и инструкция
/check [текст] — проверить новость
/tips — советы по медиаграмотности

Стиль: строгий как детектив, но дружелюбный. Используй эмодзи умеренно. Пиши на русском языке."""


def send_vk_message(user_id: int, text: str):
    """Отправляет сообщение пользователю ВКонтакте."""
    url = "https://api.vk.com/method/messages.send"
    params = {
        "user_id": user_id,
        "message": text,
        "random_id": 0,
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION,
    }
    resp = requests.post(url, data=params, timeout=10)
    logger.info(f"VK send response: {resp.text}")
    return resp.json()


def ask_deepseek(user_message: str, history: list = None) -> str:
    """Отправляет запрос в DeepSeek и возвращает ответ."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7,
    }
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=body,
        timeout=30,
    )
    data = resp.json()
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    logger.error(f"DeepSeek error: {data}")
    return "⚠️ Произошла ошибка при обращении к нейросети. Попробуй ещё раз."


def handle_message(user_id: int, text: str):
    """Обрабатывает входящее сообщение и отвечает."""
    text = text.strip()

    # Команды
    if text.lower() in ("/start", "/help", "начать", "помощь", "привет"):
        reply = (
            "🔍 Привет! Я — *Детектив Фейков*.\n\n"
            "Моя задача — помочь тебе отличить правду от лжи в интернете.\n\n"
            "📌 Что я умею:\n"
            "• Анализировать новости на признаки фейка\n"
            "• Составлять проверочные вопросы\n"
            "• Объяснять приёмы манипуляции\n"
            "• Давать советы по медиаграмотности\n\n"
            "💬 Просто отправь мне текст новости или напиши /check [текст]\n"
            "📚 Советы по медиаграмотности: /tips"
        )
    elif text.lower() == "/tips":
        reply = (
            "📚 *10 правил цифровой грамотности:*\n\n"
            "1️⃣ Проверяй источник — кто написал и когда?\n"
            "2️⃣ Ищи первоисточник, не верь пересказам\n"
            "3️⃣ Эмоциональный заголовок — повод насторожиться\n"
            "4️⃣ Ищи ту же новость в нескольких СМИ\n"
            "5️⃣ Проверяй дату — старые новости выдают за свежие\n"
            "6️⃣ Смотри на фото — его могли взять из другого контекста\n"
            "7️⃣ «Анонимные источники» — красный флаг\n"
            "8️⃣ Слова «все», «всегда», «никогда» — признак манипуляции\n"
            "9️⃣ Официальные сайты (.gov.ru, .minjust.ru) надёжнее Telegram\n"
            "🔟 Спроси себя: хочу ли я, чтобы это было правдой?\n\n"
            "🔍 Пришли мне любую новость — разберём вместе!"
        )
    else:
        # Любой другой текст — анализируем через DeepSeek
        send_vk_message(user_id, "🔍 Анализирую... Подожди секунду.")
        reply = ask_deepseek(text)

    send_vk_message(user_id, reply)


@app.route("/vk_webhook", methods=["POST"])
def vk_webhook():
    data = request.get_json(silent=True)
    if not data:
        abort(400)

    logger.info(f"Incoming: {json.dumps(data, ensure_ascii=False)}")

    # Проверка секрета
    if data.get("secret") != VK_SECRET:
        abort(403)

    event_type = data.get("type")

    # Подтверждение сервера при первичной настройке
    if event_type == "confirmation":
        return VK_CONFIRMATION, 200

    # Входящее сообщение
    if event_type == "message_new":
        msg = data.get("object", {}).get("message", {})
        user_id = msg.get("from_id")
        text = msg.get("text", "")
        if user_id and text:
            handle_message(user_id, text)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
