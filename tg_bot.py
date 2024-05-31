from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.util import quick_markup
from telebot.types import CallbackQuery, Message, InlineKeyboardMarkup
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.asyncio_storage import StateMemoryStorage
from database import DataBase
from WB_feedbacks import WBParser
from yandex_AI import YandexAI
from envparse import Env
from answer_message import Answer
from keyboard import main_menu, start_menu, top_menu, tariffs
from pprint import pprint
import asyncio

env = Env()
env.read_envfile()

BOT_TOKEN = env("BOT_TOKEN", default="Not found")
clb_edit = CallbackData('mid', prefix='edit')
clb_regenerate = CallbackData('mid', prefix='regenerate')
clb_publish = CallbackData('mid', prefix='publish')
clb_not_answer = CallbackData('mid', prefix='not_answer')
clb_add_signature = CallbackData('mid', prefix='add_signature')


bot = AsyncTeleBot(BOT_TOKEN)
db = DataBase()
user_parser = None
ya_ai = YandexAI(env("YANDEX_TOKEN"))
answer_list = []
my_state = {}
state = None
edit_msg = {"edit": None}
my_signature = ''


async def create_markup(message_id: int) -> InlineKeyboardMarkup:
    feedback_kb = quick_markup(
        {
            "📤Опубликовать": {"callback_data": clb_publish.new(mid=message_id)},
            "📝Редактировать": {"callback_data": clb_edit.new(mid=message_id)},
            "🔁Сгенерировать новый ответ": {"callback_data": clb_regenerate.new(mid=message_id)},
            "⛔️Не отвечать на отзыв": {"callback_data": clb_not_answer.new(mid=message_id)},
            "✏️Добавить подпись": {"callback_data": clb_add_signature.new(mid=message_id)}
        }
    )
    return feedback_kb


@bot.message_handler(commands=["start"])
async def start_handler(message):
    welcome_text = (
        "Привет, я {{ИМЯ}} - исскуственный интелект,"
        "помогаю отвечать на отзывы покупателей. Если ты "
        "начинающий продавец, то для тебя исспользование "
        "сервиса будет совершенно бесплатно."
        "\n \n"
        "Все что нужно сделать - это нажать на кнопку старт "
        "и подключить кабинет, вперед!"
    )
    await bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu)


@bot.message_handler(commands=["feedbacks"])
async def my_feedbacks(message):
    await bot.delete_message(message.chat.id, message.message_id)
    feedbacks_count = await db.get_count_query(message.from_user.id)
    await bot.send_message(
        message.chat.id, f"У Вас осталось {feedbacks_count} отзывов."
    )


@bot.message_handler(commands=["add_token"])
async def add_token(message):
    global state
    add_instruction = (
        "*1.* Перейдите в личный кабинет Wildberries (данное "
        "действие необходимо выполнить владельцу кабинета) "
        "[Профиль -> Настройки - Доступ к API](https://seller.wildberries.ru/about-portal/ru/)\n"
        "*2.* Введите имя токена, например WBBotToken\n"
        "*3.* Выберите 'Контент' и 'Вопросы и отзывы'\n"
        "*4.* Нажмите 'Создать токен'\n"
        "*Следующим сообщением отправьте токен!!!*"
    )
    state = 'token'
    await bot.delete_message(message.chat.id, message.id)
    await bot.send_message(message.chat.id, text=add_instruction, parse_mode="Markdown")


