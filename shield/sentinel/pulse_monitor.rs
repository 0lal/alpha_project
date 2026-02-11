/*
 * ALPHA SOVEREIGN - INTERNAL THREAD HEARTBEAT MONITOR
 * =================================================================
 * Component Name: shield/sentinel/pulse_monitor.rs
 * Core Responsibility: كشف التجميد (Deadlocks) والتأخير (Lag) داخل خيوط النظام (Stability Pillar).
 * Design Pattern: Watchdog Timer / Atomic Keep-Alive
 * Forensic Impact: يحدد بدقة "لحظة الوفاة" لأي خيط. يفرق بين "توقف النظام" و"بطء النظام".
 * =================================================================
 */

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};
use tracing::{info, warn, error};
use crate::error::{AlphaError, AlphaResult};

/// المقبض الذي يحمله كل مكون لإثبات حياته
/// (خفيف الوزن جداً لعدم التأثير على الأداء)
#[derive(Clone)]
pub struct PulseHandle {
    name: String,
    last_beat: Arc<AtomicU64>,
}

impl PulseHandle {
    /// إرسال نبضة (أنا حي!)
    /// يجب استدعاء هذه الدالة في الحلقة الرئيسية لكل خيط
    #[inline(always)]
    pub fn beat(&self) {
        // نستخدم الميلي ثانية الحالية (Monotonic لو أمكن، هنا نستخدم Unix للتبسيط مع Utils)
        let now = crate::utils::time::now_ms();
        self.last_beat.store(now, Ordering::Relaxed);
    }
}

/// حالة المكون
#[derive(Debug, PartialEq)]
pub enum ComponentHealth {
    Healthy,            // النبض منتظم
    Lagging(u64),       // تأخير بسيط (تحذير)
    Unresponsive(u64),  // تأخير خطير (ميت أو عالق)
}

/// المراقب المركزي للنبضات
pub struct PulseMonitor {
    /// سجل المكونات المراقبة
    /// الاسم -> (آخر نبضة، الحد المسموح)
    registry: RwLock<HashMap<String, (Arc<AtomicU64>, u64)>>,
}

impl PulseMonitor {
    pub fn new() -> Self {
        Self {
            registry: RwLock::new(HashMap::new()),
        }
    }

    /// تسجيل مكون جديد للمراقبة
    /// name: اسم الخيط (e.g., "MATCHING_ENGINE")
    /// max_silence_ms: أقصى فترة صمت مسموحة قبل إعلان الخطر
    pub fn register(&self, name: &str, max_silence_ms: u64) -> PulseHandle {
        let last_beat = Arc::new(AtomicU64::new(crate::utils::time::now_ms()));
        
        let mut map = self.registry.write().unwrap();
        map.insert(name.to_string(), (last_beat.clone(), max_silence_ms));
        
        info!("PULSE: Component '{}' registered. Max silence: {}ms", name, max_silence_ms);

        PulseHandle {
            name: name.to_string(),
            last_beat,
        }
    }

    /// فحص دوري لجميع المكونات (Checkup)
    /// تعيد قائمة بالمكونات المتعثرة
    pub fn check_system_health(&self) -> Vec<(String, ComponentHealth)> {
        let map = self.registry.read().unwrap();
        let now = crate::utils::time::now_ms();
        let mut report = Vec::new();

        for (name, (atom, limit)) in map.iter() {
            let last = atom.load(Ordering::Relaxed);
            
            // التعامل مع حالة تراجع الوقت (نادرة جداً ولكن ممكنة في تحديثات NTP)
            if now < last {
                continue; 
            }

            let silence = now - last;

            if silence > *limit {
                // حالة حرجة: المكون صامت لفترة أطول من المسموح
                error!("PULSE_ALARM: Component '{}' is UNRESPONSIVE! Silence: {}ms (Limit: {}ms)", name, silence, limit);
                report.push((name.clone(), ComponentHealth::Unresponsive(silence)));
            } else if silence > limit / 2 {
                // تحذير: المكون بدأ يتباطأ (50% من الحد)
                warn!("PULSE_WARN: Component '{}' is lagging. Silence: {}ms", name, silence);
                report.push((name.clone(), ComponentHealth::Lagging(silence)));
            }
        }
        
        report
    }

    /// تشغيل خيط المراقبة الخلفي (Background Watchdog)
    pub async fn start_monitoring_loop(self: Arc<Self>) {
        info!("PULSE: Watchdog thread started.");
        loop {
            tokio::time::sleep(Duration::from_millis(500)).await; // فحص كل نصف ثانية
            
            let issues = self.check_system_health();
            
            for (name, status) in issues {
                if let ComponentHealth::Unresponsive(_) = status {
                    // هنا يمكننا اتخاذ إجراءات عنيفة، مثل إرسال إشارة قتل للنظام
                    // أو تفعيل "وضع الأمان"
                    // crate::risk::emergency_stop();
                }
            }
        }
    }
}

// =================================================================
// اختبارات الوحدة (Health Check Verification)
// =================================================================
#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_pulse_detection() {
        let monitor = PulseMonitor::new();
        
        // 1. تسجيل خيط "سريع" (يجب أن ينبض كل 10ms، الحد 50ms)
        let handle = monitor.register("FAST_WORKER", 50);
        
        // نبضة أولية
        handle.beat();
        
        // محاكاة عمل طبيعي
        thread::sleep(Duration::from_millis(10));
        let issues = monitor.check_system_health();
        assert!(issues.is_empty(), "System should be healthy");

        // محاكاة تجمد (Deadlock simulation)
        // ننام لمدة 100ms (أكبر من الحد 50ms)
        thread::sleep(Duration::from_millis(100));
        
        let issues_lag = monitor.check_system_health();
        assert!(!issues_lag.is_empty(), "Should detect unresponsive thread");
        assert_eq!(issues_lag[0].0, "FAST_WORKER");
        
        match issues_lag[0].1 {
            ComponentHealth::Unresponsive(ms) => assert!(ms >= 100),
            _ => panic!("Expected Unresponsive status"),
        }
        
        // استعادة النبض (Recovery)
        handle.beat();
        thread::sleep(Duration::from_millis(5));
        let issues_recovered = monitor.check_system_health();
        assert!(issues_recovered.is_empty(), "System should recover after beat");
    }
}