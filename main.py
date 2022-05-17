import os
import random
from random import randint
import telebot
import boto3
import json
from io import BytesIO
from gtts import gTTS
from telebot import types
import logging
from pydub import AudioSegment
import speech_recognition as sr

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))


# ----------------Логгер------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

root_handler = logging.getLogger().handlers[0]
root_handler.setFormatter(logging.Formatter(
	"%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
))


# ---------------- Текст ----------------------------------------

RESET_LEARNING = 'Учить числа с нуля'

ADD_NUMBERS = 'Добавить новые числа'

LIST = 'Посмотреть изучаемые числа'

LEARN = 'Учить'

KNOW = 'Знаю'

DONT_KNOW = 'Не знаю'

END = 'Закончить'

END_BACK_TO_MENU = 'Молодец! Ты хорошо поучил(а)! Выбери что хочешь сделать'

INVALID_INPUT = 'Ты ввел что-то не то, попробуй еще раз или перепроверь что ввод корректный'

INPUT_NUMBERS = 'Введи числа, которые ты хочешь учить в подобном формате:\n<b>1-5,8,10,12-20,13</b>'

NO_MORE_NUMBERS = 'Я тебя больше ничему не могу научить...'

NUMBERS_ADDED = 'Успешно добавлено'

START_MESSAGE = f'Привет! Я научу тебя правильно произносить числа.\n' \
                f'Если ты хочешь сбросить свой прогресс и изучаемые числа нажми <b>{RESET_LEARNING}</b>\n' \
                f'Если ты хочешь добавить новые числа к уже изучаемым нажми <b>{ADD_NUMBERS}</b>\n' \
                f'Если ты хочешь посмотреть список изучаемых чисел нажми <b>{LIST}</b>\n' \
                f'Если ты хочешь приступить к изучению нажми <b>{LEARN}</b>\n' \
                f'Если что, ты всегда можешь ввести <b>/start</b> или <b>/help</b>,' \
                f'чтобы снова отобразить это сообщение и вернуться в начало'


# ---------------------Клавиатура---------------------------

def create_common_markup(one_time=False):
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=one_time)
    
    # Создаем кнопки
    start_learning_btn = types.KeyboardButton(RESET_LEARNING)
    learn_btn = types.KeyboardButton(LEARN)
    add_numbers_btn = types.KeyboardButton(ADD_NUMBERS)
    number_list_btn = types.KeyboardButton(LIST)
    
    # Добавляем кнопки в клавиатуру в два ряда
    markup.add(start_learning_btn, learn_btn)
    markup.add(add_numbers_btn, number_list_btn)
    return markup


def create_learn_markup():
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup()

    # Создаем кнопки
    learn_btn = types.KeyboardButton("Учить дальше")
    dont_know_btn = types.KeyboardButton(DONT_KNOW)
    stop_learn_btn = types.KeyboardButton(END)
    
    # Добавляем кнопки в клавиатуру в два ряда
    markup.add(learn_btn)
    markup.add(dont_know_btn)
    markup.add(stop_learn_btn)
    return markup

# Создаем клавиатуры и сохраняем
common_markup = create_common_markup()
learn_markup = create_learn_markup()
# Эту клавиатуру указываем чтобы спрятать текущую и показать обычную
hide_markup = types.ReplyKeyboardRemove()


# ---------------------Object Storage---------------------------

s3 = boto3.resource(
    's3',
    aws_access_key_id='YCAJEibMQ54FsR4sCwWVeQOtW',
    aws_secret_access_key='YCPyoSsswGbWGS_dlAcoLmbfOEgyDZJLgyQ1_bjD',
    region_name='ru-central1',
    endpoint_url='https://storage.yandexcloud.net'
).Bucket('nplb')

json.load_s3 = lambda f: json.load(s3.Object(key=f).get()["Body"])
json.dump_s3 = lambda obj, f: s3.Object(key=f).put(Body=json.dumps(obj))


# ----------------------Просто функции--------------------------
def isNumber(s):
    negative = False
    if (s[0] == '-'):
        negative = True
    if negative == True:
        s = s[1:]
    try:
        n = int(s)
        return True
    except ValueError:
        return False


