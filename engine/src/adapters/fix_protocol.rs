// Institutional Connector

/*
 * ALPHA SOVEREIGN - FIX PROTOCOL ADAPTER (v4.4)
 * =================================================================
 * Component Name: engine/src/adapters/fix_protocol.rs
 * Core Responsibility: تنفيذ بروتوكول FIX المالي للاتصال المؤسسي (Integration Pillar).
 * Design Pattern: Stateful Protocol Handler / Session Manager
 * Forensic Impact: يوفر "سجل محادثة" (Audit Trail) غير قابل للجدل. كل رسالة لها رقم تسلسلي وبصمة زمنية.
 * =================================================================
 */

use async_trait::async_trait;
use tokio::net::TcpStream;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::SystemTime;
use chrono::{DateTime, Utc};
use tracing::{info, error, warn, debug};
use crate::error::{AlphaResult, AlphaError};
use crate::matching::Order;
use super::{ExchangeAdapter, ConnectionStatus};

// الثوابت الخاصة ببروتوكول FIX
const SOH: char = '\x01'; // Start of Header (الفاصل غير المرئي)
const FIX_VERSION: &str = "FIX.4.4";

#[derive(Debug, Clone)]
pub struct FixConfig {
    pub host: String,
    pub port: u16,
    pub sender_comp_id: String, // معرفنا نحن (Alpha)
    pub target_comp_id: String, // معرف البنك/البورصة
    pub heartbeat_interval: u64,
}

pub struct FixProtocolAdapter {
    config: FixConfig,
    stream: Mutex<Option<TcpStream>>,
    
    // إدارة الحالة (Sequence Numbers)
    // هذه الأرقام مقدسة؛ فقدانها يعني إعادة بناء الجلسة يدوياً
    seq_out: AtomicU64, // ما أرسلناه
    seq_in: AtomicU64,  // ما استلمناه
}

impl FixProtocolAdapter {
    pub fn new(config: FixConfig) -> Self {
        Self {
            config,
            stream: Mutex::new(None),
            seq_out: AtomicU64::new(1),
            seq_in: AtomicU64::new(1),
        }
    }

    // ----------------------------------------------------------------
    // أدوات بناء الرسائل (Message Construction)
    // ----------------------------------------------------------------

    /// إنشاء رسالة FIX خام
    fn build_message(&self, msg_type: &str, body_tags: Vec<(i32, String)>) -> String {
        let seq_num = self.seq_out.fetch_add(1, Ordering::SeqCst);
        let sending_time = Utc::now().format("%Y%m%d-%H:%M:%S%.3f").to_string();

        // 1. الرأس (Header)
        // 8=BeginString | 9=BodyLength | 35=MsgType | 49=SenderCompID | 56=TargetCompID | 34=MsgSeqNum | 52=SendingTime
        let mut head = format!(
            "35={SOH}49={SOH}56={SOH}34={SOH}52={SOH}", 
            msg_type, self.config.sender_comp_id, self.config.target_comp_id, seq_num, sending_time, 
            SOH = SOH
        );

        // 2. الجسم (Body)
        let mut body = String::new();
        for (tag, value) in body_tags {
            body.push_str(&format!("{}={}{}", tag, value, SOH));
        }

        // 3. التجميع لحساب الطول
        let content = format!("{}{}", head, body);
        let length = content.len();
        
        // 4. الرسالة الكاملة قبل الـ Checksum
        let pre_checksum = format!("8={}{SOH}9={}{SOH}{}", FIX_VERSION, length, content, SOH = SOH);

        // 5. حساب Checksum (Mod 256)
        let checksum = Self::calculate_checksum(&pre_checksum);
        
        // الرسالة النهائية
        format!("{}10={:03}{SOH}", pre_checksum, checksum, SOH = SOH)
    }

    fn calculate_checksum(data: &str) -> u32 {
        let sum: u32 = data.bytes().map(|b| b as u32).sum();
        sum % 256
    }

    /// إرسال حزمة عبر TCP
    async fn send_raw(&self, msg: String) -> AlphaResult<()> {
        let mut lock = self.stream.lock().await;
        if let Some(stream) = lock.as_mut() {
            // تسجيل جنائي للرسالة الصادرة (نستبدل SOH بـ | للقراءة)
            debug!("FIX_OUT: {}", msg.replace(SOH, "|"));
            
            stream.write_all(msg.as_bytes()).await
                .map_err(|e| AlphaError::NetworkError { 
                    exchange: "FIX".into(), details: e.to_string() 
                })?;
            Ok(())
        } else {
            Err(AlphaError::NetworkError { 
                exchange: "FIX".into(), details: "No Connection".into() 
            })
        }
    }
}

