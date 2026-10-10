import os
import asyncio
import logging

from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8080))
URL = os.environ["RENDER_EXTERNAL_URL"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is live.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)


async def on_startup(app):
    await app["application"].bot.set_webhook(url=f"{URL}/telegram")
    logger.info(f"Webhook set to {URL}/telegram")


async def telegram_handler(request: web.Request):
    update = Update.de_json(await request.json(), app["application"].bot)
    await app["application"].process_update(update)
    return web.Response(status=200)


async def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    async with application:
        await application.start()

        aiohttp_app = web.Application()
        aiohttp_app["application"] = application
        aiohttp_app.router.add_post("/telegram", telegram_handler)
        aiohttp_app.router.add_get("/healthcheck", lambda r: web.Response(text="OK"))
        aiohttp_app.on_startup.append(on_startup)

        runner = web.AppRunner(aiohttp_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"Serving on port {PORT}")
        await asyncio.Event().wait()  # run forever


if __name__ == "__main__":
    asyncio.run(main())   
