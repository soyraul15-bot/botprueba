import os
import schedule
import time
from imapclient import IMAPClient
import pyzmail
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables del archivo .env
load_dotenv()

# Inicializar cliente OpenAI
client = OpenAI()

# API Keys y configuraciones
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("CHAT_ID")
email_user = os.getenv("EMAIL_ADDRESS")
email_pass = os.getenv("EMAIL_PASSWORD")
imap_server = 'imap.gmail.com'

# Iniciar bot de Telegram
updater = Updater(bot_token, use_context=True)
dispatcher = updater.dispatcher

def start(update, context):
    update.message.reply_text('Hola, soy tu Agente IA 🤖. Escribe tu automatización (por ejemplo: "Recuérdame cada viernes enviar email a Batalora").')

dispatcher.add_handler(CommandHandler('start', start))

def recibir_instruccion(update, context):
    instruccion = update.message.text
    respuesta = interpretar_instruccion(instruccion)
    update.message.reply_text(respuesta)

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, recibir_instruccion))

def interpretar_instruccion(texto):
    # Ver si el usuario quiere una tarea en minutos (ej. dentro de 2 minutos)
    if "dentro de" in texto and "minuto" in texto:
        import re
        match = re.search(r'dentro de (\d+) minuto', texto)
        if match:
            minutos = int(match.group(1))
            mensaje = texto.split("recordándome que")[-1].strip().capitalize()
            schedule.every(minutos).minutes.do(enviar_telegram, f"⏰ Recordatorio: {mensaje}")
            return f"✅ Recordatorio programado para dentro de {minutos} minuto(s): '{mensaje}'."

    # Prompt para instrucciones normales
    prompt = f"""Interpreta esta instrucción del usuario y responde con una línea en este formato:

EMAIL, palabra_clave
O
RECORDATORIO, dia_semana, hora, mensaje

Ejemplos:
EMAIL, universidad
RECORDATORIO, viernes, 09:00, enviar email a Batalora

Instrucción: '{texto}'"""

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que interpreta tareas y devuelve instrucciones simples para un bot de automatización."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=50
    )

    texto_respuesta = respuesta.choices[0].message.content.strip()
    partes = texto_respuesta.split(', ')

    if partes[0] == "EMAIL":
        if len(partes) < 2:
            return "⚠️ Instrucción incompleta para correo."
        palabra_clave = partes[1]
        schedule.every(1).minutes.do(verificar_email, palabra_clave)
        return f"📧 Automatización creada: correos con '{palabra_clave}' serán reenviados a Telegram."

    elif partes[0] == "RECORDATORIO":
        if len(partes) < 4:
            return "⚠️ La instrucción fue muy ambigua o incompleta. Intenta algo como: 'Recuérdame cada viernes a las 9:00 enviar mensaje a Batalora'."

        dia, hora, mensaje = partes[1], partes[2], partes[3]

        dias_validos = {
            "lunes": schedule.every().monday,
            "martes": schedule.every().tuesday,
            "miércoles": schedule.every().wednesday,
            "jueves": schedule.every().thursday,
            "viernes": schedule.every().friday,
            "sábado": schedule.every().saturday,
            "domingo": schedule.every().sunday,
        }

        if dia.lower() in dias_validos:
            dias_validos[dia.lower()].at(hora).do(enviar_telegram, mensaje)
            return f"⏰ Recordatorio creado: '{mensaje}' cada {dia} a las {hora}."
        else:
            return "⚠️ Día no válido. Usa días como: lunes, martes, viernes, etc."

    else:
        return "⚠️ No entendí la instrucción. Intenta nuevamente con más claridad."

def enviar_telegram(mensaje):
    updater.bot.send_message(chat_id=chat_id, text=mensaje)

def verificar_email(palabra_clave):
    try:
        with IMAPClient(imap_server) as client:
            client.login(email_user, email_pass)
            client.select_folder('INBOX')

            UIDs = client.search(['UNSEEN'])
            for uid in UIDs:
                raw_message = client.fetch([uid], ['BODY[]', 'FLAGS'])
                message = pyzmail.PyzMessage.factory(raw_message[uid][b'BODY[]'])
                asunto = message.get_subject()
                remitente = message.get_address('from')[1]

                if palabra_clave.lower() in asunto.lower() or palabra_clave.lower() in remitente.lower():
                    cuerpo = message.text_part.get_payload().decode(message.text_part.charset) if message.text_part else "No hay texto."
                    msg_final = f"📬 Nuevo email:\nDe: {remitente}\nAsunto: {asunto}\n\n{cuerpo}"
                    enviar_telegram(msg_final)
                    client.add_flags(uid, [b'\\Seen'])
    except Exception as e:
        enviar_telegram(f"⚠️ Error al verificar correos: {str(e)}")

# Iniciar el bot y tareas programadas
updater.start_polling()

while True:
    schedule.run_pending()
    time.sleep(10)
