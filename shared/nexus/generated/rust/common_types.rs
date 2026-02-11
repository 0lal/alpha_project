/*
 * ==============================================================================
 * ALPHA SOVEREIGN - COMMON TYPE DEFINITIONS
 * ==============================================================================
 * Component: common_types.rs
 * Responsibility: The canonical Rust structs used internally by the Engine.
 * Pattern: Domain Transfer Object (DTO) / Decoupling Layer
 * ==============================================================================
 */

use serde::{Deserialize, Serialize};
use std::fmt;

// ==============================================================================
// 1. ENUMS (المفردات الأساسية)
// ==============================================================================

/// اتجاه الصفقة (شراء/بيع)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Side {
    Buy,
    Sell,
}

impl fmt::Display for Side {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Side::Buy => write!(f, "BUY"),
            Side::Sell => write!(f, "SELL"),
        }
    }
}

/// نوع الأمر
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Market,          // تنفيذ فوري بأي سعر
    Limit,           // تنفيذ بسعر محدد أو أفضل
    StopLoss,        // أمر سوق يتفعل عند الوصول لسعر معين
    StopLimit,       // أمر محدد يتفعل عند سعر معين
    TakeProfit,      // جني أرباح
}

/// حالة الأمر (دورة الحياة)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Pending,         // تم الاستلام، في انتظار الإرسال للبورصة
    New,             // تم القبول في البورصة
    PartiallyFilled, // تم تنفيذ جزء منه
    Filled,          // تم التنفيذ بالكامل
    Canceled,        // تم الإلغاء
    Rejected,        // تم الرفض (من المخاطر أو البورصة)
    Expired,         // انتهت الصلاحية (TTL)
}

/// مدة صلاحية الأمر
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TimeInForce {
    GTC, // Good Till Canceled (حتى الإلغاء)
    IOC, // Immediate or Cancel (نفذ فوراً أو الغِ الباقي)
    FOK, // Fill or Kill (الكل أو لا شيء)
}

// ==============================================================================
// 2. CORE STRUCTS (الهياكل الرئيسية)
// ==============================================================================

/// يمثل "نبضة السوق" الموحدة داخل المحرك
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MarketTick {
    pub symbol: String,
    pub price: f64,
    pub volume: f64,
    pub timestamp_ms: u64, // توقيت البورصة
    pub arrived_at_ns: u64, // توقيت الوصول (لقياس الـ Latency)
}

/// يمثل طلب تداول قادم من "العقل" أو "الواجهة"
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderRequest {
    pub request_id: String,     // UUID من المصدر
    pub symbol: String,
    pub side: Side,
    pub order_type: OrderType,
    pub quantity: f64,
    pub price: Option<f64>,     // None if Market Order
    pub stop_price: Option<f64>,// None if not a Stop order
    pub leverage: u8,           // 1 = Spot
    pub time_in_force: TimeInForce,
    pub timestamp: u64,
}

/// يمثل أمراً نشطاً داخل النظام (State Object)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub internal_id: String,    // ID النظام
    pub exchange_id: Option<String>, // ID البورصة (يأتي لاحقاً)
    pub request: OrderRequest,  // تفاصيل الطلب الأصلي
    pub status: OrderStatus,
    
    // حالة التنفيذ
    pub filled_quantity: f64,
    pub average_fill_price: f64,
    pub remaining_quantity: f64,
    
    // التكاليف
    pub commission_paid: f64,
    pub commission_asset: String,
    
    // التوقيتات
    pub created_at: u64,
    pub updated_at: u64,
}

/// يمثل مركزاً مفتوحاً (Position) في المحفظة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub side: Side,            // Long / Short
    pub quantity: f64,
    pub entry_price: f64,
    pub current_price: f64,    // Mark Price
    pub leverage: u8,
    
    // الربح والخسارة
    pub unrealized_pnl: f64,
    pub realized_pnl: f64,
    
    // إدارة المخاطر
    pub liquidation_price: f64,
    pub margin_used: f64,
}

// ==============================================================================
// 3. CONVERSION TRAITS (محولات البروتوكولات)
// ==============================================================================
// هنا نربط بين Protobuf/Cap'n Proto وبين هذه الهياكل
// ملاحظة: يتم تفعيل هذا الجزء عند وجود الكود المولد (Generated Code)

/*
impl From<crate::proto::OrderType> for OrderType {
    fn from(proto_type: crate::proto::OrderType) -> Self {
        match proto_type {
            crate::proto::OrderType::MARKET => OrderType::Market,
            crate::proto::OrderType::LIMIT => OrderType::Limit,
            _ => OrderType::Market, // Default safety
        }
    }
}
*/

impl Order {
    /// إنشاء أمر جديد من طلب
    pub fn new(req: OrderRequest) -> Self {
        Order {
            internal_id: req.request_id.clone(), // مبدئياً نستخدم نفس الـ ID
            exchange_id: None,
            status: OrderStatus::Pending,
            filled_quantity: 0.0,
            average_fill_price: 0.0,
            remaining_quantity: req.quantity,
            commission_paid: 0.0,
            commission_asset: "USDT".to_string(), // Default logic needs refinement
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_millis() as u64,
            updated_at: 0,
            request: req,
        }
    }

    /// هل الأمر مكتمل؟ (لأغراض التنظيف)
    pub fn is_closed(&self) -> bool {
        matches!(
            self.status,
            OrderStatus::Filled | OrderStatus::Canceled | OrderStatus::Rejected | OrderStatus::Expired
        )
    }
}