// Blackbox Recorder

/*
 * ALPHA SOVEREIGN - HIGH-SPEED BLACK BOX RECORDER
 * =================================================================
 * Component Name: engine/src/hardware/telemetry_recorder.rs
 * Core Responsibility: تسجيل التليمترية بدقة النانوثانية للتحليل الجنائي (Explainability Pillar).
 * Design Pattern: Async Ring Buffer / Binary Logging
 * Forensic Impact: الدليل الوحيد القادر على إعادة بناء تسلسل الأحداث بدقة عندما تفشل كل الأنظمة الأخرى.
 * =================================================================
 */

use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{SystemTime, UNIX_EPOCH};
use crossbeam::channel::{bounded, Sender, Receiver};
use serde::{Serialize, Deserialize};
use tracing::{info, error};

// حجم القناة (عدد الأحداث قبل أن نضطر للانتظار - يجب أن يكون كبيراً)
const QUEUE_CAPACITY: usize = 1_000_000;
const BATCH_SIZE: usize = 1000;

/// أنواع الأحداث التي نسجلها (مضغوطة قدر الإمكان)
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[repr(u8)]
pub enum EventType {
    OrderIn = 1,       // استلام أمر
    RiskCheckStart = 2,
    RiskCheckEnd = 3,
    MatchingStart = 4,
    TradeExecuted = 5,
    OrderOut = 6,      // إرسال للبورصة
    Error = 255,
}

/// هيكل الحدث الثنائي (Fixed Size Struct)
/// هذا ما يتم تخزينه في الذاكرة والقرص. لا نستخدم JSON هنا للسرعة.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[repr(C)] // لضمان ترتيب الذاكرة
pub struct TelemetryFrame {
    pub timestamp_ns: u64, // 8 bytes
    pub event_type: EventType, // 1 byte
    pub entity_id: u64,    // OrderID or TradeID (8 bytes)
    pub value: i64,        // Price or Quantity (scaled) (8 bytes)
    pub duration_ns: u32,  // Latency if applicable (4 bytes)
    pub flags: u8,         // Extra info (1 byte)
}

pub struct TelemetryRecorder {
    sender: Sender<TelemetryFrame>,
    is_running: Arc<AtomicBool>,
    worker_handle: Option<thread::JoinHandle<()>>,
}

impl TelemetryRecorder {
    /// إنشاء مسجل جديد وتشغيل الخيط الخلفي
    pub fn new(file_path: &str) -> Self {
        let (tx, rx) = bounded(QUEUE_CAPACITY);
        let is_running = Arc::new(AtomicBool::new(true));
        
        let should_run = is_running.clone();
        let path = file_path.to_string();

        // تشغيل العامل الخلفي (Background Writer)
        let handle = thread::spawn(move || {
            Self::writer_loop(rx, path, should_run);
        });

        Self {
            sender: tx,
            is_running,
            worker_handle: Some(handle),
        }
    }

    /// تسجيل حدث (Hot Path - Zero Allocation)
    /// هذه الدالة يجب أن تكون سريعة جداً (nanoseconds).
    #[inline(always)]
    pub fn record(&self, event_type: EventType, entity_id: u64, value: i64, duration: u32) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        let frame = TelemetryFrame {
            timestamp_ns: now,
            event_type,
            entity_id,
            value,
            duration_ns: duration,
            flags: 0,
        };

        // محاولة الإرسال للقناة.
        // نستخدم try_send لتجنب تجميد المحرك إذا امتلأت القناة (نفضل فقدان السجل على توقف التداول)
        if let Err(_) = self.sender.try_send(frame) {
            // في حالة الامتلاء، يمكننا زيادة عداد "Dropped Frames" ذرياً
            // (لا نقوم بالطباعة هنا لأن الطباعة بطيئة)
        }
    }

    /// حلقة الكتابة الخلفية
    fn writer_loop(rx: Receiver<TelemetryFrame>, path: String, is_running: Arc<AtomicBool>) {
        // فتح الملف في وضع الإلحاق (Append)
        let file = match OpenOptions::new().create(true).append(true).open(&path) {
            Ok(f) => f,
            Err(e) => {
                error!("TELEMETRY_FAIL: Could not open file {}: {}", path, e);
                return;
            }
        };

        let mut writer = BufWriter::with_capacity(64 * 1024, file); // 64KB Buffer
        let mut buffer = Vec::with_capacity(BATCH_SIZE);

        info!("TELEMETRY: Black box recorder active at {}", path);

        while is_running.load(Ordering::Relaxed) || !rx.is_empty() {
            // تجميع دفعة من الأحداث
            while let Ok(frame) = rx.try_recv() {
                buffer.push(frame);
                if buffer.len() >= BATCH_SIZE {
                    break;
                }
            }

            if buffer.is_empty() {
                thread::sleep(std::time::Duration::from_millis(10));
                continue;
            }

            // كتابة البيانات الثنائية
            // نستخدم bincode للتسلسل السريع جداً
            for frame in &buffer {
                if let Ok(bytes) = bincode::serialize(frame) {
                     if let Err(e) = writer.write_all(&bytes) {
                         error!("TELEMETRY_WRITE_ERR: {}", e);
                     }
                }
            }
            
            // تفريغ المخزن المؤقت للقرص
            let _ = writer.flush();
            buffer.clear();
        }
        
        info!("TELEMETRY: Recorder stopped.");
    }

    /// إغلاق نظيف
    pub fn shutdown(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        if let Some(handle) = self.worker_handle.take() {
            let _ = handle.join();
        }
    }
}

// ----------------------------------------------------------------
// أداة استعادة البيانات (Forensic Reader)
// ----------------------------------------------------------------
// هذا الكود يستخدم لقراءة الملف الثنائي لاحقاً وتحويله لنص
pub fn replay_telemetry(path: &str) {
    use std::io::Read;
    
    let mut file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return,
    };

    println!("--- BLACK BOX REPLAY ---");
    // (Logic to read binary structs back and print readable text)
    // ...
}