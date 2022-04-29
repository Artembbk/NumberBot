import os
from random import randint
import telebot
import boto3
import json
from io import BytesIO
from gtts import gTTS
from telebot import types

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    start_learning_btn = types.KeyboardButton('Начать учить числа c нуля')
    markup.add(start_learning_btn)
    bot.send_message(message.chat.id, START_MESSAGE, reply_markup=markup)

@bot.message_handler(commands=['start_learning'])
def start_learning(message):
    print('start_learning')
    msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                            "1-5,8,10,12-20,13")
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
    bot.send_message(message.chat.id, number)
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

    bot.send_message(message.chat.id, "Успешно добавлено")

@bot.message_handler(commands=['add_numbers'])
def add_numbers_handler(message):
    print(add_numbers_handler)
    msg = bot.send_message(message.chat.id, "Введи числа, которые ты хочешь учить в подобном формате:\n"
                                            "1-5,8,10,12-20,13")
    bot.register_next_step_handler(msg, add_numbers)

@bot.message_handler(commands=['list'])
def number_list(message):
    data = json.load_s3("data.json")
    numbers = data[str(message.chat.id)]["numbers"]
    bot.send_message(message.chat.id, str(numbers))

@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == 'Начать учить числа c нуля':
        start_learning(message)
    else:
        bot.send_message(message.chat.id, "что то странное")

# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