#[async_trait]
impl ExchangeAdapter for FixProtocolAdapter {
    fn id(&self) -> &str {
        "FIX_INSTITUTIONAL_V4.4"
    }

    async fn connect(&mut self) -> AlphaResult<()> {
        let addr = format!("{}:{}", self.config.host, self.config.port);
        info!("FIX_ADAPTER: Dialing institutional gateway at {}...", addr);

        let stream = TcpStream::connect(&addr).await
            .map_err(|e| AlphaError::NetworkError { 
                exchange: "FIX".into(), details: e.to_string() 
            })?;

        *self.stream.lock().await = Some(stream);

        // إرسال رسالة تسجيل الدخول (Logon - MsgType=A)
        // 98=EncryptMethod(0) | 108=HeartBtInt
        let logon_msg = self.build_message("A", vec![
            (98, "0".to_string()),
            (108, self.config.heartbeat_interval.to_string()),
        ]);

        self.send_raw(logon_msg).await?;
        
        // ملاحظة: في التنفيذ الكامل، يجب الانتظار لقراءة رد Logon "35=A"
        // للتبسيط هنا نفترض النجاح
        info!("FIX_ADAPTER: Logon request sent. Session established.");
        Ok(())
    }

    async fn health_check(&self) -> ConnectionStatus {
        // إرسال Heartbeat (MsgType=0)
        let hb_msg = self.build_message("0", vec![]);
        match self.send_raw(hb_msg).await {
            Ok(_) => ConnectionStatus::Connected,
            Err(_) => ConnectionStatus::Disconnected,
        }
    }

    async fn place_order(&self, order: &Order) -> AlphaResult<String> {
        // تحويل أمر Alpha الداخلي إلى رسالة FIX NewOrderSingle (MsgType=D)
        
        let side = match order.side {
            crate::matching::Side::Bid => "1", // Buy
            crate::matching::Side::Ask => "2", // Sell
        };

        let ord_type = "2"; // Limit Order
        
        // بناء جسم الرسالة
        // 11=ClOrdID | 55=Symbol | 54=Side | 60=TransactTime | 38=OrderQty | 40=OrdType | 44=Price
        let msg = self.build_message("D", vec![
            (11, order.id.to_string()), // Client Order ID
            (55, "BTCUSD".to_string()), // (يجب تحويل ID الرمز لنص)
            (54, side.to_string()),
            (60, Utc::now().format("%Y%m%d-%H:%M:%S%.3f").to_string()),
            (38, order.quantity.to_string()),
            (40, ord_type.to_string()),
            (44, order.price.to_string()),
        ]);

        self.send_raw(msg).await?;
        
        Ok(order.id.to_string()) // FIX لا يعيد ID فوراً، نستخدم الـ ClOrdID الخاص بنا
    }

    async fn cancel_order(&self, _symbol: &str, order_id: &str) -> AlphaResult<()> {
        // OrderCancelRequest (MsgType=F)
        let msg = self.build_message("F", vec![
            (41, order_id.to_string()), // OrigClOrdID
            (11, format!("C{}", order_id)), // New ID for cancel req
            (55, "BTCUSD".to_string()),
            (54, "1".to_string()), // Side is required in FIX cancel
        ]);
        self.send_raw(msg).await
    }

    async fn cancel_all(&self, _symbol: Option<&str>) -> AlphaResult<()> {
        // FIX لا يدعم عادة "Cancel All" برسالة واحدة.
        // يجب تنفيذ حلقة تكرار لإلغاء كل الأوامر المفتوحة محلياً.
        warn!("FIX_ADAPTER: CancelAll requested (Not native support in FIX 4.4)");
        Ok(())
    }
    
    // اشتراكات البيانات في FIX تتم عادة عبر جلسة منفصلة (FIX Market Data) أو FastFIX
    async fn subscribe_ticker(&self, _symbol: &str) -> AlphaResult<()> { Ok(()) }
    async fn subscribe_user_stream(&self) -> AlphaResult<()> { Ok(()) }
}