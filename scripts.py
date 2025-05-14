import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI
from scheduler import scheduler
from dateparser.search import search_dates

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

# Manejo de mensajes
async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id

    # Buscar una fecha dentro del mensaje
    fechas_encontradas = search_dates(user_message, languages=["es"])
    if fechas_encontradas:
        texto_fecha, fecha = fechas_encontradas[0]

        # Extraer el mensaje de recordatorio (quitando la parte de la fecha)
        mensaje = user_message.replace(texto_fecha, "").strip()
        if not mensaje:
            mensaje = "¡Esto es tu recordatorio!"

        # Programar el recordatorio
        scheduler.add_job(
            context.bot.send_message,
            "date",
            run_date=fecha,
            args=[chat_id, f"📌 Recordatorio: {mensaje}"]
        )

        await update.message.reply_text(f"✅ Te lo recordaré el {fecha.strftime('%A %d a las %I:%M %p')}")
        return

    # Si no hay fecha, usar OpenAI para responder
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

# Inicialización para Webhook
async def setup_bot():
    await application.initialize()
    await application.start()
    print("🚀 Cabo está listo con Webhook y recordatorios inteligentes.")

asyncio.get_event_loop().create_task(setup_bot())

# Webhook endpoint
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

