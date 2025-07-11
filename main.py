import base64
import asyncio
import json
import os
import logging
import hmac
from typing import Dict, Any, Optional
from pathlib import Path

# Security-enhanced imports
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import TelegramError
from firebase_admin import credentials, db, initialize_app
from firebase_admin.exceptions import FirebaseError
from dotenv import load_dotenv
from datetime import datetime
import firebase_admin
from urllib.parse import unquote
from pydantic import BaseSettings, AnyUrl, validator, ValidationError

# Import your strategy modules
from strategy_loop import strategy_loop
from handlers.login import login_handler
from commands.start import start_command
from commands.help import help_command
from commands.trade import trade_command
from commands.leaderboard import leaderboard_command
from commands.setbase import setbase_command
from commands.setplatform import setplatform_command
from commands.setstrategy import setstrategy_command
from commands.setamount import setamount_command
from commands.showconfig import showconfig_command
from commands.balance import balance_command
from commands.register import register_command
from commands.autobot import autobot_command
from database import get_user_data, get_autobot_status, create_user, get_user
from utils import send_alert, format_trade_message
from price_feed import get_price
from utils.logger_utils import get_logger

# ===== Configuration Model =====
class BotSettings(BaseSettings):
    firebase_credentials: str
    database_url: AnyUrl
    bot_token: str
    fly_app: str = "crypto-bot-3-white-wind-424"
    webhook_secret: str
    log_level: str = "INFO"
    rate_limit: str = "100/minute"

    @validator("firebase_credentials")
    def validate_credentials(cls, v):
        try:
            decoded = base64.b64decode(v).decode("utf-8")
            cred_data = json.loads(decoded)
            if not all(k in cred_data for k in ["type", "project_id", "private_key"]):
                raise ValueError("Invalid Firebase credentials")
            return v
        except (base64.binascii.Error, json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Credential validation failed: {str(e)}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""

# Load settings
try:
    settings = BotSettings()
except ValidationError as e:
    print(f"Configuration error: {e}")
    exit(1)

# ===== Enhanced Logging =====
logger = get_logger("crypto-bot-3", settings.log_level)

# ===== Firebase Initialization =====
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            decoded = base64.b64decode(settings.firebase_credentials).decode("utf-8")
            cred_data = json.loads(decoded)
            cred = credentials.Certificate(cred_data)
            initialize_app(cred, {"databaseURL": settings.database_url})
            logger.info("Firebase initialized successfully")
        except (base64.binascii.Error, json.JSONDecodeError, ValueError) as e:
            logger.critical(f"Firebase initialization failed: {str(e)}")
            exit(1)

initialize_firebase()

# ===== FastAPI App Setup =====
app = FastAPI(title="Crypto Trading Bot", version="1.0.0")

# Security middleware
app.add_middleware(HTTPSRedirectMiddleware)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security scheme
security_scheme = HTTPBearer()

# ===== Telegram Bot Initialization =====
telegram_app = Application.builder().token(settings.bot_token).build()

# ===== Command Registration (Preserving your explicit handler setup) =====
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("trade", trade_command))
telegram_app.add_handler(CommandHandler("login", login_handler))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard_command))
telegram_app.add_handler(CommandHandler("setbase", setbase_command))
telegram_app.add_handler(CommandHandler("setplatform", setplatform_command))
telegram_app.add_handler(CommandHandler("setstrategy", setstrategy_command))
telegram_app.add_handler(CommandHandler("setamount", setamount_command))
telegram_app.add_handler(CommandHandler("showconfig", showconfig_command))
telegram_app.add_handler(CommandHandler("register", register_command))
telegram_app.add_handler(CommandHandler("balance", balance_command))
telegram_app.add_handler(CommandHandler("autobot", autobot_command))

# ===== Enhanced Price Command Handler =====
async def price_command(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        args = context.args
        source = args[0].lower() if args and len(args) >= 1 else "binance"
        
        if source == "binance":
            symbol = args[1] if len(args) > 1 else "BTCUSDT"
            price = await asyncio.to_thread(get_price, user_id, source="binance", symbol=symbol)
        elif source == "luno":
            pair = args[1] if len(args) > 1 else "XBTZAR"
            price = await asyncio.to_thread(get_price, user_id, source="luno", pair=pair)
        else:
            await update.message.reply_text("❌ Unknown exchange. Use 'binance' or 'luno'.")
            return

        if price is not None:
            await update.message.reply_text(f"✅ Current {source} price: {price}")
        else:
            await update.message.reply_text("❌ Error fetching price.")
    except Exception as e:
        logger.error(f"Price command error: {str(e)}")
        await update.message.reply_text("⚠️ An error occurred. Please try again later.")
        await log_event_async(user_id, "command_error", "price", error=str(e))

telegram_app.add_handler(CommandHandler("price", price_command))

# ===== Enhanced Logging Functions =====
def sync_log_event(user_id: str, event_type: str, message_text: str, status: str = "ok", error: Optional[str] = None):
    try:
        log_ref = db.reference(f"logs/{user_id}")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "message": message_text,
            "status": status,
            "environment": "production" if os.getenv("PRODUCTION") else "development"
        }
        if error:
            log_entry["error"] = error[:500]  # Truncate long errors
        log_ref.push(log_entry)
    except FirebaseError as e:
        logger.error(f"Firebase logging failed: {str(e)}")

