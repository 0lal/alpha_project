/*
 * ALPHA SOVEREIGN - RISK ENGINE LATENCY BENCHMARK
 * =================================================================
 * Component Name: engine/benches/risk_bench.rs
 * Core Responsibility: قياس سرعة رد فعل أنظمة الأمان (Circuit Breakers & Margin).
 * Design Pattern: Stress Test / Latency Measurement
 * Forensic Impact: يثبت أن النظام قادر على إيقاف النزيف قبل أن تكتمل الكارثة.
 * =================================================================
 */

use criterion::{black_box, criterion_group, criterion_main, Criterion, BatchSize};
use rust_decimal::Decimal;
use rust_decimal::prelude::FromPrimitive;

// استيراد وحدات المخاطر (نفترض الأسماء بناءً على الملفات السابقة)
use alpha_engine::risk::circuit_breaker::{CircuitBreaker, BreakerConfig, CircuitState};
use alpha_engine::risk::margin_guard::{MarginGuard, MarginConfig};
use alpha_engine::risk::pre_trade_check::{PreTradeCheck, TradeConstraints};
use alpha_engine::models::order::{Order, OrderSide, OrderType};

/// إعداد قاطع الدائرة
fn setup_breaker() -> CircuitBreaker {
    let config = BreakerConfig {
        max_daily_drawdown: Decimal::from_f64(0.05).unwrap(), // 5%
        max_consecutive_losses: 10,
        cool_down_period: 60,
    };
    CircuitBreaker::new(config)
}

/// إعداد حارس الهامش
fn setup_margin_guard() -> MarginGuard {
    let config = MarginConfig {
        max_global_leverage: Decimal::from(20),
        liquidation_safety_buffer: Decimal::from_f64(0.80).unwrap(),
        default_maintenance_margin: Decimal::from_f64(0.01).unwrap(),
    };
    MarginGuard::new(config)
}

fn bench_risk_engine(c: &mut Criterion) {
    let mut group = c.benchmark_group("RiskEngine");

    // =================================================================
    // 1. اختبار قاطع الدائرة (Circuit Breaker)
    // السيناريو: تحديث الرصيد وفحص ما إذا تجاوزنا حد الخسارة اليومي
    // =================================================================
    group.bench_function("circuit_breaker_check", |b| {
        let breaker = setup_breaker();
        let start_balance = Decimal::from(100_000);
        let current_balance = Decimal::from(94_000); // خسارة 6% (تجاوز الحد)

        b.iter(|| {
            // نقيس سرعة اتخاذ القرار: هل نوقف النظام؟
            black_box(breaker.check_drawdown(
                black_box(start_balance),
                black_box(current_balance)
            ));
        });
    });

    // =================================================================
    // 2. اختبار حارس الهامش (Margin Guard)
    // السيناريو: حساب صحة المحفظة (Health Check) مع كل تحديث للسعر
    // هذه العملية تحدث آلاف المرات في الثانية
    // =================================================================
    group.bench_function("margin_health_calc", |b| {
        let guard = setup_margin_guard();
        let equity = Decimal::from(50_000);
        let maintenance_required = Decimal::from(40_000); // 80% usage
        let total_notional = Decimal::from(500_000); // 10x leverage

        b.iter(|| {
            black_box(guard.evaluate_health(
                black_box(equity),
                black_box(maintenance_required),
                black_box(total_notional)
            ));
        });
    });

    // =================================================================
    // 3. اختبار فحص ما قبل التداول (Pre-Trade Check)
    // السيناريو: التحقق من أمر جديد ضد القواعد (Fat Finger Check)
    // =================================================================
    group.bench_function("pre_trade_validation", |b| {
        let constraints = TradeConstraints {
            min_price: Decimal::from(10),
            max_price: Decimal::from(100_000),
            min_quantity: Decimal::from_f64(0.001).unwrap(),
            max_quantity: Decimal::from(10),
            min_notional: Decimal::from(10),
            max_notional: Decimal::from(1_000_000),
            max_price_deviation: Decimal::from_f64(0.10).unwrap(),
        };
        let checker = PreTradeCheck::new(constraints);
        
        // أمر سليم
        let order = Order::new(
            1, "TEST".into(), "BTCUSD".into(), "BINANCE".into(),
            OrderSide::Buy, OrderType::Limit,
            Decimal::from_f64(0.5).unwrap(), Some(Decimal::from(50_000))
        );
        let ref_price = Some(Decimal::from(50_000));

        b.iter(|| {
            black_box(checker.validate(
                black_box(&order), 
                black_box(ref_price)
            ));
        });
    });

    group.finish();
}

criterion_group!(benches, bench_risk_engine);
criterion_main!(benches);