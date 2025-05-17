FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Use path-based credentials
ENV FIREBASE_CREDENTIALS_PATH="/app/crypto-bot-3-firebase-adminsdk-fbsvc-b07a760124.json"

ENV SECRET_KEY="{your_32_char_secret_key}"
ENV BASE_URL="https://crypto-bot-3-white-wind-424.fly.dev"
ENV BOT_TOKEN="{your_telegram_bot_token}"

EXPOSE 8080

CMD ["python", "main.py"]
