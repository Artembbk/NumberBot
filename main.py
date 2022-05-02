import os
import random
from random import randint
import telebot
import boto3
import json
from io import BytesIO
from gtts import gTTS
from telebot import types

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))


def create_common_markup(one_time=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=one_time)
    start_learning_btn = types.KeyboardButton('Учить числа c нуля')
    learn_btn = types.KeyboardButton('Учить')
    add_numbers_btn = types.KeyboardButton('Добавить новые числа')
    number_list_btn = types.KeyboardButton('Посмотреть изучаемые числа')
    markup.add(start_learning_btn, learn_btn)
    markup.add(add_numbers_btn, number_list_btn)
    return markup


def create_learn_markup():
    markup = types.ReplyKeyboardMarkup()
    know_btn = types.KeyboardButton('Знаю')
    dont_know_btn = types.KeyboardButton('Не знаю')
    stop_learn_btn = types.KeyboardButton('Закончить')
    markup.add(know_btn, dont_know_btn)
    markup.add(stop_learn_btn)
    return markup


common_markup = create_common_markup()
learn_markup = create_learn_markup()
hide_markup = types.ReplyKeyboardRemove()

s3 = boto3.resource(
    's3',
    aws_access_key_id='YCAJEibMQ54FsR4sCwWVeQOtW',
    aws_secret_access_key='YCPyoSsswGbWGS_dlAcoLmbfOEgyDZJLgyQ1_bjD',
    region_name='ru-central1',
    endpoint_url='https://storage.yandexcloud.net'
).Bucket('nplb')

json.load_s3 = lambda f: json.load(s3.Object(key=f).get()["Body"])
json.dump_s3 = lambda obj, f: s3.Object(key=f).put(Body=json.dumps(obj))

# ---------------- dialog params ----------------
START_MESSAGE = "Привет! Я научу тебя правильно произносить числа. " \
                "Пока я могу только скинуть тебе правильное произношение чиссел, но " \
                "скоро я смогу также проверять твое произношение!\n\n" \
                "Команды:\n" \
                "/start - Приветствие\n" \
                "/help - Список команд\n" \
                "/start_learning - Начать учить числа с нуля\n" \
                "/add_numbers - Добавить числа к изучению\n" \
                "/learn - прислать произношение случайного числа из выбранных\n" \
                "/list - список чисел для изучения"

START_LEARNING = "Начать учить числа с нуля\n"


# ----------------------some functions------------
def isNumber(s):
    # handle for negative values
    negative = False
    if (s[0] == '-'):
        negative = True

    if negative == True:
        s = s[1:]

    # try to convert the string to int
    try:
        n = int(s)
        return True
    # catch exception if cannot be converted
    except ValueError:
        return False


def getNumberList(numberString):
    numberList = []
    ranges = numberString.split(',')
    for range_ in ranges:
        range_ = range_.split('-')
        if len(range_) == 1:
            numberList.append(int(range_[0]))
        else:
            for n in range(int(range_[0]), int(range_[1]) + 1):
                numberList.append(n)
    return numberList


def resetNumbers(chatId):
    data = json.load_s3("data.json")

    print(data)
    print("found?", chatId in data)
    data[str(chatId)] = {"numbers": {"0": [], "1": [], "2": []}, "last_number": 0, "last_category": "0"}

    json.dump_s3(data, "data.json")


# --------------------- bot ---------------------

@bot.message_handler(commands=['help', 'start'])
def say_welcome(message):
    bot.send_message(message.chat.id, START_MESSAGE, reply_markup=common_markup)


@bot.message_handler(commands=['start_learning'])
def start_learning(message):
    try:
        print('start_learning')
        msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                                "1-5,8,10,12-20,13", reply_markup=hide_markup)
        resetNumbers(message.chat.id)
        bot.register_next_step_handler(msg, add_numbers)
    except Exception as e:
        print(e)


