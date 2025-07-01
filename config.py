import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', 'whatsapp:+14155238886')
    
    # Database Configuration
    DATABASE_PATH = 'chama.db'
    
    # Application Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        'basic': {
            'price': 100,
            'features': ['WhatsApp Bot', 'Basic Reports', 'Payment Tracking']
        },
        'premium': {
            'price': 300,
            'features': ['All Basic Features', 'PDF Reports', 'SMS Reminders', 'Advanced Analytics']
        }
    }