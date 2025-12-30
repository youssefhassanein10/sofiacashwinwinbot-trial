from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import BOT_TOKEN, ADMINS, SUPPORT_ADMIN_ID


WAIT_DEPOSIT = set()
WAIT_SUPPORT = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💰 Пополнить", "💸 Вывести"],
        ["📞 Поддержка"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Выберите действие:",
        reply_markup=markup
    )


# ───── ПОПОЛНЕНИЕ ─────
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    WAIT_DEPOSIT.add(update.effective_user.id)
    await update.message.reply_text("💰 Введите сумму пополнения (RUB):")


async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in WAIT_DEPOSIT:
        return

    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Введите число.")
        return

    WAIT_DEPOSIT.remove(user_id)

    text = (
        "💰 *Новая заявка на пополнение*\n\n"
        f"Telegram ID: `{user_id}`\n"
        f"Username: @{update.effective_user.username}\n"
        f"Сумма: {amount} RUB"
    )

    for admin in ADMINS:
        await context.bot.send_message(
            chat_id=admin,
            text=text,
            parse_mode="Markdown"
        )

    await update.message.reply_text(
        "⏳ Ваша заявка принята.\n"
        "Ожидайте реквизиты."
    )


# ───── ВЫВОД ─────
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💸 Вывод средств временно недоступен.\n"
        "Обратитесь в поддержку."
    )


# ───── ПОДДЕРЖКА ─────
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    WAIT_SUPPORT.add(update.effective_user.id)
    await update.message.reply_text("📞 Напишите сообщение для поддержки:")


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in WAIT_SUPPORT:
        return

    WAIT_SUPPORT.remove(user_id)

    text = (
        "📩 *Сообщение в поддержку*\n\n"
        f"Telegram ID: `{user_id}`\n"
        f"Username: @{update.effective_user.username}\n\n"
        f"{update.message.text}"
    )

    await context.bot.send_message(
        chat_id=SUPPORT_ADMIN_ID,
        text=text,
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ Сообщение отправлено.")


# ───── ОТВЕТ АДМИНА ─────
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    if not update.message.reply_to_message:
        return

    lines = update.message.reply_to_message.text.split("\n")
    user_id = None

    for line in lines:
        if "Telegram ID:" in line:
            user_id = int(line.split("`")[1])

    if user_id:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💬 Ответ поддержки:\n\n{update.message.text}"
        )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Text("💰 Пополнить"), deposit))
    app.add_handler(MessageHandler(filters.Text("💸 Вывести"), withdraw))
    app.add_handler(MessageHandler(filters.Text("📞 Поддержка"), support))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, admin_reply))

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
