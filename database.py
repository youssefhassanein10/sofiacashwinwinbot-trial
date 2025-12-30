import sqlite3
from datetime import datetime
import config

class Database:
    def __init__(self, db_name="database.db"):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0,
                total_deposited REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                referral_id TEXT UNIQUE,
                referrer_id INTEGER,
                referrals_count INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Транзакции
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT, -- 'deposit', 'withdraw', 'bonus', 'referral'
                amount REAL,
                status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'rejected', 'cancelled'
                payment_method TEXT,
                details TEXT,
                admin_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Выводы (отдельная таблица для лучшей структуры)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                user_id INTEGER,
                amount REAL,
                fee REAL DEFAULT 0,
                net_amount REAL,
                payment_method TEXT,
                requisites TEXT,
                status TEXT DEFAULT 'pending',
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions (id)
            )
        ''')
        
        # Реферальные выплаты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referral_id INTEGER,
                amount REAL,
                transaction_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referral_id) REFERENCES users (user_id)
            )
        ''')
        
        # Настройки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    def create_user(self, user_id, username, first_name, last_name, referrer_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Генерируем реферальный ID
        referral_id = f"REF{user_id}{datetime.now().strftime('%m%d')}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_id, referrer_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_id, referrer_id))
        
        # Если есть реферер, увеличиваем его счетчик
        if referrer_id:
            cursor.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referrer_id,))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def update_balance(self, user_id, amount, operation='deposit'):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if operation == 'deposit':
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, 
                    total_deposited = total_deposited + ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, amount, user_id))
        elif operation == 'withdraw':
            cursor.execute('''
                UPDATE users 
                SET balance = balance - ?, 
                    total_withdrawn = total_withdrawn + ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, amount, user_id))
        elif operation == 'bonus':
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, user_id))
        
        conn.commit()
        conn.close()
    
    # ===== ТРАНЗАКЦИИ =====
    def create_transaction(self, user_id, trans_type, amount, payment_method=None, details=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions 
            (user_id, type, amount, payment_method, details) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, trans_type, amount, payment_method, details))
        
        trans_id = cursor.lastrowid
        
        # Если это пополнение, создаем запись на вывод
        if trans_type == 'withdraw':
            fee = amount * (config.WITHDRAW_FEE / 100)
            net_amount = amount - fee
            
            cursor.execute('''
                INSERT INTO withdrawals 
                (transaction_id, user_id, amount, fee, net_amount, payment_method) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (trans_id, user_id, amount, fee, net_amount, payment_method))
        
        conn.commit()
        conn.close()
        return trans_id
    
    def get_user_transactions(self, user_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        transactions = cursor.fetchall()
        conn.close()
        return transactions
    
    def get_pending_withdrawals(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, u.username, u.user_id 
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.status = 'pending'
            ORDER BY w.created_at
        ''')
        withdrawals = cursor.fetchall()
        conn.close()
        return withdrawals
    
    # ===== СТАТИСТИКА =====
    def get_bot_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE("now")')
        active_today = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "deposit" AND status = "completed"')
        total_deposits = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "withdraw" AND status = "completed"')
        total_withdrawals = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE status = "pending"')
        pending_transactions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'active_today': active_today,
            'total_balance': total_balance,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'pending_transactions': pending_transactions
        }
    
    # ===== АДМИН ФУНКЦИИ =====
    def get_all_users(self, limit=100, offset=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, balance, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        users = cursor.fetchall()
        conn.close()
        return users
    
    def update_transaction_status(self, trans_id, status, admin_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE transactions 
            SET status = ?, admin_id = ?, completed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, admin_id, trans_id))
        
        # Если это вывод, обновляем и таблицу withdrawals
        cursor.execute('SELECT type FROM transactions WHERE id = ?', (trans_id,))
        trans_type = cursor.fetchone()[0]
        
        if trans_type == 'withdraw':
            cursor.execute('''
                UPDATE withdrawals 
                SET status = ?, processed_at = CURRENT_TIMESTAMP 
                WHERE transaction_id = ?
            ''', (status, trans_id))
        
        conn.commit()
        conn.close()
    
    def search_users(self, query):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE user_id = ? OR username LIKE ? OR referral_id = ?
        ''', (query if query.isdigit() else 0, f"%{query}%", query))
        
        users = cursor.fetchall()
        conn.close()
        return users
