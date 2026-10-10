import os
import asyncio
import logging
import imaplib
from email.utils import parseaddr

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8080))
URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# Conversation states
ASK_EMAIL, ASK_PASSWORD = range(2)


# --- Gmail verification ---
def verify_gmail(email: str, password: str) -> bool:
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email, password)
        mail.logout()
        return True
    except imaplib.IMAP4.error:
        return False
    except Exception:
        return False


# --- Conversation handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 Enter your **Gmail ID** (e.g. yourname@gmail.com)\n\n"
        "⚠️ You must use an **App Password**, not your regular password.\n"
        "Generate one at: https://myaccount.google.com/apppasswords",
        parse_mode="Markdown",
    )
    return ASK_EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text("❌ Invalid email. Try again.")
        return ASK_EMAIL

    context.user_data["email"] = email
    await update.message.reply_text(
        "✅ Now enter your **App Password** (16 characters, e.g. abcd efgh ijkl mnop)"
    )
    return ASK_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    email = context.user_data.get("email", "")

    # Hide the password from chat
    await update.message.reply_text("⏳ Verifying...")

    # Run IMAP in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, verify_gmail, email, password)

    if success:
        # Show the IG Service button
        keyboard = [
            [InlineKeyboardButton("📸 IG Service", callback_data="ig_service")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Login successful! Welcome.",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            "❌ Invalid credentials.\n"
            "Make sure you're using an **App Password**, not your regular password.\n\n"
            "Use /start to try again."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Use /start to begin again.")
    return ConversationHandler.END


# --- IG Service button handler ---
async def ig_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Replace this with whatever you want to do:
    # - Send to a channel
    # - Show a menu of IG services
    # - Redirect to a payment link
    await query.edit_message_text(
        "📸 **IG Services**\n\n"
        "• Followers\n"
        "• Likes\n"
        "• Views\n\n"
        "Select a service or contact support.",
        parse_mode="Markdown",
    )


# --- Webhook handler (for Render) ---
async def telegram_webhook(request):
    from aiohttp import web
    update = Update.de_json(await request.json(), request.app["application"].bot)
    await request.app["application"].process_update(update)
    return web.Response(status=200)


# --- Main ---
async def main():
    from aiohttp import web

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # Build conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(ig_service))

    async with application:
        await application.start()

        if URL:
            await application.bot.set_webhook(url=f"{URL}/telegram")
            logger.info(f"Webhook set to {URL}/telegram")

        aiohttp_app = web.Application()
        aiohttp_app["application"] = application
        aiohttp_app.router.add_post("/telegram", telegram_webhook)
        aiohttp_app.router.add_get("/healthcheck", lambda r: web.Response(text="OK"))

        runner = web.AppRunner(aiohttp_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"Serving on port {PORT}")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())   
