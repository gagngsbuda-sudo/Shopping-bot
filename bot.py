import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from google import genai
from google.genai import types

# --- НАСТРОЙКИ (безопасно из переменных окружения) ---
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Инициализация ИИ (Gemini)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Состояния для диалога с пользователем
class ShoppingState(StatesGroup):
    waiting_for_query = State()

router = Router()

# Главная клавиатура
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Подобрать товар")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "👋 Привет! Я твой **ИИ-помощник по покупкам**.\n\n"
        "Я помогу подобрать товар под твой бюджет, сравнить характеристики, "
        "дать совет и найти лучший вариант в интернете.\n\n"
        "Нажми кнопку **«🛍 Подобрать товар»**, чтобы начать!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

@router.message(F.text == "ℹ️ О боте")
async def cmd_about(message: Message):
    await message.answer(
        "🤖 Этот бот создан на базе искусственного интеллекта Gemini.\n"
        "Я умею анализировать твои пожелания, подбирать технику, одежду, гаджеты и любые другие товары, "
        "а также сравнивать их между собой.",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🛍 Подобрать товар")
async def start_shopping(message: Message, state: FSMContext):
    await state.set_state(ShoppingState.waiting_for_query)
    await message.answer(
        "✍️ Опиши, что ты хочешь купить, какой у тебя бюджет и какие важные требования.\n\n"
        "*(Например: «Ищу игровой ноутбук до $900 с видеокартой RTX и хорошим экраном» или «Нужны кроссовки для бега до 4000 грн»)*"
    )

@router.message(ShoppingState.waiting_for_query)
async def process_user_query(message: Message, state: FSMContext):
    user_prompt = message.text
    
    # Показываем, что бот «печатает», пока ИИ думает
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Формируем системный промпт для Gemini, чтобы он выступал экспертом-шоппером
        prompt_for_ai = (
            "Ты — профессиональный эксперт-помощник по покупкам. Пользователь ищет товар. "
            "Твоя задача — предложить 3 лучших варианта с учетом бюджета, указать их ориентировочную цену, "
            "ключевые плюсы, минусы и почему стоит выбрать именно их. Пиши структурированно, красиво и на языке пользователя.\n\n"
            f"Запрос пользователя: {user_prompt}"
        )
        
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_for_ai,
        )
        
        ai_reply = response.text
        await message.answer(ai_reply, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logging.error(f"Ошибка при обращении к ИИ: {e}")
        await message.answer(
            "⚠️ Ой, произошла ошибка при обращении к искусственному интеллекту. Попробуй еще раз чуть позже.",
            reply_markup=get_main_keyboard()
        )
    
    # Сбрасываем состояние, чтобы пользователь мог сделать новый запрос
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("Бот запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
