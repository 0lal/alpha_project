// Hard Stop Logic

/*
 * ALPHA SOVEREIGN - HIGH-VELOCITY CIRCUIT BREAKER
 * =================================================================
 * Component Name: engine/src/risk/circuit_breaker.rs
 * Core Responsibility: إيقاف التداول فوراً عند رصد سلوك كارثي (Stability Pillar).
 * Design Pattern: Circuit Breaker / Leaky Bucket
 * Forensic Impact: يوفر "تقرير الحادث" (Crash Report) يوضح سبب الفصل بالضبط (الوقت، القيمة، الحد).
 * =================================================================
 */

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::{Duration, Instant};
use parking_lot::Mutex; // أسرع من std::sync::Mutex
use rust_decimal::Decimal;
use rust_decimal::prelude::FromPrimitive;
use tracing::{error, warn, info};
use crate::error::{AlphaError, AlphaResult};
use super::{trigger_emergency_stop, RiskLevel, RiskReport};

/// حالات القاطع
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,     // كل شيء طبيعي (التيار يمر)
    Open,       // تم الفصل (توقف تام)
    HalfOpen,   // وضع الاختبار (نسمح بصفقات صغيرة جداً للتجربة)
}

/// إعدادات القاطع (يتم تحميلها عند البدء)
#[derive(Debug, Clone)]
pub struct BreakerConfig {
    pub max_drawdown_per_minute: Decimal, // أقصى خسارة مسموحة في الدقيقة
    pub max_consecutive_errors: u32,      // أقصى عدد أخطاء متتالية
    pub cooldown_period: Duration,        // فترة التبريد قبل الانتقال لـ HalfOpen
}

pub struct CircuitBreaker {
    // 1. الحالة الذرية (للسرعة القصوى في المسار الحرج)
    // نستخدم AtomicBool لفحص سريع جداً قبل كل أمر
    is_tripped: AtomicBool,

    // 2. تتبع الحالة الداخلية (محمي بـ Mutex)
    // هذه البيانات نكتب عليها بعد تنفيذ الصفقات
    state: Mutex<InternalState>,
    
    config: BreakerConfig,
}

struct InternalState {
    status: CircuitState,
    last_trip_time: Option<Instant>,
    
    // نافذة مراقبة الخسارة (Rolling Window)
    window_start: Instant,
    accumulated_loss: Decimal,
    
    // عداد الأخطاء
    consecutive_errors: u32,
    last_error_reason: String,
}

impl CircuitBreaker {
    pub fn new(config: BreakerConfig) -> Self {
        Self {
            is_tripped: AtomicBool::new(false),
            config,
            state: Mutex::new(InternalState {
                status: CircuitState::Closed,
                last_trip_time: None,
                window_start: Instant::now(),
                accumulated_loss: Decimal::ZERO,
                consecutive_errors: 0,
                last_error_reason: String::new(),
            }),
        }
    }

    /// الفحص السريع (Hot Path Check)
    /// يتم استدعاؤه قبل كل أمر. يجب أن يكون zero-cost تقريباً.
    #[inline]
    pub fn ensure_closed(&self) -> AlphaResult<()> {
        // قراءة ذرية سريعة جداً (Nano-second Check)
        if self.is_tripped.load(Ordering::Relaxed) {
            // إذا كان القاطع مفتوحاً، نرفض الأمر فوراً
            // يمكننا الدخول في تفاصيل الـ Mutex لمعرفة السبب، لكن الأولوية للرفض السريع
            return Err(AlphaError::RiskViolation {
                rule: "CIRCUIT_BREAKER_TRIPPED".to_string(),
                limit: "0".to_string(),
                actual: "1".to_string(),
            });
        }
        Ok(())
    }

    /// تسجيل نتيجة صفقة (لتحديث عدادات الخسارة)
    pub fn record_pnl(&self, pnl: Decimal) {
        // القفل هنا مقبول لأنه يحدث بعد التنفيذ (ليس في المسار الحرج للمطابقة)
        let mut state = self.state.lock();
        
        // 1. تدوير النافذة الزمنية (Rolling Window Reset)
        if state.window_start.elapsed() > Duration::from_secs(60) {
            state.window_start = Instant::now();
            state.accumulated_loss = Decimal::ZERO;
        }

        // 2. تحديث الخسارة التراكمية
        if pnl < Decimal::ZERO {
            state.accumulated_loss += pnl.abs();
            
            // 3. التحقق من تجاوز الحد
            if state.accumulated_loss > self.config.max_drawdown_per_minute {
                self.trip_breaker(
                    &mut state, 
                    "RAPID_DRAWDOWN", 
                    format!("Lost {} in < 60s (Limit: {})", state.accumulated_loss, self.config.max_drawdown_per_minute)
                );
            }
        } else {
            // صفقة رابحة: تقلل من عداد الأخطاء (Reset Success Streak)
            state.consecutive_errors = 0;
        }
    }

    /// تسجيل خطأ تنفيذ (لتحديث عدادات الفشل)
    pub fn record_error(&self, error_msg: &str) {
        let mut state = self.state.lock();
        state.consecutive_errors += 1;
        state.last_error_reason = error_msg.to_string();

        if state.consecutive_errors >= self.config.max_consecutive_errors {
            self.trip_breaker(
                &mut state, 
                "ERROR_STORM", 
                format!("{} consecutive errors. Last: {}", state.consecutive_errors, error_msg)
            );
        }
    }

    /// الإجراء الفعلي لفصل التيار
    fn trip_breaker(&self, state: &mut InternalState, reason_code: &str, details: String) {
        // 1. تحديث الحالة الداخلية
        state.status = CircuitState::Open;
        state.last_trip_time = Some(Instant::now());
        
        // 2. تفعيل العلم الذري (ليتوقف الفحص السريع)
        self.is_tripped.store(true, Ordering::SeqCst);
        
        // 3. تفعيل الإيقاف العالمي للمحرك (Global Kill Switch)
        // هذا يضمن توقف جميع المكونات الأخرى أيضاً
        trigger_emergency_stop();

        // 4. التوثيق الجنائي
        error!(
            target: "RISK_CRITICAL",
            "CIRCUIT_BREAKER_TRIPPED: Code=[{}] Details=[{}]", 
            reason_code, 
            details
        );
    }

    /// محاولة إعادة التشغيل اليدوي (Manual Reset)
    pub fn manual_reset(&self) -> AlphaResult<()> {
        let mut state = self.state.lock();
        
        if state.status != CircuitState::Open {
            return Ok(());
        }

        info!("CIRCUIT_BREAKER: Manual reset initiated by operator.");
        
        // تصفية العدادات
        state.status = CircuitState::Closed;
        state.accumulated_loss = Decimal::ZERO;
        state.consecutive_errors = 0;
        state.window_start = Instant::now();
        
        // إعادة فتح البوابة الذرية
        self.is_tripped.store(false, Ordering::SeqCst);
        
        Ok(())
    }
}