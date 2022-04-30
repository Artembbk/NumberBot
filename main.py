import os
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
    data[str(chatId)] = {"numbers": []}

    json.dump_s3(data, "data.json")


# --------------------- bot ---------------------

@bot.message_handler(commands=['help', 'start'])
def say_welcome(message):
    bot.send_message(message.chat.id, START_MESSAGE, reply_markup=common_markup)


@bot.message_handler(commands=['start_learning'])
def start_learning(message):
    print('start_learning')
    msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                            "1-5,8,10,12-20,13", reply_markup=hide_markup)
    resetNumbers(message.chat.id)
    bot.register_next_step_handler(msg, add_numbers)


@bot.message_handler(commands=['learn'])
def learn(message):
    print('learn')
    data = json.load_s3("data.json")
    print(data)
    numbers = data[str(message.chat.id)]["numbers"]
    print(numbers)
    number = numbers[randint(0, len(numbers) - 1)]
    tts = gTTS(text=str(number), lang="en")
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    bot.send_message(message.chat.id, number, reply_markup=learn_markup)
    bot.send_voice(message.chat.id, fp)


def add_numbers(message):
    print('add_numbers1')
    data = json.load_s3("data.json")

    print(data[str(message.chat.id)]["numbers"])
    print(getNumberList(message.text))
    data[str(message.chat.id)]["numbers"] += getNumberList(message.text)
    print(data[str(message.chat.id)]["numbers"])
    data[str(message.chat.id)]["numbers"] = list(
        set(data[str(message.chat.id)]["numbers"])
    )

    json.dump_s3(data, "data.json")

    bot.send_message(message.chat.id, "Успешно добавлено", reply_markup=common_markup)


@bot.message_handler(commands=['add_numbers'])
def add_numbers_handler(message):
    print(add_numbers_handler)
    msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                            "1-5,8,10,12-20,13", reply_markup=hide_markup)
    bot.register_next_step_handler(msg, add_numbers)


@bot.message_handler(commands=['list'])
def number_list(message):
    data = json.load_s3("data.json")
    numbers = data[str(message.chat.id)]["numbers"]
    bot.send_message(message.chat.id, str(numbers), reply_markup=common_markup)


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
        learn(message)
    elif message.text == 'Не знаю':
        learn(message)
    elif message.text == 'Закончить':
        bot.send_message(message.chat.id, "Молодец! Ты хорошо поучил! Выбери что хочешь сделать", reply_markup=common_markup)
    else:
        bot.send_message(message.chat.id, "что то странное", reply_markup=common_markup)


# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
