from telebot.async_telebot import AsyncTeleBot
from telebot import util
from database import DataBase
from WB_feedbacks import WBParser
from yandex_AI import YandexAI
from envparse import Env
from answer_message import Answer
from pprint import pprint
import asyncio

env = Env()
env.read_envfile()


BOT_TOKEN = env("BOT_TOKEN", default="Not found")


bot = AsyncTeleBot(BOT_TOKEN)
db = DataBase()
user_parser = None
ya_ai = YandexAI(env("YANDEX_TOKEN"))
answer_list = []
my_state = {}
edit_msg = {"edit": None}


@bot.message_handler(commands=["start"])
async def start_handler(message):
    markup = util.quick_markup({"Старт": {"callback_data": "get_feedback"}})
    welcome_text = (
        "Привет, я {{ИМЯ}} - исскуственный интелект,"
        "помогаю отвечать на отзывы покупателей. Если ты "
        "начинающий продавец, то для тебя исспользование "
        "сервиса будет совершенно бесплатно."
        "\n \n"
        "Все что нужно сделать - это нажать на кнопку старт "
        "и подключить кабинет, вперед!"
    )
    await bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.message_handler(commands=["feedbacks"])
async def my_feedbacks(message):
    await bot.delete_message(message.chat.id, message.message_id)
    feedbacks_count = await db.get_count_query(message.from_user.id)
    await bot.send_message(
        message.chat.id, f"У Вас осталось {feedbacks_count} отзывов."
    )


@bot.message_handler(commands=["add_token"])
async def add_token(message):
    add_instruction = (
        "*1.* Перейдите в личный кабинет Wildberries (данное "
        "действие необходимо выполнить владельцу кабинета) "
        "[Профиль -> Настройки - Доступ к API](https://seller.wildberries.ru/about-portal/ru/)\n"
        "*2.* Введите имя токена, например WBBotToken\n"
        "*3.* Выберите 'Контент' и 'Вопросы и отзывы'\n"
        "*4.* Нажмите 'Создать токен'\n"
        "*Следующим сообщением отправьте токен!!!*"
    )
    await bot.delete_message(message.chat.id, message.id)
    await bot.set_state(message.from_user.id, "token", message.chat.id)
    await bot.send_message(message.chat.id, text=add_instruction, parse_mode="Markdown")


@bot.message_handler(commands=["get_feedbacks"])
async def get_feedbacks(message):
    await bot.delete_message(message.chat.id, message.message_id)
    user_data = await db.get_user_data(message.from_user.id)
    wb_token = user_data[3]
    # is_payed = True if user_data[2] == 1 else False
    feedbacks_count = user_data[4]
    global user_parser
    user_parser = WBParser(wb_token)
    markup = util.quick_markup(
        {
            "📤Опубликовать": {"callback_data": "publish"},
            "📝Редактировать": {"callback_data": "edit"},
            "🔁Сгенерировать новый ответ": {"callback_data": "regenerate"},
            "⛔️Не отвечать на отзыв": {"callback_data": "not_answer"},
        },
        row_width=2,
    )
    feedbacks = await user_parser.get_feedback()
    unanswered_count = len(feedbacks.get("data").get("feedbacks"))
    if feedbacks_count == 0:
        await bot.send_message(
            message.chat.id,
            f"Вам необходимо произвести оплату, "
            f"баланс ваших отзывов равен: {feedbacks_count}",
        )
    else:
        if unanswered_count > feedbacks_count:
            await bot.send_message(
                message.chat.id,
                "У Вас недостаточно отзывов чтобы ответить "
                "на все сообщения, пожалуйста произведите оплату. "
                "Для этого введите команду /tariffs",
            )
            unanswered_count = feedbacks_count
        if unanswered_count == 0:
            await bot.send_message(
                message.chat.id,
                "У Вас нет неотвеченных отзывов.",
            )
        i = 0
        while i != unanswered_count:
            text_feedback = feedbacks.get("data").get(
                "feedbacks")[i].get("text")
            company = (
                feedbacks.get("data")
                .get("feedbacks")[i]
                .get("productDetails")
                .get("brandName")
            )
            created_date = (
                feedbacks.get("data").get("feedbacks")[
                    i].get("createdDate")
            )
            product_name = (
                feedbacks.get("data")
                .get("feedbacks")[i]
                .get("productDetails")
                .get("productName")
            )
            get_product_valuation = (
                feedbacks.get("data").get("feedbacks")[
                    i].get("productValuation")
            )
            feedback_id = feedbacks.get("data").get(
                "feedbacks")[i].get("id")
            if text_feedback == "":
                await bot.send_message(
                    message.chat.id, "Невозможно ответить на пустой отзыв."
                )
                i += 1
                continue
            ai_feedback = await ya_ai.create_feetbacks(text_feedback, company)
            set_product_valuation = ""
            for index in range(1, 6, 1):
                if index <= int(get_product_valuation):
                    set_product_valuation += "⭐️"
                else:
                    set_product_valuation += "♦️"
            ai_answer = (
                ai_feedback.get("result")
                .get("alternatives")[0]
                .get("message")
                .get("text")
            )
            answer_message = Answer(
                company,
                product_name,
                set_product_valuation,
                created_date[:10],
                text_feedback,
                ai_answer,
                int(message.message_id) + 1,
                feedback_id,
            )
            my_state[message.message_id + i] = answer_message
            send_message = await answer_message.create_message()
            await bot.send_message(
                message.chat.id,
                send_message,
                reply_markup=markup,
                parse_mode="Markdown",
            )
            i += 1


