/*
 * ALPHA SOVEREIGN - TRANSPORT LAYER ABSTRACTION
 * =================================================================
 * Component Name: engine/src/transport/mod.rs
 * Core Responsibility: توحيد بروتوكولات الاتصال وعزل المحرك عن تعقيدات الشبكة (Integration Pillar).
 * Design Pattern: Adapter / Event Bus / Observer
 * Forensic Impact: يضمن أن كل رسالة تدخل أو تخرج يتم ختمها بختم زمني (Timestamp) ومصدر (Source) للتحقيق لاحقاً.
 * =================================================================
 */

use serde::{Serialize, Deserialize};
use tokio::sync::mpsc;
use crate::error::AlphaResult;
use crate::matching::{Order, Trade};

// تعريف الوحدات الفرعية (سنقوم ببنائها لاحقاً)
pub mod grpc;       // الاتصال الداخلي مع Python Brain
pub mod exchange;   // الاتصال الخارجي مع البورصات (Binance/Kraken)

// =================================================================
// الأحداث الموحدة (Unified Transport Events)
// =================================================================

/// هذا هو "الدم" الذي يجري في عروق النظام.
/// يمثل أي حدث قادم من العالم الخارجي نحو المحرك.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IngressEvent {
    /// تحديث بيانات السوق (سعر، عمق، صفقة)
    MarketData {
        symbol: String,
        price: rust_decimal::Decimal,
        timestamp: u64,
    },
    
    /// أمر تداول جديد قادم من الدماغ
    NewOrderRequest(Order),
    
    /// طلب إلغاء أمر
    CancelOrderRequest {
        symbol_id: u32,
        order_id: u64,
    },
    
    /// إشارة إدارية (إيقاف النظام، تغيير الإعدادات)
    SystemCommand(SystemCommand),
}

/// يمثل أي حدث خارج من المحرك نحو العالم.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EgressEvent {
    /// تقرير تنفيذ صفقة (نرسله للبورصة وللدماغ)
    OrderExecution(Trade),
    
    /// تحديث حالة أمر (مرفوض، ملغى)
    OrderStatusUpdate {
        order_id: u64,
        status: String,
        reason: Option<String>,
    },
    
    /// تنبيه مخاطر (نرسله للدماغ وللمراقبة)
    RiskAlert {
        level: String,
        message: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SystemCommand {
    Shutdown,
    PauseTrading,
    ResumeTrading,
    ReloadConfig,
}

// =================================================================
// واجهة الاتصال المجردة (The Abstract Transporter)
// =================================================================

/// أي وسيلة نقل (gRPC, WebSocket) يجب أن تطبق هذه الواجهة.
/// هذا يسمح لنا بتبديل البورصات أو البروتوكولات دون تغيير سطر واحد في كود المحرك.
#[async_trait::async_trait]
pub trait Transporter: Send + Sync {
    /// اسم الناقل (للـ Logging)
    fn name(&self) -> &str;

    /// بدء الاستماع للأحداث (Infinite Loop)
    /// يقوم بإرسال الأحداث المستلمة عبر القناة `sender`
    async fn start(&self, sender: mpsc::Sender<IngressEvent>) -> AlphaResult<()>;

    /// إرسال حدث للخارج
    async fn send(&self, event: EgressEvent) -> AlphaResult<()>;
}

/// قناة الاتصال المركزية (Event Bus)
/// تستخدم لتمرير الرسائل بين خيوط النظام المختلفة
pub type EventTx = mpsc::Sender<IngressEvent>;
pub type EventRx = mpsc::Receiver<IngressEvent>;

/// إنشاء قناة اتصال عالية الأداء
pub fn create_event_bus(capacity: usize) -> (EventTx, EventRx) {
    mpsc::channel(capacity)
}