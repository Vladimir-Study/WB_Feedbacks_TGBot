from telebot.util import quick_markup
from telebot.callback_data import CallbackData
from telebot.types import InlineKeyboardMarkup


set_push_time = CallbackData("mid", prefix="set_push_time")
signature_answer = CallbackData("mid", prefix="signature_answer")


main_menu = quick_markup(
    {
        "ℹ️Главное меню": {"callback_data": "main_menu"},
    }, row_width=1
)


top_menu = quick_markup(
    {
        "▶️Начать пользоваться ботом": {"callback_data": "bot_start"},
        # "🕔Настроить время отправки уведомлений": {"callback_data": "set_push_time"},
        "🖋Подпись к ответу": {"callback_data": "add_signature"},
        "💵Баланс": {"callback_data": "balance"},
    }, row_width=1
)


start_menu = quick_markup(
    {
        "📊Тарифы": {"callback_data": "tariffs"},
        "📝Добавить Wildberries токен": {"callback_data": "add_token"},
        "🗣Получить отзывы": {"callback_data": "get_feedbacks"},
        "🔙Назад": {"callback_data": "main_menu"},
    }, row_width=1
)


tariffs = quick_markup(
    {
        "100": {"callback_data": "pay_100"},
        "500": {"callback_data": "pay_500"},
        "1000": {"callback_data": "pay_1000"},
        "2000": {"callback_data": "pay_2000"},
        "10000": {"callback_data": "pay_10000"},
        "🔙Назад": {"callback_data": "bot_start"},
    },
    row_width=2,
)