@bot.message_handler(commands=["tariffs"])
async def get_tariffs(message):
    await bot.delete_message(message.chat.id, message.message_id)
    markup = util.quick_markup(
        {
            "100": {"callback_data": "pay_100"},
            "500": {"callback_data": "pay_500"},
            "1000": {"callback_data": "pay_1000"},
            "2000": {"callback_data": "pay_2000"},
            "10000": {"callback_data": "pay_10000"},
        },
        row_width=2,
    )
    answer_message = (
        "Доступные тарифы:\n\n"
        "Стартовый - 100 ответов. Цена 392 руб. Цена за 1 отзыв 3.92 руб.\n"
        "Базовый - 500 ответов. Цена 1592 руб. Цена за 1 отзыв 3.18 руб.\n"
        "Расширенный - 1000 ответов. Цена 2872 руб. Цена за 1 отзыв 2.87 руб.\n"
        "Премиум - 2000 ответов. Цена 5592 руб. Цена за 1 отзыв 2.79 руб.\n"
        "ТОП - 10000 ответов. Цена 23992 руб. Цена за 1 отзыв 2.39 руб.\n"
        "Выберите подходящий тариф."
    )
    await bot.send_message(message.chat.id, answer_message, reply_markup=markup)


@bot.message_handler()
async def test_message(message):
    state = await bot.get_state(message.from_user.id)
    markup = util.quick_markup(
        {
            "📤Опубликовать": {"callback_data": "publish"},
            "📝Редактировать": {"callback_data": "edit"},
            "🔁Сгенерировать новый ответ": {"callback_data": "regenerate"},
            "⛔️Не отвечать на отзыв": {"callback_data": "not_answer"},
        },
        row_width=2,
    )
    if state == "token":
        try:
            await db.set_token_query(uid=message.from_user.id, token=message.text)
            await bot.reply_to(message, "Токен был добавлен.")
            await bot.delete_state(message.from_user.id)
        except Exception as E:
            await bot.reply_to(message, "Произошла ошибка, сообщите администратору")
    elif state == "edit":
        await bot.delete_message(message.chat.id, message.message_id - 1)
        await bot.delete_message(message.chat.id, message.message_id)
        msg = edit_msg.pop("edit", None)
        await bot.delete_message(message.chat.id, msg.message_id)
        msg.ai_answer = message.text
        msg.message_id = message.message_id + 1
        my_state[message.message_id + 1] = msg
        new_msg = await msg.create_message()
        await bot.send_message(
            message.chat.id, new_msg, parse_mode="Markdown", reply_markup=markup
        )
        await bot.delete_state(message.from_user.id)


