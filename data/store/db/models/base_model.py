# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - BASE ORM MODEL
# =================================================================
# Component Name: data/db/models/base_model.py
# Core Responsibility: توفير القالب الأساسي لتعريف جداول البيانات (ORM Interface).
# Design Pattern: Layer Supertype / Table Data Gateway
# Forensic Impact: يفرض وجود معرفات UUID وطوابع زمنية موحدة لجميع الكيانات، مما يمنع التضارب ويسهل التتبع.
# =================================================================

import uuid
import json
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

# إنشاء الفئة الأساسية لـ SQLAlchemy
class Base(DeclarativeBase):
    """
    السجل المركزي لجميع الموديلات (SQLAlchemy Registry).
    """
    pass

class AlphaBaseModel(Base):
    """
    القالب الأساسي المجرد (Abstract Base Class).
    أي جدول في النظام (مثل Users, Orders, Logs) يجب أن يرث من هذه الفئة.
    """
    
    # تحديد أن هذه الفئة مجرد قالب ولن يتم إنشاء جدول لها في قاعدة البيانات
    __abstract__ = True

    # -----------------------------------------------------------
    # الأعمدة الإجبارية (The Mandatory Contract)
    # -----------------------------------------------------------

    # 1. المعرف الفريد (ID)
    # نستخدم UUID بدلاً من Integer لمنع هجمات التخمين (Enumeration Attacks)
    # ولضمان تفرد المعرفات حتى لو دمجنا قواعد بيانات مختلفة مستقبلاً.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )

    # 2. طابع الخلق (Creation Timestamp)
    # متى ظهر هذا الكيان للوجود؟ (لا يمكن تعديله لاحقاً)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        nullable=False
    )

    # 3. طابع التحديث (Update Timestamp)
    # متى تغيرت حالته آخر مرة؟
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------------
    # الوظائف المساعدة (Helper Methods)
    # -----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل الكائن إلى قاموس (Serialization).
        ضروري جداً لإرسال البيانات عبر API أو تسجيلها في ملفات JSON.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # معالجة خاصة للأنواع غير القابلة للتسلسل المباشر (Non-serializable)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
                
            result[column.name] = value
        return result

    def update(self, **kwargs):
        """
        طريقة آمنة لتحديث الحقول المتعددة دفعة واحدة.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                # تحذير جنائي: محاولة تحديث حقل غير موجود
                # (يمكن ربطه باللوجر لاحقاً)
                pass

    def __repr__(self):
        """
        تمثيل نصي للكائن (لأغراض التصحيح Debugging).
        """
        return f"<{self.__class__.__name__}(id={self.id}, created_at={self.created_at})>"