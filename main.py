import argparse
import sys
import threading
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chama_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask web application"""
    try:
        from web.flask_app import app
        from config import Config
        
        logger.info("Starting Flask web application...")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=Config.DEBUG,
            use_reloader=False  # Disable reloader when running in thread
        )
    except Exception as e:
        logger.error(f"Error running Flask app: {str(e)}")

def run_streamlit_dashboard():
    """Run the Streamlit dashboard"""
    try:
        import subprocess
        import os
        
        logger.info("Starting Streamlit dashboard...")
        
        # Change to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_script = os.path.join(script_dir, 'streamlit_dashboard.py')
        
        # Run Streamlit
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 
            streamlit_script, '--server.port=8501', '--server.headless=true'
        ])
        
    except Exception as e:
        logger.error(f"Error running Streamlit dashboard: {str(e)}")

def run_scheduler():
    """Run the background scheduler"""
    try:
        from scheduler import ChamaScheduler
        
        logger.info("Starting background scheduler...")
        scheduler = ChamaScheduler()
        scheduler.start()
        
        # Display job status
        jobs = scheduler.get_job_status()
        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job['name']}: Next run at {job['next_run']}")
        
        # Keep running
        try:
            while True:
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.stop()
            
    except Exception as e:
        logger.error(f"Error running scheduler: {str(e)}")

def run_cli():
    """Run the command-line interface"""
    try:
        from database.models import DatabaseManager, Member, Payment, Subscription
        from services.whatsapp_service import WhatsAppService
        from services.report_service import ReportService
        
        # Initialize services
        db_manager = DatabaseManager()
        member_service = Member(db_manager)
        payment_service = Payment(db_manager)
        subscription_service = Subscription(db_manager)
        whatsapp_service = WhatsAppService()
        report_service = ReportService()
        
        logger.info("Starting Chama Management CLI...")
        print("\n" + "="*50)
        print("🏦 CHAMA MANAGEMENT SYSTEM CLI")
        print("="*50)
        
        while True:
            print("\nAvailable commands:")
            print("1. List members")
            print("2. Add member")
            print("3. Record payment")
            print("4. Generate report")
            print("5. Send WhatsApp message")
            print("6. View statistics")
            print("7. Exit")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                # List members
                members = member_service.get_all_members()
                if members:
                    print(f"\n📋 Total Members: {len(members)}")
                    print("-" * 80)
                    print(f"{'Name':<20} {'Phone':<15} {'Balance':<12} {'Last Payment':<12}")
                    print("-" * 80)
                    for member in members:
                        print(f"{member['name']:<20} {member['phone']:<15} "
                              f"KES {member['balance']:<8.0f} {member['last_payment'] or 'Never':<12}")
                else:
                    print("No members found.")
            
            elif choice == '2':
                # Add member
                print("\n➕ Add New Member")
                name = input("Enter member name: ").strip()
                phone = input("Enter phone number: ").strip()
                balance = float(input("Enter initial balance (default 0): ") or "0")
                
                if name and phone:
                    success = member_service.create_member(phone, name, balance)
                    if success:
                        print(f"✅ Member {name} added successfully!")
                    else:
                        print("❌ Member with this phone number already exists!")
                else:
                    print("❌ Name and phone number are required!")
            
            elif choice == '3':
                # Record payment
                print("\n💳 Record Payment")
                members = member_service.get_all_members()
                if not members:
                    print("❌ No members available. Add members first.")
                    continue
                
                print("Available members:")
                for i, member in enumerate(members, 1):
                    print(f"{i}. {member['name']} ({member['phone']})")
                
                try:
                    member_idx = int(input("Select member (number): ")) - 1
                    if 0 <= member_idx < len(members):
                        selected_member = members[member_idx]
                        amount = float(input("Enter payment amount: "))
                        payment_type = input("Payment type (contribution/subscription): ").strip() or "contribution"
                        description = input("Description (optional): ").strip()
                        
                        success = payment_service.add_payment(
                            selected_member['phone'], amount, payment_type, description
                        )
                        if success:
                            print(f"✅ Payment of KES {amount:,.0f} recorded for {selected_member['name']}!")
                        else:
                            print("❌ Failed to record payment!")
                    else:
                        print("❌ Invalid member selection!")
                except ValueError:
                    print("❌ Invalid input!")
            
            elif choice == '4':
                # Generate report
                print("\n📊 Generate Report")
                print("1. Member statement")
                print("2. Monthly report")
                print("3. Financial overview")
                
                report_choice = input("Select report type (1-3): ").strip()
                
                try:
                    if report_choice == '1':
                        members = member_service.get_all_members()
                        if not members:
                            print("❌ No members available.")
                            continue
                        
                        print("Available members:")
                        for i, member in enumerate(members, 1):
                            print(f"{i}. {member['name']} ({member['phone']})")
                        
                        member_idx = int(input("Select member (number): ")) - 1
                        if 0 <= member_idx < len(members):
                            selected_member = members[member_idx]
                            filename = report_service.generate_member_statement(selected_member['phone'])
                            print(f"✅ Member statement generated: {filename}")
                        else:
                            print("❌ Invalid member selection!")
                    
                    elif report_choice == '2':
                        year = int(input(f"Enter year (default {datetime.now().year}): ") or datetime.now().year)
                        month = int(input(f"Enter month (default {datetime.now().month}): ") or datetime.now().month)
                        filename = report_service.generate_monthly_report(year, month)
                        print(f"✅ Monthly report generated: {filename}")
                    
                    elif report_choice == '3':
                        filename = report_service.generate_financial_overview()
                        print(f"✅ Financial overview generated: {filename}")
                    
                    else:
                        print("❌ Invalid report type!")
                        
                except Exception as e:
                    print(f"❌ Error generating report: {str(e)}")
            
            elif choice == '5':
                # Send WhatsApp message
                print("\n💬 Send WhatsApp Message")
                members = member_service.get_all_members()
                if not members:
                    print("❌ No members available.")
                    continue
                
                print("Available members:")
                for i, member in enumerate(members, 1):
                    print(f"{i}. {member['name']} ({member['phone']})")
                print(f"{len(members) + 1}. Send to all members")
                
                try:
                    choice_idx = int(input("Select recipient: ")) - 1
                    message = input("Enter message: ").strip()
                    
                    if not message:
                        print("❌ Message cannot be empty!")
                        continue
                    
                    if choice_idx == len(members):
                        # Send to all members
                        sent_count = 0
                        for member in members:
                            success = whatsapp_service.send_message(member['phone'], message)
                            if success:
                                sent_count += 1
                        print(f"✅ Message sent to {sent_count}/{len(members)} members!")
                    
                    elif 0 <= choice_idx < len(members):
                        # Send to specific member
                        selected_member = members[choice_idx]
                        success = whatsapp_service.send_message(selected_member['phone'], message)
                        if success:
                            print(f"✅ Message sent to {selected_member['name']}!")
                        else:
                            print("❌ Failed to send message!")
                    else:
                        print("❌ Invalid selection!")
                        
                except ValueError:
                    print("❌ Invalid input!")
            
            elif choice == '6':
                # View statistics
                print("\n📈 System Statistics")
                members = member_service.get_all_members()
                payment_summary = payment_service.get_payment_summary()
                subscriptions = subscription_service.get_all_subscriptions()
                
                total_balance = sum(m['balance'] for m in members)
                active_subscriptions = len([s for s in subscriptions if s['status'] == 'active'])
                
                print("-" * 50)
                print(f"Total Members: {len(members)}")
                print(f"Active Subscriptions: {active_subscriptions}")
                print(f"Total Balance: KES {total_balance:,.2f}")
                print(f"Total Contributions: KES {payment_summary['total_contributions']:,.2f}")
                print(f"Monthly Contributions: KES {payment_summary['monthly_contributions']:,.2f}")
                print(f"Total Payments: {payment_summary['payment_count']}")
                print("-" * 50)
            
            elif choice == '7':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice! Please enter 1-7.")
                
    except KeyboardInterrupt:
        print("\n👋 CLI session ended.")
    except Exception as e:
        logger.error(f"Error in CLI: {str(e)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Chama Management System')
    parser.add_argument(
        '--mode', 
        choices=['flask', 'streamlit', 'cli', 'scheduler', 'all'],
        default='cli',
        help='Mode to run the application in'
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting Chama Management System in {args.mode} mode...")
    
    if args.mode == 'flask':
        run_flask_app()
    
    elif args.mode == 'streamlit':
        run_streamlit_dashboard()
    
    elif args.mode == 'cli':
        run_cli()
    
    elif args.mode == 'scheduler':
        run_scheduler()
    
    elif args.mode == 'all':
        # Run all services in separate threads
        threads = []
        
        # Flask app thread
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()
        threads.append(flask_thread)
        
        # Streamlit thread
        streamlit_thread = threading.Thread(target=run_streamlit_dashboard, daemon=True)
        streamlit_thread.start()
        threads.append(streamlit_thread)
        
        # Scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        threads.append(scheduler_thread)
        
        logger.info("All services started:")
        logger.info("  - Flask web app: http://localhost:5000")
        logger.info("  - Streamlit dashboard: http://localhost:8501")
        logger.info("  - Background scheduler: Running")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down all services...")

if __name__ == "__main__":
    main()