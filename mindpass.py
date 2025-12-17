import aiogram
import aiogram.types as types
import random
import string
import secrets
import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

def escape_md(text: str) -> str:
    """Экранирование спецсимволов для MarkdownV2"""
    # Экранируем спецсимволы, но НЕ экранируем \n (переносы строк)
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text).replace(r'\\n', '\n')


# Справка
HELP_TEXT = (
    "Этот бот помогает сгенерировать надежные и уникальные пароли.\n\n"
    "Команды:\n"
    "/start - Запустить бота и показать главное меню.\n"
    "/help - Показать это справочное сообщение.\n\n"
    "В главном меню:\n"
    "- Кнопка 'Справка' выводит этот текст.\n"
    "- Кнопка 'Сгенерировать пароль' начинает процесс создания пароля.\n\n"
    "Сначала вам будет предложено ввести тег для пароля, чтобы не забыть для каких целей вы его создавали.\n "
    "Рекомендуется указывать тег не слишком очевидный, чтобы случайный наблюдатель не догадался от какой именно системы этот пароль.\n"
    "После ввода тега бот сгенерирует пароль и отобразит его скрытым.\n "
    "Чтобы увидеть пароль, просто тапните на тексте.\n\n"
    "Если вам требуется дополнительная помощь или у вас есть вопросы, напишите разработчику бота @zemcoviv."
    )

# Токен бота
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Замените на ваш токен Telegram бота

# инициализация бота и диспетчера с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Callback data для экшенов кнопок
# hide_callback = CallbackData("help", "action")

# Создаем callback_data для кнопок главного меню и вложенных меню
# main_menu_cd = CallbackData("main_menu", "action")
# nested_menu_cd = CallbackData("nested_menu", "action", "level")
# Дополнительные callback_data
# confirm_callback = CallbackData('confirm', 'action', 'tag')

    
# Генерация инлайн клавиатуры главного меню
def get_main_menu_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Сгенерировать пароль", callback_data="main_menu:generate")],
        [types.InlineKeyboardButton(text="Помощь", callback_data="main_menu:help")]
    ])

# Реакция на кнопки главного меню
@dp.callback_query(F.data.startswith("main_menu:"))
async def query_main_menu(callback_query: CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[1]
    if action == "generate":
        await callback_query.message.edit_text('Введите тег для вашего пароля:', reply_markup=None)
        await state.set_state(Form.waiting_for_tag)
    elif action == "help":
        await callback_query.message.edit_text(HELP_TEXT)
        # Добавим кнопку "Назад" или "Закрыть"
        back_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Назад", callback_data="nested_menu:back:main")]
        ])
        await callback_query.message.edit_reply_markup(reply_markup=back_keyboard)

    await callback_query.answer()  # Убираем "часики"

# Реакция на кнопки вложенного меню
@dp.callback_query(F.data.startswith("nested_menu:"))
async def query_nested_menu(callback_query: CallbackQuery):
    level = callback_query.data.split(":")[2]
    if level == "main":
        await callback_query.message.edit_text("Выберите действие:", reply_markup=get_main_menu_keyboard())
    await callback_query.answer()  # Убираем "часики"


# Функция для загрузки списка слов из файла
def load_words_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        words_list = [line.strip() for line in file if len(line.strip()) <= 5]
    return words_list

# Загрузка списка слов из файла 'russian.txt'
simple_russian_words = load_words_from_file('russian.txt')


# Создадим класс состояний для машины состояний пользователя
class Form(StatesGroup):
    waiting_for_tag = State()  # состояние для ожидания ввода тега
    waiting_for_password_confirmation = State()  # новое состояние для подтверждения пароля
    tag = State()  # состояние для хранения тега
    password_with_tag = State()  # состояние для хранения пароля с тегом


# функция для транслитерации
def transliterate(word):
    # Таблица транслитерации
    translit_table = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 
               'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 
               'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 
               'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 
               'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': "'", 'ы': 'y', 'ь': "'", 
               'э': 'e', 'ю': 'yu', 'я': 'ya'} # словарь транслитераций кириллицы в латиницу
    trans_word = ''.join(translit_table.get(c, c) for c in word.lower())
    return trans_word

# функция для создания пароля
def generate_password(num_words=2, num_numbers=2, num_symbols=1):
    words = [transliterate(random.choice(simple_russian_words)).capitalize() for _ in range(num_words)]
    numbers = [str(secrets.choice(range(10))) for _ in range(num_numbers)]
    easy_symbols = '~!@#$&*(){}[]+\"\':<>/%'  # Ограничиваем набор спецсимволов
    symbols = [secrets.choice(easy_symbols) for _ in range(num_symbols)]
    password_components = words + numbers + symbols
    random.shuffle(password_components)
    password = ''.join(password_components)
    return password

