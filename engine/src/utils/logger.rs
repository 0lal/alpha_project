// Lock-free Logger & Data Structure

/*
 * ALPHA SOVEREIGN - NON-BLOCKING ASYNC LOGGER
 * =================================================================
 * Component Name: engine/src/utils/logger.rs
 * Core Responsibility: 
 * 1. تسجيل الأحداث محلياً دون تعطيل المسار الحرج (Performance Pillar).
 * 2. تعريف هيكل البيانات لنقل السجلات إلى الواجهات الخارجية (Integration Pillar).
 * Design Pattern: Async Appender / Ring Buffer / DTO
 * Status: HYBRID (Disk Writing + Network Serialization)
 * =================================================================
 */

use std::path::Path;
use tracing::Level;
use tracing_appender::non_blocking::{NonBlocking, WorkerGuard};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};
use serde::{Deserialize, Serialize}; // [مضاف] للتسلسل

// =================================================================
// 1. هياكل البيانات (Data Structures)
// هذا هو الجزء الذي طلبه المترجم في lib.rs
// =================================================================

/// هيكل السجل القابل للنقل (Serializable Log Entry).
/// نستخدم هذا الهيكل عندما نريد إرسال السجل إلى Python Brain أو Flutter UI
/// وليس للكتابة في الملفات النصية (التي تتولاها مكتبة tracing).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub level: String,      // مستوى الخطورة (INFO, WARN, ERROR)
    pub message: String,    // نص الرسالة
    pub timestamp: u64,     // التوقيت (Epoch Millis)
}

impl LogEntry {
    /// دالة مساعدة لإنشاء سجل جديد بسرعة
    pub fn new(level: &str, message: &str) -> Self {
        Self {
            level: level.to_string(),
            message: message.to_string(),
            timestamp: chrono::Utc::now().timestamp_millis() as u64,
        }
    }
}

// =================================================================
// 2. نظام التسجيل غير المتزامن (Async Tracing System)
// هذا هو النظام المعقد المسؤول عن الكتابة في الملفات بسرعة قصوى
// =================================================================

/// تهيئة نظام التسجيل العالمي.
/// يجب استدعاء هذه الدالة مرة واحدة فقط في `main.rs`.
/// تعيد `WorkerGuard` الذي يجب الاحتفاظ به حياً حتى نهاية البرنامج.
pub fn init_logger(log_dir: &str, file_name: &str, level: &str) -> WorkerGuard {
    
    // أ. إعداد الكتابة الدورية للملفات (Rolling File Appender)
    // يقوم بإنشاء ملف جديد كل يوم أو ساعة تلقائياً.
    let file_appender = tracing_appender::rolling::daily(log_dir, file_name);

    // ب. تحويل الكاتب إلى "غير متزامن" (Non-Blocking)
    // هذا هو السحر: Main Thread يكتب في Buffer، والـ Guard يدير الخيط الخلفي.
    let (non_blocking_file, guard) = tracing_appender::non_blocking(file_appender);

    // ج. تكوين تنسيق السجلات (Format)
    // نريد: Timestamp | Level | Thread ID | Target | Message
    let file_layer = fmt::layer()
        .with_writer(non_blocking_file)
        .with_thread_ids(true) // مهم جداً جنائياً لمعرفة من قام بالفعل
        .with_thread_names(true)
        .with_file(true)
        .with_line_number(true)
        .with_target(false) // تقليل الضجيج
        .with_ansi(false)   // لا نريد ألواناً في الملف النصي
        .compact();         // تنسيق مضغوط لتوفير المساحة

    // د. إعداد الفلتر (Filter)
    // يحدد مستوى التفاصيل (INFO, DEBUG, WARN) بناءً على الإعدادات
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(level));

    // هـ. تجميع الطبقات وتعيينها عالمياً
    tracing_subscriber::registry()
        .with(filter)
        .with(file_layer)
        .init();

    tracing::info!("LOGGER: Initialized non-blocking logging system at {}/{}", log_dir, file_name);

    guard
}

// =================================================================
// 3. وحدات مساعدة للتسجيل المهيكل (Structured Logging Helper)
// =================================================================

/// تسجيل عملية تداول (للأرشفة النصية بجانب التليمترية)
pub fn log_trade(symbol: &str, side: &str, price: &str, qty: &str, exec_id: &str) {
    tracing::info!(
        target: "TRADE_AUDIT",
        symbol = symbol,
        side = side,
        price = price,
        qty = qty,
        exec_id = exec_id,
        "EXECUTION CONFIRMED"
    );
}

/// تسجيل خطأ في المخاطر
pub fn log_risk_reject(reason: &str, limit: &str, actual: &str) {
    tracing::warn!(
        target: "RISK_AUDIT",
        reason = reason,
        limit = limit,
        actual = actual,
        "ORDER REJECTED BY RISK ENGINE"
    );
}