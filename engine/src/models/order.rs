/*
 * ALPHA SOVEREIGN - UNIVERSAL ORDER MODEL
 * =================================================================
 * Component Name: engine/src/models/order.rs
 * Core Responsibility: توحيد هيكلية الأوامر لتتوافق مع جميع البروتوكولات.
 * Status: FINAL PRODUCTION (High Precision)
 * =================================================================
 */

use serde::{Serialize, Deserialize};
use rust_decimal::Decimal;
use rust_decimal::prelude::Zero; // لاستخدام Decimal::ZERO
use std::fmt;
use uuid::Uuid;

// =================================================================
// التعدادات الصارمة (Strict Enums)
// =================================================================

/// نوع الأمر (يحدد سلوك التنفيذ)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Market,             // الشراء بسعر السوق الحالي (الأسرع، الأخطر)
    Limit,              // الشراء بسعر محدد أو أفضل (الأكثر أماناً)
    StopLoss,           // أمر سوق يتفعل عند الوصول لسعر معين
    StopLimit,          // أمر محدد يتفعل عند الوصول لسعر معين
    TakeProfit,         // جني أرباح
    TakeProfitLimit,    // جني أرباح محدد
    TrailingStop,       // وقف خسارة متحرك
}

/// مدة صلاحية الأمر (Time In Force)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TimeInForce {
    GTC, // Good Till Cancel (يبقى حتى نلغيه)
    IOC, // Immediate Or Cancel (نفذ ما تستطيع فوراً وألغ الباقي)
    FOK, // Fill Or Kill (الكل أو لا شيء)
    GTD, // Good Till Date (حتى تاريخ معين)
}

/// حالة الأمر الحالية (دورة الحياة)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Created,        // تم الإنشاء داخلياً ولم يرسل بعد
    PendingNew,     // تم الإرسال وننتظر تأكيد البورصة
    New,            // البورصة قبلت الأمر وهو نشط في الدفتر
    PartiallyFilled,// تم تنفيذ جزء منه
    Filled,         // تم التنفيذ بالكامل
    Canceled,       // تم الإلغاء يدوياً
    Rejected,       // تم الرفض من البورصة (خطأ)
    Expired,        // انتهت صلاحيته
}

/// جانب الأمر (الشراء/البيع)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderSide {
    Buy,
    Sell,
}

// =================================================================
// الهيكل الرئيسي للأمر (The Order Entity)
// =================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    /// المعرف الداخلي (Internal ID) - رقمي للسرعة داخل المحرك
    pub id: u64,

    /// معرف التتبع الخارجي (Client Order ID)
    /// سلسلة نصية فريدة نرسلها للبورصة لربط الردود بالأوامر
    pub client_order_id: String,

    /// معرف البورصة (Exchange Order ID)
    /// يتم تعبئته لاحقاً عندما ترد البورصة بالتأكيد
    pub exchange_order_id: Option<String>,

    /// معرف الاستراتيجية التي ولدت الأمر (Forensic Trace)
    pub strategy_id: String,

    /// اسم الرمز (e.g., "BTCUSDT")
    pub symbol: String,

    /// البورصة المستهدفة (e.g., "BINANCE")
    pub exchange: String,

    pub side: OrderSide,
    pub order_type: OrderType,
    pub time_in_force: TimeInForce,

    /// الكمية المطلوبة (بدقة عالية)
    pub original_qty: Decimal,

    /// الكمية المنفذة حتى الآن
    pub executed_qty: Decimal,
    
    /// السعر المحدد (للأوامر المحددة فقط)
    pub price: Option<Decimal>,
    
    /// سعر التفعيل (Stop Price)
    pub stop_price: Option<Decimal>,

    /// متوسط سعر التنفيذ (يحسب بناءً على الصفقات الجزئية)
    pub avg_fill_price: Option<Decimal>,

    pub status: OrderStatus,

    /// طوابع زمنية (Timestamps)
    pub created_at: u64,
    pub updated_at: u64,
}

impl Order {
    /// إنشاء أمر جديد (Factory Method)
    pub fn new(
        id: u64,
        strategy_id: String,
        symbol: String,
        exchange: String,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal,
        price: Option<Decimal>,
    ) -> Self {
        let now = chrono::Utc::now().timestamp_millis() as u64;
        
        // توليد Client ID فريد يتضمن اسم الاستراتيجية لسهولة التتبع
        let client_id = format!("ALPHA-{}-{}", strategy_id, Uuid::new_v4().simple());

        Self {
            id,
            client_order_id: client_id,
            exchange_order_id: None,
            strategy_id,
            symbol,
            exchange,
            side,
            order_type,
            time_in_force: TimeInForce::GTC, // الافتراضي
            original_qty: qty,
            executed_qty: Decimal::ZERO,
            price,
            stop_price: None,
            avg_fill_price: None,
            status: OrderStatus::Created,
            created_at: now,
            updated_at: now,
        }
    }

    /// هل الأمر نشط حالياً؟ (Active / Open)
    pub fn is_active(&self) -> bool {
        matches!(
            self.status,
            OrderStatus::New | OrderStatus::PartiallyFilled | OrderStatus::PendingNew
        )
    }

    /// هل الأمر انتهى؟ (Terminal State)
    pub fn is_closed(&self) -> bool {
        !self.is_active() && self.status != OrderStatus::Created
    }

    /// حساب النسبة المئوية للتنفيذ
    pub fn fill_percentage(&self) -> Decimal {
        if self.original_qty.is_zero() {
            return Decimal::ZERO;
        }
        (self.executed_qty / self.original_qty) * Decimal::from(100)
    }

    /// تحديث حالة الأمر بناءً على تنفيذ جديد
    pub fn update_execution(&mut self, fill_qty: Decimal, fill_price: Decimal) {
        // تحديث المتوسط المرجح للسعر (Weighted Average Price)
        let old_total_val = self.executed_qty * self.avg_fill_price.unwrap_or(Decimal::ZERO);
        let fill_val = fill_qty * fill_price;
        
        self.executed_qty += fill_qty;
        
        if !self.executed_qty.is_zero() {
            self.avg_fill_price = Some((old_total_val + fill_val) / self.executed_qty);
        }

        // تحديث الحالة
        if self.executed_qty >= self.original_qty {
            self.status = OrderStatus::Filled;
        } else {
            self.status = OrderStatus::PartiallyFilled;
        }
        
        self.updated_at = chrono::Utc::now().timestamp_millis() as u64;
    }
}

// لتسهيل الطباعة والتصحيح (Debugging)
impl fmt::Display for Order {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[Order #{}] {} {} {} @ {:?} (Status: {:?})",
            self.id,
            self.exchange,
            match self.side { OrderSide::Buy => "BUY", OrderSide::Sell => "SELL" },
            self.original_qty,
            self.price.unwrap_or(Decimal::ZERO),
            self.status
        )
    }
}