@bot.message_handler(commands=["get_feedbacks"])
async def get_feedbacks(message):
    await bot.delete_message(message.chat.id, message.message_id)
    user_data = await db.get_user_data(message.from_user.id)
    wb_token = user_data[3]
    feedbacks_count = user_data[4]
    global user_parser
    user_parser = WBParser(wb_token)
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
            user_name = feedbacks.get("data").get("feedbacks")[i].get("userName")
            if text_feedback == "":
                # await bot.send_message(
                #     message.chat.id, "Невозможно ответить на пустой отзыв."
                # )
                i += 1
                continue
            ai_feedback = await ya_ai.create_feetbacks(text_feedback, company, user_name)
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
            next_message_id = (message.message_id + i + 1)
            answer_message = Answer(
                company,
                product_name,
                set_product_valuation,
                created_date[:10],
                text_feedback,
                ai_answer,
                int(next_message_id),
                feedback_id,
                user_name
            )
            my_state[next_message_id] = answer_message
            send_message = await answer_message.create_message_not_signature()
            markup = await create_markup(next_message_id)
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
    markup = quick_markup(
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
    global state
    global my_signature
    if state == "token":
        try:
            await db.set_token_query(uid=message.from_user.id, token=message.text)
            await bot.send_message(message.chat.id, "Токен был добавлен.", reply_markup=top_menu)
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
        new_msg = await msg.create_message_not_signature()
        markup = await create_markup(msg.message_id)
        await bot.send_message(
            message.chat.id, new_msg, parse_mode="Markdown", reply_markup=markup
        )
        await bot.delete_state(message.from_user.id)
    elif state == "signature":
        my_signature = message.text
        await bot.send_message(
            message.chat.id, 'Вы изменили подпись!', reply_markup=top_menu
        )


@bot.callback_query_handler(func=lambda callback: callback.data == 'signature_answer')
async def callback_edit(callback: CallbackQuery) -> None:
    global state
    state = 'signature'
    await bot.send_message(
        callback.message.chat.id,
        "Введите Вашу подпись для отзывов в следующем сообщени"
    )
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: callback.data == 'get_feedbacks')
async def callback_edit(callback: CallbackQuery) -> None:
    user_data = await db.get_user_data(callback.from_user.id)
    wb_token = user_data[3]
    feedbacks_count = user_data[4]
    global user_parser
    user_parser = WBParser(wb_token)
    feedbacks = await user_parser.get_feedback()
    if feedbacks.get('code') == 401:
        await bot.send_message(
            callback.message.chat.id,
            "Ваш токен не действителен, попробуйте заменить токен!",
            reply_markup=start_menu
        )
    unanswered_count = len(feedbacks.get("data").get("feedbacks"))
    if feedbacks_count == 0:
        await bot.send_message(
            callback.message.chat.id,
            f"Вам необходимо произвести оплату, "
            f"баланс ваших отзывов равен: {feedbacks_count}",
        )
    else:
        if unanswered_count > feedbacks_count:
            await bot.send_message(
                callback.message.chat.id,
                "У Вас недостаточно отзывов чтобы ответить "
                "на все сообщения, пожалуйста произведите оплату. "
                "Для этого введите команду /tariffs",
            )
            unanswered_count = feedbacks_count
        if unanswered_count == 0:
            await bot.send_message(
                callback.message.chat.id,
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
            user_name = feedbacks.get("data").get("feedbacks")[i].get("userName")
            if text_feedback == "":
                # await bot.send_message(
                #     callback.message.chat.id, "Невозможно ответить на пустой отзыв."
                # )
                i += 1
                continue
            ai_feedback = await ya_ai.create_feetbacks(text_feedback, company, user_name)
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
            next_message_id = (callback.message.message_id + i + 1)
            answer_message = Answer(
                company,
                product_name,
                set_product_valuation,
                created_date[:10],
                text_feedback,
                ai_answer,
                int(next_message_id),
                feedback_id,
                user_name
            )
            my_state[next_message_id] = answer_message
            send_message = await answer_message.create_message_not_signature()
            markup = await create_markup(next_message_id)
            await bot.send_message(
                callback.message.chat.id,
                send_message,
                reply_markup=markup,
                parse_mode="Markdown",
            )
            i += 1
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: callback.data == 'add_token')
async def callback_edit(callback: CallbackQuery) -> None:
    global state
    add_instruction = (
        "*1.* Перейдите в личный кабинет Wildberries (данное "
        "действие необходимо выполнить владельцу кабинета) "
        "[Профиль -> Настройки - Доступ к API](https://seller.wildberries.ru/about-portal/ru/)\n"
        "*2.* Введите имя токена, например WBBotToken\n"
        "*3.* Выберите 'Контент' и 'Вопросы и отзывы'\n"
        "*4.* Нажмите 'Создать токен'\n"
        "*Следующим сообщением отправьте токен!!!*"
    )
    state = 'token'
    await bot.send_message(callback.message.chat.id, text=add_instruction, parse_mode="Markdown")
    await bot.answer_callback_query(callback.id)

@bot.callback_query_handler(func=lambda callback: clb_edit.filter().check(callback))
async def callback_edit(callback: CallbackQuery):
    global state
    cl_data = clb_edit.parse(callback_data=callback.data)
    mid = cl_data.get('mid')
    state = "edit"
    # await bot.set_state(callback.from_user.id, "edit", callback.message.chat.id)
    edit_msg["edit"] = my_state.pop(int(mid), None)
    await bot.send_message(
        callback.message.chat.id,
        "Отправьте отредактированный отзыв в следующем сообщении.",
    )
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: clb_regenerate.filter().check(callback))
async def callback_regenerate(callback: CallbackQuery):
    cl_data = clb_regenerate.parse(callback_data=callback.data)
    mid = cl_data.get('mid')
    fedback_msg = my_state.pop(int(mid), None)
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    ai_feedback = await ya_ai.create_feetbacks(
        fedback_msg.text_feedback, fedback_msg.company, fedback_msg.user_name
    )
    ai_answer = (
        ai_feedback.get("result").get("alternatives")[
            0].get("message").get("text")
    )
    fedback_msg.ai_answer = ai_answer
    fedback_msg.message_id = callback.message.message_id + 1
    my_state[callback.message.message_id + 1] = fedback_msg
    send_msg = await fedback_msg.create_message_not_signature()
    markup = await create_markup(callback.message.message_id+1)
    await bot.send_message(
        callback.message.chat.id,
        send_msg,
        reply_markup=markup,
        parse_mode="Markdown",
    )
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: clb_not_answer.filter().check(callback))
async def callback_not_answer(callback: CallbackQuery):
    cl_data = clb_not_answer.parse(callback_data=callback.data)
    mid = cl_data.get('mid')
    del my_state[int(mid)]
    await bot.delete_message(callback.message.chat.id, int(mid))
    await bot.answer_callback_query(int(callback.id))


