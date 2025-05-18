FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Firebase credential path (adjust filename if needed)
ENV FIREBASE_CREDENTIALS_PATH="/app/crypto-bot-3-firebase-adminsdk-fbsvc-b07a760124.json"

# Telegram bot token and secret (REPLACE with actual or use secrets in Fly.io)
ENV TELEGRAM_BOT_TOKEN="your_actual_bot_token"
ENV SECRET_KEY="your_32_char_secret_key"
ENV BASE_URL="https://crypto-bot-3-white-wind-424.fly.dev"

# Redis URL (set automatically by Fly.io Redis addon)
ENV REDIS_URL="redis://default:password@fly-redis.internal:6379/0"

EXPOSE 8080

# Default command: start the Flask app
CMD ["python", "main.py"]
