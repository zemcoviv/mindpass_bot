import aiogram
import random
import string
import secrets
import asyncio
from aiogram.utils.callback_data import CallbackData
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
BOT_TOKEN = '7091814213:AAGOxYtD6XU8u_k7xcRqHTOKBBIvgembinw'

# инициализация бота и диспетчера с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Callback data factory для экшенов кнопок
hide_callback = CallbackData("help", "action")

# Создаем callback_data фабрику для кнопок главного меню и вложенных меню
main_menu_cd = CallbackData("main_menu", "action")
nested_menu_cd = CallbackData("nested_menu", "action", "level")
# Дополнительные callback_data
confirm_callback = CallbackData('confirm', 'action', 'tag')

    
# Генерация инлайн клавиатуры главного меню
def get_main_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Сгенерировать пароль", callback_data=main_menu_cd.new(action="generate")))
    keyboard.add(types.InlineKeyboardButton(text="Помощь", callback_data=main_menu_cd.new(action="help")))
    return keyboard

# Реакция на кнопки главного меню
@dp.callback_query_handler(main_menu_cd.filter(action=["generate", "help"]))
async def query_main_menu(callback_query: types.CallbackQuery, callback_data: dict):
    action = callback_data['action']
    if action == "generate":
        await callback_query.message.edit_text('Введите тег для вашего пароля:', reply_markup=None)
        await Form.waiting_for_tag.set()
    elif action == "help":
        await callback_query.message.edit_text(HELP_TEXT)
        # Добавим кнопку "Назад" или "Закрыть"
        back_keyboard = types.InlineKeyboardMarkup()
        back_keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data=nested_menu_cd.new(action="back", level="main")))
        await callback_query.message.edit_reply_markup(reply_markup=back_keyboard)

    await callback_query.answer()  # Убираем "часики"

# Реакция на кнопки вложенного меню
@dp.callback_query_handler(nested_menu_cd.filter(action="back"))
async def query_nested_menu(callback_query: types.CallbackQuery, callback_data: dict):
    level = callback_data['level']
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
@dp.message_handler(Command('start'))
async def command_start(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Привет! Это бот для генерации паролей.\n Создай надежный пароль, который будет легко запомнить.\n Выбери действие:", reply_markup=get_main_menu_keyboard())

    
# Обновленный обработчик команды /help
@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    # Удаление сообщения "Помощь"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    # Создание инлайн клавиатуры для скрытия справки
    keyboard = types.InlineKeyboardMarkup()
    hide_button = types.InlineKeyboardButton(text="Скрыть это сообщение", callback_data=hide_callback.new(action="hide"))
    keyboard.add(hide_button)

    await message.answer(HELP_TEXT, reply_markup=keyboard)
    
# Обработчик нажатия на кнопку "Скрыть это сообщение"
@dp.callback_query_handler(hide_callback.filter(action="hide"))
async def hide_help_message(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.message.delete()
    await callback_query.answer()  # Отправляем пустой ответ, чтобы убрать "часики" на кнопке

# Изменим обработчик кнопки "Сгенерировать пароль"
@dp.message_handler(text='Сгенерировать пароль', state='*')
async def enter_tag(message: types.Message):
    # Удаление сообщения "Выберите действие"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    # Удаление сообщения "Сгенерировать пароль"
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await message.reply('Введите тег для вашего пароля:')
    await Form.waiting_for_tag.set()  # устанавливаем состояние ожидания тега
    await callback_query.answer()

# Обработчик текстовых сообщений для получения тега и генерации пароля
@dp.message_handler(state=Form.waiting_for_tag)
async def process_tag(message: types.Message, state: FSMContext):
    # Получаем тег, введенный пользователем, и генерируем пароль
    tag = message.text
    password = generate_password()


    # Удаление сообщения с запросом на ввод тега
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    # Удаление сообщения, где пользователь ввел тег
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = aiogram.utils.markdown.escape_md(tag)
    escaped_password = aiogram.utils.markdown.escape_md(password)
                         
    await state.update_data(tag=tag, password=password)
    await Form.waiting_for_password_confirmation.set()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Перегенерировать", callback_data='regenerate'))
    markup.add(types.InlineKeyboardButton("Сохранить", callback_data=confirm_callback.new(action='save', tag=tag)))

                                    
    # Отправляем сообщение с паролем, где пароль скрыт и начинается с новой строки
    await message.answer(f'Тег: {escaped_tag}\nПароль: ||{escaped_password}|| \n\n\* Отобразить \- Тап по паролю\n\n  Сложно запомнить такой пароль\? Перегенерируй\! \n\n Нравится\? Сохрани\!', parse_mode=aiogram.types.ParseMode.MARKDOWN_V2, reply_markup=markup)

    

# Обработчик для кнопки "Перегенерировать"
@dp.callback_query_handler(lambda c: c.data == 'regenerate', state=Form.waiting_for_password_confirmation)
async def regenerate_password(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    tag = user_data['tag']
    # Генерация нового пароля с использованием того же тега
    password = generate_password()
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = aiogram.utils.markdown.escape_md(tag)
    escaped_password = aiogram.utils.markdown.escape_md(password)

    await state.update_data(tag=tag, password=password)
    await Form.waiting_for_password_confirmation.set()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Перегенерировать", callback_data='regenerate'))
    markup.add(types.InlineKeyboardButton("Сохранить", callback_data=confirm_callback.new(action='save', tag=tag)))


    # Отправляем пароль пользователю и предупреждение о проверке надёжности
    await callback_query.message.edit_text(f'Тег: {escaped_tag}\nПароль: ||{escaped_password}|| \n\n\* Отобразить \- Тап по паролю\n\n  Сложно запомнить такой пароль\? Перегенерируй\! \n\n Нравится\? Сохрани\!', parse_mode=aiogram.types.ParseMode.MARKDOWN_V2, reply_markup=markup)
                    
 
# Обработчик кнопки "Сохранить"
@dp.callback_query_handler(confirm_callback.filter(action='save'), state=Form.waiting_for_password_confirmation)
async def save_password(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение текущих данных из состояния
    user_data = await state.get_data()
    tag = user_data['tag']
    password = user_data['password']
    
    # Завершаем состояние FSM (если после сохранения пароля это больше не требуется)
    await state.finish()
    
    # Обратите внимание на двойной обратный слеш для экранирования в MarkdownV2
    escaped_tag = aiogram.utils.markdown.escape_md(tag)
    escaped_password = aiogram.utils.markdown.escape_md(password)

    # Отправляем сообщение с паролем, где пароль скрыт и начинается с новой строки
    await callback_query.message.edit_text(f'Тег: {escaped_tag}\nПароль: ||{escaped_password}||', 
                         parse_mode=aiogram.types.ParseMode.MARKDOWN_V2, reply_markup=None)
    
    # Убираем клавиатуру после сохранения пароля
    await callback_query.message.edit_reply_markup(reply_markup=None)
    
    # Информируем пользователя об успешном сохранении
    await callback_query.answer("Пароль сохранён.")


# Запуск бота
if __name__ == "__main__":
    aiogram.executor.start_polling(dp, skip_updates=True)

