import os
from pathlib import Path

import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
from dotenv import load_dotenv

#Загрузка переменных окружения
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Логирование для отслеживания ошибок
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Настройка OpenAI API
openai.api_key = os.getenv("API_GPT")  # Замените на ваш OpenAI API ключ
openai.api_base = "https://api.proxyapi.ru/openai/v1"

# Словарь для хранения данных пользователя
user_data_storage = {}


# Функция для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Инициализируем данные пользователя
    user_data_storage[user_id] = {
        'username': update.effective_user.username,
        'congratulations_count': 0,
        'name': None,
        'congratulation_type': None,
        'male': False,
        'female': False,
        'informal': False,
        'formal': False,
        'short': False,
        'medium': False,
        'long': False
    }

    keyboard = [
        [InlineKeyboardButton("Пожелание хорошего дня 🌞", callback_data='good_day')],
        [InlineKeyboardButton("День рождения 🎂", callback_data='birthday')],
        [InlineKeyboardButton("2️⃣3️⃣ февраля 🪖", callback_data='february_23')],
        [InlineKeyboardButton("8 марта 💐", callback_data='march_8')],
        [InlineKeyboardButton("Новый год 🎇", callback_data='new_year')],
        [InlineKeyboardButton("Рождество 🎄", callback_data='christmas')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с клавиатурой
    if update.message:
        await update.message.reply_text('🌠 Выберите тип поздравления:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('🌠 Выберите тип поздравления:', reply_markup=reply_markup)


# Функция для выбора типа поздравления
async def choose_congratulation_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_data_storage[user_id]['congratulation_type'] = query.data  # Сохраняем тип поздравления
    await query.answer()

    # Если выбрано "Пожелание хорошего дня", сразу генерируем пожелание
    if query.data == 'good_day':
        await generate_good_day_wish(update, context)
    else:
        # Переходим к выбору параметров поздравления для других типов
        await show_congratulation_params(update, context)


# Функция для генерации пожелания хорошего дня
async def generate_good_day_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Формируем запрос к чат-модели через эндпоинт v1/chat/completions
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Чат-модель
            messages=[
                {"role": "system", "content": "Ты позитивный ассистент."},  # Системное сообщение, задающее стиль
                {"role": "user",
                 "content": "Создай креативное пожелание хорошего дня. Ты не общаешься с пользователем, а просто выдаешь сформированное поздравление. Прежде чем отправить поздравление - проверь правописание. При формировании поздравления ты учитываешь, что выбрал пользователь ты/вы, женщине/мужчине в контексте поздравления. Поздравление должно быть законченным, учитывая максимальное количество символов "}
                # Сообщение от пользователя
            ],
            max_tokens=150
        )
        good_day_wish = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"Ошибка при генерации пожелания: {e}")
        good_day_wish = f"Ошибка при генерации пожелания: {e}"

    keyboard = [
        [InlineKeyboardButton("Следующее", callback_data='next_good_day')],
        [InlineKeyboardButton("Новое", callback_data='new')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем пожелание
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"Пожелание хорошего дня:\n{good_day_wish}",
            reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            f"Пожелание хорошего дня:\n{good_day_wish}",
            reply_markup=reply_markup)


# Функция для показа параметров поздравления с изменением кнопок
async def show_congratulation_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = user_data_storage[user_id]

    name = user_data.get('name', None)
    name_button = f"Имя: {name}" if name else "Добавить имя"

    # Функция для добавления зелёного кружка к выбранным параметрам
    def format_button(text, selected):
        return f"{'✅ ' if selected else '◽️'}{text}"

    # Обновляем клавиатуру так, чтобы в каждой категории можно было выбрать только один параметр
    keyboard = [
        [InlineKeyboardButton(name_button, callback_data='add_name')],
        [
            InlineKeyboardButton(format_button("Мужчине", user_data.get('male', False)), callback_data='male'),
            InlineKeyboardButton(format_button("Женщине", user_data.get('female', False)), callback_data='female')
        ],
        [
            InlineKeyboardButton(format_button("Ты", user_data.get('informal', False)), callback_data='informal'),
            InlineKeyboardButton(format_button("Вы", user_data.get('formal', False)), callback_data='formal')
        ],
        [
            InlineKeyboardButton(format_button("Короткое", user_data.get('short', False)), callback_data='short'),
            InlineKeyboardButton(format_button("Среднее", user_data.get('medium', False)), callback_data='medium'),
            InlineKeyboardButton(format_button("Длинное", user_data.get('long', False)), callback_data='long')
        ],
        [InlineKeyboardButton("Сгенерировать поздравление", callback_data='generate')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Определяем, был ли это callback запрос или обычное сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text('🎇 Уточните параметры поздравления:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('🎇 Уточните параметры поздравления:', reply_markup=reply_markup)


# Функция для обработки нажатий на кнопки с параметрами
async def choose_congratulation_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    # Обработка каждого выбранного параметра
    if query.data == 'add_name':
        await query.edit_message_text("Введите имя человека, которого поздравляем:")
        user_data_storage[user_id]['awaiting_name'] = True
        return

    # Переключение состояния в каждой категории (пол, стиль обращения, длина)
    if query.data == 'male':
        user_data_storage[user_id]['male'] = True
        user_data_storage[user_id]['female'] = False
    elif query.data == 'female':
        user_data_storage[user_id]['female'] = True
        user_data_storage[user_id]['male'] = False
    elif query.data == 'informal':
        user_data_storage[user_id]['informal'] = True
        user_data_storage[user_id]['formal'] = False
    elif query.data == 'formal':
        user_data_storage[user_id]['formal'] = True
        user_data_storage[user_id]['informal'] = False
    elif query.data == 'short':
        user_data_storage[user_id]['short'] = True
        user_data_storage[user_id]['medium'] = False
        user_data_storage[user_id]['long'] = False
    elif query.data == 'medium':
        user_data_storage[user_id]['medium'] = True
        user_data_storage[user_id]['short'] = False
        user_data_storage[user_id]['long'] = False
    elif query.data == 'long':
        user_data_storage[user_id]['long'] = True
        user_data_storage[user_id]['short'] = False
        user_data_storage[user_id]['medium'] = False
    elif query.data == 'generate':
        await generate_congratulation(update, context)
        return

    # Обновляем клавиатуру после каждого выбора
    await show_congratulation_params(update, context)


# Функция для получения имени
async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = user_data_storage.get(user_id, {})
    if user_data.get('awaiting_name', False):
        name = update.message.text
        user_data_storage[user_id]['name'] = name
        user_data_storage[user_id]['awaiting_name'] = False
        # Показываем обновленное меню с параметрами
        await show_congratulation_params(update, context)
    else:
        pass  # Если мы не ожидаем ввода имени, можно игнорировать сообщение


# Функция для генерации поздравления с использованием OpenAI
async def generate_congratulation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = user_data_storage[user_id]

    name = user_data.get('name', 'Не указано')
    congratulation_type = user_data.get('congratulation_type', 'Не указано')

    # Определяем пол
    if user_data.get('male'):
        gender = 'мужчине'
    elif user_data.get('female'):
        gender = 'женщине'
    else:
        gender = 'человеку'

    # Определяем стиль обращения
    if user_data.get('informal'):
        style = 'на ты'
    elif user_data.get('formal'):
        style = 'на вы'
    else:
        style = ''

    # Определяем длину сообщения
    if user_data.get('short'):
        length = 'короткое'
        max_length = 150  # Максимум символов для короткого сообщения
    elif user_data.get('medium'):
        length = 'среднее'
        max_length = 250  # Максимум символов для среднего сообщения
    else:
        length = 'длинное'
        max_length = 350  # Максимум символов для длинного сообщения


    # Формируем запрос к OpenAI для генерации текста поздравления
    prompt = (
        f"Создай {length} поздравление с праздником {congratulation_type} для {gender}, обращение {style}."
        f"Имя: {name}. Сообщение не должно превышать {max_length} символов и должно быть завершенным."
        f"//1. Учитывай правила правописания. Поздравление должно начинаться и заканчиваться логически завершенной мыслью."
        f"//2. Если количество символов превышает {max_length}, укороти текст так, чтобы мысль осталась завершенной. "
        f"//3. ЗАПРЕЩЕНО отправлять незавершенные фразы. При необходимости, добавь короткие фразы для завершения мысли. "
        f"//4. Имя пользователя {name} должно склоняться в соответствии с контекстом поздравления."
        f"//5. Обязательно учитывай {style} и {gender} при формировании текста поздравления!"
        f"//6. Если пользователь не ввел имя {name}, то ты формируешь поздравление, учитывая {gender}, но не указывая его в тексте."
        f"//7. Перед отправкой убедись, что все требования выполнены, и поздравление состоит из логически завершенных предложений."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Используем чат-модель
            messages=[
                {"role": "system", "content": "Ты позитивный ассистент."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250
        )
        congratulation_text = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"Ошибка при генерации поздравления: {e}")
        congratulation_text = f"Ошибка при генерации поздравления: {e}"

    # Отправляем результат
    keyboard = [
        [InlineKeyboardButton("Следующее", callback_data='next')],
        [InlineKeyboardButton("Новое", callback_data='new')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Словарь для сопоставления типов поздравлений с их названиями и эмодзи
    congratulation_mapping = {
        'march_8': ("8 марта 💐", "Поздравление с праздником"),
        'good_day': ("Пожелание хорошего дня 🌞", "Поздравление"),
        'birthday': ("День рождения 🎂", "Поздравление с праздником"),
        'february_23': ("2️⃣3️⃣ февраля 🪖", "Поздравление с праздником"),
        'new_year': ("Новый год 🎇", "Поздравление с праздником"),
        'christmas': ("Рождество 🎄", "Поздравление с праздником"),
    }

    title, message = congratulation_mapping.get(congratulation_type, ("Праздник", "Поздравление"))

    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"{message}\n{title}:\n{congratulation_text}",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"{message}\n{title}:\n{congratulation_text}",
            reply_markup=reply_markup
        )


# Функция для обработки кнопок "Следующее" и "Новое"
async def handle_next_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == 'next':
        # Повторно вызываем функцию generate_congratulation с уже сохраненными параметрами
        await generate_congratulation(update, context)
    elif query.data == 'next_good_day':
        # Повторно генерируем пожелание хорошего дня
        await generate_good_day_wish(update, context)
    elif query.data == 'new':
        await start(update, context)


# Основная функция
if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()  # Замените на ваш Telegram Bot Token

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(choose_congratulation_type,
                                                 pattern='^(good_day|birthday|february_23|march_8|new_year|christmas)$'))
    application.add_handler(CallbackQueryHandler(choose_congratulation_params,
                                                 pattern='^(male|female|informal|formal|short|medium|long|add_name|generate)$'))
    application.add_handler(CallbackQueryHandler(handle_next_new, pattern='^(next|new|next_good_day)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_name))

    # Запуск бота
    application.run_polling()
