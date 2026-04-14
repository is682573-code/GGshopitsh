import os
import hashlib
import hmac
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

YOOMONEY_SECRET   = os.getenv("YOOMONEY_SECRET", "")
YOOMONEY_WALLET   = os.getenv("YOOMONEY_WALLET", "")  # Номер кошелька

# Цены
PRICE_BASE        = 499
PRICE_ULTIMATE    = 699
PRICE_ULTIMATE_DISCOUNT = 499  # со скидкой 200₽ если есть Base

# Ссылки на скрипты (приватный GitHub — raw ссылки с токеном)
SCRIPT_URLS = {
    "base":     os.getenv("SCRIPT_URL_BASE", "https://github.com/YOUR/REPO/raw/main/base.lua"),
    "ultimate": os.getenv("SCRIPT_URL_ULTIMATE", "https://github.com/YOUR/REPO/raw/main/ultimate.lua"),
}


class PaymentHandler:
    def __init__(self, bot, db, admin_id: int):
        self.bot = bot
        self.db = db
        self.admin_id = admin_id
        self.on_payment_success = None  # будет подключён из bot.py
        self._pending: dict[str, dict] = {}  # label -> {user_id, plan, amount}

    def get_price(self, plan: str, has_base: bool = False) -> int:
        if plan == "base":
            return PRICE_BASE
        if plan == "ultimate":
            return PRICE_ULTIMATE_DISCOUNT if has_base else PRICE_ULTIMATE
        return 0

    def get_script_url(self, plan: str) -> str:
        return SCRIPT_URLS.get(plan, "")

    def create_payment_link(self, user_id: int, plan: str, price: int) -> str:
        """Генерирует ссылку на оплату ЮMoney с уникальным label."""
        label = f"{user_id}_{plan}_{price}"
        self._pending[label] = {"user_id": user_id, "plan": plan, "amount": price}

        # Стандартная ссылка оплаты ЮMoney (форма)
        url = (
            f"https://yoomoney.ru/quickpay/confirm?"
            f"receiver={YOOMONEY_WALLET}"
            f"&quickpay-form=donate"
            f"&targets=Script+{plan.upper()}"
            f"&sum={price}"
            f"&label={label}"
            f"&successURL=https://t.me/"
        )
        return url

    def _check_signature(self, data: dict) -> bool:
        """Проверка подписи входящего уведомления от ЮMoney."""
        params = [
            data.get("notification_type", ""),
            data.get("operation_id", ""),
            data.get("amount", ""),
            data.get("currency", ""),
            data.get("datetime", ""),
            data.get("sender", ""),
            data.get("codepro", ""),
            YOOMONEY_SECRET,
            data.get("label", ""),
        ]
        check_str = "&".join(params)
        expected = hashlib.sha1(check_str.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected, data.get("sha1_hash", ""))

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Обработчик POST-запросов от ЮMoney."""
        try:
            data = dict(await request.post())
            logger.info(f"YooMoney webhook: {data}")

            if not self._check_signature(data):
                logger.warning("Invalid YooMoney signature!")
                return web.Response(status=400, text="Bad signature")

            label = data.get("label", "")
            if not label or label not in self._pending:
                logger.warning(f"Unknown label: {label}")
                return web.Response(status=200, text="OK")

            pending = self._pending.pop(label)
            user_id    = pending["user_id"]
            plan       = pending["plan"]
            amount     = int(float(data.get("amount", 0)))
            payer_name = data.get("sender", "Неизвестно")
            # Определяем метод оплаты из данных уведомления
            pay_type   = data.get("notification_type", "")
            pay_method = "ЮMoney-кошелёк" if pay_type == "p2p-incoming" else "Карта"

            # Записываем покупку
            self.db.add_purchase(user_id, plan, amount, pay_method, payer_name)

            # Уведомляем пользователя и администратора
            if self.on_payment_success:
                await self.on_payment_success(user_id, plan, payer_name, pay_method, amount)

            return web.Response(status=200, text="OK")

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(status=500, text="Error")


def setup_webhook_server(payment_handler: PaymentHandler, port: int = 8080):
    """Запускает aiohttp-сервер для приёма вебхуков."""
    app = web.Application()
    app.router.add_post("/webhook/yoomoney", payment_handler.handle_webhook)
    return app, port