@bot.message_handler(commands=['learn'])
def learn(message):
    try:
        print('learn')
        data = json.load_s3("data.json")
        print(data)
        not_empty_categories = []
        weights = [6, 2, 1]
        for category in ["0", "1", "2"]:
            if data[str(message.chat.id)]["numbers"][category]:
                not_empty_categories.append(category)
        category = random.choices(not_empty_categories, weights=weights[:len(not_empty_categories)])[0]
        print("Oh")
        print(data)
        print(category)
        numbers = data[str(message.chat.id)]["numbers"][category]
        print("YEAH")
        print(numbers)
        number = numbers[randint(0, len(numbers) - 1)]
        tts = gTTS(text=str(number), lang="en")
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        data[str(message.chat.id)]["last_number"] = number
        data[str(message.chat.id)]["last_category"] = category
        json.dump_s3(data, "data.json")
        bot.send_message(message.chat.id, number, reply_markup=learn_markup)
        bot.send_voice(message.chat.id, fp)
    except Exception as e:
        print(e)

def add_numbers(message):
    try:
        print('add_numbers')
        data = json.load_s3("data.json")
        print("data = json.load_s3('data.json')")
        data[str(message.chat.id)]["numbers"]["0"] += getNumberList(message.text)
        print('data[str(message.chat.id)]["numbers"]["0"] += getNumberList(message.text)')
        data[str(message.chat.id)]["numbers"]["0"] = list(
            set(data[str(message.chat.id)]["numbers"]["0"]) - set(data[str(message.chat.id)]["numbers"]["1"]) - set(data[str(message.chat.id)]["numbers"]["2"])
        )
        print('data[str(message.chat.id)]["numbers"]["0"] = list')
        json.dump_s3(data, "data.json")
        print('json.dump_s3(data, "data.json")')
        bot.send_message(message.chat.id, "Успешно добавлено", reply_markup=common_markup)
    except Exception as e:
        print(e)


@bot.message_handler(commands=['add_numbers'])
def add_numbers_handler(message):
    print(add_numbers_handler)
    msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                            "1-5,8,10,12-20,13", reply_markup=hide_markup)
    bot.register_next_step_handler(msg, add_numbers)


@bot.message_handler(commands=['list'])
def number_list(message):
    print("number_list")
    data = json.load_s3("data.json")
    print(data)
    print(data[str(message.chat.id)]["numbers"]["0"])
    print(data[str(message.chat.id)]["numbers"]["1"])
    print(data[str(message.chat.id)]["numbers"]["2"])
    numbers = data[str(message.chat.id)]["numbers"]["0"] + data[str(message.chat.id)]["numbers"]["1"] + data[str(message.chat.id)]["numbers"]["2"]
    numbers.sort()
    bot.send_message(message.chat.id, str(numbers), reply_markup=common_markup)


def know(message):
    try:
        print('know')
        data = json.load_s3("data.json")
        print("know", data)
        last_category = data[str(message.chat.id)]["last_category"]
        last_number = data[str(message.chat.id)]["last_number"]
        data[str(message.chat.id)]["numbers"][last_category].remove(last_number)
        data[str(message.chat.id)]["numbers"][str(min(int(last_category) + 1, 2))].append(last_number)
        print("know", data)
        json.dump_s3(data, "data.json")
    except Exception as e:
        print(e)

def dont_know(message):
    print('dont_know')
    data = json.load_s3("data.json")
    print("dont_know", data)
    last_category = data[str(message.chat.id)]["last_category"]
    last_number = data[str(message.chat.id)]["last_number"]
    data[str(message.chat.id)]["numbers"][last_category].remove(last_number)
    data[str(message.chat.id)]["numbers"][str(max(int(last_category) - 1, 0))].append(last_number)
    print("dont_know", data)
    json.dump_s3(data, "data.json")


@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == 'Учить числа c нуля':
        start_learning(message)
    elif message.text == 'Учить':
        learn(message)
    elif message.text == 'Добавить новые числа':
        add_numbers_handler(message)
    elif message.text == 'Посмотреть изучаемые числа':
        number_list(message)
    elif message.text == 'Знаю':
        know(message)
        learn(message)
    elif message.text == 'Не знаю':
        dont_know(message)
        learn(message)
    elif message.text == 'Закончить':
        bot.send_message(message.chat.id, "Молодец! Ты хорошо поучил! Выбери что хочешь сделать", reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, "что то странное", reply_markup=common_markup)


# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
