import os
import asyncio
import dateparser
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI
from scheduler import scheduler

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

# Mensajes normales + alertas
async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id

    # Detectar si es una solicitud de recordatorio
    if "recuérdame" in user_message.lower() or "recuerda" in user_message.lower():
        fecha = dateparser.parse(user_message, languages=["es"])
        if fecha is None:
            await update.message.reply_text("No entendí bien cuándo debo recordártelo. Intenta con: 'el jueves a las 5pm recuérdame comprar té'")
            return

        # Extraer mensaje después de "recuérdame"
        partes = user_message.lower().split("recuérdame")
        mensaje = partes[1].strip() if len(partes) > 1 else "¡Esto es tu recordatorio!"

        scheduler.add_job(
            context.bot.send_message,
            "date",
            run_date=fecha,
            args=[chat_id, f"📌 Recordatorio: {mensaje}"]
        )

        await update.message.reply_text(f"✅ Te lo recordaré el {fecha.strftime('%A %d a las %I:%M %p')}")
    else:
        # Procesamiento normal con OpenAI
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

# Inicialización para webhook
async def setup_bot():
    await application.initialize()
    await application.start()
    print("🚀 Cabo está listo con Webhook y recordatorios.")

asyncio.get_event_loop().create_task(setup_bot())

# Webhook endpoint
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

