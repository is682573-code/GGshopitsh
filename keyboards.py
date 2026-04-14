from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BTN = {
    "buy":      {"ru": "🛒 Купить",         "en": "🛒 Buy"},
    "faq":      {"ru": "❓ FAQ",             "en": "❓ FAQ"},
    "support":  {"ru": "🛠 Поддержка",       "en": "🛠 Support"},
    "lang":     {"ru": "🌐 Язык / Language", "en": "🌐 Язык / Language"},
    "back":     {"ru": "◀ Назад",            "en": "◀ Back"},
    "base":     {"ru": "📦 Base — 499₽",     "en": "📦 Base — 499₽"},
    "ultimate": {"ru": "⭐ Ultimate",         "en": "⭐ Ultimate"},
    "confirm":  {"ru": "✅ Перейти к оплате", "en": "✅ Proceed to pay"},
}


def t(key: str, lang: str) -> str:
    return BTN[key].get(lang, BTN[key]["ru"])


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("buy", lang),     callback_data="menu_buy")],
        [InlineKeyboardButton(text=t("faq", lang),     callback_data="menu_faq")],
        [InlineKeyboardButton(text=t("support", lang), callback_data="menu_support")],
        [InlineKeyboardButton(text=t("lang", lang),    callback_data="menu_lang")],
    ])


def buy_menu_kb(lang: str, has_base: bool = False) -> InlineKeyboardMarkup:
    from payments import PRICE_ULTIMATE, PRICE_ULTIMATE_DISCOUNT
    ultimate_price = PRICE_ULTIMATE_DISCOUNT if has_base else PRICE_ULTIMATE
    ultimate_label = f"⭐ Ultimate — {ultimate_price}₽"
    if has_base:
        ultimate_label += " 🎁"

    rows = []
    if not has_base:
        rows.append([InlineKeyboardButton(text=t("base", lang), callback_data="buy_base")])
    rows.append([InlineKeyboardButton(text=ultimate_label, callback_data="buy_ultimate")])
    rows.append([InlineKeyboardButton(text=t("back", lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plan_confirm_kb(lang: str, plan: str, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("confirm", lang),
            callback_data=f"pay_{plan}_{price}"
        )],
        [InlineKeyboardButton(text=t("back", lang), callback_data="menu_buy")],
    ])


def faq_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("back", lang), callback_data="menu_main")],
    ])


def back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("back", lang), callback_data="menu_main")],
    ])


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ],
    ])
