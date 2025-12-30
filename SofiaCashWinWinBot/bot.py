import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode, ChatAction

from config import Config
from database import Database
from api_client import SofiaCashAPI
from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_deposit_keyboard,
    get_user_deposit_keyboard, get_payment_methods_keyboard,
    get_broadcast_keyboard, get_support_keyboard, get_cancel_keyboard
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout  # Важно для Render
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
DEPOSIT_AMOUNT, DEPOSIT_METHOD, WITHDRAW_AMOUNT = range(3)
ADMIN_SEARCH_USER, ADMIN_BROADCAST = range(3, 5)

class WinWinBot:
    def __init__(self):
        self.config = Config
        self.db = Database()
        self.api = SofiaCashAPI()
        
        # Проверка конфигурации
        if not self.config.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не настроен! Добавьте в Environment Variables")
            sys.exit(1)
    
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        return user_id in self.config.ADMINS
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_or_update_user(user.id, user.username, user.full_name)
        
        if self.is_admin(user.id):
            welcome_text = f"""
👋 Добро пожаловать, Администратор {user.first_name}!

🤖 **WinWin Bot - SofiaCash System**
💼 Касса: SofiaCash
🔗 Интеграция: WinWin Gaming Platform

📊 **Панель администратора:**
- Управление депозитами
- Обработка выплат
- Рассылка сообщений
- Мониторинг баланса

Используйте меню ниже для управления.
            """
            await update.message.reply_text(
                welcome_text, 
                reply_markup=get_admin_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            welcome_text = f"""
🎰 Добро пожаловать в WinWin, {user.first_name}!

💰 **Быстрые депозиты и выплаты**
⚡ Мгновенные операции
🛡 Безопасные транзакции
🆘 Круглосуточная поддержка

💵 **Минимальный депозит:** {self.config.MIN_DEPOSIT} ₽
💳 **Методы оплаты:** Карты, ЮMoney, QIWI, Crypto

Выберите действие ниже ⤵️
            """
            await update.message.reply_text(
                welcome_text,
                reply_markup=get_main_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        text = update.message.text
        
        if self.is_admin(user.id):
            # Обработка сообщений администратора
            await self.handle_admin_message(update, context, text)
        else:
            # Обработка сообщений пользователя
            await self.handle_user_message(update, context, text)
    
    async def handle_admin_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка сообщений администратора"""
        if text == "📊 Статистика":
            await self.admin_stats(update, context)
        elif text == "⏳ Ожидающие депозиты":
            await self.show_pending_deposits(update, context)
        elif text == "🔄 В обработке":
            await self.show_processing_deposits(update, context)
        elif text == "📢 Рассылка":
            await update.message.reply_text(
                "📢 Введите сообщение для рассылки:",
                reply_markup=get_cancel_keyboard()
            )
            return ADMIN_BROADCAST
        elif text == "💼 Баланс кассы":
            await self.show_cashier_balance(update, context)
        elif text == "👤 Поиск игрока":
            await update.message.reply_text(
                "🔍 Введите ID игрока для поиска:",
                reply_markup=get_cancel_keyboard()
            )
            return ADMIN_SEARCH_USER
        elif text == "❌ Отмена":
            await update.message.reply_text(
                "❌ Операция отменена",
                reply_markup=get_admin_keyboard()
            )
            return ConversationHandler.END
    
    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка сообщений пользователя"""
        if text == "💰 Пополнить счет":
            await self.start_deposit(update, context)
        elif text == "💸 Вывести средства":
            await self.start_withdrawal(update, context)
        elif text == "📊 Мой баланс":
            await self.show_user_balance(update, context)
        elif text == "📋 Мои депозиты":
            await self.show_user_deposits(update, context)
        elif text == "🆘 Поддержка":
            await self.show_support(update, context)
        elif text == "📞 Связаться с поддержкой":
            await self.contact_support(update, context)
        elif text == "❌ Отмена":
            await update.message.reply_text(
                "❌ Операция отменена",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
    
    async def start_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса депозита"""
        await update.message.reply_text(
            f"💵 **Пополнение счета**\n\n"
            f"Введите сумму пополнения в рублях:\n"
            f"Минимальная сумма: {self.config.MIN_DEPOSIT} ₽",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )
        return DEPOSIT_AMOUNT
    
    async def process_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка суммы депозита"""
        try:
            amount = float(update.message.text)
            
            if amount < self.config.MIN_DEPOSIT:
                await update.message.reply_text(
                    f"❌ Минимальная сумма депозита: {self.config.MIN_DEPOSIT} ₽\n"
                    f"Попробуйте еще раз:"
                )
                return DEPOSIT_AMOUNT
            
            context.user_data['deposit_amount'] = amount
            
            # Показываем методы оплаты
            await update.message.reply_text(
                f"💰 Сумма: {amount:.2f} ₽\n\n"
                "Выберите метод оплаты:",
                reply_markup=get_payment_methods_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return DEPOSIT_METHOD
            
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректную сумму (например: 500)"
            )
            return DEPOSIT_AMOUNT
    
    async def process_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора метода оплаты"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_main":
            await query.edit_message_text(
                "❌ Операция отменена",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        method = query.data.replace("method_", "")
        amount = context.user_data['deposit_amount']
        
        methods_text = {
            'card': '💳 Банковская карта',
            'yoomoney': '📱 ЮMoney',
            'qiwi': '🎯 QIWI Кошелек',
            'crypto': '🔗 Криптовалюта'
        }
        
        # Создаем депозит в базе данных
        user = update.effective_user
        deposit_id = self.db.add_deposit(
            user.id,
            user.username,
            user.full_name,
            amount,
            methods_text.get(method, method)
        )
        
        await query.edit_message_text(
            f"✅ **Заявка на депозит создана!**\n\n"
            f"📋 Номер: #{deposit_id}\n"
            f"👤 Игрок: {user.full_name}\n"
            f"💵 Сумма: {amount:.2f} ₽\n"
            f"💳 Метод: {methods_text.get(method, method)}\n\n"
            f"⏳ Ожидайте реквизиты для оплаты от администратора...",
            reply_markup=get_user_deposit_keyboard(deposit_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Уведомляем администраторов
        await self.notify_admins_about_deposit(
            context, deposit_id, user, amount, method
        )
        
        return ConversationHandler.END
    
    async def notify_admins_about_deposit(self, context, deposit_id, user, amount, method):
        """Уведомление администраторов о новом депозите"""
        methods_text = {
            'card': '💳 Банковская карта',
            'yoomoney': '📱 ЮMoney',
            'qiwi': '🎯 QIWI',
            'crypto': '🔗 Крипто'
        }
        
        admin_message = (
            f"🆕 **Новый депозит #{deposit_id}**\n\n"
            f"👤 Игрок: {user.full_name}\n"
            f"🆔 TG ID: `{user.id}`\n"
            f"👤 Username: @{user.username or 'нет'}\n"
            f"💰 Сумма: {amount:.2f} ₽\n"
            f"💳 Метод: {methods_text.get(method, method)}\n"
            f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
            "👇 Для обработки нажмите кнопку ниже:"
        )
        
        for admin_id in self.config.ADMINS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    reply_markup=get_deposit_keyboard(deposit_id),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Уведомление отправлено администратору {admin_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('accept_'):
            deposit_id = int(data.split('_')[1])
            await self.accept_deposit(query, deposit_id, context)
        elif data.startswith('reject_'):
            deposit_id = int(data.split('_')[1])
            await self.reject_deposit(query, deposit_id, context)
        elif data.startswith('paid_'):
            deposit_id = int(data.split('_')[1])
            await self.user_paid(query, deposit_id, context)
        elif data.startswith('user_cancel_'):
            deposit_id = int(data.split('_')[2])
            await self.user_cancel_deposit(query, deposit_id, context)
        elif data == 'broadcast_confirm':
            await self.confirm_broadcast(query, context)
        elif data == 'broadcast_cancel':
            await query.edit_message_text("❌ Рассылка отменена")
    
    async def accept_deposit(self, query, deposit_id, context):
        """Администратор принимает депозит"""
        deposit = self.db.get_deposit(deposit_id)
        if not deposit:
            await query.edit_message_text("❌ Депозит не найден")
            return
        
        await query.edit_message_text(
            f"✅ Вы принимаете депозит #{deposit_id}\n\n"
            "Введите реквизиты для оплаты:\n"
            "(например: номер карты, кошелька и т.д.)",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Сохраняем контекст для следующего шага
        context.user_data['action'] = 'add_payment_details'
        context.user_data['deposit_id'] = deposit_id
        context.user_data['admin_id'] = query.from_user.id
    
    async def process_payment_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка реквизитов оплаты от администратора"""
        if context.user_data.get('action') == 'add_payment_details':
            deposit_id = context.user_data['deposit_id']
            admin_id = context.user_data['admin_id']
            payment_details = update.message.text
            
            # Обновляем депозит
            self.db.update_deposit(
                deposit_id,
                status='оплачен',
                payment_details=payment_details,
                admin_id=admin_id
            )
            
            # Получаем информацию о депозите
            deposit = self.db.get_deposit(deposit_id)
            
            # Отправляем реквизиты пользователю
            try:
                await context.bot.send_message(
                    chat_id=deposit['user_id'],
                    text=f"💳 **Реквизиты для оплаты**\n\n"
                         f"📋 Депозит #{deposit_id}\n"
                         f"💰 Сумма: {deposit['amount']:.2f} ₽\n"
                         f"💳 Метод: {deposit['payment_method']}\n\n"
                         f"🔗 Реквизиты:\n"
                         f"`{payment_details}`\n\n"
                         f"⏳ Время на оплату: 10 минут\n"
                         f"После оплаты нажмите кнопку 'Я оплатил'",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_user_deposit_keyboard(deposit_id)
                )
                
                await update.message.reply_text(
                    f"✅ Реквизиты отправлены игроку\n"
                    f"Депозит #{deposit_id}\n"
                    f"⏰ Таймер: 10 минут",
                    reply_markup=get_admin_keyboard()
                )
                
                # Запускаем таймер на 10 минут
                asyncio.create_task(self.deposit_timeout_check(deposit_id, context))
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Не удалось отправить сообщение игроку: {e}",
                    reply_markup=get_admin_keyboard()
                )
            
            # Очищаем контекст
            context.user_data.clear()
    
    async def deposit_timeout_check(self, deposit_id, context):
        """Проверка таймаута депозита (10 минут)"""
        await asyncio.sleep(self.config.DEPOSIT_TIMEOUT)
        
        deposit = self.db.get_deposit(deposit_id)
        if deposit and deposit['status'] == 'оплачен':
            # Депозит не оплачен вовремя
            self.db.update_deposit(deposit_id, status='отменен')
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=deposit['user_id'],
                    text=f"❌ Депозит #{deposit_id} отменен\n"
                         f"Причина: истекло время оплаты"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя: {e}")
    
    async def user_paid(self, query, deposit_id, context):
        """Пользователь нажал 'Я оплатил'"""
        await query.edit_message_text(
            f"✅ Вы подтвердили оплату депозита #{deposit_id}\n\n"
            "📎 Пожалуйста, загрузите чек (PDF, фото или скриншот):",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Обновляем статус
        self.db.update_deposit(deposit_id, status='в обработке')
        
        # Уведомляем администраторов
        deposit = self.db.get_deposit(deposit_id)
        
        for admin_id in self.config.ADMINS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📎 Игрок подтвердил оплату депозита #{deposit_id}\n"
                         f"👤 Игрок: {deposit['full_name']}\n"
                         f"💰 Сумма: {deposit['amount']:.2f} ₽\n"
                         f"⏳ Ожидает загрузки чека...",
                    reply_markup=get_deposit_keyboard(deposit_id)
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить администратора: {e}")
    
    async def handle_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженного чека"""
        user_id = update.effective_user.id
        
        # Ищем депозит в обработке для этого пользователя
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT id FROM deposits 
            WHERE user_id = ? AND status = 'в обработке'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        if not result:
            await update.message.reply_text(
                "❌ У вас нет депозитов, ожидающих загрузки чека",
                reply_markup=get_main_keyboard()
            )
            return
        
        deposit_id = result[0]
        file_id = None
        
        # Получаем ID файла
        if update.message.document:
            if update.message.document.mime_type == 'application/pdf':
                file_id = update.message.document.file_id
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
        
        if file_id:
            # Сохраняем файл
            self.db.update_deposit(deposit_id, receipt_file_id=file_id)
            
            # Получаем информацию о депозите
            deposit = self.db.get_deposit(deposit_id)
            
            # Отправляем чек администраторам
            for admin_id in self.config.ADMINS:
                try:
                    caption = (
                        f"📎 Чек для депозита #{deposit_id}\n"
                        f"👤 Игрок: {deposit['full_name']}\n"
                        f"💰 Сумма: {deposit['amount']:.2f} ₽\n"
                        f"💳 Метод: {deposit['payment_method']}"
                    )
                    
                    if update.message.document:
                        await context.bot.send_document(
                            chat_id=admin_id,
                            document=file_id,
                            caption=caption,
                            reply_markup=get_deposit_keyboard(deposit_id)
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=file_id,
                            caption=caption,
                            reply_markup=get_deposit_keyboard(deposit_id)
                        )
                except Exception as e:
                    logger.error(f"Не удалось отправить чек администратору: {e}")
            
            await update.message.reply_text(
                f"✅ Чек получен и отправлен администратору\n"
                f"Ожидайте подтверждения платежа",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Пожалуйста, загрузите PDF-файл или фото",
                reply_markup=get_main_keyboard()
            )
    
    async def reject_deposit(self, query, deposit_id, context):
        """Администратор отклоняет депозит"""
        self.db.update_deposit(
            deposit_id, 
            status='отменен',
            admin_id=query.from_user.id
        )
        
        deposit = self.db.get_deposit(deposit_id)
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=deposit['user_id'],
                text=f"❌ Депозит #{deposit_id} отклонен\n"
                     f"💰 Сумма: {deposit['amount']:.2f} ₽\n\n"
                     f"Если у вас есть вопросы, обратитесь в поддержку"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")
        
        await query.edit_message_text(
            f"❌ Депозит #{deposit_id} отклонен\n"
            f"Игрок уведомлен"
        )
    
    async def user_cancel_deposit(self, query, deposit_id, context):
        """Пользователь отменяет депозит"""
        self.db.update_deposit(deposit_id, status='отменен')
        
        await query.edit_message_text(
            f"❌ Депозит #{deposit_id} отменен\n\n"
            f"Для создания нового депозита нажмите '💰 Пополнить счет'",
            reply_markup=get_main_keyboard()
        )
    
    async def complete_deposit_via_api(self, deposit_id, admin_id, context):
        """Завершение депозита через API SofiaCash"""
        deposit = self.db.get_deposit(deposit_id)
        
        # Пополняем счет через API
        result = self.api.deposit_to_user(deposit['user_id'], deposit['amount'])
        
        if result['success']:
            # Обновляем статус депозита
            self.db.update_deposit(
                deposit_id,
                status='завершен',
                admin_id=admin_id,
                processed_at=datetime.now().isoformat()
            )
            
            # Обновляем баланс пользователя
            self.db.update_user_balance(deposit['user_id'], deposit['amount'])
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=deposit['user_id'],
                    text=f"✅ **Депозит успешно зачислен!**\n\n"
                         f"📋 Номер: #{deposit_id}\n"
                         f"💵 Сумма: {deposit['amount']:.2f} ₽\n"
                         f"💰 Ваш счет пополнен\n"
                         f"🎰 Удачной игры в WinWin!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_keyboard()
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя: {e}")
            
            return True
        else:
            # Ошибка API
            try:
                await context.bot.send_message(
                    chat_id=deposit['user_id'],
                    text=f"⚠️ **Ошибка зачисления депозита**\n\n"
                         f"📋 Номер: #{deposit_id}\n"
                         f"💵 Сумма: {deposit['amount']:.2f} ₽\n"
                         f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n"
                         f"📞 Свяжитесь с поддержкой",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя об ошибке: {e}")
            
            return False
    
    async def show_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о поддержке"""
        support_text = f"""
🆘 **Служба поддержки WinWin**

📞 **Связаться с поддержкой:**
Нажмите кнопку ниже, чтобы написать напрямую

🕒 **Часы работы:**
Круглосуточно, 24/7

📋 **Что предоставить при обращении:**
1. Ваш ID в боте
2. Номер операции (если есть)
3. Описание проблемы

👇 **Выберите действие:**
        """
        
        await update.message.reply_text(
            support_text,
            reply_markup=get_support_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Связаться с поддержкой"""
        user = update.effective_user
        support_link = f"https://t.me/{self.config.SUPPORT_USERNAME[1:]}?start=user{user.id}"
        
        await update.message.reply_text(
            f"📞 **Связь с поддержкой**\n\n"
            f"👤 Ваш ID: `{user.id}`\n"
            f"📛 Имя: {user.full_name}\n\n"
            f"Нажмите кнопку ниже, чтобы написать в поддержку:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 Написать в поддержку", url=support_link)
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_user_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать баланс пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data:
            balance = user_data['balance'] or 0
            await update.message.reply_text(
                f"💰 **Ваш баланс:** {balance:.2f} ₽\n\n"
                f"📊 Всего пополнено: {user_data['total_deposited']:.2f} ₽\n"
                f"📈 Количество депозитов: {user_data['deposits_count']}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Информация не найдена")
    
    async def show_user_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать историю депозитов пользователя"""
        user = update.effective_user
        deposits = self.db.get_user_deposits(user.id)
        
        if not deposits:
            await update.message.reply_text(
                "📭 У вас еще нет депозитов\n\n"
                "Для создания первого депозита нажмите '💰 Пополнить счет'",
                reply_markup=get_main_keyboard()
            )
            return
        
        message = "📋 **Ваши депозиты:**\n\n"
        
        for deposit in deposits[:10]:  # Показываем последние 10
            status_icons = {
                'ожидает оплаты': '⏳',
                'оплачен': '💳',
                'в обработке': '🔄',
                'завершен': '✅',
                'отменен': '❌'
            }
            
            icon = status_icons.get(deposit['status'], '📝')
            created = datetime.fromisoformat(deposit['created_at']).strftime('%d.%m.%Y %H:%M')
            
            message += (
                f"{icon} **#{deposit['id']}** - {deposit['amount']:.2f} ₽\n"
                f"   Статус: {deposit['status']}\n"
                f"   Дата: {created}\n"
                f"   Метод: {deposit['payment_method']}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика для администратора"""
        stats = self.db.get_stats()
        
        message = (
            f"📊 **Статистика системы**\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"📈 Всего депозитов: {stats['total_deposits']}\n"
            f"💰 Общая сумма: {stats['total_amount']:.2f} ₽\n"
            f"⏳ Ожидают оплаты: {stats['pending_deposits']}\n\n"
            f"🕒 Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def show_pending_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать депозиты, ожидающие оплаты"""
        deposits = self.db.get_pending_deposits()
        
        if not deposits:
            await update.message.reply_text("✅ Нет депозитов, ожидающих оплаты")
            return
        
        message = "⏳ **Депозиты, ожидающие оплаты:**\n\n"
        
        for deposit in deposits[:5]:  # Показываем последние 5
            created = datetime.fromisoformat(deposit['created_at']).strftime('%H:%M')
            
            message += (
                f"📋 **#{deposit['id']}**\n"
                f"👤 {deposit['full_name']} (@{deposit['username'] or 'нет'})\n"
                f"💰 {deposit['amount']:.2f} ₽\n"
                f"💳 {deposit['payment_method']}\n"
                f"⏰ {created}\n\n"
            )
        
        if len(deposits) > 5:
            message += f"📝 ... и еще {len(deposits) - 5} депозитов\n\n"
        
        message += "Для обработки используйте панель администратора"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def show_processing_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать депозиты в обработке"""
        deposits = self.db.get_processing_deposits()
        
        if not deposits:
            await update.message.reply_text("✅ Нет депозитов в обработке")
            return
        
        message = "🔄 **Депозиты в обработке:**\n\n"
        
        for deposit in deposits[:5]:
            created = datetime.fromisoformat(deposit['created_at']).strftime('%H:%M')
            
            message += (
                f"📋 **#{deposit['id']}**\n"
                f"👤 {deposit['full_name']}\n"
                f"💰 {deposit['amount']:.2f} ₽\n"
                f"⏰ {created}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def show_cashier_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать баланс кассы через API"""
        await update.message.reply_text("⏳ Запрашиваю баланс кассы...")
        
        balance_data = self.api.get_balance()
        
        if balance_data.get('success'):
            response = (
                f"💰 **Баланс кассы SofiaCash**\n\n"
                f"💵 Доступно: {balance_data['balance']:.2f} ₽\n"
                f"📊 Лимит: {balance_data['limit']:.2f} ₽\n"
                f"📈 Свободно: {balance_data['available']:.2f} ₽\n\n"
                f"🔄 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            response = (
                f"❌ **Не удалось получить баланс кассы**\n\n"
                f"Ошибка: {balance_data.get('error', 'Неизвестная ошибка')}\n"
                f"Проверьте настройки API в переменных окружения"
            )
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def process_admin_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка поиска пользователя администратором"""
        try:
            user_id = int(update.message.text)
            await update.message.reply_text(f"🔍 Ищу игрока с ID: {user_id}...")
            
            # Ищем в базе данных
            user_data = self.db.get_user(user_id)
            
            if user_data:
                message = (
                    f"✅ **Пользователь найден в базе**\n\n"
                    f"🆔 ID: {user_data['user_id']}\n"
                    f"👤 Username: @{user_data['username'] or 'нет'}\n"
                    f"📛 Имя: {user_data['full_name']}\n"
                    f"💰 Баланс: {user_data['balance']:.2f} ₽\n"
                    f"📊 Депозитов: {user_data['deposits_count']}\n"
                    f"📈 Всего внесено: {user_data['total_deposited']:.2f} ₽"
                )
            else:
                # Пробуем найти через API SofiaCash
                api_result = self.api.find_user(user_id)
                
                if api_result.get('success'):
                    api_data = api_result['data']
                    message = (
                        f"✅ **Пользователь найден в WinWin**\n\n"
                        f"🆔 ID: {api_data.get('userId')}\n"
                        f"📛 Имя: {api_data.get('name', 'Не указано')}\n"
                        f"💱 Валюта: {api_data.get('currencyId', 'Не указан')}"
                    )
                else:
                    message = f"❌ Пользователь с ID {user_id} не найден"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_keyboard()
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ ID должен быть числом. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard()
            )
            return ADMIN_SEARCH_USER
        
        return ConversationHandler.END
    
    async def process_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщения для рассылки"""
        message_text = update.message.text
        context.user_data['broadcast_message'] = message_text
        
        await update.message.reply_text(
            f"📢 **Предпросмотр рассылки:**\n\n"
            f"{message_text}\n\n"
            f"✅ Отправить это сообщение всем пользователям?",
            reply_markup=get_broadcast_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def confirm_broadcast(self, query, context):
        """Подтверждение и отправка рассылки"""
        await query.edit_message_text("⏳ Отправка рассылки...")
        
        message_text = context.user_data.get('broadcast_message', '')
        
        if not message_text:
            await query.edit_message_text("❌ Сообщение для рассылки не найдено")
            return
        
        # Получаем всех пользователей
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user[0],
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
            except Exception as e:
                fail_count += 1
                logger.error(f"Не удалось отправить рассылку пользователю {user[0]}: {e}")
        
        await query.edit_message_text(
            f"✅ Рассылка завершена!\n\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Не удалось: {fail_count}\n"
            f"👥 Всего: {len(users)}"
        )
        
        context.user_data.clear()
    
    async def start_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса вывода средств"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not user_data or user_data['balance'] <= 0:
            await update.message.reply_text(
                "❌ На вашем счете недостаточно средств для вывода",
                reply_markup=get_main_keyboard()
            )
            return
        
        await update.message.reply_text(
            f"💸 **Вывод средств**\n\n"
            f"💰 Доступно для вывода: {user_data['balance']:.2f} ₽\n\n"
            f"Введите сумму для вывода:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )
        
        return WITHDRAW_AMOUNT
    
    async def process_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка суммы для вывода"""
        try:
            amount = float(update.message.text)
            user = update.effective_user
            user_data = self.db.get_user(user.id)
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0",
                    reply_markup=get_cancel_keyboard()
                )
                return WITHDRAW_AMOUNT
            
            if amount > user_data['balance']:
                await update.message.reply_text(
                    f"❌ Недостаточно средств\n"
                    f"Доступно: {user_data['balance']:.2f} ₽",
                    reply_markup=get_cancel_keyboard()
                )
                return WITHDRAW_AMOUNT
            
            # Здесь должна быть логика вывода через API
            # Пока просто показываем сообщение
            await update.message.reply_text(
                f"✅ Заявка на вывод {amount:.2f} ₽ принята\n\n"
                f"Для завершения вывода обратитесь к администратору: {self.config.SUPPORT_USERNAME}",
                reply_markup=get_main_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Уведомляем администраторов
            for admin_id in self.config.ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"💸 **Новая заявка на вывод**\n\n"
                             f"👤 Игрок: {user.full_name}\n"
                             f"🆔 ID: {user.id}\n"
                             f"💰 Сумма: {amount:.2f} ₽\n"
                             f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить администратора: {e}")
            
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректную сумму",
                reply_markup=get_cancel_keyboard()
            )
            return WITHDRAW_AMOUNT
        
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

def main():
    """Запуск бота"""
    # Создаем бота
    bot = WinWinBot()
    
    # Создаем приложение
    application = Application.builder().token(bot.config.BOT_TOKEN).build()
    
    # ConversationHandler для депозитов пользователя
    deposit_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💰 Пополнить счет"]), bot.start_deposit)],
        states={
            DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_deposit_amount)
            ],
            DEPOSIT_METHOD: [
                CallbackQueryHandler(bot.process_payment_method, pattern="^method_"),
                CallbackQueryHandler(bot.process_payment_method, pattern="^back_main")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Text(["❌ Отмена"]), bot.handle_message),
            CommandHandler("cancel", bot.handle_message)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для вывода средств
    withdraw_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💸 Вывести средства"]), bot.start_withdrawal)],
        states={
            WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_withdrawal)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Text(["❌ Отмена"]), bot.handle_message),
            CommandHandler("cancel", bot.handle_message)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для администратора
    admin_conv_handler = ConversationHandler(
        entry_points=[],
        states={
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_admin_search)
            ],
            ADMIN_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_broadcast)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Text(["❌ Отмена"]), bot.handle_message),
            CommandHandler("cancel", bot.handle_message)
        ],
        allow_reentry=True
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.start))
    application.add_handler(deposit_conv_handler)
    application.add_handler(withdraw_conv_handler)
    application.add_handler(admin_conv_handler)
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(
        bot.handle_callback, 
        pattern="^(accept|reject|paid|user_cancel|broadcast)_"
    ))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_message
    ))
    
    # Обработчик документов и фото (чеки)
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO,
        bot.handle_receipt
    ))
    
    # Обработчик платежных реквизитов от администратора
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot.process_payment_details
    ))
    
    # Обработчик ошибок
    application.add_error_handler(bot.error_handler)
    
    # Запуск бота
    logger.info("🤖 Бот WinWin запускается...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
