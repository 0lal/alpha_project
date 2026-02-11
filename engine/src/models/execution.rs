// Fill Reports Struct

/*
 * ALPHA SOVEREIGN - EXECUTION & TRADE RESULT MODEL
 * =================================================================
 * Component Name: engine/src/models/execution.rs
 * Core Responsibility: هيكلية نتائج التنفيذ الدقيقة (Explainability Pillar).
 * Design Pattern: Immutable Event Record
 * Forensic Impact: يفرق بين التمني (Order) والواقع (Execution). يحدد بدقة التكاليف (Fees) ودور السيولة.
 * =================================================================
 */

use serde::{Serialize, Deserialize};
use rust_decimal::Decimal;
use std::fmt;
use super::order::OrderSide; // استخدام نفس Enum من ملف Order

// =================================================================
// تصنيفات التنفيذ (Execution Classifications)
// =================================================================

/// دورنا في الصفقة (يحدد هيكل العمولات)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LiquidityRole {
    Maker, // وضعنا أمراً معلقاً ونفذه شخص آخر (Passive - غالباً رسوم أقل)
    Taker, // نفذنا فوراً ضد أمر موجود (Aggressive - غالباً رسوم أعلى)
    None,  // لا ينطبق (في حالات الإلغاء أو الرفض)
}

/// نوع حدث التنفيذ
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionType {
    New,            // تأكيد قبول الأمر
    Trade,          // تنفيذ جزئي أو كلي (Fill)
    Canceled,       // تأكيد الإلغاء
    Replaced,       // تعديل الأمر
    Rejected,       // رفض (مع ذكر السبب)
    Expired,        // انتهاء الصلاحية
    TradeCorrection,// تصحيح من البورصة (نادر جداً ولكنه كارثي)
}

// =================================================================
// هيكل التنفيذ (The Execution Entity)
// =================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Execution {
    /// المعرف الداخلي للتنفيذ (Unique Event ID)
    pub exec_id: String,

    /// معرف التنفيذ لدى البورصة (للمطابقة مع كشوف الحساب)
    pub exchange_exec_id: Option<String>,

    /// ربط بالأمر الأصلي
    pub order_id: u64,
    pub client_order_id: String,

    /// تفاصيل الرمز والجهة
    pub symbol: String,
    pub side: OrderSide,

    /// نوع الحدث
    pub exec_type: ExecutionType,

    /// الكمية المنفذة في *هذا* الحدث تحديداً (Last Qty)
    pub last_qty: Decimal,

    /// السعر المنفذ في *هذا* الحدث (Last Price)
    pub last_price: Decimal,

    /// الكمية المتبقية من الأمر (Leaves Qty)
    pub leaves_qty: Decimal,

    /// الكمية التراكمية المنفذة للأمر ككل (Cumulative Qty)
    pub cum_qty: Decimal,

    /// العمولة المقتطعة
    pub commission: Decimal,
    pub commission_asset: Option<String>, // e.g., "BNB" or "USDT"

    /// دور السيولة (مهم جداً لحسابات الـ Micro-structure)
    pub role: LiquidityRole,

    /// وقت التنفيذ الدقيق (من محرك المطابقة أو البورصة)
    pub transaction_time: u64,

    /// ملاحظات نصية (مثل سبب الرفض)
    pub text: Option<String>,
}

impl Execution {
    /// حساب القيمة الإسمية لهذا التنفيذ (Notional Value)
    pub fn value(&self) -> Decimal {
        self.last_qty * self.last_price
    }

    /// هل هذا التنفيذ أغلق الأمر بالكامل؟
    pub fn is_closed(&self) -> bool {
        self.leaves_qty.is_zero() && (self.exec_type == ExecutionType::Trade || self.exec_type == ExecutionType::Canceled)
    }

    /// هل هذا مجرد تأكيد استلام (ليس صفقة مالية)؟
    pub fn is_informative_only(&self) -> bool {
        matches!(self.exec_type, ExecutionType::New | ExecutionType::Canceled | ExecutionType::Rejected)
    }

    /// إنشاء تقرير سريع للرفض (Helper)
    pub fn reject(order_id: u64, client_id: String, reason: String) -> Self {
        Self {
            exec_id: uuid::Uuid::new_v4().to_string(),
            exchange_exec_id: None,
            order_id,
            client_order_id: client_id,
            symbol: "UNKNOWN".to_string(),
            side: OrderSide::Buy, // Default dummy
            exec_type: ExecutionType::Rejected,
            last_qty: Decimal::ZERO,
            last_price: Decimal::ZERO,
            leaves_qty: Decimal::ZERO,
            cum_qty: Decimal::ZERO,
            commission: Decimal::ZERO,
            commission_asset: None,
            role: LiquidityRole::None,
            transaction_time: chrono::Utc::now().timestamp_millis() as u64,
            text: Some(reason),
        }
    }
}

// للطباعة المنظمة في السجلات
impl fmt::Display for Execution {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let type_str = format!("{:?}", self.exec_type).to_uppercase();
        if self.is_informative_only() {
            write!(f, "[EXEC::{}] Order #{} ({})", type_str, self.order_id, self.text.as_deref().unwrap_or("-"))
        } else {
            write!(
                f,
                "[EXEC::{}] Order #{} | {:?} {} @ {} | Fee: {} {:?} | Role: {:?}",
                type_str,
                self.order_id,
                self.side,
                self.last_qty,
                self.last_price,
                self.commission,
                self.commission_asset.as_deref().unwrap_or("?"),
                self.role
            )
        }
    }
}