def getNumberList(numberString):
    numberList = []
    ranges = numberString.split(',')
    for range_ in ranges:
        range_ = range_.split('-')
        if len(range_) == 1:
            if not isNumber(range_[0]):
                raise ValueError("В вводе содержится не число")
            numberList.append(int(range_[0]))
        else:
            if int(range_[0]) > int(range_[1]):
                range_[0], range_[1] = range_[1], range_[0]
            for n in range(int(range_[0]), int(range_[1]) + 1):
                if not isNumber(range_[0]) or not isNumber(range_[1]):
                    raise ValueError("В вводе содержится не число")
                
                    
                numberList.append(n)
    return numberList

def numberList2String(numbers):
    if not numbers:
        return ""
    last_number = -2
    numbers_string = ""
    first_num = False
    for number in numbers:
        if number != last_number + 1:
            if numbers_string != "":
                if not first_num:
                    numbers_string += str(last_number)
                numbers_string += ", "
            numbers_string += str(number)
            first_num = True
            
        else:
            if first_num:
                numbers_string += " - "
                first_num = False
        last_number = number
    if not first_num:
        numbers_string += str(last_number)
    return numbers_string

def resetNumbers(chatId):
    data = json.load_s3("data.json")
    data[str(chatId)] = {"numbers": {"0": [], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}, "last_number": 0, "last_category": "0"}

    json.dump_s3(data, "data.json")


def getFpOfSynthesizedNumber(number):
    tts = gTTS(text=str(number), lang="en")
    
    file_name_mp3 = "/tmp/" + str(number) + ".mp3"
    tts.save(file_name_mp3)

    file_name_opus = "/tmp/" + str(number) + ".opus"
    sound = AudioSegment.from_mp3(file_name_mp3)
    sound.export(file_name_opus, format="opus")

    return file_name_opus


r = sr.Recognizer()

def recognise(filename):
    with sr.AudioFile(filename) as source:
        audio_text = r.listen(source)
        try:
            text = r.recognize_google(audio_text, language="en-GB")
            print('Converting audio transcripts into text ...')
            print(text)
            return text
        except:
            print('Sorry.. run again...')
            return "Sorry.. run again..."


# --------------------- Бот ---------------------

@bot.message_handler(commands=['help', 'start'])
def say_welcome(message):
    logger.info('Пользователь ввел: %s', message.text)
    bot.send_message(message.chat.id, START_MESSAGE, reply_markup=common_markup, parse_mode="HTML")
    logger.info("Отработало")


@bot.message_handler(commands=['start_learning'])
def start_learning(message):
    msg = bot.send_message(message.chat.id, INPUT_NUMBERS, reply_markup=hide_markup, parse_mode="HTML")
    resetNumbers(message.chat.id)
    bot.register_next_step_handler(msg, add_numbers)

    logger.info("Отработало")


@bot.message_handler(commands=['learn'])
def learn(message):
    
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    # Ищем непустые категории
    not_empty_categories = []
    for category in ["0", "1", "2", "3", "4", "5"]:
        if data[chatId]["numbers"][category]:
            not_empty_categories.append(category)
    if not not_empty_categories:
        bot.send_message(message.chat.id, NO_MORE_NUMBERS, reply_markup=common_markup)
        return
    
    # Строим веса
    weights = []
    for i in range(len(not_empty_categories) - 1, -1, -1):
        weights.append(8**i)

    # Выбираем категорию в соответствии с весами
    category = random.choices(not_empty_categories, weights=weights, k=1)[0]
    
    # Выбираем число из выбранной категории
    numbers = data[chatId]["numbers"][category]
    number = numbers[randint(0, len(numbers) - 1)]

    # Озвучиваем число
    # file_name = getFpOfSynthesizedNumber(number)

    # Сохраняем число и категорию чтобы после 
    # ответа знаю/не знаю переместить нужное число
    # в нужную категорию
    data[chatId]["last_number"] = number
    data[chatId]["last_category"] = category
    
    json.dump_s3(data, "data.json")
    
    msg = bot.send_message(message.chat.id, number, reply_markup=learn_markup)
    
    # with open(file_name, "rb") as voice:
    #     bot.send_voice(message.chat.id, voice)

    bot.register_next_step_handler(msg, handle_answer)
    logger.info("Отработало")


