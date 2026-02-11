/*
 * ALPHA SOVEREIGN - SAFETY CIRCUIT INTEGRITY TEST
 * =================================================================
 * Component Name: engine/tests/risk_circuit_test.rs
 * Core Responsibility: التحقق من أن مكابح الطوارئ تعمل عند الكوارث (Testing Pillar).
 * Design Pattern: Failure Mode Analysis
 * Forensic Impact: يثبت أن النظام يمتلك "غريزة البقاء". إذا خسرنا المال، النظام يتوقف تلقائياً لحماية رأس المال المتبقي.
 * =================================================================
 */

use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use alpha_engine::risk::circuit_breaker::{CircuitBreaker, BreakerConfig, CircuitState};
use alpha_engine::risk::margin_guard::{MarginGuard, MarginConfig};

// =================================================================
// 1. اختبار حد الخسارة اليومي (Daily Drawdown)
// =================================================================
#[test]
fn test_daily_drawdown_kill_switch() {
    // الإعداد: نسمح بخسارة قصوى 5%
    let config = BreakerConfig {
        max_daily_drawdown: dec!(0.05), // 5%
        max_consecutive_losses: 10,
        cool_down_period: 60,
    };
    let breaker = CircuitBreaker::new(config);

    let start_balance = dec!(100_000.0);

    // الحالة 1: خسارة بسيطة (1%) - يجب أن يمر
    let current_balance_1 = dec!(99_000.0);
    let res1 = breaker.check_drawdown(start_balance, current_balance_1);
    assert!(res1.is_ok(), "Small loss should be allowed");

    // الحالة 2: خسارة عند الحد تماماً (5%) - منطقة الخطر
    let current_balance_2 = dec!(95_000.0);
    let res2 = breaker.check_drawdown(start_balance, current_balance_2);
    assert!(res2.is_ok(), "At the limit is technically okay (warning zone)");

    // الحالة 3: انهيار (6%) - يجب تفعيل القاطع فوراً
    let current_balance_3 = dec!(94_000.0);
    let res3 = breaker.check_drawdown(start_balance, current_balance_3);
    
    assert!(res3.is_err(), "Circuit breaker FAILED to stop excessive drawdown!");
    
    // التحقق من رسالة الخطأ الجنائية
    match res3 {
        Err(e) => assert!(format!("{}", e).contains("DRAWDOWN_LIMIT"), "Wrong error type returned"),
        _ => panic!("Expected error"),
    }
}

// =================================================================
// 2. اختبار سلسلة الخسائر المتتالية (Losing Streak)
// =================================================================
#[test]
fn test_consecutive_loss_prevention() {
    // الإعداد: إذا خسرنا 3 مرات متتالية، توقف للتفكير
    let config = BreakerConfig {
        max_daily_drawdown: dec!(0.50),
        max_consecutive_losses: 3,
        cool_down_period: 60,
    };
    let mut breaker = CircuitBreaker::new(config);

    // الخسارة الأولى
    breaker.record_trade_result(dec!(-100.0)); 
    assert!(breaker.is_operational(), "Should be active after 1 loss");

    // الخسارة الثانية
    breaker.record_trade_result(dec!(-50.0));
    assert!(breaker.is_operational(), "Should be active after 2 losses");

    // الخسارة الثالثة (القاضية)
    breaker.record_trade_result(dec!(-10.0));
    
    // الآن يجب أن يكون النظام في حالة إيقاف
    assert!(!breaker.is_operational(), "Breaker should TRIPPED after 3 consecutive losses");

    // محاولة التداول والنظام متوقف
    let trade_attempt = breaker.check_permission();
    assert!(trade_attempt.is_err(), "Trading should be blocked during cool-down");
}

// =================================================================
// 3. اختبار حارس الرافعة المالية (Leverage Guard)
// =================================================================
#[test]
fn test_leverage_limit_enforcement() {
    // الإعداد: رافعة قصوى 10x
    let config = MarginConfig {
        max_global_leverage: dec!(10.0),
        liquidation_safety_buffer: dec!(0.80),
        default_maintenance_margin: dec!(0.01),
    };
    let guard = MarginGuard::new(config);

    let equity = dec!(10_000.0); // الرصيد 10,000

    // محاولة فتح مركز بـ 50,000 (رافعة 5x) - مسموح
    let res1 = guard.check_new_order(equity, dec!(0.0), dec!(50_000.0));
    assert!(res1.is_ok());

    // محاولة فتح مركز بـ 100,000 (رافعة 10x) - الحد الأقصى
    let res2 = guard.check_new_order(equity, dec!(0.0), dec!(100_000.0));
    assert!(res2.is_ok());

    // محاولة فتح مركز بـ 100,001 (رافعة 10.0001x) - مرفوض
    let res3 = guard.check_new_order(equity, dec!(0.0), dec!(100_001.0));
    assert!(res3.is_err(), "Leverage guard failed to stop over-leveraging");
}

// =================================================================
// 4. اختبار التسييل الاستباقي (Liquidation Avoidance)
// =================================================================
#[test]
fn test_liquidation_safety_buffer() {
    // الإعداد: نريد هامش أمان 20% قبل التسييل الحقيقي
    let config = MarginConfig {
        max_global_leverage: dec!(100.0),
        liquidation_safety_buffer: dec!(0.80), // التحذير عند 80% من الهامش
        default_maintenance_margin: dec!(0.01), // الهامش المطلوب 1%
    };
    let guard = MarginGuard::new(config);

    let equity = dec!(1000.0);
    // مركز ضخم يتطلب هامش صيانة 850 (85% من الرصيد)
    let maintenance_required = dec!(850.0); 
    let total_notional = dec!(85_000.0);

    // فحص الصحة
    let report = guard.evaluate_health(equity, maintenance_required, total_notional).unwrap();
    
    // نسبة الهامش = 850 / 1000 = 0.85
    // الحد المسموح = 0.80
    // يجب أن يطلق النظام تحذيراً (في الواقع يرسل إشارة De-leveraging)
    
    assert!(report.margin_ratio > dec!(0.80));
    // في التنفيذ الفعلي، كنا سنفحص السجلات لرؤية "WARN: Approaching Liquidation"
}