/*
 * ==============================================================================
 * ALPHA SOVEREIGN - RUST EVENT QUEUE MANAGER (The Iron Gate)
 * ==============================================================================
 * Component: data/buffers/event_queue_mgr.rs
 * Core Responsibility: إدارة طوابير البيانات عالية السرعة بضمان "عدم الفقدان".
 * Performance: Zero-Copy handling & Backpressure support.
 * Integration: Designed to be wrapped by PyO3 for Python access.
 * ==============================================================================
 */

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::time::{timeout, Duration};

// تعريف أنواع البيانات التي يستقبلها الطابور
// نستخدم Enum لتوحيد أنواع البيانات المختلفة في قناة واحدة
#[derive(Debug, Clone)]
pub enum IngestionEvent {
    MarketTick { symbol: String, price: f64, volume: f64, ts: u64 },
    OrderBookSnapshot { symbol: String, depth: usize },
    SystemSignal { code: u16, message: String },
    // إشارة خاصة لإيقاف الطابور بأمان
    Terminate,
}

// هيكل مدير الطابور
pub struct EventQueueManager {
    sender: mpsc::Sender<IngestionEvent>,
    receiver: mpsc::Receiver<IngestionEvent>, // في الواقع، المستهلك سيسحب هذا
    capacity: usize,
    
    // مقاييس الأداء (Telemetry)
    enqueued_count: Arc<AtomicUsize>,
    dropped_count: Arc<AtomicUsize>,
}

impl EventQueueManager {
    /// إنشاء مدير طوابير جديد
    /// capacity: الحد الأقصى للعناصر في الذاكرة (لمنع استهلاك الرام بالكامل)
    pub fn new(capacity: usize) -> Self {
        let (tx, rx) = mpsc::channel(capacity);
        
        Self {
            sender: tx,
            receiver: rx,
            capacity,
            enqueued_count: Arc::new(AtomicUsize::new(0)),
            dropped_count: Arc::new(AtomicUsize::new(0)),
        }
    }

    /// دالة الإدخال الآمن (The Safe Push)
    /// هذه الدالة تحاول الإدخال، وإذا كان الطابور ممتلئاً، تنتظر (Backpressure)
    /// بدلاً من رفض البيانات فوراً.
    pub async fn push_safe(&self, event: IngestionEvent) -> Result<(), String> {
        // ننتظر 100 ملي ثانية كحد أقصى لإيجاد مكان في الطابور
        let result = timeout(Duration::from_millis(100), self.sender.send(event)).await;

        match result {
            Ok(Ok(_)) => {
                self.enqueued_count.fetch_add(1, Ordering::Relaxed);
                Ok(())
            }
            Ok(Err(_)) => {
                // القناة مغلقة (النظام متوقف)
                Err("CHANNEL_CLOSED".to_string())
            }
            Err(_) => {
                // انتهى الوقت والطابور ما زال ممتلئاً (حالة حرجة)
                self.dropped_count.fetch_add(1, Ordering::Relaxed);
                Err("QUEUE_FULL_TIMEOUT".to_string())
            }
        }
    }

    /// دالة الإدخال السريع (Fire & Forget)
    /// تستخدم للبيانات الأقل أهمية (مثل السجلات) حيث السرعة أهم من الضمان.
    pub fn push_fast(&self, event: IngestionEvent) -> Result<(), String> {
        match self.sender.try_send(event) {
            Ok(_) => {
                self.enqueued_count.fetch_add(1, Ordering::Relaxed);
                Ok(())
            }
            Err(mpsc::error::TrySendError::Full(_)) => {
                self.dropped_count.fetch_add(1, Ordering::Relaxed);
                Err("QUEUE_FULL".to_string())
            }
            Err(mpsc::error::TrySendError::Closed(_)) => {
                Err("CHANNEL_CLOSED".to_string())
            }
        }
    }

    /// استخراج المستهلك (Consumer)
    /// يتم استدعاؤها من قبل "محرك المعالجة" لبدء سحب البيانات
    pub fn take_receiver(mut self) -> Option<mpsc::Receiver<IngestionEvent>> {
        // نستخدم Option للتحايل على نظام الملكية في Rust إذا لزم الأمر
        // هنا نقوم بإنشاء قناة جديدة وهمية لاستبدال الحالية وإرجاع الأصلية
        let (tx, rx) = mpsc::channel(1);
        self.sender = tx; // استبدال المرسل بآخر وهمي (أو مغلق)
        let mut original_rx = rx; 
        std::mem::swap(&mut self.receiver, &mut original_rx);
        
        Some(original_rx)
    }

    /// تقرير الحالة
    pub fn get_metrics(&self) -> (usize, usize) {
        (
            self.enqueued_count.load(Ordering::Relaxed),
            self.dropped_count.load(Ordering::Relaxed)
        )
    }
}

// -----------------------------------------------------------------------------
// اختبار وحدة بسيط للتأكد من العمل
// -----------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_queue_backpressure() {
        let mgr = EventQueueManager::new(2); // سعة صغيرة جداً للاختبار

        // 1. ملء الطابور
        assert!(mgr.push_safe(IngestionEvent::SystemSignal { code: 1, message: "A".into() }).await.is_ok());
        assert!(mgr.push_safe(IngestionEvent::SystemSignal { code: 2, message: "B".into() }).await.is_ok());

        // 2. المحاولة الثالثة يجب أن تفشل (TimeOut) لأننا لم نسحب البيانات
        let res = mgr.push_safe(IngestionEvent::SystemSignal { code: 3, message: "C".into() }).await;
        assert!(res.is_err());
        assert_eq!(res.err().unwrap(), "QUEUE_FULL_TIMEOUT");
    }
}