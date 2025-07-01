from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from services.whatsapp_service import WhatsAppService
from database.models import DatabaseManager, Member, Subscription

class ChamaScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.whatsapp_service = WhatsAppService()
        self.db_manager = DatabaseManager()
        self.member_service = Member(self.db_manager)
        self.subscription_service = Subscription(self.db_manager)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Set up scheduled jobs
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Set up all scheduled jobs"""
        
        # Weekly payment reminders (every Monday at 9 AM)
        self.scheduler.add_job(
            func=self.send_weekly_reminders,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
            id='weekly_reminders',
            name='Send weekly payment reminders',
            replace_existing=True
        )
        
        # Monthly subscription charges (1st of every month at 8 AM)
        self.scheduler.add_job(
            func=self.process_monthly_subscriptions,
            trigger=CronTrigger(day=1, hour=8, minute=0),
            id='monthly_subscriptions',
            name='Process monthly subscription charges',
            replace_existing=True
        )
        
        # Daily backup (every day at 2 AM)
        self.scheduler.add_job(
            func=self.daily_backup,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_backup',
            name='Daily database backup',
            replace_existing=True
        )
        
        # Weekly reports (every Sunday at 6 PM)
        self.scheduler.add_job(
            func=self.generate_weekly_reports,
            trigger=CronTrigger(day_of_week='sun', hour=18, minute=0),
            id='weekly_reports',
            name='Generate weekly reports',
            replace_existing=True
        )
    
    def send_weekly_reminders(self):
        """Send weekly payment reminders to all active members"""
        try:
            self.logger.info("Starting weekly payment reminders...")
            
            members = self.member_service.get_all_members()
            reminder_count = 0
            
            for member in members:
                if member['status'] == 'active':
                    subscription = self.subscription_service.get_subscription(member['phone'])
                    if subscription and subscription['status'] == 'active':
                        message = (
                            f"Hi {member['name']}! 🏦\n\n"
                            f"Weekly Chama reminder:\n"
                            f"💰 Current balance: KES {member['balance']:,.0f}\n"
                            f"📅 Last payment: {member['last_payment'] or 'Never'}\n\n"
                            f"Reply 'PAY <amount>' to contribute.\n"
                            f"Reply 'BALANCE' to check your balance."
                        )
                        
                        success = self.whatsapp_service.send_message(member['phone'], message)
                        if success:
                            reminder_count += 1
            
            self.logger.info(f"Weekly reminders sent to {reminder_count} members")
            
        except Exception as e:
            self.logger.error(f"Error sending weekly reminders: {str(e)}")
    
    def process_monthly_subscriptions(self):
        """Process monthly subscription charges"""
        try:
            self.logger.info("Processing monthly subscription charges...")
            
            subscriptions = self.subscription_service.get_all_subscriptions()
            processed_count = 0
            
            for subscription in subscriptions:
                if subscription['status'] == 'active':
                    member = self.member_service.get_member(subscription['phone'])
                    if member:
                        # Determine subscription fee
                        fee = 100 if subscription['plan'] == 'basic' else 300
                        
                        # Check if member has sufficient balance
                        if member['balance'] >= fee:
                            # Deduct subscription fee
                            new_balance = member['balance'] - fee
                            self.member_service.update_member(subscription['phone'], balance=new_balance)
                            
                            # Record subscription payment
                            from services.whatsapp_service import WhatsAppService
                            payment_service = WhatsAppService().payment_service
                            payment_service.add_payment(
                                subscription['phone'], 
                                fee, 
                                'subscription', 
                                f"Monthly {subscription['plan']} subscription"
                            )
                            
                            # Send confirmation message
                            message = (
                                f"Hi {member['name']}! 📋\n\n"
                                f"Monthly subscription processed:\n"
                                f"💳 Plan: {subscription['plan'].title()}\n"
                                f"💰 Fee: KES {fee:,.0f}\n"
                                f"💰 New balance: KES {new_balance:,.0f}\n\n"
                                f"Thank you for your continued membership!"
                            )
                            
                            self.whatsapp_service.send_message(subscription['phone'], message)
                            processed_count += 1
                        else:
                            # Insufficient balance - send warning
                            message = (
                                f"Hi {member['name']}! ⚠️\n\n"
                                f"Insufficient balance for monthly subscription:\n"
                                f"💳 Plan: {subscription['plan'].title()}\n"
                                f"💰 Required: KES {fee:,.0f}\n"
                                f"💰 Current balance: KES {member['balance']:,.0f}\n\n"
                                f"Please top up your balance to continue your subscription."
                            )
                            
                            self.whatsapp_service.send_message(subscription['phone'], message)
            
            self.logger.info(f"Processed {processed_count} subscription charges")
            
        except Exception as e:
            self.logger.error(f"Error processing monthly subscriptions: {str(e)}")
    
    def daily_backup(self):
        """Perform daily database backup"""
        try:
            self.logger.info("Starting daily database backup...")
            
            import shutil
            import os
            from datetime import datetime
            
            # Create backup directory if it doesn't exist
            backup_dir = 'backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{backup_dir}/chama_backup_{timestamp}.db"
            
            # Copy database file
            shutil.copy2('chama.db', backup_filename)
            
            # Keep only last 7 days of backups
            self._cleanup_old_backups(backup_dir, days_to_keep=7)
            
            self.logger.info(f"Database backup completed: {backup_filename}")
            
        except Exception as e:
            self.logger.error(f"Error during daily backup: {str(e)}")
    
    def generate_weekly_reports(self):
        """Generate and send weekly reports to premium members"""
        try:
            self.logger.info("Generating weekly reports...")
            
            from services.report_service import ReportService
            report_service = ReportService()
            
            # Get premium subscribers
            subscriptions = self.subscription_service.get_all_subscriptions()
            premium_members = [sub for sub in subscriptions if sub['plan'] == 'premium' and sub['status'] == 'active']
            
            for subscription in premium_members:
                member = self.member_service.get_member(subscription['phone'])
                if member:
                    try:
                        # Generate member statement
                        filename = report_service.generate_member_statement(subscription['phone'])
                        
                        # Send notification
                        message = (
                            f"Hi {member['name']}! 📊\n\n"
                            f"Your weekly Chama report is ready!\n"
                            f"💰 Current balance: KES {member['balance']:,.0f}\n"
                            f"📄 Report generated: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                            f"Access your detailed report on the dashboard."
                        )
                        
                        self.whatsapp_service.send_message(subscription['phone'], message)
                        
                    except Exception as e:
                        self.logger.error(f"Error generating report for {subscription['phone']}: {str(e)}")
            
            self.logger.info(f"Weekly reports generated for {len(premium_members)} premium members")
            
        except Exception as e:
            self.logger.error(f"Error generating weekly reports: {str(e)}")
    
    def _cleanup_old_backups(self, backup_dir: str, days_to_keep: int = 7):
        """Clean up old backup files"""
        try:
            import os
            import time
            from datetime import datetime, timedelta
            
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('chama_backup_') and filename.endswith('.db'):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.getctime(file_path) < cutoff_time:
                        os.remove(file_path)
                        self.logger.info(f"Removed old backup: {filename}")
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {str(e)}")
    
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            self.logger.info("Chama scheduler started successfully")
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
    
    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            self.logger.info("Chama scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {str(e)}")
    
    def get_job_status(self):
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'Not scheduled'
            })
        return jobs

# Example usage
if __name__ == "__main__":
    scheduler = ChamaScheduler()
    
    try:
        scheduler.start()
        print("Scheduler started. Press Ctrl+C to stop.")
        
        # Keep the script running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping scheduler...")
        scheduler.stop()