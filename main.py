import os
import sys
import json
import random
import datetime
import asyncio

import openai
from openai.error import RateLimitError, OpenAIError
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ─── 1) ENV-Variablen prüfen und laden ─────────────────────────────────────────
for var in ("OPENAI_KEY", "TELEGRAM_TOKEN", "USER_CHAT_ID"):
    if not os.getenv(var):
        print(f"ERROR: Missing environment variable {var}")
        sys.exit(1)

OPENAI_KEY     = os.getenv("OPENAI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_CHAT_ID   = int(os.getenv("USER_CHAT_ID"))

openai.api_key = OPENAI_KEY

# ─── 2) System-Prompt mit ultra-kurzem Jugend-Slang-Stil ───────────────────────
SYSTEM_PROMPT = """Du bist Sophie Schertler, 24 Jahre alt aus Lauterach, Vorarlberg.
Du hast mit Armin Politikwissenschaft in Innsbruck studiert, WG-Partys, Bibliotheks-Marathons und Mensa-Wochen erlebt.
Armin spielt FIFA 22, Strategiespiele und kocht gern Tiramisu und Eiskaffeetorte.
Ihr seid seit dem Studium beste Freunde.

Stil-Regeln:
- Schreibe ultra-kurz: max. 1–2 kurze Sätze.
- Nutze Jugendslang: "krass", "nice", "chillig", "yo".
- Antworte auch mal mit "yep", "nope", "lol" oder "moin".
- Emojis nur, wenn’s richtig passt (max. 1).
- Sei direkt, vermeide Förmlichkeiten.
- Sprich offen über dein Vermögen und dein Familienunternehmen, wenn Armin danach fragt.
"""

# ─── 3) Gedächtnis initialisieren ───────────────────────────────────────────────
MEMORY_FILE = "memory.json"
memory = []
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)

def save_memory():
    global memory
    memory = memory[-40:]  # nur die letzten 40 Einträge
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# ─── 4) /start-Handler ─────────────────────────────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = (
        "Hi Armin! Wir kennen uns aus Innsbruck und Mensa-Wochen. "
        "Ich bin Sophie – deine freche Studien-Bot!"
    )
    await update.message.reply_text(intro)

# ─── 5) Nachrichten-Handler ────────────────────────────────────────────────────
async def antwort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    memory.append({"role": "user", "content": text})
    save_memory()

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.randint(6, 10))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *memory,
        {"role": "user", "content": text}
    ]
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.9,
            top_p=0.8,
            max_tokens=60
        )
        reply = resp.choices[0].message.content.strip()
    except RateLimitError:
        reply = "Sorry, gerade kein Guthaben lol 😅"
    except OpenAIError:
        reply = "Uff, Denk-Block 😵‍💫 Versuch später nochmal."

    memory.append({"role": "assistant", "content": reply})
    save_memory()
    await update.message.reply_text(reply)

# ─── 6) Spontane Nachrichten-Funktion ──────────────────────────────────────────
async def send_random(app):
    prompts = [
        "Yo, wie läuft’s?",
        "Alles fit?",
        "Bock auf Kaffee? ☕",
        "Ready zum Zocken?",
        "Kurzes Update?"
    ]
    p = random.choice(prompts)
    memory.append({"role": "user", "content": p})
    save_memory()

    await app.bot.send_chat_action(USER_CHAT_ID, ChatAction.TYPING)
    await asyncio.sleep(random.randint(6, 12))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *memory,
        {"role": "user", "content": p}
    ]
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.9,
            top_p=0.8,
            max_tokens=60
        )
        text = resp.choices[0].message.content.strip()
    except RateLimitError:
        text = "Sorry, out of quota 😂"
    except OpenAIError:
        text = "Huch, Denk-Error 🤯"

    memory.append({"role": "assistant", "content": text})
    save_memory()
    await app.bot.send_message(chat_id=USER_CHAT_ID, text=text)

# ─── 7) Loop für zufällige Nachrichten ─────────────────────────────────────────
async def random_loop(app):
    while True:
        now = datetime.datetime.now()
        if now.hour < 8:
            target = now.replace(hour=8, minute=0, second=0)
            await asyncio.sleep((target - now).total_seconds())
        else:
            await asyncio.sleep(random.randint(3600, 14400))  # 1–4 h
            now2 = datetime.datetime.now()
            if 8 <= now2.hour < 24:
                await send_random(app)

# ─── 8) Startup-Hook ───────────────────────────────────────────────────────────
async def on_startup(app):
    asyncio.create_task(random_loop(app))

# ─── 9) Bot konfigurieren & Polling starten ────────────────────────────────────
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antwort))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
