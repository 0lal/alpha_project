# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - WEBSOCKET SESSION HANDLER
# =================================================================
# Component Name: shield/nexus/websocket/client_handler.py
# Core Responsibility: إدارة جلسة اتصال فردية ومعالجة أوامر العميل (Session Layer).
# Design Pattern: Command Processor
# Security: Input Validation & Exception Isolation
# =================================================================

import json
import logging
import asyncio
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

# استيراد مدير البث (Singleton Instance)
from shield.nexus.websocket.stream_manager import stream_manager

# إعداد السجلات
logger = logging.getLogger("Alpha.Nexus.ClientHandler")

class ClientHandler:
    """
    معالج الجلسات.
    يتم إنشاء مثيل لكل اتصال جديد (أو استخدام دوال Static للتبسيط في Async).
    هنا نترجم رغبات العميل إلى إجراءات في النظام.
    """

    async def handle_session(self, websocket: WebSocket):
        """
        الحلقة الرئيسية لإدارة دورة حياة الاتصال.
        """
        client_id = f"{websocket.client.host}:{websocket.client.port}"
        logger.info(f"WS_INIT: محاولة اتصال جديدة من {client_id}")

        try:
            # 1. المصافحة وقبول الاتصال (Handshake)
            # نمرر قائمة فارغة مبدئياً، العميل سيشترك لاحقاً
            await stream_manager.connect(websocket, topics=[])
            
            # إرسال رسالة ترحيب لتأكيد الاتصال
            await websocket.send_json({
                "type": "WELCOME",
                "message": "Connected to Alpha Sovereign Nexus",
                "status": "ONLINE"
            })

            # 2. حلقة الاستماع (Event Loop)
            while True:
                # انتظار رسالة من العميل
                data = await websocket.receive_text()
                
                # معالجة الرسالة
                await self._process_message(websocket, data)

        except WebSocketDisconnect:
            logger.info(f"WS_CLOSE: العميل {client_id} قطع الاتصال.")
            await stream_manager.disconnect(websocket)
            
        except Exception as e:
            logger.error(f"WS_ERROR: خطأ غير متوقع مع {client_id}: {e}")
            # محاولة تنظيف الاتصال في حال حدوث خطأ
            await stream_manager.disconnect(websocket)

    async def _process_message(self, websocket: WebSocket, raw_data: str):
        """
        تحليل وتنفيذ أوامر العميل (Command Parser).
        """
        try:
            # التحقق من صحة JSON
            message: Dict[str, Any] = json.loads(raw_data)
            action = message.get("action", "").upper()
            
            # --- Command: SUBSCRIBE (اشتراك في قنوات) ---
            if action == "SUBSCRIBE":
                topics = message.get("topics", [])
                if topics and isinstance(topics, list):
                    # نستخدم القفل الخاص بمدير البث لضمان سلامة البيانات
                    # نقوم بالإضافة يدوياً هنا لأن دالة connect تقوم بـ accept مرة أخرى
                    async with stream_manager._lock:
                        for topic in topics:
                            if topic not in stream_manager.active_subscriptions:
                                stream_manager.active_subscriptions[topic] = set()
                            stream_manager.active_subscriptions[topic].add(websocket)
                    
                    logger.debug(f"CMD_SUB: تم الاشتراك في {topics}")
                    await self._send_ack(websocket, "SUBSCRIBED", {"topics": topics})

            # --- Command: UNSUBSCRIBE (إلغاء اشتراك) ---
            elif action == "UNSUBSCRIBE":
                topics = message.get("topics", [])
                if topics:
                    await stream_manager.disconnect(websocket, topics)
                    await self._send_ack(websocket, "UNSUBSCRIBED", {"topics": topics})

            # --- Command: PING (فحص الاتصال) ---
            elif action == "PING":
                await websocket.send_json({"type": "PONG", "timestamp": message.get("timestamp")})

            # --- أمر غير معروف ---
            else:
                logger.warning(f"WS_WARN: أمر غير معروف: {action}")
                await websocket.send_json({"type": "ERROR", "message": "Unknown Action"})

        except json.JSONDecodeError:
            await websocket.send_json({"type": "ERROR", "message": "Invalid JSON format"})
        except Exception as e:
            logger.error(f"CMD_FAIL: فشل تنفيذ الأمر: {e}")

    async def _send_ack(self, websocket: WebSocket, type_str: str, data: Dict):
        """
        إرسال إشعار تأكيد للعميل (Acknowledgement).
        """
        response = {"type": type_str}
        response.update(data)
        await websocket.send_json(response)

# =================================================================
# Global Handler Instance
# =================================================================
client_handler = ClientHandler()