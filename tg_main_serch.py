import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ТОКЕН (напоминание: никогда не выкладывай его в публичный доступ!)
TOKEN = "YOUR TOKEN"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ссылка на картинку для главного меню (можно заменить на прямую ссылку на .jpg или .png)
WELCOME_IMAGE_URL = "https://img.freepik.com/free-vector/hot-sale-banner-template-design_1017-31343.jpg"

def get_pepper_deals():
    url = "https://www.pepper.ru/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    best_discount = []
    try:
        page = requests.get(url, headers=headers, timeout=10)
        if page.status_code != 200: return None
        
        soup = BeautifulSoup(page.text, "html.parser")
        items = soup.find_all("article")

        for item in items:
            name_tag = item.find("a", class_="visited:text-secondary-text-light dark:visited:text-secondary-text-dark group-hover:!text-primary")
            name = name_tag.text.strip() if name_tag else "Без названия"

            discount_tag = item.find("div", class_="md:text-base text-sm text-secondary-text-light dark:text-secondary-text-dark")
            discount_text = discount_tag.text.strip() if discount_tag else "0"

            price_after = item.find("div", class_="md:text-xll text-lg font-bold text-primary mr-2")
            price_after = price_after.text.strip() if price_after else "—"

            price_before = item.find("div", class_="md:text-xll text-lg line-through text-secondary-text-light dark:text-secondary-text-dark mr-2")
            price_before = price_before.text.strip() if price_before else "—"

            digits_only = "".join(filter(str.isdigit, discount_text))
            val = int(digits_only) if digits_only else 0

            if val > 0:
                best_discount.append({
                    "name": name,
                    "price_after": price_after,
                    "discount": val,
                    "price_before": price_before
                })
        
        return sorted(best_discount, key=lambda x: x['discount'], reverse=True)[:10]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None

# Функция для создания инлайн-клавиатуры главного меню
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Получить скидки", callback_data="get_deals"))
    builder.row(types.InlineKeyboardButton(text="🔄 Рестарт", callback_data="restart_bot"))
    return builder.as_markup()

# Обработчик команды /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer_photo(
        photo=WELCOME_IMAGE_URL,
        caption="**Добро пожаловать в Pepper Parser!**\n\nЯ помогу тебе найти самые выгодные предложения. Выбери действие ниже:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "Получить скидки" (инлайн)
# Измените цикл формирования текста в обработчике send_deals_callback
# Обновленный обработчик кнопки "Получить скидки" и "Обновить"
@dp.callback_query(F.data == "get_deals")
async def send_deals_callback(callback: types.CallbackQuery):
    # 1. Если это не первое открытие (нет фото), показываем статус загрузки
    if not callback.message.photo:
        try:
            await callback.message.edit_text("⏳ <i>Обновляю данные, секунду...</i>", parse_mode="HTML")
        except TelegramBadRequest:
            pass # Если вдруг не удалось отредактировать, не страшно

    # 2. Получаем данные
    deals = get_pepper_deals()
    
    if not deals:
        await callback.message.answer("❌ Ошибка парсинга. Попробуйте позже.")
        await callback.answer()
        return

    # 3. Формируем сообщение (HTML)
    full_message_parts = ["<b>🔥 ТОП 10 САМЫХ ГОРЯЧИХ СКИДОК! 🔥</b>"]
    for i, item in enumerate(deals, 1):
        safe_name = item['name'].replace("<", "&lt;").replace(">", "&gt;")
        text = (
            f"{i}. <b>{safe_name}</b>\n"
            f"💰 Цена: <b>{item['price_after']}</b> (<s>{item['price_before']}</s>)\n"
            f"🔥 Скидка: <code>{item['discount']}%</code>"
        )
        full_message_parts.append(text)

    final_text = "\n\n".join(full_message_parts)

    # 4. Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Обновить список 🔄", callback_data="get_deals"))
    builder.row(types.InlineKeyboardButton(text="🔙 В главное меню", callback_data="restart_bot"))

    # 5. Вывод результата
    if callback.message.photo:
        # Если нажали из главного меню (где фото) — удаляем старое, шлем новое
        await callback.message.delete()
        await callback.message.answer(
            final_text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    else:
        # Если уже были в списке — просто заменяем текст "Обновляю..." на результат
        await callback.message.edit_text(
            final_text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    
    # 6. Закрываем уведомление на кнопке
    await callback.answer("Данные обновлены!")

# Обработчик кнопки Рестарт
@dp.callback_query(F.data == "restart_bot")
async def restart_callback(callback: types.CallbackQuery):
    # Вместо удаления просто редактируем текущее сообщение на приветственное
    # Или отправляем новое, как при /start
    await callback.message.delete()
    await start_cmd(callback.message)
    await callback.answer("Бот перезапущен")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