@bot.callback_query_handler(func=lambda callback: clb_add_signature.filter().check(callback))
async def callback_add_signature(callback: CallbackQuery):
    global my_signature
    cl_data = clb_add_signature.parse(callback_data=callback.data)
    mid = cl_data.get('mid')
    fedback_msg = my_state.pop(int(mid), None)
    ai_answer = f"{fedback_msg.ai_answer} {my_signature}"
    fedback_msg.ai_answer = ai_answer
    fedback_msg.message_id = callback.message.message_id + 1
    my_state[callback.message.message_id + 1] = fedback_msg
    send_msg = await fedback_msg.create_message_with_signature()
    markup = await create_markup(callback.message.message_id+1)
    await bot.send_message(
        callback.message.chat.id,
        send_msg,
        reply_markup=markup,
        parse_mode="Markdown",
    )
    await bot.delete_message(callback.message.chat.id, int(fedback_msg.message_id))
    await bot.answer_callback_query(callback.id)

@bot.callback_query_handler(func=lambda callback: clb_publish.filter().check(callback))
async def callback_pulish(callback: CallbackQuery):
    global user_parser
    uid = int(callback.from_user.id)
    cl_data = clb_add_signature.parse(callback_data=callback.data)
    mid = cl_data.get('mid')
    fedback_msg = my_state.pop(int(mid), None)
    await user_parser.feedback_answer(
        fedback_msg.feedback_id, fedback_msg.ai_answer
    )
    await db.minus_count_query(uid)
    await bot.delete_message(callback.message.chat.id, int(mid))
    await bot.answer_callback_query(int(callback.id))


@bot.callback_query_handler(func=lambda callback: callback.data == "bot_start")
async def bot_start(callback: CallbackQuery) -> None:
    await bot.send_message(callback.message.chat.id, callback.message.text, reply_markup=start_menu)
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: callback.data == "tariffs")
async def bot_start(callback: CallbackQuery) -> None:
    answer_message = (
        "Доступные тарифы:\n\n"
        "Стартовый - 100 ответов. Цена 392 руб. Цена за 1 отзыв 3.92 руб.\n"
        "Базовый - 500 ответов. Цена 1592 руб. Цена за 1 отзыв 3.18 руб.\n"
        "Расширенный - 1000 ответов. Цена 2872 руб. Цена за 1 отзыв 2.87 руб.\n"
        "Премиум - 2000 ответов. Цена 5592 руб. Цена за 1 отзыв 2.79 руб.\n"
        "ТОП - 10000 ответов. Цена 23992 руб. Цена за 1 отзыв 2.39 руб.\n"
        "Выберите подходящий тариф."
    )
    await bot.send_message(callback.message.chat.id, answer_message, reply_markup=tariffs)
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: callback.data == "balance")
async def bot_start(callback: CallbackQuery) -> None:
    feedbacks_count = await db.get_count_query(callback.message.from_user.id)
    await bot.send_message(
        callback.message.chat.id, f"У Вас осталось {feedbacks_count} отзывов.", reply_markup=top_menu
    )
    await bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda callback: True)
async def callbacks(callback: CallbackQuery) -> None:
    uid = int(callback.from_user.id)
    if callback.data == "main_menu":
        add_user = await db.add_user_query(uid)
        if add_user:
            answer_message = (
                f"Поздравляем {callback.from_user.first_name}, Вам доступно 60 бесплатных отзывов!"
            )
            await bot.send_message(callback.message.chat.id, answer_message)
        else:
            count_query = await db.get_count_query(uid)
            answer_message = (
                f"{callback.from_user.first_name} Ваш аккаунт был добавлен раннее, "
                f"у Вас осталось {count_query} ответов."
            )
            await bot.send_message(callback.message.chat.id, answer_message, reply_markup=top_menu)
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
    await bot.answer_callback_query(callback.id)


if __name__ == "__main__":
    asyncio.run(bot.polling(non_stop=True))
