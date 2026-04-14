import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database
from payments import PaymentHandler
from texts import get_text
from keyboards import (
    main_menu_kb, buy_menu_kb, faq_kb,
    language_kb, back_kb, plan_confirm_kb
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
payment_handler = PaymentHandler(bot, db, ADMIN_ID)


# ─── helpers ───────────────────────────────────────────────
async def edit_or_send(message: Message | CallbackQuery, text: str, reply_markup=None):
    """Delete old message and send new one (animation effect)."""
    if isinstance(message, CallbackQuery):
        try:
            await message.message.delete()
        except Exception:
            pass
        await bot.send_message(
            message.from_user.id,
            text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        await message.answer()
    else:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


def get_lang(user_id: int) -> str:
    return db.get_language(user_id) or "ru"


# ─── /start ────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    db.ensure_user(user_id, message.from_user.username)

    text = get_text("welcome", lang)
    await message.answer(text, reply_markup=main_menu_kb(lang), parse_mode="HTML")


# ─── MAIN MENU ─────────────────────────────────────────────
@dp.callback_query(F.data == "menu_main")
async def cb_main_menu(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await edit_or_send(call, get_text("welcome", lang), main_menu_kb(lang))


@dp.callback_query(F.data == "menu_buy")
async def cb_buy(call: CallbackQuery):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    has_base = db.has_plan(user_id, "base")
    has_ultimate = db.has_plan(user_id, "ultimate")

    if has_ultimate:
        await edit_or_send(call, get_text("already_ultimate", lang), back_kb(lang))
        return

    text = get_text("buy_menu", lang, has_base=has_base)
    await edit_or_send(call, text, buy_menu_kb(lang, has_base=has_base))


@dp.callback_query(F.data == "menu_faq")
async def cb_faq(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await edit_or_send(call, get_text("faq", lang), faq_kb(lang))


@dp.callback_query(F.data == "menu_support")
async def cb_support(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await edit_or_send(call, get_text("support", lang), back_kb(lang))


@dp.callback_query(F.data == "menu_lang")
async def cb_lang(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await edit_or_send(call, get_text("choose_lang", lang), language_kb())


@dp.callback_query(F.data.in_({"lang_ru", "lang_en"}))
async def cb_set_lang(call: CallbackQuery):
    new_lang = "ru" if call.data == "lang_ru" else "en"
    db.set_language(call.from_user.id, new_lang)
    await edit_or_send(call, get_text("welcome", new_lang), main_menu_kb(new_lang))


# ─── BUY FLOW ──────────────────────────────────────────────
@dp.callback_query(F.data.in_({"buy_base", "buy_ultimate"}))
async def cb_buy_plan(call: CallbackQuery):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    plan = "base" if call.data == "buy_base" else "ultimate"

    if db.has_plan(user_id, plan):
        await edit_or_send(call, get_text("already_bought", lang, plan=plan), back_kb(lang))
        return

    has_base = db.has_plan(user_id, "base")
    price = payment_handler.get_price(plan, has_base)
    text = get_text("confirm_purchase", lang, plan=plan, price=price)
    await edit_or_send(call, text, plan_confirm_kb(lang, plan, price))


@dp.callback_query(F.data.startswith("pay_"))
async def cb_pay(call: CallbackQuery):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    _, plan, price_str = call.data.split("_", 2)
    price = int(price_str)

    pay_url = payment_handler.create_payment_link(user_id, plan, price)
    text = get_text("pay_instructions", lang, plan=plan, price=price, url=pay_url)
    await edit_or_send(call, text, back_kb(lang))


# ─── WEBHOOK from YooMoney (called by payments.py) ─────────
async def on_payment_success(user_id: int, plan: str, payer_name: str, pay_method: str, amount: int):
    lang = get_lang(user_id)
    db.add_purchase(user_id, plan)

    script_url = payment_handler.get_script_url(plan)
    text = get_text("purchase_success", lang, plan=plan, url=script_url)
    await bot.send_message(user_id, text, parse_mode="HTML")

    # Admin report
    report = (
        f"💰 <b>Новая покупка!</b>\n"
        f"👤 TG ID: <code>{user_id}</code>\n"
        f"📦 План: <b>{plan.upper()}</b>\n"
        f"💳 Способ: {pay_method}\n"
        f"👛 Имя: {payer_name}\n"
        f"💵 Сумма: {amount}₽"
    )
    await bot.send_message(ADMIN_ID, report, parse_mode="HTML")

payment_handler.on_payment_success = on_payment_success


# ─── MAIN ──────────────────────────────────────────────────
async def main():
    db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
