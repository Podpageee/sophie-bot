# Sophie Schertler Telegram Bot (Full Persona)

## Einrichtung

1. **Clone oder kopiere** das Projekt auf deinen Server.
2. **Docker bauen**:
   ```
   docker build -t sophie-bot .
   ```
3. **Container starten**:
   ```
   docker run -d --name sophie-bot \
     -e TELEGRAM_TOKEN="DEIN_TELEGRAM_TOKEN" \
     -e OPENAI_KEY="DEIN_OPENAI_API_KEY" \
     -e USER_CHAT_ID="1591555196" \
     sophie-bot
   ```

Der Bot läuft 24/7, nutzt GPT-4o, merkt sich Konversationen und nutzt die vollständige Persona.
