# main.py
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

# --- Telegram handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your bot.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# --- Flask (keeps Render alive + receives webhooks) ---
@app.route("/")
def health():
    return "Bot is alive!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), None)
    # Process asynchronously
    asyncio.run(handle_update(update))
    return "ok"

async def handle_update(update: Update):
    # Simple dispatch (or use a proper application instance)
    if update.message and update.message.text == "/start":
        await update.message.reply_text("Hello! I am your bot.")
    elif update.message and update.message.text:
        await update.message.reply_text(update.message.text)

# --- Main ---
def main():
    # Set webhook with Telegram
    import requests
    url = os.environ["RENDER_EXTERNAL_URL"]
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={url}/webhook")
    print(f"Webhook set to: {url}/webhook")

    # Start Flask
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()   

