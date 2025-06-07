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
    CommandHandler,
    filters,
)

# 1) ENV-Variablen prüfen und laden
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
memory = []
if os.path.exists(MEMORY_FILE):
    memory = json.loads(open(MEMORY_FILE, "r", encoding="utf-8").read())

def save_memory():
    global memory
    memory = memory[-40:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# 4) /start handler
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi, ich bin Sophie Schertler – dein freche, witzige Studienfreundin-Bot! 😅")

# 5) Nachrichten-Handler
async def antwort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    memory.append({"role":"user","content":text}); save_memory()

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.randint(6,10))

    msgs = [{"role":"system","content":PERSONA}] + memory + [{"role":"user","content":text}]
    resp = openai.chat.completions.create(model="gpt-4o", messages=msgs)
    reply = resp.choices[0].message.content

    memory.append({"role":"assistant","content":reply}); save_memory()
    await update.message.reply_text(reply)

# 6) Spontane Nachrichten-Funktion
async def send_random(app):
    prompts = [
       "Yo, wie läuft’s?",
    "Bock auf ’nen schnellen Kaffee? ☕",
    "Hey hehy :)",
    "Heeeyy",
    "Kurzes Status-Update?"
    ]
    p = random.choice(prompts)
    memory.append({"role":"user","content":p}); save_memory()

    await app.bot.send_chat_action(USER_CHAT_ID, ChatAction.TYPING)
    await asyncio.sleep(random.randint(6,12))

    msgs = [{"role":"system","content":PERSONA}] + memory + [{"role":"user","content":p}]
    resp = openai.chat.completions.create(model="gpt-4o", messages=msgs)
    text = resp.choices[0].message.content

    memory.append({"role":"assistant","content":text}); save_memory()
    await app.bot.send_message(chat_id=USER_CHAT_ID, text=text)

# 7) Loop für zufällige Nachrichten
async def random_loop(app):
    while True:
        now = datetime.datetime.now()
        if now.hour < 8:
            delta = (now.replace(hour=8,minute=0,second=0)-now).total_seconds()
            await asyncio.sleep(delta)
        else:
            await asyncio.sleep(random.randint(3600,14400))
            now2 = datetime.datetime.now()
            if 8 <= now2.hour < 24:
                await send_random(app)

# 8) Startup-Hook für den Loop
async def on_startup(app):
    asyncio.create_task(random_loop(app))

# 9) Bot konfigurieren & Polling starten
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antwort))

    # nur eine Polling-Instanz – alte Updates verwerfen
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
