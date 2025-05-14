#!/bin/bash

# Configura el webhook (una sola vez al iniciar)
curl -F "url=https://TU_DOMINIO_RENDER.onrender.com" https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook

# Inicia el servidor FastAPI en el puerto 10000
uvicorn scripts:app --host 0.0.0.0 --port 10000

