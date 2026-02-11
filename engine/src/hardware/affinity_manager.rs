// Core Pinning

/*
 * ALPHA SOVEREIGN - CPU AFFINITY & ISOLATION MANAGER
 * =================================================================
 * Component Name: engine/src/hardware/affinity_manager.rs
 * Core Responsibility: إدارة تخصيص الأنوية لتقليل الـ Context Switching (Performance Pillar).
 * Design Pattern: Strategy / Resource Manager
 * Forensic Impact: يوثق "الجغرافيا الفيزيائية" للتنفيذ. هل كان سبب البطء هو مزاحمة عملية "Windows Update" للمحرك؟
 * =================================================================
 */

use std::thread;
use core_affinity; // نفترض وجود هذه المكتبة في Cargo.toml
use tracing::{info, warn, error};
use crate::error::{AlphaResult, AlphaError};

/// أدوار الخيوط في النظام (حسب الأهمية)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ThreadRole {
    /// المحرك النووي: يجب أن يعمل على نواة معزولة تماماً (High Priority)
    MatchingEngine,
    
    /// حارس المخاطر: يجب أن يكون قريباً جداً من المحرك
    RiskGate,
    
    /// استقبال الشبكة: يفضل أن يكون قريباً من مقاطعات بطاقة الشبكة (NIC)
    NetworkIngress,
    
    /// العمال الخلفيون: (Logging, DB) يمكنهم العمل على أي نواة متبقية
    BackgroundWorker,
}

pub struct AffinityManager {
    core_ids: Vec<core_affinity::CoreId>,
}

impl AffinityManager {
    /// تهيئة المدير واكتشاف الأنوية المتاحة
    pub fn new() -> AlphaResult<Self> {
        let core_ids = core_affinity::get_core_ids()
            .ok_or_else(|| AlphaError::BootstrapError("Failed to detect CPU cores topology".into()))?;

        info!("AFFINITY_MGR: Detected {} logical cores.", core_ids.len());

        // تحذير إذا كانت الموارد شحيحة
        if core_ids.len() < 4 {
            warn!("PERF_WARNING: Low core count ({}). Isolation will be compromised.", core_ids.len());
        }

        Ok(Self { core_ids })
    }

    /// تثبيت الخيط الحالي بناءً على دوره
    pub fn pin_current_thread(&self, role: ThreadRole) {
        let thread_id = thread::current().id();
        let core_count = self.core_ids.len();

        if core_count == 0 {
            return;
        }

        // استراتيجية التوزيع (Allocation Strategy)
        // الهدف: تجنب النواة رقم 0 (مشغولة بالنظام) وتخصيص أفضل الأنوية للمطابقة.
        
        let target_core_index = match role {
            // المحرك يأخذ آخر نواة (عادة تكون الأقل إزعاجاً من الـ OS)
            ThreadRole::MatchingEngine => core_count - 1,
            
            // المخاطر تأخذ النواة قبل الأخيرة (لتكون قريبة من المحرك في L3 Cache)
            ThreadRole::RiskGate => if core_count > 1 { core_count - 2 } else { 0 },
            
            // الشبكة تأخذ النواة رقم 1 (لتبتعد عن النواة 0 الخاصة بالنظام)
            ThreadRole::NetworkIngress => if core_count > 2 { 1 } else { 0 },
            
            // الخلفية تأخذ النواة 0 (تشارك النظام في أعبائه)
            ThreadRole::BackgroundWorker => 0,
        };

        // محاولة التثبيت
        if let Some(core_id) = self.core_ids.get(target_core_index) {
            let success = core_affinity::set_for_current(*core_id);
            
            if success {
                info!(
                    "THREAD_PINNED: Role [{:?}] -> Core #{} (ThreadID: {:?})", 
                    role, target_core_index, thread_id
                );
            } else {
                error!(
                    "PINNING_FAIL: Could not pin {:?} to Core #{}", 
                    role, target_core_index
                );
            }
        } else {
            error!("AFFINITY_ERROR: Calculated core index {} out of bounds (Total: {})", target_core_index, core_count);
        }
    }

    /// (للمستقبل) وضع الخيط في وضع "العزل التام"
    /// يتطلب تعديلات على مستوى Kernel (cgroups / isolcpus)
    pub fn enable_realtime_priority(&self) {
        // هذا مجرد مؤشر، التنفيذ الفعلي يتطلب صلاحيات Root واستدعاءات libc
        // unsafe {
        //     let param = sched_param { sched_priority: 99 };
        //     sched_setscheduler(0, SCHED_FIFO, &param);
        // }
        info!("REALTIME_MODE: Attempting to elevate thread priority to SCHED_FIFO (Requires Root)");
    }
}

// ----------------------------------------------------------------
// اختبار سريع للمفهوم (Unit Test)
// ----------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_core_strategy() {
        // محاكاة نظام بـ 8 أنوية
        let mgr = AffinityManager { 
            core_ids: (0..8).map(|i| core_affinity::CoreId { id: i }).collect() 
        };
        
        // يجب أن يذهب المحرك للنواة 7
        // يجب أن تذهب المخاطر للنواة 6
        // يجب أن تذهب الشبكة للنواة 1
    }
}