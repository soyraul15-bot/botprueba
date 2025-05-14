import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI

# Claves desde entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializaciones
app = FastAPI()
application = Application.builder().token(TELEGRAM_TOKEN).build()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Comando /start
async def start(update: Update, context):
    await update.message.reply_text("Hola, soy Cabo, tu bot con Webhook activo 🐶🚀")

# Respuesta automática con OpenAI
async def handle_message(update: Update, context):
    user_message = update.message.text

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un bot amigable llamado Cabo."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("Hubo un error procesando tu mensaje.")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔧 Inicializar la aplicación (necesario para Webhook)
asyncio.create_task(application.initialize())

# Webhook endpoint
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