@bot.callback_query_handler(func=lambda callback: True)
async def callbacks(callback):
    uid = int(callback.from_user.id)
    markup = util.quick_markup(
        {
            "📤Опубликовать": {"callback_data": "publish"},
            "📝Редактировать": {"callback_data": "edit"},
            "🔁Сгенерировать новый ответ": {"callback_data": "regenerate"},
            "⛔️Не отвечать на отзыв": {"callback_data": "not_answer"},
        },
        row_width=2,
    )
    if callback.data == "get_feedback":
        add_user = await db.add_user_query(uid)
        if add_user:
            answer_message = (
                "Поздравляем, Вам доступно 60 бесплатных отзывов! Для того чтобы начать "
                "использовать бота введите команду /add_token для добавления токена"
            )
            await bot.send_message(callback.message.chat.id, answer_message)
        else:
            count_query = await db.get_count_query(callback.message.from_user.id)
            answer_message = (
                f"Ваш аккаунт был добавлен раннее, у Вас осталось {count_query} ответов. "
                f"Мы можете дополнительно приобрести отзывов, введите команду /tariffs для ознакомления с "
                f"нашими тарифами. Если вы еще не добавили свой магазин, введите команду "
                f"/add_token для добавления токена"
            )
            await bot.send_message(callback.message.chat.id, answer_message)
    elif callback.data == "pay_100":
        await db.add_count_query(uid, 100)
        await db.payed_query_true(uid)
        await bot.send_message(
            callback.message.chat.id, "Поздравляем, Вы оплатили 100 отзывов."
        )
    elif callback.data == "pay_500":
        await db.add_count_query(uid, 500)
        await db.payed_query_true(uid)
        await bot.send_message(
            callback.message.chat.id, "Поздравляем, Вы оплатили 500 отзывов."
        )
    elif callback.data == "pay_1000":
        await db.add_count_query(uid, 1000)
        await db.payed_query_true(uid)
        await bot.send_message(
            callback.message.chat.id, "Поздравляем, Вы оплатили 1000 отзывов."
        )
    elif callback.data == "pay_2000":
        await db.add_count_query(uid, 2000)
        await db.payed_query_true(uid)
        await bot.send_message(
            callback.message.chat.id, "Поздравляем, Вы оплатили 2000 отзывов."
        )
    elif callback.data == "pay_10000":
        await db.add_count_query(uid, 10000)
        await db.payed_query_true(uid)
        await bot.send_message(
            callback.message.chat.id, "Поздравляем, Вы оплатили 10000 отзывов."
        )
    elif callback.data == "edit":
        await bot.set_state(callback.from_user.id, "edit", callback.message.chat.id)
        edit_msg["edit"] = my_state.pop(callback.message.message_id-1, None)
        await bot.send_message(
            callback.message.chat.id,
            "Отправьте отредактированный отзыв " "в следующем сообщении.",
        )
    elif callback.data == "regenerate":
        fedback_msg = my_state.pop(callback.message.message_id-1, None)
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
        ai_feedback = await ya_ai.create_feetbacks(
            fedback_msg.text_feedback, fedback_msg.company
        )
        ai_answer = (
            ai_feedback.get("result").get("alternatives")[
                0].get("message").get("text")
        )
        fedback_msg.ai_answer = ai_answer
        my_state[callback.message.message_id + 1] = fedback_msg
        send_msg = await fedback_msg.create_message()
        await bot.send_message(
            callback.message.chat.id,
            send_msg,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    elif callback.data == "not_answer":
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    elif callback.data == "publish":
        fedback_msg = my_state.pop(callback.message.message_id-1, None)
        await user_parser.feedback_answer(
            fedback_msg.feedback_id, fedback_msg.ai_answer
        )
        # await user_parser.check_feedback(fedback_msg.feedback_id)
        await db.minus_count_query(uid)
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)


if __name__ == "__main__":
    asyncio.run(bot.polling(non_stop=True))
