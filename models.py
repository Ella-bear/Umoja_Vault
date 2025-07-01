import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

class DatabaseManager:
    def __init__(self, db_path: str = 'chama.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                phone TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                last_payment DATE,
                join_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                phone TEXT PRIMARY KEY,
                plan TEXT NOT NULL,
                start_date DATE DEFAULT CURRENT_DATE,
                end_date DATE,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (phone) REFERENCES members (phone)
            )
        ''')
        
        # Payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date DATE DEFAULT CURRENT_DATE,
                payment_type TEXT DEFAULT 'contribution',
                description TEXT,
                FOREIGN KEY (phone) REFERENCES members (phone)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a SELECT query and return results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return affected_rows

class Member:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_member(self, phone: str, name: str, initial_balance: float = 0.0) -> bool:
        """Create a new member"""
        try:
            query = '''
                INSERT INTO members (phone, name, balance, join_date)
                VALUES (?, ?, ?, ?)
            '''
            params = (phone, name, initial_balance, datetime.now().strftime('%Y-%m-%d'))
            self.db.execute_update(query, params)
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_member(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get member by phone number"""
        query = '''
            SELECT phone, name, balance, last_payment, join_date, status
            FROM members WHERE phone = ?
        '''
        result = self.db.execute_query(query, (phone,))
        if result:
            row = result[0]
            return {
                'phone': row[0],
                'name': row[1],
                'balance': row[2],
                'last_payment': row[3],
                'join_date': row[4],
                'status': row[5]
            }
        return None
    
    def get_all_members(self) -> List[Dict[str, Any]]:
        """Get all members"""
        query = '''
            SELECT phone, name, balance, last_payment, join_date, status
            FROM members ORDER BY name
        '''
        results = self.db.execute_query(query)
        return [
            {
                'phone': row[0],
                'name': row[1],
                'balance': row[2],
                'last_payment': row[3],
                'join_date': row[4],
                'status': row[5]
            }
            for row in results
        ]
    
    def update_member(self, phone: str, **kwargs) -> bool:
        """Update member information"""
        if not kwargs:
            return False
        
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        query = f"UPDATE members SET {set_clause} WHERE phone = ?"
        params = tuple(kwargs.values()) + (phone,)
        
        affected_rows = self.db.execute_update(query, params)
        return affected_rows > 0
    
    def delete_member(self, phone: str) -> bool:
        """Delete a member and all related records"""
        try:
            # Delete related records first
            self.db.execute_update("DELETE FROM payments WHERE phone = ?", (phone,))
            self.db.execute_update("DELETE FROM subscriptions WHERE phone = ?", (phone,))
            
            # Delete member
            affected_rows = self.db.execute_update("DELETE FROM members WHERE phone = ?", (phone,))
            return affected_rows > 0
        except Exception:
            return False

class Payment:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_payment(self, phone: str, amount: float, payment_type: str = 'contribution', 
                   description: str = '') -> bool:
        """Add a new payment"""
        try:
            # Add payment record
            query = '''
                INSERT INTO payments (phone, amount, payment_type, description)
                VALUES (?, ?, ?, ?)
            '''
            params = (phone, amount, payment_type, description)
            self.db.execute_update(query, params)
            
            # Update member balance if it's a contribution
            if payment_type == 'contribution':
                update_query = '''
                    UPDATE members 
                    SET balance = balance + ?, last_payment = ?
                    WHERE phone = ?
                '''
                update_params = (amount, datetime.now().strftime('%Y-%m-%d'), phone)
                self.db.execute_update(update_query, update_params)
            
            return True
        except Exception:
            return False
    
    def get_payments(self, phone: str = None) -> List[Dict[str, Any]]:
        """Get payments, optionally filtered by phone"""
        if phone:
            query = '''
                SELECT p.id, p.phone, m.name, p.amount, p.payment_date, 
                       p.payment_type, p.description
                FROM payments p
                JOIN members m ON p.phone = m.phone
                WHERE p.phone = ?
                ORDER BY p.payment_date DESC
            '''
            params = (phone,)
        else:
            query = '''
                SELECT p.id, p.phone, m.name, p.amount, p.payment_date, 
                       p.payment_type, p.description
                FROM payments p
                JOIN members m ON p.phone = m.phone
                ORDER BY p.payment_date DESC
            '''
            params = ()
        
        results = self.db.execute_query(query, params)
        return [
            {
                'id': row[0],
                'phone': row[1],
                'name': row[2],
                'amount': row[3],
                'payment_date': row[4],
                'payment_type': row[5],
                'description': row[6]
            }
            for row in results
        ]
    
    def get_payment_summary(self) -> Dict[str, Any]:
        """Get payment summary statistics"""
        # Total contributions
        total_query = '''
            SELECT SUM(amount) FROM payments WHERE payment_type = 'contribution'
        '''
        total_result = self.db.execute_query(total_query)
        total_contributions = total_result[0][0] if total_result[0][0] else 0
        
        # Monthly contributions
        monthly_query = '''
            SELECT SUM(amount) FROM payments 
            WHERE payment_type = 'contribution' 
            AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
        '''
        monthly_result = self.db.execute_query(monthly_query)
        monthly_contributions = monthly_result[0][0] if monthly_result[0][0] else 0
        
        # Payment count
        count_query = '''
            SELECT COUNT(*) FROM payments WHERE payment_type = 'contribution'
        '''
        count_result = self.db.execute_query(count_query)
        payment_count = count_result[0][0] if count_result else 0
        
        return {
            'total_contributions': total_contributions,
            'monthly_contributions': monthly_contributions,
            'payment_count': payment_count
        }

class Subscription:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_subscription(self, phone: str, plan: str) -> bool:
        """Create or update a subscription"""
        try:
            query = '''
                INSERT OR REPLACE INTO subscriptions (phone, plan, start_date, status)
                VALUES (?, ?, ?, 'active')
            '''
            params = (phone, plan, datetime.now().strftime('%Y-%m-%d'))
            self.db.execute_update(query, params)
            return True
        except Exception:
            return False
    
    def get_subscription(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get subscription by phone number"""
        query = '''
            SELECT phone, plan, start_date, end_date, status
            FROM subscriptions WHERE phone = ?
        '''
        result = self.db.execute_query(query, (phone,))
        if result:
            row = result[0]
            return {
                'phone': row[0],
                'plan': row[1],
                'start_date': row[2],
                'end_date': row[3],
                'status': row[4]
            }
        return None
    
    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions"""
        query = '''
            SELECT s.phone, m.name, s.plan, s.start_date, s.end_date, s.status
            FROM subscriptions s
            JOIN members m ON s.phone = m.phone
            ORDER BY s.start_date DESC
        '''
        results = self.db.execute_query(query)
        return [
            {
                'phone': row[0],
                'name': row[1],
                'plan': row[2],
                'start_date': row[3],
                'end_date': row[4],
                'status': row[5]
            }
            for row in results
        ]