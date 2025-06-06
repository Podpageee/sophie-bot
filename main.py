import os
import openai
import time
import random
import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import json

# Load API keys and chat ID from env
OPENAI_KEY = os.getenv("OPENAI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_CHAT_ID = int(os.getenv("USER_CHAT_ID"))

# Check env vars
import sys
for var in ("OPENAI_KEY","TELEGRAM_TOKEN","USER_CHAT_ID"):
    if not os.getenv(var):
        print(f"ERROR: Missing environment variable {var}")
        sys.exit(1)

openai.api_key = OPENAI_KEY

# Load persona
with open("persona.txt", "r", encoding="utf-8") as f:
    PERSONA = f.read()

# Memory file
MEMORY_FILE = "memory.json"
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = []

def save_memory():
    global memory
    memory = memory[-40:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

async def antwort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    memory.append({"role": "user", "content": text})
    save_memory()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(random.randint(6, 10))
    messages = [{"role": "system", "content": PERSONA}] + memory + [{"role": "user", "content": text}]
    resp = openai.ChatCompletion.create(model="gpt-4o", messages=messages)
    reply = resp.choices[0].message.content
    memory.append({"role": "assistant", "content": reply})
    save_memory()
    await update.message.reply_text(reply)

async def send_random(app):
    prompt = random.choice([
        "Hallo Armin, wie geht's dir heute?",
        "Erinnerst du dich an unser WG-Brunch mit kaltem Kaffee? 😅",
        "Ich hab heute an unser Lernmarathon gedacht.",
        "Luzia hat heute wieder Crêpes gemacht lol 😅",
        "Wenn du hier wärst, würde ich dir einen Kaffee machen ☕️"
    ])
    memory.append({"role": "user", "content": prompt})
    save_memory()
    await app.bot.send_chat_action(chat_id=USER_CHAT_ID, action="typing")
    await asyncio.sleep(random.randint(6, 12))
    messages = [{"role": "system", "content": PERSONA}] + memory + [{"role": "user", "content": prompt}]
    resp = openai.ChatCompletion.create(model="gpt-4o", messages=messages)
    text = resp.choices[0].message.content
    memory.append({"role": "assistant", "content": text})
    save_memory()
    await app.bot.send_message(chat_id=USER_CHAT_ID, text=text)

async def random_loop(app):
    while True:
        now = datetime.datetime.now()
        if now.hour < 8:
            next_run = now.replace(hour=8, minute=0, second=0)
            delay = (next_run - now).total_seconds()
            await asyncio.sleep(delay)
            continue
        delay = random.randint(3600, 14400)
        await asyncio.sleep(delay)
        now2 = datetime.datetime.now()
        if 8 <= now2.hour < 24:
            await send_random(app)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antwort))
    asyncio.create_task(random_loop(app))
    await app.run_polling()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
