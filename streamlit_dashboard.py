import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from models import DatabaseManager, Member, Payment, Subscription
from service import ReportService, WhatsAppService

# Page configuration
st.set_page_config(
    page_title="Chama Management Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def init_services():
    db_manager = DatabaseManager()
    member_service = Member(db_manager)
    payment_service = Payment(db_manager)
    subscription_service = Subscription(db_manager)
    report_service = ReportService()
    whatsapp_service = WhatsAppService()
    
    return {
        'db_manager': db_manager,
        'member_service': member_service,
        'payment_service': payment_service,
        'subscription_service': subscription_service,
        'report_service': report_service,
        'whatsapp_service': whatsapp_service
    }

services = init_services()

# Sidebar navigation
st.sidebar.title("🏦 Chama Manager")
st.sidebar.markdown("---")

page = st.sidebar.selectbox(
    "Navigate to:",
    ["Dashboard", "Members", "Payments", "Reports", "WhatsApp Bot", "Settings"]
)

# Dashboard Page
if page == "Dashboard":
    st.title("📊 Dashboard")
    st.markdown("Overview of your Chama's financial activity")
    
    # Get data
    members = services['member_service'].get_all_members()
    payment_summary = services['payment_service'].get_payment_summary()
    recent_payments = services['payment_service'].get_payments()[:10]
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Members",
            value=len(members),
            delta="2 this month"
        )
    
    with col2:
        total_balance = sum(m['balance'] for m in members)
        st.metric(
            label="Total Savings",
            value=f"KES {total_balance:,.0f}",
            delta="15% from last month"
        )
    
    with col3:
        st.metric(
            label="Monthly Contributions",
            value=f"KES {payment_summary['monthly_contributions']:,.0f}",
            delta="8% from last month"
        )
    
    with col4:
        avg_contribution = payment_summary['total_contributions'] / max(len(members), 1)
        st.metric(
            label="Avg. Contribution",
            value=f"KES {avg_contribution:,.0f}",
            delta="Per member"
        )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Payments")
        if recent_payments:
            df_payments = pd.DataFrame(recent_payments)
            fig = px.bar(
                df_payments.head(5), 
                x='name', 
                y='amount',
                title="Last 5 Payments",
                color='amount',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No payments recorded yet")
    
    with col2:
        st.subheader("Member Balances")
        if members:
            df_members = pd.DataFrame(members)
            df_members = df_members.sort_values('balance', ascending=False).head(5)
            fig = px.pie(
                df_members, 
                values='balance', 
                names='name',
                title="Top 5 Contributors"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No members registered yet")

# Members Page
elif page == "Members":
    st.title("👥 Members Management")
    
    # Add new member form
    with st.expander("Add New Member"):
        with st.form("add_member"):
            col1, col2, col3 = st.columns(3)
            with col1:
                phone = st.text_input("Phone Number", placeholder="+254712345678")
            with col2:
                name = st.text_input("Full Name", placeholder="John Doe")
            with col3:
                balance = st.number_input("Initial Balance", min_value=0.0, value=0.0)
            
            if st.form_submit_button("Add Member"):
                if phone and name:
                    success = services['member_service'].create_member(phone, name, balance)
                    if success:
                        st.success(f"Member {name} added successfully!")
                        st.rerun()
                    else:
                        st.error("Member with this phone number already exists!")
                else:
                    st.error("Please fill in all required fields")
    
    # Display members
    members = services['member_service'].get_all_members()
    subscriptions = services['subscription_service'].get_all_subscriptions()
    
    if members:
        # Create DataFrame
        df_members = pd.DataFrame(members)
        
        # Add subscription info
        subscription_dict = {sub['phone']: sub['plan'] for sub in subscriptions}
        df_members['subscription'] = df_members['phone'].map(subscription_dict).fillna('None')
        
        # Display table
        st.dataframe(
            df_members[['name', 'phone', 'balance', 'last_payment', 'join_date', 'subscription']],
            use_container_width=True,
            column_config={
                'balance': st.column_config.NumberColumn(
                    'Balance (KES)',
                    format="%.2f"
                ),
                'last_payment': st.column_config.DateColumn('Last Payment'),
                'join_date': st.column_config.DateColumn('Join Date')
            }
        )
        
        # Member actions
        st.subheader("Member Actions")
        selected_phone = st.selectbox("Select Member", [m['phone'] for m in members])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("View Details"):
                member = services['member_service'].get_member(selected_phone)
                if member:
                    st.json(member)
        
        with col2:
            if st.button("Generate Statement"):
                try:
                    filename = services['report_service'].generate_member_statement(selected_phone)
                    st.success(f"Statement generated: {os.path.basename(filename)}")
                except Exception as e:
                    st.error(f"Error generating statement: {str(e)}")
        
        with col3:
            if st.button("Delete Member", type="secondary"):
                if st.checkbox("Confirm deletion"):
                    success = services['member_service'].delete_member(selected_phone)
                    if success:
                        st.success("Member deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete member")
    else:
        st.info("No members registered yet. Add your first member above!")

# Payments Page
elif page == "Payments":
    st.title("💳 Payments Management")
    
    # Add payment form
    with st.expander("Record New Payment"):
        members = services['member_service'].get_all_members()
        if members:
            with st.form("add_payment"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    selected_member = st.selectbox(
                        "Select Member", 
                        options=[f"{m['name']} ({m['phone']})" for m in members]
                    )
                with col2:
                    amount = st.number_input("Amount (KES)", min_value=0.01, value=100.0)
                with col3:
                    payment_type = st.selectbox("Payment Type", ["contribution", "subscription"])
                
                description = st.text_input("Description (optional)")
                
                if st.form_submit_button("Record Payment"):
                    # Extract phone from selection
                    phone = selected_member.split('(')[1].split(')')[0]
                    success = services['payment_service'].add_payment(phone, amount, payment_type, description)
                    if success:
                        st.success(f"Payment of KES {amount:,.2f} recorded successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to record payment")
        else:
            st.warning("No members available. Please add members first.")
    
    # Display payments
    payments = services['payment_service'].get_payments()
    
    if payments:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            payment_type_filter = st.selectbox("Filter by Type", ["All", "contribution", "subscription"])
        with col2:
            member_filter = st.selectbox("Filter by Member", ["All"] + [p['name'] for p in payments])
        with col3:
            date_range = st.date_input("Date Range", value=[])
        
        # Apply filters
        df_payments = pd.DataFrame(payments)
        
        if payment_type_filter != "All":
            df_payments = df_payments[df_payments['payment_type'] == payment_type_filter]
        
        if member_filter != "All":
            df_payments = df_payments[df_payments['name'] == member_filter]
        
        # Display filtered payments
        st.dataframe(
            df_payments[['name', 'phone', 'amount', 'payment_date', 'payment_type', 'description']],
            use_container_width=True,
            column_config={
                'amount': st.column_config.NumberColumn(
                    'Amount (KES)',
                    format="%.2f"
                ),
                'payment_date': st.column_config.DateColumn('Payment Date')
            }
        )
        
        # Payment statistics
        st.subheader("Payment Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_amount = df_payments['amount'].sum()
            st.metric("Total Amount", f"KES {total_amount:,.2f}")
        
        with col2:
            payment_count = len(df_payments)
            st.metric("Number of Payments", payment_count)
        
        with col3:
            avg_payment = df_payments['amount'].mean() if len(df_payments) > 0 else 0
            st.metric("Average Payment", f"KES {avg_payment:,.2f}")
        
        # Payment trends chart
        if len(df_payments) > 0:
            df_payments['payment_date'] = pd.to_datetime(df_payments['payment_date'])
            monthly_payments = df_payments.groupby(df_payments['payment_date'].dt.to_period('M'))['amount'].sum()
            
            fig = px.line(
                x=monthly_payments.index.astype(str),
                y=monthly_payments.values,
                title="Monthly Payment Trends",
                labels={'x': 'Month', 'y': 'Amount (KES)'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No payments recorded yet. Record your first payment above!")

# Reports Page
elif page == "Reports":
    st.title("📈 Reports & Analytics")
    
    # Report generation
    st.subheader("Generate Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Member Statement")
        members = services['member_service'].get_all_members()
        if members:
            selected_member = st.selectbox(
                "Select Member for Statement", 
                options=[f"{m['name']} ({m['phone']})" for m in members],
                key="statement_member"
            )
            if st.button("Generate Member Statement"):
                phone = selected_member.split('(')[1].split(')')[0]
                try:
                    filename = services['report_service'].generate_member_statement(phone)
                    st.success(f"Statement generated: {os.path.basename(filename)}")
                    
                    # Provide download link
                    with open(filename, "rb") as file:
                        st.download_button(
                            label="Download Statement",
                            data=file.read(),
                            file_name=os.path.basename(filename),
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error generating statement: {str(e)}")
    
    with col2:
        st.markdown("### Monthly Report")
        col_month, col_year = st.columns(2)
        with col_month:
            month = st.selectbox("Month", range(1, 13), index=datetime.now().month - 1)
        with col_year:
            year = st.selectbox("Year", range(2020, 2030), index=datetime.now().year - 2020)
        
        if st.button("Generate Monthly Report"):
            try:
                filename = services['report_service'].generate_monthly_report(year, month)
                st.success(f"Monthly report generated: {os.path.basename(filename)}")
                
                with open(filename, "rb") as file:
                    st.download_button(
                        label="Download Monthly Report",
                        data=file.read(),
                        file_name=os.path.basename(filename),
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
    
    # Financial Overview
    st.subheader("Financial Overview")
    if st.button("Generate Financial Overview"):
        try:
            filename = services['report_service'].generate_financial_overview()
            st.success(f"Financial overview generated: {os.path.basename(filename)}")
            
            with open(filename, "rb") as file:
                st.download_button(
                    label="Download Financial Overview",
                    data=file.read(),
                    file_name=os.path.basename(filename),
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Error generating overview: {str(e)}")
    
    # Export data
    st.subheader("Export Data")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Members to CSV"):
            try:
                filename = services['report_service'].export_to_csv('members')
                st.success(f"Members exported: {os.path.basename(filename)}")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col2:
        if st.button("Export Payments to CSV"):
            try:
                filename = services['report_service'].export_to_csv('payments')
                st.success(f"Payments exported: {os.path.basename(filename)}")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col3:
        if st.button("Export Subscriptions to CSV"):
            try:
                filename = services['report_service'].export_to_csv('subscriptions')
                st.success(f"Subscriptions exported: {os.path.basename(filename)}")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")

# WhatsApp Bot Page
elif page == "WhatsApp Bot":
    st.title("💬 WhatsApp Bot")
    
    st.markdown("""
    ### WhatsApp Bot Commands
    
    The bot supports the following commands:
    
    - **REGISTER <name>** - Register as a new member
    - **PAY <amount>** - Record a payment contribution
    - **BALANCE** - Check current balance
    - **SUBSCRIBE** - Subscribe to basic plan
    - **UPGRADE** - Learn about premium features
    - **REPORT** - Generate PDF report (Premium only)
    - **HELP** - Show available commands
    """)
    
    # Bot simulator
    st.subheader("Bot Simulator")
    
    members = services['member_service'].get_all_members()
    if members:
        selected_phone = st.selectbox(
            "Simulate as member:", 
            options=[f"{m['name']} ({m['phone']})" for m in members]
        )
        
        message = st.text_input("Enter WhatsApp message:")
        
        if st.button("Send Message"):
            if message:
                phone = selected_phone.split('(')[1].split(')')[0]
                response = services['whatsapp_service'].process_incoming_message(f"whatsapp:{phone}", message)
                
                st.markdown("**Bot Response:**")
                st.info(response)
    
    # Send reminders
    st.subheader("Send Payment Reminders")
    if st.button("Send Reminders to All Members"):
        try:
            services['whatsapp_service'].send_payment_reminders()
            st.success("Payment reminders sent to all active members!")
        except Exception as e:
            st.error(f"Failed to send reminders: {str(e)}")

# Settings Page
elif page == "Settings":
    st.title("⚙️ Settings")
    
    st.subheader("Twilio Configuration")
    
    with st.form("twilio_settings"):
        account_sid = st.text_input("Twilio Account SID", type="password")
        auth_token = st.text_input("Twilio Auth Token", type="password")
        phone_number = st.text_input("WhatsApp Business Number", placeholder="whatsapp:+14155238886")
        
        if st.form_submit_button("Save Twilio Settings"):
            # In a real app, you would save these to a config file or database
            st.success("Twilio settings saved successfully!")
    
    st.subheader("Subscription Plans")
    
    plans_data = [
        {"Plan": "Basic", "Price": "KES 100/month", "Features": "WhatsApp Bot, Basic Reports, Payment Tracking"},
        {"Plan": "Premium", "Price": "KES 300/month", "Features": "All Basic + PDF Reports, SMS Reminders, Advanced Analytics"}
    ]
    
    st.table(plans_data)
    
    st.subheader("Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Backup Database"):
            st.info("Database backup functionality would be implemented here")
    
    with col2:
        if st.button("Reset Database", type="secondary"):
            if st.checkbox("I understand this will delete all data"):
                st.warning("Database reset functionality would be implemented here")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Chama Management System v1.0**")
st.sidebar.markdown("Built with Python & Streamlit")