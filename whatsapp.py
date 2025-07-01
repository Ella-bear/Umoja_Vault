from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from typing import Dict, Any
import logging
from config import Config
from database.models import DatabaseManager, Member, Payment, Subscription

class WhatsAppService:
    def __init__(self):
        self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        self.db_manager = DatabaseManager()
        self.member_service = Member(self.db_manager)
        self.payment_service = Payment(self.db_manager)
        self.subscription_service = Subscription(self.db_manager)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, to: str, body: str) -> bool:
        """Send WhatsApp message"""
        try:
            message = self.client.messages.create(
                from_=Config.TWILIO_PHONE_NUMBER,
                body=body,
                to=f'whatsapp:{to}'
            )
            self.logger.info(f"Message sent to {to}: {message.sid}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to {to}: {str(e)}")
            return False
    
    def process_incoming_message(self, from_number: str, message_body: str) -> str:
        """Process incoming WhatsApp message and return response"""
        # Clean phone number
        phone = from_number.replace('whatsapp:', '')
        message = message_body.strip().upper()
        
        # Check if user has subscription
        subscription = self.subscription_service.get_subscription(phone)
        if not subscription and not message.startswith('SUBSCRIBE'):
            return "Please subscribe to use this service. Reply 'SUBSCRIBE' to join for KES 100/month."
        
        # Process commands
        if message.startswith('PAY '):
            return self._process_payment(phone, message)
        elif message == 'BALANCE':
            return self._process_balance_inquiry(phone)
        elif message.startswith('REGISTER '):
            return self._process_registration(phone, message)
        elif message == 'SUBSCRIBE':
            return self._process_subscription(phone)
        elif message == 'UPGRADE':
            return self._process_upgrade_inquiry(phone)
        elif message == 'REPORT':
            return self._process_report_request(phone)
        elif message == 'HELP':
            return self._get_help_message()
        else:
            return "Unknown command. Reply 'HELP' for available commands."
    
    def _process_payment(self, phone: str, message: str) -> str:
        """Process payment command"""
        try:
            parts = message.split()
            if len(parts) < 2:
                return "Invalid format. Use 'PAY <amount>' (e.g., PAY 500)"
            
            amount = float(parts[1])
            if amount <= 0:
                return "Amount must be greater than 0"
            
            member = self.member_service.get_member(phone)
            if not member:
                return "You're not registered. Reply 'REGISTER <name>' to join."
            
            success = self.payment_service.add_payment(phone, amount, 'contribution')
            if success:
                updated_member = self.member_service.get_member(phone)
                return f"Payment of KES {amount:,.0f} recorded. New balance: KES {updated_member['balance']:,.0f}"
            else:
                return "Failed to record payment. Please try again."
        
        except ValueError:
            return "Invalid amount. Use 'PAY <amount>' (e.g., PAY 500)"
        except Exception as e:
            self.logger.error(f"Payment processing error: {str(e)}")
            return "Error processing payment. Please try again."
    
    def _process_balance_inquiry(self, phone: str) -> str:
        """Process balance inquiry"""
        member = self.member_service.get_member(phone)
        if member:
            return f"Hi {member['name']}, your current balance is KES {member['balance']:,.0f}"
        else:
            return "You're not registered. Reply 'REGISTER <name>' to join."
    
    def _process_registration(self, phone: str, message: str) -> str:
        """Process member registration"""
        try:
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "Please provide your name. Use 'REGISTER <name>' (e.g., REGISTER John Doe)"
            
            name = parts[1].title()
            success = self.member_service.create_member(phone, name)
            
            if success:
                return f"Welcome {name}! You're registered. Reply 'PAY <amount>' to contribute."
            else:
                return "You're already registered. Reply 'BALANCE' to check your balance."
        
        except Exception as e:
            self.logger.error(f"Registration error: {str(e)}")
            return "Error during registration. Please try again."
    
    def _process_subscription(self, phone: str) -> str:
        """Process subscription request"""
        try:
            success = self.subscription_service.create_subscription(phone, 'basic')
            if success:
                return "Subscribed to basic plan (KES 100/month). Reply 'REGISTER <name>' to start."
            else:
                return "Error creating subscription. Please try again."
        
        except Exception as e:
            self.logger.error(f"Subscription error: {str(e)}")
            return "Error creating subscription. Please try again."
    
    def _process_upgrade_inquiry(self, phone: str) -> str:
        """Process upgrade inquiry"""
        subscription = self.subscription_service.get_subscription(phone)
        if subscription and subscription['plan'] == 'premium':
            return "You already have a premium subscription!"
        
        return ("Upgrade to premium for PDF reports and advanced features. "
                "Premium plan: KES 300/month. Contact admin for upgrade.")
    
    def _process_report_request(self, phone: str) -> str:
        """Process report request"""
        subscription = self.subscription_service.get_subscription(phone)
        if subscription and subscription['plan'] == 'premium':
            # In a real implementation, this would generate and send a PDF
            return "PDF report generated and available on the dashboard."
        else:
            return "Upgrade to premium for PDF reports. Reply 'UPGRADE' to learn more."
    
    def _get_help_message(self) -> str:
        """Get help message with available commands"""
        return ("Available commands:\n"
                "• PAY <amount> - Record payment\n"
                "• BALANCE - Check balance\n"
                "• REGISTER <name> - Register as member\n"
                "• SUBSCRIBE - Subscribe to basic plan\n"
                "• UPGRADE - Learn about premium\n"
                "• REPORT - Generate report (Premium)\n"
                "• HELP - Show this message")
    
    def send_payment_reminders(self):
        """Send payment reminders to all active members"""
        members = self.member_service.get_all_members()
        
        for member in members:
            if member['status'] == 'active':
                subscription = self.subscription_service.get_subscription(member['phone'])
                if subscription:
                    message = (f"Hi {member['name']}, your Chama contribution reminder. "
                             f"Current balance: KES {member['balance']:,.0f}. "
                             f"Reply 'PAY <amount>' to contribute.")
                    self.send_message(member['phone'], message)
        
        self.logger.info("Payment reminders sent to all active members")