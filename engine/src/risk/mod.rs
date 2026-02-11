/*
 * ALPHA SOVEREIGN - RISK MANAGEMENT MODULE INTERFACE
 * =================================================================
 * Component Name: engine/src/risk/mod.rs
 * Core Responsibility: تعريف واجهات فحص المخاطر وآليات الإيقاف الطارئ (Risk Management Pillar).
 * Design Pattern: Module Facade / Global Atomic State
 * Forensic Impact: يحدد "قوانين اللعبة". إذا تم تنفيذ صفقة تخالف هذه القواعد، فهذا دليل على اختراق أو فشل كارثي.
 * =================================================================
 */

use std::sync::atomic::{AtomicBool, Ordering};
use serde::{Serialize, Deserialize};
use rust_decimal::Decimal;

// تصدير الوحدات الفرعية (سنكتبها لاحقاً)
pub mod engine;      // المحرك الرئيسي للمخاطر
pub mod limits;      // قواعد الحدود (Limits)

// =================================================================
// مفتاح الطوارئ العالمي (The Physical Kill Switch)
// =================================================================
// هذا المتغير موجود في منطقة ذاكرة مشتركة (Static Memory).
// يمكن لأي خيط (Thread) قراءته في دورة معالج واحدة (CPU Cycle).
// إذا أصبح true، يتوقف المحرك فوراً عن قبول أي أوامر جديدة.
pub static GLOBAL_EMERGENCY_STOP: AtomicBool = AtomicBool::new(false);

/// تفعيل الإيقاف الطارئ (يستخدم عند اكتشاف اختراق أو انهيار سوقي)
pub fn trigger_emergency_stop() {
    GLOBAL_EMERGENCY_STOP.store(true, Ordering::SeqCst);
    tracing::error!("RISK_ALERT: GLOBAL KILL SWITCH ACTIVATED! All trading halted.");
}

/// التحقق مما إذا كان النظام في حالة إيقاف
pub fn is_emergency_state() -> bool {
    GLOBAL_EMERGENCY_STOP.load(Ordering::Relaxed)
}

// =================================================================
// أنواع بيانات المخاطر (Risk Data Types)
// =================================================================

/// نوع المخالفة (لتصنيف خطورة الحادث)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskLevel {
    Warning,        // تحذير (مثلاً: اقتربت من الحد الأقصى)
    Rejection,      // رفض الأمر فقط (مثلاً: الرصيد غير كافٍ)
    Critical,       // تجميد الحساب (مثلاً: محاولة تلاعب Wash Trading)
    Fatal,          // إيقاف المحرك بالكامل (مثلاً: خطأ في الحسابات)
}

/// تقرير فحص المخاطر (Forensic Evidence)
/// يتم إرجاعه عند رفض الأمر، ويوضح بدقة "لماذا" تم الرفض.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskReport {
    pub check_name: String,     // اسم الفحص (e.g., "MaxDrawdown")
    pub level: RiskLevel,       // مستوى الخطورة
    pub threshold: Decimal,     // الحد المسموح
    pub attempted: Decimal,     // القيمة التي حاول الأمر تنفيذها
    pub message: String,        // رسالة بشرية
    pub timestamp: u64,
}

/// السمة (Trait) التي يجب أن يطبقها أي فحص مخاطر جديد.
/// هذا يسمح لنا بإضافة قواعد جديدة (Plugin System) دون تعديل المحرك.
pub trait RiskCheck: Send + Sync {
    /// اسم الفحص (للسجلات)
    fn name(&self) -> &'static str;

    /// تنفيذ الفحص. يعود بـ Ok(()) إذا مر، أو Err(Report) إذا فشل.
    fn check(&self, order: &crate::matching::Order, context: &RiskContext) -> Result<(), RiskReport>;
    
    /// هل هذا الفحص مفعل؟
    fn is_enabled(&self) -> bool { true }
}

/// السياق الذي يحتاجه فاحص المخاطر لاتخاذ القرار
/// (يحتوي على لقطة من المحفظة وحالة السوق)
pub struct RiskContext {
    pub portfolio_value: Decimal,
    pub open_orders_count: usize,
    pub daily_loss: Decimal,
    pub volatility_index: Decimal,
}