import requests
from app.config.settings import settings

def send_telegram_alert(message: str):
    """
    Sends a message to the configured Telegram chat.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        print(f"Telegram alert not sent (missing credentials): {message}")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Telegram alert sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
