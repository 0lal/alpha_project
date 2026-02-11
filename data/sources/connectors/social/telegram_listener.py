import os
import logging
import asyncio
from typing import List, Callable, Dict, Any

# استيراد مكتبة Telethon: المعيار الصناعي للاتصال الحي ببروتوكول Telegram
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# استيراد أنظمة الدولة (State Machinery) التي بنيناها سابقاً
try:
    from inventory.key_loader import key_loader
    from audit.logger_service import audit_logger
except ImportError:
    # حماية ضد الانهيار أثناء التشغيل المنفصل (Standalone Mode)
    logging.critical("🔥 FATAL: Missing Core Components for Telegram Listener!")
    key_loader = None
    audit_logger = None

# إعداد السجل الجنائي للمستشعر
logger = logging.getLogger("Alpha.Drivers.TelegramListener")

class TelegramFinancialListener:
    """
    المستشعر المالي الحي لشبكة تيليجرام (Live MTProto Listener).
    
    المهام الجنائية:
    1. الاتصال المستمر (24/7) بخوادم تيليجرام عبر بروتوكول MTProto.
    2. التنصت على قنوات مالية محددة (أخبار، حيتان، توصيات) واستخراج النص فور نشره.
    3. الحفاظ على بقاء الجلسة (Session Persistence) لتجنب حظر الحساب (Bans).
    4. معالجة الانقطاعات المفاجئة للشبكة وإعادة الاتصال الذاتي (Auto-Reconnect).
    """

    def __init__(self):
        """
        تهيئة المستشعر وتجهيز مفاتيح الدخول (API ID & API Hash).
        """
        # 1. جلب بيانات الاعتماد من ملف التكوين (telegram_keys.json)
        self.config = self._load_config()
        
        # تيليجرام يتطلب api_id (رقم) و api_hash (نص)
        self.api_id = self.config.get("credentials", {}).get("api_id")
        self.api_hash = self.config.get("credentials", {}).get("api_hash")
        
        if not self.api_id or not self.api_hash:
            logger.critical("❌ FATAL: Telegram API ID or Hash is missing! Cannot start listener.")
            raise ValueError("Missing Telegram Credentials")

        # 2. تحديد مسار تخزين الجلسة (Session) لضمان عدم ضياعها
        # يتم تخزينها في مجلد السجلات (audit) لأنها تعتبر دليلاً أمنياً وملفاً حساساً
        os.makedirs("audit/sessions", exist_ok=True)
        self.session_path = "audit/sessions/alpha_financial_node"

        # 3. تهيئة العميل (The Client)
        # نستخدم نظام إعادة المحاولة التلقائية المدمج في Telethon لضمان الاستقرار
        self.client = TelegramClient(
            self.session_path, 
            self.api_id, 
            self.api_hash,
            connection_retries=None, # المحاولة للأبد إذا انقطع الإنترنت
            retry_delay=5 # الانتظار 5 ثوانٍ بين كل محاولة
        )

        # قائمة الدوال التي سيتم تنفيذها عند وصول رسالة جديدة (Callbacks)
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []
        
        # قائمة القنوات المستهدفة (Target Channels IDs or Usernames)
        self._target_channels: List[str] = self.config.get("listening_policy", {}).get("target_channels", [])

    def _load_config(self) -> Dict:
        """
        تحميل الإعدادات الخاصة بتيليجرام من الخزنة الآمنة.
        """
        if key_loader:
            cfg = key_loader.get_config("telegram")
            if not cfg:
                logger.error("❌ Configuration not found for Telegram in keys inventory.")
                return {}
            return cfg
        return {}

    def register_handler(self, callback_function: Callable[[Dict[str, Any]], None]):
        """
        تسجيل "رد فعل" (Callback).
        مثال: عندما تأتي رسالة، قم بتمريرها إلى المترجم أو المحلل الذكي.
        """
        self._message_handlers.append(callback_function)
        logger.info(f"🔗 Registered new message handler. Total handlers: {len(self._message_handlers)}")

    async def start_listening(self, phone_number: str = None):
        """
        تشغيل الرادار والبدء في التقاط الإشارات.
        يجب تشغيل هذه الدالة داخل حدث غير متزامن (Async Event Loop).
        
        المعاملات:
        - phone_number: رقم الهاتف بصيغة دولية (+123...). يطلب فقط في أول مرة لإنشاء الجلسة.
        """
        try:
            logger.info("📡 Initializing Telegram MTProto Connection...")
            
            # 1. الاتصال المبدئي
            await self.client.connect()
            
            # 2. التحقق من حالة تسجيل الدخول (Authorization Check)
            if not await self.client.is_user_authorized():
                if not phone_number:
                    logger.critical("🛑 Cannot authorize: No phone number provided and session is empty.")
                    return
                    
                logger.warning(f"🔐 Session unauthorized. Sending code to {phone_number}...")
                await self.client.send_code_request(phone_number)
                
                # إيقاف التنفيذ وتنبيه النظام أن التدخل البشري مطلوب لإدخال الكود
                logger.critical("⚠️ MANUAL INTERVENTION REQUIRED: Please input the Telegram code via the UI or console script.")
                # ملاحظة: في بيئة الإنتاج، يتم تمرير الكود عبر واجهة المستخدم (FastAPI endpoint)
                # ثم استدعاء await self.client.sign_in(phone_number, code)
                return

            logger.info("✅ Telegram Authorization Successful. Connection Secured.")

            # 3. تسجيل أحداث الاستماع (Event Listeners)
            # نراقب فقط القنوات المحددة في ملف التكوين لتوفير موارد السيرفر
            if self._target_channels:
                logger.info(f"🎯 Locking radar onto channels: {self._target_channels}")
                
                @self.client.on(events.NewMessage(chats=self._target_channels))
                async def message_interceptor(event):
                    await self._process_incoming_signal(event)
            else:
                logger.warning("⚠️ No target channels defined in config. Listening to ALL incoming messages (Not Recommended for RAM).")
                
                @self.client.on(events.NewMessage())
                async def message_interceptor_all(event):
                    await self._process_incoming_signal(event)

            # 4. إبقاء الاتصال حياً (Keep-Alive Loop)
            logger.info("🎧 Radar is ACTIVE. Listening for financial signals...")
            await self.client.run_until_disconnected()

        except FloodWaitError as e:
            # الدرع المضاد للعقوبات (Anti-Ban Shield)
            logger.error(f"🛑 Telegram Rate Limit Hit! Sleeping for {e.seconds} seconds as mandated by server.")
            if audit_logger:
                audit_logger.log_security_event("TELEGRAM_FLOOD_WAIT", f"Forced sleep for {e.seconds}s")
            
            await asyncio.sleep(e.seconds)
            # محاولة إعادة الاتصال بعد انتهاء العقوبة
            await self.start_listening(phone_number)

        except Exception as e:
            logger.critical(f"🔥 FATAL: Telegram Listener Crashed: {str(e)}")
            if audit_logger:
                audit_logger.log_error("TELEGRAM_LISTENER_CRASH", "Fatal exception in async loop", str(e))

    async def _process_incoming_signal(self, event: events.NewMessage.Event):
        """
        معالجة وتغليف الرسالة القادمة قبل إرسالها لباقي أجزاء النظام.
        """
        try:
            # 1. استخراج الأدلة الجنائية للرسالة (Metadata Extraction)
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # 2. بناء الهيكل الموحد لبيانات ألفا (Alpha Standard Format)
            signal_payload = {
                "timestamp": event.date.isoformat(),
                "channel_id": chat.id if chat else None,
                "channel_name": getattr(chat, 'title', getattr(chat, 'username', 'Unknown')),
                "sender_id": sender.id if sender else None,
                "message_id": event.id,
                "text": event.message.message,
                "has_media": event.message.media is not None
            }

            logger.info(f"📥 Signal received from [{signal_payload['channel_name']}]: {signal_payload['text'][:50]}...")

            # 3. توثيق الحدث (Audit Logging)
            if audit_logger:
                # نسجل فقط الأحداث كتدقيق لمعرفة كم رسالة تم استقبالها
                audit_logger.log_anomaly("TELEGRAM_SIGNAL", f"Msg {event.id}", "INFO")

            # 4. توزيع الرسالة على المعالجات (Broadcast to Handlers)
            # مثل المترجم، أو محلل الذكاء الاصطناعي (Groq) لاستخراج أسماء الأسهم
            for handler in self._message_handlers:
                try:
                    # التنفيذ بشكل متزامن أو غير متزامن بناءً على نوع الدالة
                    if asyncio.iscoroutinefunction(handler):
                        await handler(signal_payload)
                    else:
                        handler(signal_payload)
                except Exception as handler_error:
                    logger.error(f"❌ Handler failed to process Telegram signal: {handler_error}")

        except Exception as e:
            logger.error(f"❌ Failed to process incoming Telegram event: {e}")

    async def disconnect(self):
        """
        قطع الاتصال الآمن (Graceful Shutdown).
        يمنع تلف ملف الجلسة عند إغلاق النظام.
        """
        if self.client and self.client.is_connected():
            logger.info("🛑 Disconnecting Telegram Listener...")
            await self.client.disconnect()
            logger.info("✅ Telegram Connection Closed Safely.")

# يمكن لاحقاً استدعاء TelegramFinancialListener() وتشغيل start_listening داخل loop