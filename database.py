import sqlite3
import datetime
from config import Config

class Database:
    def __init__(self, db_name='winwin_bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица депозитов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'ожидает оплаты',
                payment_method TEXT,
                payment_details TEXT,
                receipt_file_id TEXT,
                admin_message_id TEXT,
                user_message_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                admin_id INTEGER
            )
        ''')
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0,
                total_deposited REAL DEFAULT 0,
                deposits_count INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                reference_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_deposit(self, user_id, username, full_name, amount, payment_method):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO deposits (user_id, username, full_name, amount, payment_method, status)
            VALUES (?, ?, ?, ?, ?, 'ожидает оплаты')
        ''', (user_id, username, full_name, amount, payment_method))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_deposit(self, deposit_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deposits WHERE id = ?', (deposit_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def update_deposit(self, deposit_id, **kwargs):
        cursor = self.conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(deposit_id)
        
        cursor.execute(f'UPDATE deposits SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
    
    def add_or_update_user(self, user_id, username, full_name):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, full_name))
        else:
            cursor.execute('''
                UPDATE users 
                SET username = ?, full_name = ?, last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username, full_name, user_id))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def update_user_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, 
                total_deposited = total_deposited + ?,
                deposits_count = deposits_count + 1
            WHERE user_id = ?
        ''', (amount, amount, user_id))
        self.conn.commit()
    
    def get_pending_deposits(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM deposits 
            WHERE status = 'ожидает оплаты'
            ORDER BY created_at DESC
        ''')
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_processing_deposits(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM deposits 
            WHERE status = 'в обработке'
            ORDER BY created_at DESC
        ''')
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_user_deposits(self, user_id, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM deposits 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_stats(self):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) as total_deposits FROM deposits')
        total_deposits = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) as total_amount FROM deposits WHERE status = "завершен"')
        total_amount = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) as pending_deposits FROM deposits WHERE status = "ожидает оплаты"')
        pending_deposits = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_deposits': total_deposits,
            'total_amount': total_amount,
            'pending_deposits': pending_deposits
        }
