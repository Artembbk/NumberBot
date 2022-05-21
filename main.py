from curses.ascii import isdigit
import os
import random
from random import randint
from re import M
import telebot
import boto3
import json
from io import BytesIO
from gtts import gTTS
from telebot import types
import logging
from pydub import AudioSegment
import speech_recognition as sr
from enum import Enum

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))


# ----------------Логгер------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

root_handler = logging.getLogger().handlers[0]
root_handler.setFormatter(logging.Formatter(
	"%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
))


languages = {
    "Английский": "en",
    "Французский": "fr",
    "Немецкий": "de"
}

modes = {
    "По числу записать голосовое": "numbers",
    "По голосовому написать число": "numbers_reversed",
}

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
                f'Когда ты нажмешь <b>{LEARN}</b> тебе будет присланно число и в ответ тебе надо будет отправить голосовое сообщение с произношением\n' \
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
    change_mode_btn = types.KeyboardButton("Поменять режим изучения")
    
    # Добавляем кнопки в клавиатуру в два ряда
    markup.add(start_learning_btn, learn_btn)
    markup.add(add_numbers_btn, number_list_btn, change_mode_btn)
    return markup


def create_learn_markup_dont_know():
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup()

    # Создаем кнопки
    learn_btn = types.KeyboardButton("Учить дальше")
    dont_know_btn = types.KeyboardButton(DONT_KNOW)
    stop_learn_btn = types.KeyboardButton(END)
    
    # Добавляем кнопки в клавиатуру в два ряда
    markup.add(dont_know_btn)
    markup.add(stop_learn_btn)
    return markup

def create_learn_markup_continue():
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup()

    # Создаем кнопки
    learn_btn = types.KeyboardButton("Учить дальше")
    dont_know_btn = types.KeyboardButton(DONT_KNOW)
    stop_learn_btn = types.KeyboardButton(END)
    
    # Добавляем кнопки в клавиатуру в два ряда
    markup.add(learn_btn)
    markup.add(stop_learn_btn)
    return markup


def create_language_markup():
    markup = types.ReplyKeyboardMarkup()

    english_btn = types.KeyboardButton("Английский")
    french_btn = types.KeyboardButton("Французский")
    german_btn = types.KeyboardButton("Немецкий")

    markup.add(english_btn, french_btn, german_btn)
    return markup


def create_mode_markup():
    markup = types.ReplyKeyboardMarkup()

    num_to_voice_btn = types.KeyboardButton("По числу записать голосовое")
    voice_to_num_btn = types.KeyboardButton("По голосовому написать число")

    markup.add(voice_to_num_btn, num_to_voice_btn)
    return markup

# Создаем клавиатуры и сохраняем
common_markup = create_common_markup()
learn_markup_continue = create_learn_markup_continue()
learn_markup_dont_know = create_learn_markup_dont_know()
language_markup = create_language_markup()
mode_markup = create_mode_markup()
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

