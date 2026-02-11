// ALPHA SOVEREIGN - HARDWARE ACCELERATION
// Status: FINAL PRODUCTION

use core_affinity;

/// محاولة تثبيت الخيط الحالي على نواة معينة لتقليل الـ Context Switching
pub fn apply_affinity(core_id: usize) -> Result<(), String> {
    // 1. الحصول على الأنوية المتاحة
    let core_ids = core_affinity::get_core_ids()
        .ok_or_else(|| "Failed to retrieve processor cores".to_string())?;

    // 2. التحقق من وجود النواة المطلوبة
    if core_id >= core_ids.len() {
        return Err(format!(
            "Core {} is not available. System has {} cores.", 
            core_id, core_ids.len()
        ));
    }

    // 3. تثبيت الخيط
    let core = core_ids[core_id];
    let success = core_affinity::set_for_current(core);

    if success {
        Ok(())
    } else {
        Err(format!("OS refused to pin thread to Core {}", core_id))
    }
}
