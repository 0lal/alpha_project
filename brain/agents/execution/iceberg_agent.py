# Order Slicing Logic

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - ICEBERG EXECUTION ALGO
# =================================================================
# Component Name: brain/agents/execution/iceberg_agent.py
# Core Responsibility: تجزئة الأوامر الضخمة لإخفاء النية الحقيقية (Performance Pillar).
# Design Pattern: Generator / State Machine
# Forensic Impact: يمنع "تأثير السوق" (Market Impact) والانزلاق السعري الناتج عن كشف السيولة.
# =================================================================

import logging
import random
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

class IcebergAgent:
    """
    وكيل تنفيذ جبل الجليد (Iceberg Algo).
    يقوم بتحويل "الأمر الأب" (Parent Order) إلى سلسلة من "الأوامر الأبناء" (Child Orders).
    """

    def __init__(self, variance_factor: float = 0.30):
        """
        Args:
            variance_factor: نسبة العشوائية (30% تعني أن حجم الأمر قد يزيد أو ينقص بنسبة 30%).
        """
        self.logger = logging.getLogger("Alpha.Brain.Execution.Iceberg")
        self.variance = variance_factor
        
        # الحد الأدنى لإظهار "القمة" (حتى لا يتم رفض الأمر كغبار)
        self.min_visible_chunk = 100.0 # بالدولار

    def create_execution_plan(self, parent_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        إنشاء خطة تقطيع للأمر الضخم.
        
        Args:
            parent_order: {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "total_qty": 10.0,
                "price_limit": 50000,
                "urgency": "MEDIUM" # LOW, MEDIUM, HIGH
            }
            
        Returns:
            كائن تتبع حالة التنفيذ (Execution State).
        """
        total_qty = parent_order["total_qty"]
        price = parent_order.get("price_limit", 0)
        
        # 1. تحديد حجم "القمة" المثالي (Visible Tip Size)
        # يعتمد على الإلحاح (Urgency). الإلحاح العالي يعني قطعاً أكبر للإسراع.
        urgency = parent_order.get("urgency", "MEDIUM")
        slice_percentage = 0.05 # الافتراضي: إظهار 5% فقط
        
        if urgency == "HIGH": slice_percentage = 0.10
        elif urgency == "LOW": slice_percentage = 0.02
        
        avg_slice_qty = total_qty * slice_percentage

        # التحقق من الحد الأدنى للحجم
        if (avg_slice_qty * price) < self.min_visible_chunk and price > 0:
            avg_slice_qty = self.min_visible_chunk / price

        # 2. إنشاء معرف الجلسة
        session_id = str(uuid.uuid4())
        
        self.logger.info(f"ICEBERG_INIT: Starting execution for {total_qty} {parent_order['symbol']}. Avg Slice: {avg_slice_qty:.4f}")

        return {
            "session_id": session_id,
            "parent_order": parent_order,
            "total_qty": total_qty,
            "remaining_qty": total_qty,
            "filled_qty": 0.0,
            "avg_slice_qty": avg_slice_qty,
            "status": "ACTIVE",
            "child_orders_history": []
        }

    def get_next_slice(self, execution_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        توليد "الأمر الابن" التالي (The Next Slice).
        يتم استدعاء هذه الدالة كلما تم ملء الأمر السابق.
        """
        remaining = execution_state["remaining_qty"]
        
        # 1. شرط التوقف
        if remaining <= 0.0000001: # التعامل مع أخطاء الفاصلة العائمة
            execution_state["status"] = "COMPLETED"
            return None

        # 2. حساب حجم الشريحة التالية (مع العشوائية)
        # نستخدم توزيعاً طبيعياً أو موحداً لتضليل الخوارزميات
        # Randomness = Avg * (1 +/- variance)
        noise = random.uniform(-self.variance, self.variance)
        next_qty = execution_state["avg_slice_qty"] * (1.0 + noise)
        
        # التأكد من عدم تجاوز المتبقي
        next_qty = min(next_qty, remaining)
        
        # التأكد من أن الكمية موجبة ولها دقة عشرية صحيحة (مثلاً 5 أرقام عشرية)
        next_qty = round(next_qty, 5) # هذا يجب أن يطابق دقة البورصة (Lot Size)

        if next_qty <= 0:
            execution_state["status"] = "COMPLETED"
            return None

        # 3. تحديث الحالة
        # (نخصم الكمية "نظرياً" هنا، لكن التحديث الفعلي يتم عند تأكيد التنفيذ من البورصة)
        # في هذا التصميم، نفترض أن النظام سيحدث remaining_qty بناءً على التعبئة الفعلية
        
        parent = execution_state["parent_order"]
        
        child_order = {
            "child_id": str(uuid.uuid4()),
            "parent_id": execution_state["session_id"],
            "symbol": parent["symbol"],
            "side": parent["side"],
            "type": "LIMIT", # جبل الجليد يستخدم Limit دائماً لعدم حرق السيولة
            "quantity": next_qty,
            "price": self._calculate_limit_price(parent, execution_state),
            "is_iceberg_slice": True
        }
        
        self.logger.debug(f"ICEBERG_SLICE: Generated child {next_qty} (Rem: {remaining - next_qty:.4f})")
        return child_order

    def update_state(self, execution_state: Dict[str, Any], fill_qty: float):
        """تحديث الحالة بعد تنفيذ أمر فرعي."""
        execution_state["remaining_qty"] -= fill_qty
        execution_state["filled_qty"] += fill_qty
        
        if execution_state["remaining_qty"] <= 0.0000001:
            execution_state["status"] = "COMPLETED"
            self.logger.info("ICEBERG_COMPLETE: All slices executed successfully.")

    def _calculate_limit_price(self, parent: Dict[str, Any], state: Dict[str, Any]) -> float:
        """
        تحديد سعر الأمر الفرعي.
        يمكن تطوير هذا ليكون ديناميكياً (Pegged to Best Bid/Ask).
        حالياً نستخدم سعر الحد الخاص بالأب.
        """
        # يمكن إضافة منطق هنا: "ضع السعر عند أفضل طلب + 1 تكة"
        return parent.get("price_limit", 0)