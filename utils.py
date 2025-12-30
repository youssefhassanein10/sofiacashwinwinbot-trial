from datetime import datetime
import config

def format_balance(amount):
    """Форматирование суммы с разделителями"""
    return f"{amount:,.2f}₽".replace(',', ' ').replace('.', ',')

def format_date(date_str):
    """Форматирование даты"""
    if isinstance(date_str, str):
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    else:
        dt = date_str
    
    return dt.strftime("%d.%m.%Y %H:%M")

def validate_amount(amount, min_amount, max_amount):
    """Проверка суммы на корректность"""
    try:
        amount = float(str(amount).replace(',', '.'))
        
        if amount < min_amount:
            return False, f"Минимальная сумма: {format_balance(min_amount)}"
        
        if amount > max_amount:
            return False, f"Максимальная сумма: {format_balance(max_amount)}"
        
        return True, amount
    except ValueError:
        return False, "Некорректная сумма"

def get_transaction_status_emoji(status):
    """Получение emoji для статуса транзакции"""
    status_emojis = {
        'pending': '🕐',
        'completed': '✅',
        'rejected': '❌',
        'cancelled': '🚫'
    }
    return status_emojis.get(status, '❓')

def format_transaction(trans):
    """Форматирование информации о транзакции"""
    trans_id, user_id, trans_type, amount, status, method, details, admin_id, created_at, completed_at = trans
    
    type_text = {
        'deposit': '📥 Пополнение',
        'withdraw': '📤 Вывод',
        'bonus': '🎁 Бонус',
        'referral': '👥 Реферал'
    }.get(trans_type, trans_type)
    
    method_text = config.PAYMENT_SYSTEMS.get(method, method or "Не указан")
    
    return (
        f"{get_transaction_status_emoji(status)} {type_text}\n"
        f"💵 Сумма: {format_balance(amount)}\n"
        f"💳 Способ: {method_text}\n"
        f"📅 Дата: {format_date(created_at)}\n"
        f"🆔 ID: {trans_id}"
    )

def calculate_withdraw_fee(amount):
    """Расчет комиссии на вывод"""
    fee = amount * (config.WITHDRAW_FEE / 100)
    net_amount = amount - fee
    return fee, net_amount

def generate_payment_details(payment_method, amount):
    """Генерация деталей для оплаты"""
    import random
    
    if payment_method == "qiwi":
        return {
            "phone": "+7**********",
            "comment": f"Оплата {amount}₽ | {random.randint(1000, 9999)}"
        }
    elif payment_method == "yoomoney":
        return {
            "wallet": "4100**********",
            "comment": f"Пополнение {amount}₽"
        }
    elif payment_method == "bank_card":
        return {
            "card": "2200**********",
            "bank": "Тинькофф"
        }
    elif payment_method == "crypto":
        return {
            "wallet": "T*******************",
            "network": "TRC20"
        }
    return {}
