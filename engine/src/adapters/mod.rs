/*
 * ALPHA SOVEREIGN - EXCHANGE ADAPTER INTERFACE
 * =================================================================
 * Component Name: engine/src/adapters/mod.rs
 * Core Responsibility: توحيد واجهات الاتصال بالبورصات المختلفة (Integration Pillar).
 * Design Pattern: Adapter / Factory
 * Forensic Impact: يعزل "مشاكل البورصة" عن "مشاكل المحرك". إذا فشل الاتصال، نعرف أنه خطأ السفير وليس الملك.
 * =================================================================
 */

use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use crate::error::AlphaResult;
use crate::matching::{Order, OrderType, Side};

// سنقوم ببناء هذه الوحدات لاحقاً
// pub mod binance;
// pub mod kraken;
// pub mod simulator; // للمحاكاة والاختبار

/// حالة اتصال المحول
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
    Maintenance, // البورصة في صيانة
    FatalError,  // توقف بسبب خطأ في التوثيق أو الحظر
}

/// الواجهة الذهبية التي يجب أن يطبقها أي محول بورصة
/// (The Contract that every exchange must sign)
#[async_trait]
pub trait ExchangeAdapter: Send + Sync {
    /// المعرف الفريد للمحول (e.g., "BINANCE_FUTURES_V2")
    fn id(&self) -> &str;

    /// بدء الاتصال (WebSockets + REST Auth)
    async fn connect(&mut self) -> AlphaResult<()>;

    /// فحص الصحة (Ping/Heartbeat)
    async fn health_check(&self) -> ConnectionStatus;

    // ------------------------------------------------------------
    // عمليات التداول (Execution)
    // ------------------------------------------------------------

    /// إرسال أمر للسوق
    /// يعود بـ ID الأمر الخارجي (Exchange Order ID)
    async fn place_order(&self, order: &Order) -> AlphaResult<String>;

    /// إلغاء أمر
    async fn cancel_order(&self, symbol: &str, order_id: &str) -> AlphaResult<()>;

    /// إلغاء جميع الأوامر فوراً (Panic Button)
    async fn cancel_all(&self, symbol: Option<&str>) -> AlphaResult<()>;

    // ------------------------------------------------------------
    // بيانات السوق (Market Data)
    // ------------------------------------------------------------
    
    /// الاشتراك في تدفق الأسعار لزوج معين
    async fn subscribe_ticker(&self, symbol: &str) -> AlphaResult<()>;
    
    /// الاشتراك في تحديثات المحفظة (Balance/Position)
    async fn subscribe_user_stream(&self) -> AlphaResult<()>;
}

/// مدير الجلسات (Session Manager)
/// يحتفظ بجميع السفراء النشطين ويوجه الأوامر للسفير الصحيح.
pub struct AdapterManager {
    /// خريطة: Exchange Name -> Adapter Instance
    adapters: RwLock<HashMap<String, Box<dyn ExchangeAdapter>>>,
}

impl AdapterManager {
    pub fn new() -> Self {
        Self {
            adapters: RwLock::new(HashMap::new()),
        }
    }

    /// تسجيل سفير جديد (بورصة جديدة)
    pub async fn register_adapter(&self, adapter: Box<dyn ExchangeAdapter>) {
        let mut map = self.adapters.write().await;
        tracing::info!("ADAPTER_MGR: Registering new exchange adapter: {}", adapter.id());
        map.insert(adapter.id().to_string(), adapter);
    }

    /// الحصول على سفير محدد بالاسم
    pub async fn get_adapter(&self, id: &str) -> Option<Arc<Box<dyn ExchangeAdapter>>> {
        // ملاحظة: للتنفيذ الحقيقي، قد نحتاج لتغيير هيكلية الملكية لتمكين المشاركة
        // هنا نستخدم منطقاً مبسطاً للتوضيح
        None // (في التنفيذ الكامل سنعيد مرجعاً ذكياً)
    }

    /// توجيه أمر "إلغاء الكل" لجميع البورصات المتصلة (Global Panic)
    pub async fn panic_shutdown(&self) {
        let map = self.adapters.read().await;
        tracing::warn!("ADAPTER_MGR: EXECUTION GLOBAL PANIC PROTOCOL ACROSS {} EXCHANGES", map.len());
        
        for (id, adapter) in map.iter() {
            tracing::warn!("ADAPTER_MGR: Sending CancelAll to {}", id);
            // نتجاهل الأخطاء هنا لأننا نريد المحاولة مع الجميع
            let _ = adapter.cancel_all(None).await;
        }
    }
}

// ----------------------------------------------------------------
// المصنع (Factory) لإنشاء المحولات ديناميكياً
// ----------------------------------------------------------------
pub struct AdapterFactory;

impl AdapterFactory {
    // هذه الدالة ستستخدم لاحقاً لقراءة ملف الإعدادات وإنشاء المحولات المطلوبة
    /*
    pub fn create(config: &str) -> Box<dyn ExchangeAdapter> {
        match config {
            "binance" => Box::new(binance::BinanceAdapter::new()),
            "kraken" => Box::new(kraken::KrakenAdapter::new()),
            _ => Box::new(simulator::SimAdapter::new()),
        }
    }
    */
}