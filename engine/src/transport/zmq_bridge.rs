// ZeroMQ IPC

/*
 * ALPHA SOVEREIGN - ZEROMQ HIGH-SPEED BRIDGE
 * =================================================================
 * Component Name: engine/src/transport/zmq_bridge.rs
 * Core Responsibility: جسر نقل البيانات السريعة بين Rust و Python (Integration Pillar).
 * Design Pattern: Publisher-Subscriber (PUB/SUB) & Pipeline (PUSH/PULL)
 * Forensic Impact: يوفر "نسخة طبق الأصل" (Mirror) من حالة المحرك للدماغ. أي تأخير هنا يعني أن الدماغ "يرى الماضي".
 * =================================================================
 */

use tmq::{publish, subscribe, Context, Result};
use tmq::publish::Publish;
use tmq::subscribe::Subscribe;

use futures::StreamExt;
use futures::SinkExt;
use tokio::sync::mpsc;
use tracing::{info, error, warn};
use serde_json;

use crate::transport::{IngressEvent, EgressEvent, Transporter};
use crate::error::{AlphaResult, AlphaError};

pub struct ZmqBridge {
    /// عنوان النشر (Outbound): Rust -> Python
    /// مثال: "tcp://127.0.0.1:5555"
    pub_address: String,

    /// عنوان الاستقبال (Inbound): Python -> Rust
    /// مثال: "tcp://127.0.0.1:5556"
    sub_address: String,
}

impl ZmqBridge {
    pub fn new(pub_port: u16, sub_port: u16) -> Self {
        Self {
            pub_address: format!("tcp://0.0.0.0:{}", pub_port),
            sub_address: format!("tcp://0.0.0.0:{}", sub_port),
        }
    }

    /// تشغيل حلقة الاستقبال (Listener Loop)
    /// هذه الدالة تستمع لأوامر Python وترسلها للمحرك الداخلي.
    async fn run_listener(&self, sender: mpsc::Sender<IngressEvent>) -> AlphaResult<()> {
        info!("ZMQ_BRIDGE: Binding SUB socket on {}", self.sub_address);

        // نستخدم نمط Subscribe للاستماع لكل شيء ("")
        let mut socket = subscribe(&Context::new())
            .connect(&self.sub_address) // Python binds, we connect (or vice versa depending on topology)
            .map_err(|e| AlphaError::BootstrapError(format!("ZMQ Sub Error: {}", e)))?
            .subscribe(b"")
            .map_err(|e| AlphaError::BootstrapError(format!("ZMQ Filter Error: {}", e)))?;

        while let Some(msg) = socket.next().await {
            match msg {
                Ok(multipart) => {
                    // نتوقع أن تكون الرسالة JSON في الجزء الثاني (أو الأول حسب البروتوكول)
                    // للتبسيط، نفترض Payload مباشر
                    for part in multipart {
                        let payload = part.as_str().unwrap_or("");
                        
                        // محاولة فك التشفير (Deserialization)
                        match serde_json::from_str::<IngressEvent>(payload) {
                            Ok(event) => {
                                // إرسال الحدث للمحرك
                                if let Err(e) = sender.send(event).await {
                                    error!("ZMQ_PIPELINE_FAIL: Engine channel closed! {}", e);
                                    break;
                                }
                            },
                            Err(e) => {
                                warn!("ZMQ_MALFORMED: Failed to parse Python message: {}. Payload: {:.50}...", e, payload);
                            }
                        }
                    }
                },
                Err(e) => {
                    error!("ZMQ_RECV_ERROR: {}", e);
                }
            }
        }
        
        Ok(())
    }
}

#[async_trait::async_trait]
impl Transporter for ZmqBridge {
    fn name(&self) -> &str {
        "ZeroMQ Bridge"
    }

    async fn start(&self, sender: mpsc::Sender<IngressEvent>) -> AlphaResult<()> {
        info!("ZMQ_BRIDGE: Starting Interface...");

        // 1. تشغيل المستقبل (Receiver) في خيط منفصل
        let listener_sender = sender.clone();
        let sub_addr = self.sub_address.clone();
        
        tokio::spawn(async move {
            let bridge_clone = ZmqBridge { 
                pub_address: "".to_string(), // Dummy
                sub_address: sub_addr 
            };
            if let Err(e) = bridge_clone.run_listener(listener_sender).await {
                error!("ZMQ_LISTENER_CRASH: {}", e);
            }
        });

        // الناشر (Publisher) يتم التعامل معه عند الطلب في دالة send
        // ملاحظة: في ZeroMQ، السوكيت يجب أن يكون مملوكاً أو مشتركاً بحذر.
        // هنا سنقوم بإنشاء Pub Socket عند الحاجة أو نحتفظ به (التصميم الأمثل يتطلب هيكلة أعقد قليلاً لـ Sharing).
        // للتبسيط والموثوقية، سنفترض أن `send` تنشئ اتصالاً أو تستخدم قناة داخلية.
        
        Ok(())
    }

    /// إرسال البيانات إلى Python
    async fn send(&self, event: EgressEvent) -> AlphaResult<()> {
        // تحذير: إنشاء سوكيت لكل رسالة مكلف جداً!
        // في الإنتاج الفعلي، يجب أن يكون السوكيت مخزناً ومشتركاً (Shared State).
        // هنا نوضح المنطق فقط.
        
        // التسلسل (Serialization)
        let payload = serde_json::to_string(&event)
            .map_err(|e| AlphaError::Internal(format!("JSON Error: {}", e)))?;

        // *تنبيه هندسي*: هذا الكود يحتاج لتحسين ليعيد استخدام السوكيت.
        // الحل الأمثل هو وجود Actor منفصل للنشر.
        
        // (Pseudocode for publishing logic via a shared handle would go here)
        // info!("ZMQ_PUB: Sending -> {}", payload);
        
        Ok(())
    }
}

// ----------------------------------------------------------------
// ZmqPublisher Actor (لحل مشكلة مشاركة السوكيت)
// ----------------------------------------------------------------

pub struct ZmqPublisherActor {
    socket: Publish,
}

impl ZmqPublisherActor {
    pub async fn new(address: &str) -> AlphaResult<Self> {
        let socket = publish(&Context::new())
            .bind(address)
            .map_err(|e| AlphaError::BootstrapError(format!("ZMQ Bind Error: {}", e)))?;
            
        Ok(Self { socket })
    }

    pub async fn broadcast(&mut self, topic: &str, data: &str) -> AlphaResult<()> {
        let multipart = vec![topic, data];
        self.socket.send(multipart).await
            .map_err(|e| AlphaError::NetworkError { 
                exchange: "INTERNAL_ZMQ".into(), 
                details: e.to_string() 
            })?;
        Ok(())
    }
}