import os
import sys
import json
import random
import datetime
import asyncio

import openai
from openai import RateLimitError, OpenAIError
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

# 2) Persona laden aus persona.txt
try:
    with open("persona.txt", "r", encoding="utf-8") as f:
        PERSONA = f.read().strip()
except FileNotFoundError:
    print("ERROR: persona.txt not found")
    sys.exit(1)

# 3) System-Prompt: Persona + streng geregelter Stil
SYSTEM_PROMPT = PERSONA + "\n\n" + (
    "Stil-Regeln:\n"
    "- Schreibe in kurzer Umgangssprache, wie Jugendiche und echte Menschen schreiben würden, du kannst auch frech sein\n"
    "- Vermeide und benutze KEINE Füllwörter und Emojis.\n"
    "- Nutze direkte Sätze: kein ‚ich finde‘, statt dessen ‚finde‘.\n"
    "- Maximal 1 Slangwort pro Satz (z.B. ‚yo‘, ‚krass‘).\n"
    "- Vermeide eher Fragen; formuliere eher Statements.\n"
    "- Sprich offen über dein Vermögen, wenn du danach gefragt wirst."
)

# 4) Gedächtnis initialisieren
MEMORY_FILE = "memory.json"
memory = []
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)

def save_memory():
    global memory
    memory = memory[-40:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# 5) /start-Handler
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("yo Armin, Mensa-Wochen-Flashback 😂")

# 6) Nachrichten-Handler
async def antwort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    memory.append({"role": "user", "content": text})
    save_memory()

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.randint(2, 5))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *memory,
        {"role": "user", "content": text}
    ]
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.8,
            top_p=0.7,
            max_tokens=20
        )
        reply = resp.choices[0].message.content.strip()
    except RateLimitError:
        reply = "sorry, kein kredit 😂"
    except OpenAIError:
        reply = "denk-block 😂"

    memory.append({"role": "assistant", "content": reply})
    save_memory()
    await update.message.reply_text(reply)

# 7) Spontane Nachrichten
async def send_random(app):
    prompts = ["yo, was geht?", "alles klar?", "kaffee?", "zocken?", "update?"]
    p = random.choice(prompts)
    memory.append({"role": "user", "content": p})
    save_memory()

    await app.bot.send_chat_action(USER_CHAT_ID, ChatAction.TYPING)
    await asyncio.sleep(random.randint(2, 5))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *memory,
        {"role": "user", "content": p}
    ]
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.8,
            top_p=0.7,
            max_tokens=20
        )
        text = resp.choices[0].message.content.strip()
    except RateLimitError:
        text = "sorry, kein kredit 😂"
    except OpenAIError:
        text = "denk-block 😂"

    memory.append({"role": "assistant", "content": text})
    save_memory()
    await app.bot.send_message(chat_id=USER_CHAT_ID, text=text)

# 8) Loop für spontane Nachrichten
async def random_loop(app):
    while True:
        now = datetime.datetime.now()
        if now.hour < 8:
            await asyncio.sleep((now.replace(hour=8, minute=0, second=0) - now).total_seconds())
        else:
            await asyncio.sleep(random.randint(3600, 14400))
            if 8 <= datetime.datetime.now().hour < 24:
                await send_random(app)

# 9) Startup-Hook
async def on_startup(app):
    asyncio.create_task(random_loop(app))

# 10) Bot starten
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antwort))
    app.run_polling(drop_pending_updates=True)
