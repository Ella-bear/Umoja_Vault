from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any
import pandas as pd
from models import DatabaseManager, Member, Payment, Subscription

class ReportService:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.member_service = Member(self.db_manager)
        self.payment_service = Payment(self.db_manager)
        self.subscription_service = Subscription(self.db_manager)
        
        # Create reports directory if it doesn't exist
        self.reports_dir = 'reports'
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_member_statement(self, phone: str) -> str:
        """Generate individual member statement PDF"""
        member = self.member_service.get_member(phone)
        if not member:
            raise ValueError("Member not found")
        
        payments = self.payment_service.get_payments(phone)
        subscription = self.subscription_service.get_subscription(phone)
        
        filename = f"{self.reports_dir}/member_statement_{phone}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("CHAMA MEMBER STATEMENT", title_style))
        story.append(Spacer(1, 20))
        
        # Member Information
        member_info = [
            ['Member Name:', member['name']],
            ['Phone Number:', member['phone']],
            ['Join Date:', member['join_date']],
            ['Current Balance:', f"KES {member['balance']:,.2f}"],
            ['Last Payment:', member['last_payment'] or 'No payments yet'],
            ['Subscription Plan:', subscription['plan'].title() if subscription else 'None']
        ]
        
        member_table = Table(member_info, colWidths=[2*inch, 3*inch])
        member_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(member_table)
        story.append(Spacer(1, 30))
        
        # Payment History
        story.append(Paragraph("PAYMENT HISTORY", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if payments:
            payment_data = [['Date', 'Amount (KES)', 'Type', 'Description']]
            for payment in payments:
                payment_data.append([
                    payment['payment_date'],
                    f"{payment['amount']:,.2f}",
                    payment['payment_type'].title(),
                    payment['description'] or '-'
                ])
            
            payment_table = Table(payment_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
            payment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(payment_table)
        else:
            story.append(Paragraph("No payment history available.", styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 50))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=1
        )
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
        
        doc.build(story)
        return filename
    
    def generate_monthly_report(self, year: int = None, month: int = None) -> str:
        """Generate monthly summary report"""
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        filename = f"{self.reports_dir}/monthly_report_{year}_{month:02d}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"MONTHLY CHAMA REPORT - {datetime(year, month, 1).strftime('%B %Y')}", title_style))
        story.append(Spacer(1, 20))
        
        # Summary Statistics
        summary_data = self._get_monthly_summary(year, month)
        
        summary_info = [
            ['Total Members:', str(summary_data['total_members'])],
            ['Active Members:', str(summary_data['active_members'])],
            ['Monthly Contributions:', f"KES {summary_data['monthly_contributions']:,.2f}"],
            ['Total Balance:', f"KES {summary_data['total_balance']:,.2f}"],
            ['Average Contribution:', f"KES {summary_data['avg_contribution']:,.2f}"]
        ]
        
        summary_table = Table(summary_info, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Top Contributors
        story.append(Paragraph("TOP CONTRIBUTORS", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        top_contributors = self._get_top_contributors(year, month)
        if top_contributors:
            contrib_data = [['Rank', 'Name', 'Phone', 'Amount (KES)']]
            for i, contrib in enumerate(top_contributors, 1):
                contrib_data.append([
                    str(i),
                    contrib['name'],
                    contrib['phone'],
                    f"{contrib['amount']:,.2f}"
                ])
            
            contrib_table = Table(contrib_data, colWidths=[0.8*inch, 2*inch, 1.5*inch, 1.5*inch])
            contrib_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(contrib_table)
        
        doc.build(story)
        return filename
    
    def generate_financial_overview(self) -> str:
        """Generate comprehensive financial overview"""
        filename = f"{self.reports_dir}/financial_overview_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("CHAMA FINANCIAL OVERVIEW", title_style))
        story.append(Spacer(1, 20))
        
        # Overall Statistics
        overall_stats = self._get_overall_statistics()
        
        stats_info = [
            ['Total Members:', str(overall_stats['total_members'])],
            ['Total Contributions:', f"KES {overall_stats['total_contributions']:,.2f}"],
            ['Total Balance:', f"KES {overall_stats['total_balance']:,.2f}"],
            ['Average Member Balance:', f"KES {overall_stats['avg_balance']:,.2f}"],
            ['Total Payments:', str(overall_stats['total_payments'])]
        ]
        
        stats_table = Table(stats_info, colWidths=[2.5*inch, 2.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 30))
        
        # Monthly Trends (last 6 months)
        story.append(Paragraph("MONTHLY CONTRIBUTION TRENDS", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        monthly_trends = self._get_monthly_trends()
        if monthly_trends:
            trend_data = [['Month', 'Contributions (KES)', 'Number of Payments']]
            for trend in monthly_trends:
                trend_data.append([
                    trend['month'],
                    f"{trend['amount']:,.2f}",
                    str(trend['count'])
                ])
            
            trend_table = Table(trend_data, colWidths=[2*inch, 2*inch, 2*inch])
            trend_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(trend_table)
        
        doc.build(story)
        return filename
    
    def _get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly summary statistics"""
        # Get all members
        members = self.member_service.get_all_members()
        total_members = len(members)
        active_members = len([m for m in members if m['status'] == 'active'])
        total_balance = sum(m['balance'] for m in members)
        
        # Get monthly payments
        query = '''
            SELECT SUM(amount), COUNT(*) FROM payments 
            WHERE payment_type = 'contribution' 
            AND strftime('%Y', payment_date) = ? 
            AND strftime('%m', payment_date) = ?
        '''
        result = self.db_manager.execute_query(query, (str(year), f"{month:02d}"))
        monthly_contributions = result[0][0] if result[0][0] else 0
        payment_count = result[0][1] if result[0][1] else 0
        
        avg_contribution = monthly_contributions / max(payment_count, 1)
        
        return {
            'total_members': total_members,
            'active_members': active_members,
            'monthly_contributions': monthly_contributions,
            'total_balance': total_balance,
            'avg_contribution': avg_contribution
        }
    
    def _get_top_contributors(self, year: int, month: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top contributors for a specific month"""
        query = '''
            SELECT m.name, m.phone, SUM(p.amount) as total_amount
            FROM payments p
            JOIN members m ON p.phone = m.phone
            WHERE p.payment_type = 'contribution'
            AND strftime('%Y', p.payment_date) = ?
            AND strftime('%m', p.payment_date) = ?
            GROUP BY m.phone, m.name
            ORDER BY total_amount DESC
            LIMIT ?
        '''
        results = self.db_manager.execute_query(query, (str(year), f"{month:02d}", limit))
        
        return [
            {
                'name': row[0],
                'phone': row[1],
                'amount': row[2]
            }
            for row in results
        ]
    
    def _get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        members = self.member_service.get_all_members()
        payment_summary = self.payment_service.get_payment_summary()
        
        total_members = len(members)
        total_balance = sum(m['balance'] for m in members)
        avg_balance = total_balance / max(total_members, 1)
        
        return {
            'total_members': total_members,
            'total_contributions': payment_summary['total_contributions'],
            'total_balance': total_balance,
            'avg_balance': avg_balance,
            'total_payments': payment_summary['payment_count']
        }
    
    def _get_monthly_trends(self, months: int = 6) -> List[Dict[str, Any]]:
        """Get monthly contribution trends"""
        query = '''
            SELECT strftime('%Y-%m', payment_date) as month,
                   SUM(amount) as total_amount,
                   COUNT(*) as payment_count
            FROM payments
            WHERE payment_type = 'contribution'
            AND payment_date >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', payment_date)
            ORDER BY month DESC
        '''
        results = self.db_manager.execute_query(query)
        
        return [
            {
                'month': row[0],
                'amount': row[1],
                'count': row[2]
            }
            for row in results
        ]
    
    def export_to_csv(self, data_type: str) -> str:
        """Export data to CSV format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if data_type == 'members':
            members = self.member_service.get_all_members()
            df = pd.DataFrame(members)
            filename = f"{self.reports_dir}/members_export_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
        elif data_type == 'payments':
            payments = self.payment_service.get_payments()
            df = pd.DataFrame(payments)
            filename = f"{self.reports_dir}/payments_export_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
        elif data_type == 'subscriptions':
            subscriptions = self.subscription_service.get_all_subscriptions()
            df = pd.DataFrame(subscriptions)
            filename = f"{self.reports_dir}/subscriptions_export_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
        else:
            raise ValueError("Invalid data type. Choose from: members, payments, subscriptions")
        
        return filename

class WhatsAppService:
    def __init__(self):
        pass

    def send_payment_reminders(self):
        # TODO: Implement actual WhatsApp reminder logic
        print("Sending payment reminders to all members...")
        # Example: You can integrate Twilio or another service here
        return True