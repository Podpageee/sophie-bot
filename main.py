import os
import sys
import json
import random
import datetime
import asyncio

import openai
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# 1) Umgebungsvariablen prüfen und laden
for var in ("OPENAI_KEY", "TELEGRAM_TOKEN", "USER_CHAT_ID"):
    if not os.getenv(var):
        print(f"ERROR: Missing environment variable {var}")
        sys.exit(1)

OPENAI_KEY     = os.getenv("OPENAI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_CHAT_ID   = int(os.getenv("USER_CHAT_ID"))

openai.api_key = OPENAI_KEY

# 2) Persona laden
with open("persona.txt", "r", encoding="utf-8") as f:
    PERSONA = f.read()

# 3) Gedächtnis initialisieren
MEMORY_FILE = "memory.json"
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = []

def save_memory():
    global memory
    # nur die letzten 40 Einträge behalten
    memory = memory[-40:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# 4) Handler für eingehende Nachrichten
async def antwort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    memory.append({"role":"user","content":text})
    save_memory()

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )
    await asyncio.sleep(random.randint(6, 10))

    messages = [{"role":"system","content":PERSONA}] + memory + [{"role":"user","content":text}]
    resp = openai.ChatCompletion.create(model="gpt-4o", messages=messages)
    reply = resp.choices[0].message.content

    memory.append({"role":"assistant","content":reply})
    save_memory()

    await update.message.reply_text(reply)

# 5) Funktion für spontane Nachrichten
async def send_random(app):
    prompts = [
        "Hallo Armin, wie geht's dir heute?",
        "Erinnerst du dich an unser WG-Brunch mit kaltem Kaffee? 😂",
        "Ich hab heute an unser Lernmarathon gedacht.",
        "Luzia hat heute wieder Crêpes gemacht lol 😅",
        "Wenn du hier wärst, würde ich dir einen Kaffee machen ☕️"
    ]
    prompt = random.choice(prompts)

    memory.append({"role":"user","content":prompt})
    save_memory()

    await app.bot.send_chat_action(
        chat_id=USER_CHAT_ID,
        action=ChatAction.TYPING
    )
    await asyncio.sleep(random.randint(6, 12))

    messages = [{"role":"system","content":PERSONA}] + memory + [{"role":"user","content":prompt}]
    resp = openai.ChatCompletion.create(model="gpt-4o", messages=messages)
    text = resp.choices[0].message.content

    memory.append({"role":"assistant","content":text})
    save_memory()

    await app.bot.send_message(chat_id=USER_CHAT_ID, text=text)

# 6) Loop für zufällige Nachrichten zwischen 08:00 und 24:00
async def random_loop(app):
    while True:
        now = datetime.datetime.now()
        if now.hour < 8:
            next_run = now.replace(hour=8, minute=0, second=0)
            await asyncio.sleep((next_run - now).total_seconds())
            continue
        await asyncio.sleep(random.randint(3600, 14400))
        now2 = datetime.datetime.now()
        if 8 <= now2.hour < 24:
            await send_random(app)

# 7) Startup-Hook, damit random_loop im selben Event-Loop läuft
async def on_startup(app):
    asyncio.create_task(random_loop(app))

# 8) Bot starten
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antwort))
    app.run_polling()

if __name__ == "__main__":
    main()
