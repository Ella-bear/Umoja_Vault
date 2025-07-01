from flask import Flask, request, jsonify, render_template, send_file, flash, redirect, url_for
from twilio.twiml.messaging_response import MessagingResponse
import os
from datetime import datetime
import logging
from config import Config
from services.whatsapp_service import WhatsAppService
from services.report_service import ReportService
from database.models import DatabaseManager, Member, Payment, Subscription

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize services
whatsapp_service = WhatsAppService()
report_service = ReportService()
db_manager = DatabaseManager()
member_service = Member(db_manager)
payment_service = Payment(db_manager)
subscription_service = Subscription(db_manager)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        # Get summary statistics
        members = member_service.get_all_members()
        payment_summary = payment_service.get_payment_summary()
        recent_payments = payment_service.get_payments()[:5]  # Last 5 payments
        
        stats = {
            'total_members': len(members),
            'total_balance': sum(m['balance'] for m in members),
            'monthly_contributions': payment_summary['monthly_contributions'],
            'total_contributions': payment_summary['total_contributions']
        }
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_payments=recent_payments,
                             members=members[:3])  # Top 3 members
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', stats={}, recent_payments=[], members=[])

@app.route('/members')
def members_page():
    """Members management page"""
    try:
        members = member_service.get_all_members()
        subscriptions = subscription_service.get_all_subscriptions()
        
        # Add subscription info to members
        for member in members:
            member['subscription'] = next(
                (sub for sub in subscriptions if sub['phone'] == member['phone']), 
                None
            )
        
        return render_template('members.html', members=members)
    except Exception as e:
        logger.error(f"Members page error: {str(e)}")
        flash('Error loading members', 'error')
        return render_template('members.html', members=[])

@app.route('/payments')
def payments_page():
    """Payments page"""
    try:
        payments = payment_service.get_payments()
        members = member_service.get_all_members()
        return render_template('payments.html', payments=payments, members=members)
    except Exception as e:
        logger.error(f"Payments page error: {str(e)}")
        flash('Error loading payments', 'error')
        return render_template('payments.html', payments=[], members=[])

@app.route('/reports')
def reports_page():
    """Reports page"""
    try:
        members = member_service.get_all_members()
        payment_summary = payment_service.get_payment_summary()
        return render_template('reports.html', members=members, payment_summary=payment_summary)
    except Exception as e:
        logger.error(f"Reports page error: {str(e)}")
        flash('Error loading reports', 'error')
        return render_template('reports.html', members=[], payment_summary={})

# API Routes
@app.route('/api/members', methods=['GET', 'POST'])
def api_members():
    """Members API endpoint"""
    if request.method == 'GET':
        members = member_service.get_all_members()
        return jsonify(members)
    
    elif request.method == 'POST':
        data = request.get_json()
        success = member_service.create_member(
            data['phone'], 
            data['name'], 
            data.get('balance', 0)
        )
        if success:
            return jsonify({'success': True, 'message': 'Member created successfully'})
        else:
            return jsonify({'success': False, 'message': 'Member already exists'}), 400

@app.route('/api/members/<phone>', methods=['PUT', 'DELETE'])
def api_member_detail(phone):
    """Individual member API endpoint"""
    if request.method == 'PUT':
        data = request.get_json()
        success = member_service.update_member(phone, **data)
        if success:
            return jsonify({'success': True, 'message': 'Member updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Member not found'}), 404
    
    elif request.method == 'DELETE':
        success = member_service.delete_member(phone)
        if success:
            return jsonify({'success': True, 'message': 'Member deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Member not found'}), 404

@app.route('/api/payments', methods=['GET', 'POST'])
def api_payments():
    """Payments API endpoint"""
    if request.method == 'GET':
        phone = request.args.get('phone')
        payments = payment_service.get_payments(phone)
        return jsonify(payments)
    
    elif request.method == 'POST':
        data = request.get_json()
        success = payment_service.add_payment(
            data['phone'],
            data['amount'],
            data.get('payment_type', 'contribution'),
            data.get('description', '')
        )
        if success:
            return jsonify({'success': True, 'message': 'Payment recorded successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to record payment'}), 400

@app.route('/api/reports/generate', methods=['POST'])
def api_generate_report():
    """Generate report API endpoint"""
    data = request.get_json()
    report_type = data.get('type')
    
    try:
        if report_type == 'member_statement':
            phone = data.get('phone')
            filename = report_service.generate_member_statement(phone)
        elif report_type == 'monthly':
            year = data.get('year', datetime.now().year)
            month = data.get('month', datetime.now().month)
            filename = report_service.generate_monthly_report(year, month)
        elif report_type == 'financial_overview':
            filename = report_service.generate_financial_overview()
        else:
            return jsonify({'success': False, 'message': 'Invalid report type'}), 400
        
        return jsonify({
            'success': True, 
            'message': 'Report generated successfully',
            'filename': os.path.basename(filename)
        })
    
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/reports/download/<filename>')
def api_download_report(filename):
    """Download report file"""
    try:
        file_path = os.path.join('reports', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """WhatsApp webhook endpoint"""
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        # Process the message
        response_text = whatsapp_service.process_incoming_message(from_number, incoming_msg)
        
        # Create Twilio response
        resp = MessagingResponse()
        resp.message(response_text)
        
        logger.info(f"WhatsApp message processed: {from_number} -> {incoming_msg}")
        return str(resp)
    
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, there was an error processing your request. Please try again.")
        return str(resp)

@app.route('/api/whatsapp/send_reminders', methods=['POST'])
def api_send_reminders():
    """Send payment reminders to all members"""
    try:
        whatsapp_service.send_payment_reminders()
        return jsonify({'success': True, 'message': 'Reminders sent successfully'})
    except Exception as e:
        logger.error(f"Send reminders error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)