# Функция для отправки сообщения с клавиатурой
async def send_keyboard(message: aiogram.types.Message, text: str, keyboard: list):
    await message.answer(text, reply_markup=aiogram.types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))

# Обработчик команды /start
@dp.message(Command('start'))
async def command_start(message: Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Привет! Это бот для генерации паролей.\n Создай надежный пароль, который будет легко запомнить.\n Выбери действие:", reply_markup=get_main_menu_keyboard())

    
# Обновленный обработчик команды /help
@dp.message(Command('help'))
async def send_help(message: Message):
    # Удаление сообщения "Помощь"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    # Создание инлайн клавиатуры для скрытия справки
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Скрыть это сообщение", callback_data="hide_help")]
    ])

    await message.answer(HELP_TEXT, reply_markup=keyboard)
    
# Обработчик нажатия на кнопку "Скрыть это сообщение"
@dp.callback_query(F.data == "hide_help")
async def hide_help_message(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await callback_query.answer()  # Отправляем пустой ответ, чтобы убрать "часики" на кнопке

# Изменим обработчик кнопки "Сгенерировать пароль"
@dp.message(F.text == 'Сгенерировать пароль', StateFilter('*'))
async def enter_tag(message: Message, state: FSMContext):
    # Удаление сообщения "Выберите действие"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    # Удаление сообщения "Сгенерировать пароль"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await message.reply('Введите тег для вашего пароля:')
    await state.set_state(Form.waiting_for_tag)  # устанавливаем состояние ожидания тега

# Обработчик текстовых сообщений для получения тега и генерации пароля
@dp.message(StateFilter(Form.waiting_for_tag))
async def process_tag(message: Message, state: FSMContext):
    # Получаем тег, введенный пользователем, и генерируем пароль
    tag = message.text
    password = generate_password()


    # Удаление сообщения с запросом на ввод тега
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    # Удаление сообщения, где пользователь ввел тег
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = escape_md(tag)
    escaped_password = escape_md(password)
                         
    await state.update_data(tag=tag, password=password)
    await state.set_state(Form.waiting_for_password_confirmation)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Перегенерировать", callback_data='regenerate')],
        [types.InlineKeyboardButton(text="Сохранить", callback_data=f"confirm:save:{tag}")]
    ])

                                    
    # Отправляем сообщение с паролем, где пароль скрыт и начинается с новой строке
    msg_text = f'Тег: {escaped_tag}\nПароль: ||{escaped_password}|| \n\n\\* Отобразить \\- Тап по паролю\n\n  Сложно запомнить такой пароль\\? Перегенерируй\\! \n\n Нравится\\? Сохрани\\!'
    await message.answer(msg_text, parse_mode="MarkdownV2", reply_markup=markup)

    

# Обработчик для кнопки "Перегенерировать"
@dp.callback_query(F.data == 'regenerate', StateFilter(Form.waiting_for_password_confirmation))
async def regenerate_password(callback_query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    tag = user_data['tag']
    # Генерация нового пароля с использованием того же тега
    password = generate_password()
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = escape_md(tag)
    escaped_password = escape_md(password)

    await state.update_data(tag=tag, password=password)
    await state.set_state(Form.waiting_for_password_confirmation)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Перегенерировать", callback_data='regenerate')],
        [types.InlineKeyboardButton(text="Сохранить", callback_data=f"confirm:save:{tag}")]
    ])


    # Отправляем пароль пользователю и предупреждение о проверке надёжности
    msg_text = f'Тег: {escaped_tag}\nПароль: ||{escaped_password}|| \n\n\\* Отобразить \\- Тап по паролю\n\n  Сложно запомнить такой пароль\\? Перегенерируй\\! \n\n Нравится\\? Сохрани\\!'
    await callback_query.message.edit_text(msg_text, parse_mode="MarkdownV2", reply_markup=markup)
                    
 
# Обработчик кнопки "Сохранить"
@dp.callback_query(F.data.startswith("confirm:"), StateFilter(Form.waiting_for_password_confirmation))
async def save_password(callback_query: CallbackQuery, state: FSMContext):
    # Получение текущих данных из состояния
    user_data = await state.get_data()
    tag = user_data['tag']
    password = user_data['password']
    
    # Завершаем состояние FSM
    await state.clear()
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = escape_md(tag)
    escaped_password = escape_md(password)

    # Отправляем сообщение с паролем, где пароль скрыт и начинается с новой строки
    await callback_query.message.edit_text(f'Тег: {escaped_tag}\nПароль: ||{escaped_password}||', 
                         parse_mode="MarkdownV2", reply_markup=None)
    
    # Информируем пользователя об успешном сохранении
    await callback_query.answer("Пароль сохранён.")


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

