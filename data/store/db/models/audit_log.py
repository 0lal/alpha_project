# -*- coding: utf-8 -*-
# Component: data/db/models/audit_log.py
# Responsibility: تعريف جدول السجلات الجنائية باستخدام القالب الأساسي.

from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
# لاحظ كيف نستورد القالب الذي وجدته
from .base_model import AlphaBaseModel

class AuditLog(AlphaBaseModel):
    """
    جدول الصندوق الأسود. يسجل كل حركة حساسة في النظام.
    يرث تلقائياً: id, created_at, updated_at من AlphaBaseModel.
    """
    __tablename__ = "audit_logs"

    # من قام بالفعل؟ (System, User, or Agent Name)
    actor: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # نوع الحدث (LOGIN, TRADE_EXECUTION, ERROR)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # مستوى الخطورة (INFO, WARNING, CRITICAL)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")

    # تفاصيل الحدث (يخزن كـ JSON لمرونة البيانات)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)

    # بصمة التحقق (Hash) لضمان عدم تلاعب الأدمن بالسجل لاحقاً
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    def __repr__(self):
        return f"<AuditLog(actor={self.actor}, event={self.event_type})>"