def resetNumbers(chatId, language):
    data = json.load_s3("data.json")
    data[chatId] = {"numbers": {"0": [], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
                    "numbers_reversed": {"0": [], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
                    "last_number": 0, "last_category": "0", "language": language, "mode": modes["По числу записать голосовое"]}

    json.dump_s3(data, "data.json")
    logger.info("Отработало")


def synthesizeNumber(number, language, filename):
    tts = gTTS(text=str(number), lang=language)
    
    tts.save("/tmp/num.mp3");
    
    sound = AudioSegment.from_mp3("/tmp/num.mp3")
    sound.export(filename, format="opus")
    logger.info("Отработало")

r = sr.Recognizer()

def recognise(filename, language):
    with sr.AudioFile(filename) as source:
        audio_text = r.listen(source)
        try:
            text = r.recognize_google(audio_text, language=language)
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


def start_learning(message):
    msg = bot.send_message(message.chat.id, "Выбери язык", reply_markup=language_markup, parse_mode="HTML")
    bot.register_next_step_handler(msg, start_learning2)


def start_learning2(message):
    msg = bot.send_message(message.chat.id, INPUT_NUMBERS, reply_markup=hide_markup, parse_mode="HTML")
    language = languages[message.text]
    resetNumbers(str(message.chat.id), language)
    bot.register_next_step_handler(msg, add_numbers)

    logger.info("Отработало")


def change_mode(message):
    msg = bot.send_message(message.chat.id, "Выбери режим обучения", reply_markup=mode_markup)
    bot.register_next_step_handler(msg, change_mode2)
    logger.info("Отработало")

def change_mode2(message):
    data = json.load_s3("data.json")
    data[str(message.chat.id)]["mode"] = modes[message.text]
    json.dump_s3(data, "data.json")

    bot.send_message(message.chat.id, "Режим обучения успешно изменен", reply_markup=common_markup)
    logger.info("Отработало")


def choose_number(message):
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    mode = data[chatId]["mode"]
    
    # Ищем непустые категории
    not_empty_categories = []
    for category in ["0", "1", "2", "3", "4", "5"]:
        if data[chatId][mode][category]:
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
    numbers = data[chatId][mode][category]
    number = numbers[randint(0, len(numbers) - 1)]

    # Сохраняем число и категорию чтобы после 
    # ответа знаю/не знаю переместить нужное число
    # в нужную категорию
    data[chatId]["last_number"] = number
    data[chatId]["last_category"] = category
    
    json.dump_s3(data, "data.json")

    return number


def learn(message):
    number = choose_number(message)
    
    msg = bot.send_message(message.chat.id, number, reply_markup=learn_markup_dont_know)
    
    bot.register_next_step_handler(msg, handle_answer)
    logger.info("Отработало")


def learn_reversed(message):
    number = choose_number(message)
    send_voice(message, number)
    msg=bot.send_message(message.chat.id, "Что это за число?", reply_markup=hide_markup)
    bot.register_next_step_handler(msg, handle_answer_reversed)


def add_numbers(message):
    logger.info('Пользователь ввел: %s', message.text)

    if message.text == '/start' or message.text == '/help':
        say_welcome(message)
        return

    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    for numbers in ["numbers", "numbers_reversed"]:
        # Добавляем числа в нулевую категорию и убираем повторы
        try:
            data[chatId][numbers]["0"] += getNumberList(message.text)
        except:
            logger.exception("В вводе содержится не число")
            bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)
            return
        
        category_0_set = set(data[chatId][numbers]["0"])
        for category in ["1", "2", "3", "4", "5", "6"]:
            category_0_set -= set(data[chatId][numbers][category])
        data[chatId][numbers]["0"] = list(category_0_set)
    
    json.dump_s3(data, "data.json")
    
    bot.send_message(message.chat.id, NUMBERS_ADDED, reply_markup=common_markup)

    logger.info("Отработало")

def add_numbers_handler(message):
    msg = bot.send_message(message.chat.id, INPUT_NUMBERS, reply_markup=hide_markup, parse_mode="HTML")
    bot.register_next_step_handler(msg, add_numbers)

    logger.info("Отработало")

def number_list(message):

    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    
    
    numbers = []
    for category in ["0", "1", "2", "3", "4", "5", "6"]:
        numbers += data[chatId]["numbers"][category]
    
    numbers.sort()
    numbers_str = numberList2String(numbers)
    if numbers_str != "":
        bot.send_message(message.chat.id, numbers_str, reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, "Вы ничего не учите", reply_markup=common_markup)
    
    logger.info("Отработало")

def up_category(message):
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    mode = data[chatId]["mode"]
    last_category = data[chatId]["last_category"]
    last_number = data[chatId]["last_number"]
    data[chatId][mode][last_category].remove(last_number)
    data[chatId][mode][str(min(int(last_category) + 1, 6))].append(last_number)
    
    json.dump_s3(data, "data.json")

    logger.info("Отработало")


def know(message):
    up_category(message)
    bot.send_message(message.chat.id, "Правильно!", reply_markup=learn_markup_continue)


def to_down_category(message):
    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    mode = data[chatId]["mode"]
    last_category = data[chatId]["last_category"]
    last_number = data[chatId]["last_number"]
    data[chatId][mode][last_category].remove(last_number)
    data[chatId][mode][str(max(int(last_category) - 1, 0))].append(last_number)
    
    json.dump_s3(data, "data.json")

    logger.info("Отработало")


def dont_know(message, message_for_user):
    to_down_category(message)
    chatId = str(message.chat.id)
    data = json.load_s3("data.json")
    last_number = data[chatId]["last_number"]
    bot.send_message(message.chat.id, message_for_user, reply_markup=learn_markup_continue)
    
    if (data[chatId]["mode"] == modes["По числу записать голосовое"]):
        send_voice(message, last_number)
    else:
        bot.send_message(message.chat.id, last_number)
    logger.info("Отработало")
    # file_name = getFpOfSynthesizedNumber(last_number)
    # with open(file_name, "rb") as voice:
    #     bot.send_voice(message.chat.id, voice)


def send_voice(message, number):
    data = json.load_s3("data.json")
    language = data[str(message.chat.id)]["language"]
    
    file_name =  str(number) + "-" + language + ".opus"
    file_name_saved = '/tmp/' + file_name
    
    

    success = True
    try:
        s3.download_file(file_name, file_name_saved)
    except:
        success = False

    if not success:
        synthesizeNumber(number, language, file_name_saved)
        s3.upload_file(file_name_saved, file_name)

    with open(file_name_saved, "rb") as voice:
        return bot.send_voice(message.chat.id, voice)
    logger.info("Отработало")



@bot.message_handler(content_types='text')
def message_reply(message):
    logger.info('Пользователь ввел: %s', message.text)
    if message.text == RESET_LEARNING:
        start_learning(message)
    elif message.text == LEARN or message.text == "Учить дальше":
        data = json.load_s3("data.json")
        if data[str(message.chat.id)]["mode"] == modes["По числу записать голосовое"]:
            learn(message)
        elif data[str(message.chat.id)]["mode"] == modes["По голосовому написать число"]:
            learn_reversed(message)
    elif message.text == ADD_NUMBERS:
        add_numbers_handler(message)
    elif message.text == LIST:
        number_list(message)
    elif message.text == "Поменять режим изучения":
        change_mode(message)
    elif message.text == END:
        bot.send_message(message.chat.id, END_BACK_TO_MENU, reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)
    logger.info("Отработало")


def handle_answer(message):
    if message.text:
        if message.text == END:
            bot.send_message(message.chat.id, END_BACK_TO_MENU, reply_markup=common_markup)
        elif message.text == DONT_KNOW:
            dont_know(message, "Ну раз не знаешь, то вот -- запоминай")
        else:
            bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)
        logger.info("Отработало")
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

    data = json.load_s3("data.json")
    chatId = str(message.chat.id)
    language = data[chatId]["language"]

    text=recognise(file_name_full_converted, language)
    
    
    
    last_number = data[chatId]["last_number"]
    if (text == str(last_number)):
        know(message)
    else:
        dont_know(message, "Не правильно!")
    logger.info("Отработало")


def handle_answer_reversed(message):
    data = json.load_s3("data.json")
    answer = message.text
    if isNumber(answer):
        if int(answer) == data[str(message.chat.id)]["last_number"]:
            know(message)
        else:
            dont_know(message, "Не правильно")
    else:
        bot.send_message(message.chat.id, INVALID_INPUT, reply_markup=common_markup)


@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    bot.send_message(message.chat.id, "Не время для голосового", reply_markup=common_markup)
    logger.info("Отработало")

# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
