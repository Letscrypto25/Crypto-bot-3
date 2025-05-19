# database.py

import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db

# Decode Firebase credentials if not already decoded
if not os.path.exists("firebase_credentials.json"):
    with open("firebase_encoded.txt", "r") as f:
        encoded = f.read().strip()
    decoded = base64.b64decode(encoded).decode("utf-8")
    with open("firebase_credentials.json", "w") as f:
        f.write(decoded)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'firebase-adminsdk-fbsvc@crypto-bot-3.iam.gserviceaccount.com'  # Replace this with your actual database URL
    })

firebase_ref = db.reference("users")

# Get user data from database
def get_user_data(user_id):
    return db.reference(f'users/{user_id}').get()

# Update a user's data
def update_user_data(user_id, data):
    db.reference(f'users/{user_id}').update(data)

# Save a trade for a user
def save_trade(user_id, trade_data):
    db.reference(f'trades/{user_id}').push(trade_data)

# Get leaderboard reference
def get_leaderboard_ref():
    return db.reference('leaderboard')

# Get trades reference
def get_trades_ref():
    return db.reference('trades')

# Get user info (used in commands.py)
def get_user(user_id):
    return db.reference(f'users/{user_id}').get()

def get_all_users():
    return db.reference('users').get()