def add_numbers(message):
    logger.info('Пользователь ввел: %s', message.text)

    if message.text == '/start' or message.text == '/help':
        say_welcome(message)
        return

    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    # Добавляем числа в нулевую категорию и убираем повторы
    try:
        data[chatId]["numbers"]["0"] += getNumberList(message.text)
    except:
        logger.exception("В вводе содержится не число")
        bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)
        return
    
    category_0_set = set(data[chatId]["numbers"]["0"])
    for category in ["1", "2", "3", "4", "5", "6"]:
        category_0_set -= set(data[chatId]["numbers"][category])
    data[chatId]["numbers"]["0"] = list(category_0_set)
    
    json.dump_s3(data, "data.json")
    
    bot.send_message(message.chat.id, NUMBERS_ADDED, reply_markup=common_markup)

    logger.info("Отработало")

@bot.message_handler(commands=['add_numbers'])
def add_numbers_handler(message):
    msg = bot.send_message(message.chat.id, INPUT_NUMBERS, reply_markup=hide_markup, parse_mode="HTML")
    bot.register_next_step_handler(msg, add_numbers)

    logger.info("Отработало")

@bot.message_handler(commands=['list'])
def number_list(message):

    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    
    numbers = []
    for category in ["0", "1", "2", "3", "4", "5"]:
        numbers += data[chatId]["numbers"][category]
    
    numbers.sort()
    numbers_str = numberList2String(numbers)
    if numbers_str != "":
        bot.send_message(message.chat.id, numbers_str, reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, "Вы ничего не учите", reply_markup=common_markup)
    
    logger.info("Отработало")

def know(message):
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    last_category = data[chatId]["last_category"]
    last_number = data[chatId]["last_number"]
    data[chatId]["numbers"][last_category].remove(last_number)
    data[chatId]["numbers"][str(min(int(last_category) + 1, 6))].append(last_number)
    
    json.dump_s3(data, "data.json")

    bot.send_message(message.chat.id, "Правильно!", reply_markup=learn_markup)

    logger.info("Отработало")

def dont_know(message):
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    last_category = data[chatId]["last_category"]
    last_number = data[chatId]["last_number"]
    data[chatId]["numbers"][last_category].remove(last_number)
    data[chatId]["numbers"][str(max(int(last_category) - 1, 0))].append(last_number)
    
    json.dump_s3(data, "data.json")

    bot.send_message(message.chat.id, "Не правильно!", reply_markup=learn_markup)
    
    file_name = getFpOfSynthesizedNumber(last_number)
    with open(file_name, "rb") as voice:
        bot.send_voice(message.chat.id, voice)

    logger.info("Отработало")


@bot.message_handler(content_types='text')
def message_reply(message):
    logger.info('Пользователь ввел: %s', message.text)
    if message.text == RESET_LEARNING:
        start_learning(message)
    elif message.text == LEARN or message.text == "Учить дальше":
        learn(message)
    elif message.text == ADD_NUMBERS:
        add_numbers_handler(message)
    elif message.text == LIST:
        number_list(message)
    elif message.text == END:
        bot.send_message(message.chat.id, END_BACK_TO_MENU, reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)


def handle_answer(message):
    if message.text:
        if message.text == END:
            bot.send_message(message.chat.id, END_BACK_TO_MENU, reply_markup=common_markup)
        elif message.text == DONT_KNOW:
            dont_know(message)
            data = json.load_s3("data.json")
            chatId = str(message.chat.id)
            last_number = data[chatId]["last_number"]
            bot.send_message(message.chat.id, "Ну раз не знаешь, то вот -- запоминай", reply_markup=learn_markup)
            file_name = getFpOfSynthesizedNumber(last_number)
            with open(file_name, "rb") as voice:
                bot.send_voice(message.chat.id, voice)
        else:
            bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)
        return

    filename = "num"
    file_name_full="/tmp/"+filename+".ogg"
    file_name_full_converted="/tmp/"+filename+".wav"
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_name_full, 'wb') as new_file:
        new_file.write(downloaded_file)
    

    sound = AudioSegment.from_ogg(file_name_full)
    sound.export(file_name_full_converted, format="wav")

    text=recognise(file_name_full_converted)
    
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    last_number = data[chatId]["last_number"]
    if (text == str(last_number)):
        know(message)
    else:
        dont_know(message)
        bot.send_message(message.chat.id, "Не правильно!", reply_markup=learn_markup)
        file_name = getFpOfSynthesizedNumber(last_number)
        with open(file_name, "rb") as voice:
            bot.send_voice(message.chat.id, voice)

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    bot.send_message(message.chat.id, "Не время для голосового", reply_markup=common_markup)

# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
