/*
 * ALPHA SOVEREIGN - MATCHING ENGINE CORE TYPES
 * =================================================================
 * Component Name: engine/src/matching/mod.rs
 * Core Responsibility: تعريف أنواع بيانات المطابقة وتصدير الوحدات الفرعية (Performance Pillar).
 * Design Pattern: Module Facade / Type Definitions
 * Forensic Impact: يحدد بدقة حقول الأمر والصفقة. إذا لم يوجد حقل "timestamp" هنا، فلن نستطيع إثبات وقت التنفيذ.
 * =================================================================
 */

use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::fmt;

// تصدير الوحدات الفرعية التي ستحتوي على المنطق الفعلي
// سنقوم بكتابة هذه الملفات (orderbook.rs, engine.rs) لاحقاً
pub mod orderbook;
pub mod engine;

// =================================================================
// أنواع البيانات الأساسية (Fundamental Data Types)
// =================================================================

/// اتجاه الأمر (شراء أم بيع).
/// نستخدم Copy, Clone لأن هذا النوع خفيف جداً (مجرد بايت واحد).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Side {
    Bid, // شراء
    Ask, // بيع
}

impl Side {
    /// عكس الاتجاه (مفيد للمطابقة)
    pub fn opposite(&self) -> Side {
        match self {
            Side::Bid => Side::Ask,
            Side::Ask => Side::Bid,
        }
    }
}

/// نوع الأمر (كيفية التنفيذ).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Limit,          // نفذ بسعر محدد أو أفضل
    Market,         // نفذ فوراً بأي سعر متاح
    ImmediateOrCancel, // نفذ ما تستطيع فوراً وألغ الباقي (IOC)
    FillOrKill,     // نفذ الكل فوراً أو ألغ الكل (FOK)
    PostOnly,       // لا تأخذ سيولة أبداً (كن صانع سوق فقط)
}

/// الهيكل الرئيسي للأمر (The Atom of the Engine).
/// يحتوي على كل ما يلزم لاتخاذ قرار المطابقة.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    /// معرف فريد للأمر (يتم توليده في الدماغ أو المحرك)
    pub id: u64,
    
    /// معرف الزوج (تم تحويله لرقم لسرعة المقارنة، e.g., 1 = BTCUSDT)
    pub symbol_id: u32,
    
    pub side: Side,
    pub order_type: OrderType,
    
    /// السعر (Decimal لضمان الدقة المالية)
    pub price: Decimal,
    
    /// الكمية المطلوبة
    pub quantity: Decimal,
    
    /// وقت الإنشاء (Unix Nanoseconds) - للأولوية الزمنية والتحقيق الجنائي
    pub timestamp: u64,
    
    /// المصدر (Strategy ID / User ID)
    pub owner_id: String,
}

impl Order {
    /// التحقق السريع من صحة الأمر قبل إدخاله للدفتر
    pub fn validate(&self) -> bool {
        self.quantity > Decimal::ZERO && self.price >= Decimal::ZERO
    }
}

// =================================================================
// نتائج المطابقة (Output Events)
// =================================================================

/// حدث تنفيذ صفقة (Trade Event).
/// هذا ما يتم تسجيله وإعادته للدماغ.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    /// معرف الأمر الآخذ (Taker) الذي تسبب في التنفيذ
    pub taker_order_id: u64,
    
    /// معرف الأمر الصانع (Maker) الذي كان ينتظر في الدفتر
    pub maker_order_id: u64,
    
    /// السعر الذي تمت به الصفقة
    pub price: Decimal,
    
    /// الكمية التي تم تنفيذها
    pub quantity: Decimal,
    
    /// هل كان التيكر مشترياً أم بائعاً؟ (يحدد اتجاه شمعة السوق)
    pub taker_side: Side,
    
    /// وقت التنفيذ الدقيق
    pub executed_at: u64,
}

/// ملخص نتيجة معالجة أمر واحد.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchingResult {
    /// الصفقات التي نتجت عن هذا الأمر (قد تكون متعددة)
    pub trades: Vec<Trade>,
    
    /// الكمية المتبقية من الأمر (إذا لم ينفذ بالكامل)
    pub remaining_qty: Decimal,
    
    /// حالة الأمر النهائية
    pub status: OrderStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Filled,         // تم التنفيذ بالكامل
    PartiallyFilled,// تم تنفيذ جزء، والباقي في الدفتر
    Queued,         // لم ينفذ، دخل الدفتر بالكامل
    Cancelled,      // تم الإلغاء (مثلاً FOK فشل)
    Rejected,       // مرفوض (خطأ في البيانات)
}

// لتسهيل الطباعة في السجلات
impl fmt::Display for Side {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}