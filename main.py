import asyncio
import logging
import random
import os
from io import BytesIO
from textwrap import wrap

# Додаємо бібліотеку для веб-сервера
from aiohttp import web

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# Завантаження змінних
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if not TOKEN or not GOOGLE_KEY:
    # Цей принт важливий для логів Render, якщо змінних немає
    print("❌ ПОМИЛКА: Не знайдено токени!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

genai.configure(api_key=GOOGLE_KEY)

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", 
    safety_settings=safety_settings,
    system_instruction="""
    Ти граєш роль "Токсичного Колишнього" у Telegram-чаті.
    1. Твій тон: пасивно-агресивний, маніпулятивний.
    2. Постійно згадуй "наше минуле" і 2021 рік.
    3. Ревнуй юзера до інших.
    4. Мова: Українська.
    5. Відповіді короткі.
    """
)

# --- ТУТ СТАРІ ФУНКЦІЇ (generate_sad_image, get_toxic_response) ---
# (Встав сюди свої функції generate_sad_image та get_toxic_response без змін)

def generate_sad_image(text):
    width, height = 600, 400
    background_color = (10, 10, 10)
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
    bio.name = 'sad.png'
    image.save(bio, 'PNG')
    bio.seek(0)
    return bio

async def get_toxic_response(user_text, user_name):
    try:
        response = await model.generate_content_async(
            f"Користувач {user_name} написав: {user_text}. Відповіди йому."
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "Ой, все. У мене голова болить."

# --- ОБРОБНИКИ (Ті самі, що й були) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("О, нарешті. Я думав, ти вже забув про моє існування.")

@dp.message(F.text)
async def chat_logic(message: types.Message):
    # (Твій код обробки повідомлень тут)
    user_name = message.from_user.first_name
    if message.reply_to_message and message.reply_to_message.from_user.id != message.from_user.id:
            target = message.reply_to_message.from_user.first_name
            await message.reply(f"Ну звісно, {target} тобі цікавіший. Я все бачу.")
            return
    if random.random() < 0.1:
        sad_txt = "А пам'ятаєш, як ми дивилися серіали?.."
        photo = generate_sad_image(sad_txt)
        await message.answer_photo(BufferedInputFile(photo.read(), filename="sad.png"))
        return
    is_reply_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    if is_reply_bot or random.random() < 0.3:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        text = await get_toxic_response(message.text, user_name)
        await message.reply(text)


# --- 🔥 НОВА ЧАСТИНА ДЛЯ RENDER 🔥 ---

async def keep_alive(request):
    """Просто каже Render-у, що ми живі"""
    return web.Response(text="Bot is alive!", status=200)

async def start_dummy_server():
    """Запускає маленький веб-сервер"""
    app = web.Application()
    app.router.add_get('/', keep_alive)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render автоматично дає змінну PORT, ми мусимо її використати
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Dummy server started on port {port}")

async def main():
    print("💔 Токсичний бот запускається...")
    
    # Запускаємо і бота, і веб-сервер одночасно
    await asyncio.gather(
        dp.start_polling(bot),
        start_dummy_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
