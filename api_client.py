import hashlib
import requests
import logging
from datetime import datetime, timezone
from config import Config

logger = logging.getLogger(__name__)

class SofiaCashAPI:
    def __init__(self):
        self.config = Config
        self.base_url = self.config.API_BASE_URL
        self.timeout = 30
    
    def _calculate_confirm(self, param_value):
        """Расчет confirm строки (MD5(param:hash))"""
        data = f"{param_value}:{self.config.API_HASH}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _generate_balance_signature(self, dt_str):
        """Генерация подписи для получения баланса"""
        # SHA256(hash={0}&cashierpass={1}&dt={2})
        str_a = f"hash={self.config.API_HASH}&cashierpass={self.config.API_CASHIERPASS}&dt={dt_str}"
        hash_a = hashlib.sha256(str_a.encode()).hexdigest()
        
        # MD5(dt={0}&cashierpass={1}&cashdeskid={2})
        str_b = f"dt={dt_str}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
        hash_b = hashlib.md5(str_b.encode()).hexdigest()
        
        # SHA256(a + b)
        combined = hash_a + hash_b
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _generate_find_user_signature(self, user_id):
        """Генерация подписи для поиска пользователя"""
        # SHA256(hash={0}&userid={1}&cashdeskid={2})
        str_a = f"hash={self.config.API_HASH}&userid={user_id}&cashdeskid={self.config.API_CASHDESKID}"
        hash_a = hashlib.sha256(str_a.encode()).hexdigest()
        
        # MD5(userid={0}&cashierpass={1}&hash={2})
        str_b = f"userid={user_id}&cashierpass={self.config.API_CASHIERPASS}&hash={self.config.API_HASH}"
        hash_b = hashlib.md5(str_b.encode()).hexdigest()
        
        # SHA256(a + b)
        combined = hash_a + hash_b
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _generate_deposit_signature(self, user_id, amount, language="ru"):
        """Генерация подписи для пополнения"""
        # SHA256(hash={0}&lng={1}&UserId={2})
        str_a = f"hash={self.config.API_HASH}&lng={language}&UserId={user_id}"
        hash_a = hashlib.sha256(str_a.encode()).hexdigest()
        
        # MD5(summa={0}&cashierpass={1}&cashdeskid={2})
        str_b = f"summa={amount}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
        hash_b = hashlib.md5(str_b.encode()).hexdigest()
        
        # SHA256(a + b)
        combined = hash_a + hash_b
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _generate_payout_signature(self, user_id, code, language="ru"):
        """Генерация подписи для выплаты"""
        # SHA256(hash={0}&lng={1}&UserId={2})
        str_a = f"hash={self.config.API_HASH}&lng={language}&UserId={user_id}"
        hash_a = hashlib.sha256(str_a.encode()).hexdigest()
        
        # MD5(code={0}&cashierpass={1}&cashdeskid={2})
        str_b = f"code={code}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
        hash_b = hashlib.md5(str_b.encode()).hexdigest()
        
        # SHA256(a + b)
        combined = hash_a + hash_b
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get_balance(self):
        """Получение баланса кассы"""
        try:
            dt = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
            confirm = self._calculate_confirm(self.config.API_CASHDESKID)
            signature = self._generate_balance_signature(dt)
            
            url = f"{self.base_url}Cashdesk/{self.config.API_CASHDESKID}/Balance"
            params = {"confirm": confirm, "dt": dt}
            headers = {"sign": signature}
            
            logger.info(f"Запрос баланса: {url}")
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Баланс получен: {data}")
                return {
                    'success': True,
                    'balance': data.get('Balance', 0),
                    'limit': data.get('Limit', 0),
                    'available': data.get('Limit', 0) - data.get('Balance', 0)
                }
            else:
                logger.error(f"Ошибка баланса {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"Исключение при запросе баланса: {e}")
            return {'success': False, 'error': str(e)}
    
    def find_user(self, user_id):
        """Поиск игрока в системе Winwin"""
        try:
            confirm = self._calculate_confirm(user_id)
            signature = self._generate_find_user_signature(user_id)
            
            url = f"{self.base_url}Users/{user_id}"
            params = {
                "confirm": confirm,
                "cashdeskId": self.config.API_CASHDESKID
            }
            headers = {"sign": signature}
            
            logger.info(f"Поиск пользователя {user_id}")
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Пользователь найден: {data}")
                return {'success': True, 'data': data}
            else:
                logger.warning(f"Пользователь не найден: {response.status_code}")
                return {'success': False, 'error': 'Пользователь не найден'}
                
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя: {e}")
            return {'success': False, 'error': str(e)}
    
    def deposit_to_user(self, user_id, amount):
        """Пополнение счета игрока через SofiaCash"""
        try:
            confirm = self._calculate_confirm(user_id)
            signature = self._generate_deposit_signature(user_id, amount)
            
            url = f"{self.base_url}Deposit/{user_id}/Add"
            headers = {
                "sign": signature,
                "Content-Type": "application/json"
            }
            payload = {
                "cashdeskId": int(self.config.API_CASHDESKID),
                "lng": "ru",
                "summa": float(amount),
                "confirm": confirm
            }
            
            logger.info(f"Пополнение счета {user_id} на {amount}")
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"Пополнение успешно: {data}")
                    return {
                        'success': True,
                        'amount': data.get('summa', amount),
                        'message': data.get('message', 'Успешно'),
                        'data': data
                    }
                else:
                    logger.error(f"Пополнение отклонено: {data}")
                    return {
                        'success': False,
                        'error': data.get('message', 'Неизвестная ошибка'),
                        'message_id': data.get('messageId')
                    }
            else:
                logger.error(f"Ошибка пополнения {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"Исключение при пополнении: {e}")
            return {'success': False, 'error': str(e)}
    
    def payout_from_user(self, user_id, code):
        """Выплата со счета игрока"""
        try:
            confirm = self._calculate_confirm(user_id)
            signature = self._generate_payout_signature(user_id, code)
            
            url = f"{self.base_url}Deposit/{user_id}/Payout"
            headers = {
                "sign": signature,
                "Content-Type": "application/json"
            }
            payload = {
                "cashdeskId": int(self.config.API_CASHDESKID),
                "lng": "ru",
                "code": code,
                "confirm": confirm
            }
            
            logger.info(f"Выплата для {user_id} с кодом {code}")
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Ответ выплаты: {data}")
                return {'success': True, 'data': data}
            else:
                logger.error(f"Ошибка выплаты {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"Исключение при выплате: {e}")
            return {'success': False, 'error': str(e)}