async def log_event_async(user_id: str, event_type: str, message_text: str, status: str = "ok", error: Optional[str] = None):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, 
        sync_log_event, 
        user_id, event_type, message_text, status, error
    )

# ===== Webhook Security =====
async def verify_webhook_signature(request: Request) -> Dict[str, Any]:
    try:
        # Verify Telegram secret token
        if settings.webhook_secret:
            signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not hmac.compare_digest(signature, settings.webhook_secret):
                raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        # Verify Bearer token
        credentials: HTTPAuthorizationCredentials = await security_scheme(request)
        if credentials.credentials != settings.bot_token:
            raise HTTPException(status_code=403, detail="Invalid authentication token")
        
        return await request.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid request")

# ===== Webhook Endpoint with Legacy Support =====
@app.post("/webhook/{token}", dependencies=[Depends(limiter.limit("10/second"))])
async def telegram_webhook(request: Request, token: str):
    token = unquote(token)
    if token != settings.bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        data = await verify_webhook_signature(request)
        
        # Standard Telegram update processing
        if "update_id" in data:
            update = Update.de_json(data, telegram_app.bot)
            await telegram_app.process_update(update)
        # Legacy message processing
        else:
            message = data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")

            if not chat_id:
                return {"ok": False}

            user_id = str(chat_id)
            user = get_user(user_id)

            if not user:
                create_user(user_id)
                send_alert("Welcome! Your crypto bot profile has been created.", chat_id)
                await log_event_async(user_id, "new_user", text)
                return {"ok": True}

            if text.startswith("/"):
                try:
                    response = handle_command(text, user_id)
                    if response:
                        send_alert(response, chat_id)
                    await log_event_async(user_id, "command", text)
                except Exception as e:
                    send_alert(f"Command error for user {user_id}: {e}", chat_id)
                    send_alert("Oops, there was an error handling your command.", chat_id)
                    await log_event_async(user_id, "command", text, status="error", error=str(e))
                return {"ok": True}

            try:
                if get_autobot_status(user_id):
                    run_auto_bot(user_id)
                    await log_event_async(user_id, "autobot", text)
            except Exception as e:
                send_alert(f"AutoBot error for {user_id}: {e}", chat_id)
                send_alert("Error running AutoBot. Check your settings.", chat_id)
                await log_event_async(user_id, "autobot", text, status="error", error=str(e))

        return {"ok": True}
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload in webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ===== Health and Root Endpoints =====
@app.get("/")
def root():
    return {"status": "active", "service": "crypto-trading-bot"}

@app.get("/health")
async def health_check():
    status = {
        "telegram": telegram_app.running if telegram_app else False,
        "firebase": bool(firebase_admin._apps),
        "database": "unknown"
    }
    
    try:
        # Simple Firebase health check
        db.reference('healthcheck').set({'ping': datetime.utcnow().isoformat()})
        status["database"] = "connected"
    except FirebaseError:
        status["database"] = "disconnected"
    
    return status

# ===== Error Handling =====
def global_error_handler(update: object, context: CallbackContext):
    error = context.error
    logger.error(f"Global error: {str(error)}", exc_info=error)
    
    if update and isinstance(update, Update) and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ An unexpected error occurred. Our team has been notified."
        )

telegram_app.add_error_handler(global_error_handler)

# ===== Startup/Shutdown Events =====
@app.on_event("startup")
async def start_bot():
    logger.info("Starting bot initialization...")
    
    # Initialize Telegram commands
    commands = [
        ("start", "Start the bot"),
        ("help", "Show help info"),
        ("trade", "Execute a manual trade"),
        ("stopautobot", "Stop the auto trading bot"),
        ("leaderboard", "Show the leaderboard"),
        ("setbase", "Set your base currency"),
        ("setplatform", "Choose Luno or Binance"),
        ("setstrategy", "Select your strategy"),
        ("setamount", "Set trade amount"),
        ("showconfig", "View your current configuration"),
        ("register", "Register a new account"),
        ("login", "Log into your account"),
        ("balance", "Check your crypto balance"),
        ("price", "Check crypto prices"),
    ]
    
    await telegram_app.initialize()
    await telegram_app.bot.set_my_commands(commands)
    
    # Set webhook with enhanced verification
    webhook_url = f"https://{settings.fly_app}.fly.dev/webhook/{settings.bot_token}"
    await telegram_app.bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret
    )
    logger.info(f"Webhook set to: {webhook_url}")
    
    # Start strategy loop in background
    asyncio.create_task(strategy_loop())
    logger.info("Bot startup complete")

@app.on_event("shutdown")
async def stop_bot():
    logger.info("Shutting down bot...")
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Bot shutdown complete")

# ===== Main Entry Point =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        ssl_keyfile=os.getenv("SSL_KEYFILE", None),
        ssl_certfile=os.getenv("SSL_CERTFILE", None)
            )
