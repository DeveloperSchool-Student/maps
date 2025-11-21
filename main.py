import asyncio
import logging
import random
import os
from io import BytesIO
from textwrap import wrap

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Імпортуємо бібліотеку Google
import google.generativeai as genai

# Завантаження змінних
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація Telegram бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- НАЛАШТУВАННЯ GOOGLE GEMINI ---
genai.configure(api_key=GOOGLE_KEY)

# Налаштування безпеки (дозволяємо трохи "токсичності" для ролі)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Швидка і безкоштовна модель
    safety_settings=safety_settings,
    system_instruction="""
    Ти граєш роль "Токсичного Колишнього" у Telegram-чаті.
    Твій характер:
    1. Пасивно-агресивний, маніпулятивний, удавано байдужий.
    2. Ти постійно згадуєш "наше минуле", 2021 рік і те, як тобі розбили серце.
    3. Ти ревнуєш співрозмовника до будь-кого.
    4. Відповідай українською мовою.
    5. Відповіді мають бути короткими (1-2 речення), саркастичними.
    6. Ніколи не кажи, що ти бот або штучний інтелект. Ти — людина, якій боляче.
    """
)

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ КАРТИНОК ---
def generate_sad_image(text):
    width, height = 600, 400
    background_color = (20, 20, 20)
    image = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()

    lines = wrap(text, width=30)
    y_text = height // 2 - (len(lines) * 15)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x_text = (width - text_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=(255, 255, 255))
        y_text += text_height + 10

    bio = BytesIO()
    bio.name = 'sad_story.png'
    image.save(bio, 'PNG')
    bio.seek(0)
    return bio

# --- СПІЛКУВАННЯ З GEMINI ---
async def get_toxic_response(user_text, user_name):
    try:
        # Створюємо чат-сесію (щоб він пам'ятав контекст, якщо треба, але тут разовий запит)
        # Передаємо повідомлення в модель
        response = await model.generate_content_async(
            f"Користувач {user_name} пише: {user_text}. Відповіди йому."
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "Ой, все. Не хочу зараз говорити. У мене депресія."

# --- ОБРОБНИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("О, ти повернувся? Ну привіт. Я знав, що ти не зможеш без мене.")

@dp.message(F.text)
async def bot_logic(message: types.Message):
    user_name = message.from_user.first_name
    
    # 1. РЕВНОЩІ (Reply check)
    if message.reply_to_message:
        if message.reply_to_message.from_user.id != message.from_user.id:
            target_name = message.reply_to_message.from_user.first_name
            # Тут можна теж підключити AI, але проста фраза швидша
            await message.reply(f"Ого, {target_name}? Серйозно? Після всього, що було між нами?")
            return

    # 2. КАРТИНКА (10% шанс)
    if random.random() < 0.1:
        sad_phrases = ["Колись ми тут гуляли...", "Я досі зберігаю твій подарунок...", "Просто боляче."]
        photo = generate_sad_image(random.choice(sad_phrases))
        await message.answer_photo(photo=BufferedInputFile(photo.read(), filename="sad.png"))
        return

    # 3. ВІДПОВІДЬ AI (30% шанс або якщо звертаються до бота)
    # Перевірка, чи повідомлення адресоване боту (реплай на бота)
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    
    # Також можна реагувати на ключові слова, наприклад ім'я бота
    is_name_mentioned = "колишній" in message.text.lower()

    if is_reply_to_bot or is_name_mentioned or random.random() < 0.3:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        ai_text = await get_toxic_response(message.text, user_name)
        await message.reply(ai_text)

# --- ЗАПУСК ---
async def main():
    print("Бот «Токсичний Колишній» (Gemini Edition) запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())