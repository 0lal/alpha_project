// =================================================================
// ALPHA SOVEREIGN ORGANISM - COMMON TYPES AGGREGATOR
// =================================================================
// File: engine/src/common_types.rs
// Status: PRODUCTION (Generated Code Bridge)
// Pillar: Integration (الركيزة: التكامل)
// Forensic Purpose: هذا الملف هو "نقطة التجميع" التي تجلب أكواد FlatBuffers المولدة آلياً من مجلد البناء المخفي وتجعلها متاحة للمحرك.
// =================================================================

#![allow(dead_code)]
#![allow(unused_imports)]
#![allow(clippy::all)] // تعطيل تدقيق الكود هنا لأنه مولد آلياً ولا نتحكم فيه.

// استيراد مكتبة FlatBuffers الأساسية
use flatbuffers;

// -----------------------------------------------------------------
// 1. تضمين نبضات السوق (Market Ticks)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/market_tick.fbs
pub mod market_tick {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/market_tick_generated.rs"));
}

// -----------------------------------------------------------------
// 2. تضمين عمق السوق (Order Book Depth)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/order_book_depth.fbs
pub mod order_book_depth {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/order_book_depth_generated.rs"));
}

// -----------------------------------------------------------------
// 3. تضمين أحداث الصفقات (Trade Events)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/trade_event.fbs
pub mod trade_event {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/trade_event_generated.rs"));
}

// -----------------------------------------------------------------
// 4. تضمين تحديثات الأوامر (Order Updates)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/order_update.fbs
pub mod order_update {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/order_update_generated.rs"));
}

// -----------------------------------------------------------------
// 5. تضمين تقارير المخاطر (Risk Reports)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/risk_report.fbs
pub mod risk_report {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/risk_report_generated.rs"));
}

// -----------------------------------------------------------------
// 6. تضمين نبض القلب (Heartbeat)
// -----------------------------------------------------------------
// المصدر: schemas/flatbuffers/heartbeat.fbs
pub mod heartbeat {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/heartbeat_generated.rs"));
}

// -----------------------------------------------------------------
// 7. أنواع مساعدة (Helper Types)
// -----------------------------------------------------------------
// هنا يمكننا إضافة دوال مساعدة لسهولة التعامل مع الأنواع المولدة.

/// دالة مساعدة للحصول على الوقت الحالي بدقة النانو ثانية (للاستخدام في الحقول المولدة).
pub fn current_timestamp_nanos() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as i64
}