import os
import asyncio
import datetime
import dateparser
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI
from scheduler import scheduler
from dateparser.search import search_dates

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

# Inicializaciones
app = FastAPI()
application = Application.builder().token(TELEGRAM_TOKEN).build()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Comando /start
async def start(update: Update, context):
    await update.message.reply_text("Hola, soy Cabo, tu bot con Webhook activo 🐶🚀")

# Comando /macrohoy
async def macrohoy(update: Update, context):
    url = f"https://api.marketaux.com/v1/economic_events?filter=country:us&date=TODAY&api_token={MARKETAUX_API_KEY}"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            data = r.json()

        events = data.get("data", [])
        if not events:
            await update.message.reply_text("📭 Hoy no hay eventos económicos relevantes.")
            return

        resumen = "📅 *Eventos macroeconómicos de hoy:*\n"
        for e in events:
            hora = e.get("date", "")[-8:-3]
            importancia = e.get("importance", "unknown").capitalize()
            resumen += f"🕒 {hora} — {e['title']} ({importancia})\n"

        await update.message.reply_text(resumen, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Error consultando eventos macro de hoy.")

# Comando /macromanana
async def macromanana(update: Update, context):
    url = f"https://api.marketaux.com/v1/economic_events?filter=country:us&date=TOMORROW&api_token={MARKETAUX_API_KEY}"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            data = r.json()

        events = data.get("data", [])
        if not events:
            await update.message.reply_text("📭 Mañana no hay eventos económicos relevantes.")
            return

        resumen = "🔮 *Eventos macroeconómicos de mañana:*\n"
        for e in events:
            hora = e.get("date", "")[-8:-3]
            importancia = e.get("importance", "unknown").capitalize()
            resumen += f"🕒 {hora} — {e['title']} ({importancia})\n"

        await update.message.reply_text(resumen, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Error consultando eventos de mañana.")

# Comando /macrosemana
async def macrosemana(update: Update, context):
    url = f"https://api.marketaux.com/v1/economic_events?filter=country:us&date_from=TODAY&date_to=+7DAYS&api_token={MARKETAUX_API_KEY}"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            data = r.json()

        events = data.get("data", [])
        if not events:
            await update.message.reply_text("📭 No hay eventos macroeconómicos esta semana.")
            return

        resumen = "📅 *Eventos macroeconómicos próximos:*\n"
        for e in events:
            fecha = e.get("date", "")[:16].replace("T", " ")
            importancia = e.get("importance", "unknown").capitalize()
            resumen += f"📆 {fecha} — {e['title']} ({importancia})\n"

        await update.message.reply_text(resumen, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Error consultando eventos macroeconómicos.")

# Manejo de mensajes (recordatorios o IA)
async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id

    fechas_encontradas = search_dates(user_message, languages=["es"])
    if fechas_encontradas:
        texto_fecha, fecha = fechas_encontradas[0]
        mensaje = user_message.replace(texto_fecha, "").strip()
        if not mensaje:
            mensaje = "¡Esto es tu recordatorio!"

        # Validar que sea en el futuro
        if fecha < datetime.datetime.now():
            await update.message.reply_text("⚠️ Esa hora ya pasó. Intenta con una futura.")
            return

        scheduler.add_job(
            context.bot.send_message,
            "date",
            run_date=fecha,
            args=[chat_id, f"📌 Recordatorio: {mensaje}"]
        )

        await update.message.reply_text(f"✅ Te lo recordaré el {fecha.strftime('%A %d a las %I:%M %p')}")
        return

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
    except Exception:
        await update.message.reply_text("⚠️ Hubo un error procesando tu mensaje.")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("macrohoy", macrohoy))
application.add_handler(CommandHandler("macromanana", macromanana))
application.add_handler(CommandHandler("macrosemana", macrosemana))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Iniciar el bot
async def setup_bot():
    await application.initialize()
    await application.start()
    print("🚀 Cabo está listo con Webhook, recordatorios y macroeconomía.")

asyncio.get_event_loop().create_task(setup_bot())

# Webhook
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
