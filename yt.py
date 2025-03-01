import os
import time
import json
import telebot
from telebot import types
import yt_dlp

bot = telebot.TeleBot('7749883296:AAE9ndo4NxzT2xX-TO9RRM4A5eDT8fvqrKQ')

import firebase_admin
from firebase_admin import credentials, db

def read_firebase_json(path: str, search_value=None):
    # Инициализация Firebase, если не была выполнена ранее
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")  # Замените на путь к вашему ключу
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://downloader-19e7e-default-rtdb.firebaseio.com/"  # Укажите ваш URL базы данных
        })
    
    ref = db.reference(path)  # Получаем ссылку на указанный путь в базе данных
    data = ref.get()  # Читаем данные
    
    if search_value:
        # Проверяем, есть ли точное совпадение значения в данных
        exists = any(str(value) == str(search_value) for value in data.values()) if isinstance(data, dict) else False
        return exists
    
    return data  # Возвращаем данные без изменений


def append_firebase_json(path: str, data):
    # Инициализация Firebase, если не была выполнена ранее
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")  # Замените на путь к вашему ключу
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://downloader-19e7e-default-rtdb.firebaseio.com/"  # Укажите ваш URL базы данных
        })
    
    ref = db.reference(path)  # Получаем ссылку на указанный путь в базе данных
    ref.push(data)  # Добавляем новое значение в список

def is_donator(chat_id, filename="users.json"):
    """Проверяет, является ли пользователь донатором"""
    try:
        with open(filename, 'r') as f:
            donators = json.load(f)
        return str(chat_id) in donators  # chat_id хранится как строка
    except (FileNotFoundError, json.JSONDecodeError):
        return False  # Если файла нет или он пустой, никто не донатор

def downloader(file_name: str, url: str, settings: list = None):
    """Скачивает видео с YouTube с указанными настройками."""
    ydl_opts = {
            'outtmpl': f'{file_name}.%(ext)s',
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        }

    if settings:
        for setting in settings:
            if '=' in setting:
                key, value = setting.split('=', 1)
                ydl_opts[key] = value
            else:
                ydl_opts[setting] = True  # Если это флаг (без значения)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)  # Возвращаем точное имя файла
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == 1354551468:
        print('sfasfasf')
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Скачать видео", "Тут ничего нет", 'Для админа')
        bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Скачать видео", "Тут ничего нет")
        bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)

    user = read_firebase_json('users', message.chat.id)
    if user == False:
        append_firebase_json('users', message.chat.id)
        

@bot.message_handler(func=lambda message: message.text == "Скачать видео")
def request_video_link(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Обычный режим", callback_data="default"),
        types.InlineKeyboardButton("*Идут работы*", callback_data="sasf"),
    )
    bot.send_message(message.chat.id, "Выбери режим:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Для админа' and message.chat.id == 1354551468)
def admin_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Сделать пост", callback_data="post"),
    )
    bot.send_message(message.chat.id, "Выбери:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["default", "donate"])
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == "default":
        bot.send_message(chat_id, "Отправьте ссылку на видео.")
        bot.register_next_step_handler(call.message, download_video)
    elif call.data == "donate":
        if is_donator(chat_id):
            bot.send_message(chat_id, "Отправьте ссылку на видео (донат режим).")
            bot.register_next_step_handler(call.message, download_video_donate)
        else:
            bot.answer_callback_query(call.id, "❌ Вы не донатер!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'post')
def request_post_content(call):
    bot.send_message(call.message.chat.id, "Отправьте текст, фото или видео с подписью для рассылки.")
    bot.register_next_step_handler(call.message, send_post_to_users)

def send_post_to_users(message):
    users = read_firebase_json('users')  # Получаем всех пользователей из Firebase
    
    if not users:
        bot.send_message(message.chat.id, "❌ В базе данных нет пользователей для рассылки.")
        return
    
    if message.content_type == 'text':
        for user_id in users.values():
            bot.send_message(user_id, message.text)

    elif message.content_type == 'photo':
        file_id = message.photo[-1].file_id  # Берем самое большое фото
        caption = message.caption if message.caption else ""
        for user_id in users.values():
            bot.send_photo(user_id, file_id, caption=caption)

    elif message.content_type == 'video':   
        file_id = message.video.file_id
        caption = message.caption if message.caption else ""
        for user_id in users.values():
            bot.send_video(user_id, file_id, caption=caption)
    
    bot.send_message(message.chat.id, "✅ Пост успешно разослан!")


def download_video(message):
    url = message.text
    chat_id = message.chat.id
    file_name = f"video_{chat_id}_{int(time.time())}"

    clocks = bot.send_message(chat_id, '⏳')

    video_path = downloader(file_name, url, settings=["format=best", "ffmpeg-opts=-b:v 1000k"])

    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            bot.send_video(chat_id, video)
        os.remove(video_path)
    else:
        bot.send_message(chat_id, "❌ Ошибка скачивания. Попробуйте другую ссылку.")

    bot.delete_message(chat_id, clocks.message_id)

def download_video_donate(message):
    url = message.text
    chat_id = message.chat.id
    file_name = f"donate_video_{chat_id}_{int(time.time())}"

    downloading_msg = bot.send_message(chat_id, '💎 Скачиваем в донат-режиме...')

    video_path = downloader(file_name, url, settings=["format=bestvideo+bestaudio"])

    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            bot.send_video(chat_id, video)
        os.remove(video_path)
    else:
        bot.send_message(chat_id, "❌ Ошибка скачивания. Попробуйте другую ссылку.")

    bot.delete_message(chat_id, downloading_msg.message_id)

def add_donator(chat_id, filename="users.json"):
    """Добавляет chat_id в файл users.json"""
    try:
        with open(filename, 'r') as f:
            donators = json.load(f)
        
        if not isinstance(donators, list):
            donators = []  # Если не список, заменяем пустым списком
    except (FileNotFoundError, json.JSONDecodeError):
        donators = []  # Если файла нет, создаем новый список

    if str(chat_id) not in donators:
        donators.append(str(chat_id))
        with open(filename, 'w') as f:
            json.dump(donators, f, indent=4)
        return f"✅ ID {chat_id} добавлен в список донаторов!"
    else:
        return f"⚠️ ID {chat_id} уже есть в списке."
    
@bot.message_handler(func=lambda message: message.text == "Тут ничего нет")
def nothing(message):
    bot.send_message(message.chat.id, 'Тут рил ничего нет')

bot.polling(non_stop=True)
