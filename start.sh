#!/bin/bash

# Configurar el webhook correctamente con tu dominio de Render
curl -F "url=https://botprueba-s4rm.onrender.com" https://api.telegram.org/bot7775273072:AAHUmQp0G5CFGwAu8RuB6OFOjp704Ooqw38/setWebhook

# Iniciar el servidor FastAPI
uvicorn scripts:app --host 0.0.0.0 --port 10000

