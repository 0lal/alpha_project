// Nanosecond Timer

/*
 * ALPHA SOVEREIGN - NANOSECOND LATENCY TRACKER
 * =================================================================
 * Component Name: engine/src/matching/latency_tracker.rs
 * Core Responsibility: تتبع زمن التأخير بدقة النانو-ثانية (Performance Pillar).
 * Design Pattern: HDR Histogram / Atomic Sampling
 * Forensic Impact: يكشف "الاختناقات الخفية" (Micro-bursts). يحدد هل التأخير من الشبكة، أم من خوارزمية المطابقة، أم من جامع القمامة؟
 * =================================================================
 */

use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};
use std::collections::HashMap;
use parking_lot::RwLock;
use tracing::warn;

/// أنواع القياسات التي نتتبعها
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MetricType {
    OrderIngress,   // وقت استلام الأمر من الشبكة
    RiskCheck,      // وقت فحص المخاطر
    MatchingLogic,  // وقت المطابقة الفعلي (داخل OrderBook)
    PersistState,   // وقت حفظ الحالة
    TotalRoundtrip, // الزمن الكلي من الدخول للخروج
}

/// هيكل لتجميع الإحصائيات (Buckets)
#[derive(Debug, Default)]
struct LatencyBuckets {
    count: u64,
    min_ns: u64,
    max_ns: u64,
    sum_ns: u64,
    
    // دلاء التوزيع (Distribution Buckets)
    // < 1us, < 10us, < 100us, < 1ms, > 1ms
    micros_1: u64,
    micros_10: u64,
    micros_100: u64,
    millis_1: u64,
    slow: u64,
}

pub struct LatencyTracker {
    /// تخزين الإحصائيات محمياً بقفل قراءة/كتابة سريع
    stats: RwLock<HashMap<MetricType, LatencyBuckets>>,
    
    /// عتبة التحذير (Spike Threshold) بالنانوثانية
    /// أي عملية تتجاوز هذا الرقم سيتم تسجيلها كـ Warning فوراً
    spike_threshold_ns: u64,
}

impl LatencyTracker {
    pub fn new() -> Self {
        Self {
            stats: RwLock::new(HashMap::new()),
            spike_threshold_ns: 500_000, // 500 ميكروثانية (0.5ms) كحد أقصى مقبول
        }
    }

    /// تسجيل قياس جديد
    pub fn record(&self, metric: MetricType, duration_ns: u64) {
        // 1. كشف الشذوذ الفوري (Anomaly Detection)
        if duration_ns > self.spike_threshold_ns {
            warn!("PERF_SPIKE: {:?} took {} µs (Threshold: {} µs)", 
                metric, 
                duration_ns / 1000, 
                self.spike_threshold_ns / 1000
            );
        }

        // 2. تحديث الإحصائيات (Locking scope is minimal)
        let mut map = self.stats.write();
        let bucket = map.entry(metric).or_insert_with(LatencyBuckets::default);

        bucket.count += 1;
        bucket.sum_ns += duration_ns;
        
        if bucket.min_ns == 0 || duration_ns < bucket.min_ns {
            bucket.min_ns = duration_ns;
        }
        if duration_ns > bucket.max_ns {
            bucket.max_ns = duration_ns;
        }

        // تصنيف الدلو (Histogram Binning)
        if duration_ns < 1_000 {
            bucket.micros_1 += 1;
        } else if duration_ns < 10_000 {
            bucket.micros_10 += 1;
        } else if duration_ns < 100_000 {
            bucket.micros_100 += 1;
        } else if duration_ns < 1_000_000 {
            bucket.millis_1 += 1;
        } else {
            bucket.slow += 1;
        }
    }

    /// الحصول على تقرير الأداء
    pub fn get_report(&self) -> String {
        let map = self.stats.read();
        let mut report = String::from("\n--- ENGINE LATENCY REPORT (Nanoseconds) ---\n");

        for (metric, bucket) in map.iter() {
            if bucket.count == 0 { continue; }
            let avg = bucket.sum_ns / bucket.count;
            
            report.push_str(&format!(
                "{:?}:\n  Count: {}\n  Avg: {} ns\n  Min: {} ns\n  Max: {} ns\n  Distribution: [<1µs: {}, <10µs: {}, <100µs: {}, <1ms: {}, SLOW: {}]\n",
                metric, bucket.count, avg, bucket.min_ns, bucket.max_ns,
                bucket.micros_1, bucket.micros_10, bucket.micros_100, bucket.millis_1, bucket.slow
            ));
        }
        report
    }
}

/// مساعد (Helper) لقياس النطاق تلقائياً (RAII Timer)
/// بمجرد أن يخرج المتغير من النطاق (Scope Drop)، يتم تسجيل الوقت.
pub struct ScopedTimer<'a> {
    tracker: &'a LatencyTracker,
    metric: MetricType,
    start: Instant,
}

impl<'a> ScopedTimer<'a> {
    pub fn new(tracker: &'a LatencyTracker, metric: MetricType) -> Self {
        Self {
            tracker,
            metric,
            start: Instant::now(),
        }
    }
}

impl<'a> Drop for ScopedTimer<'a> {
    fn drop(&mut self) {
        let elapsed = self.start.elapsed().as_nanos() as u64;
        self.tracker.record(self.metric, elapsed);
    }
}