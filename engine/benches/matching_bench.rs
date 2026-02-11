// Micro-benchmarks

/*
 * ALPHA SOVEREIGN - MICRO-BENCHMARKING SUITE
 * =================================================================
 * Component Name: engine/benches/matching_bench.rs
 * Core Responsibility: قياس أداء المحرك تحت الضغط الشديد (Performance Pillar).
 * Design Pattern: Statistical Micro-benchmarking
 * Forensic Impact: يوفر "خط الأساس" (Baseline). إذا أجرينا تعديلاً وزاد الزمن 50ns، هذا الاختبار سيفضح التراجع فوراً.
 * =================================================================
 */

use criterion::{black_box, criterion_group, criterion_main, Criterion, BatchSize};
use rust_decimal::Decimal;
use rust_decimal::prelude::FromPrimitive;
use alpha_engine::matching::orderbook::OrderBook; // نفترض أن اسم المكتبة alpha_engine
use alpha_engine::models::order::{Order, OrderSide, OrderType};

/// دالة مساعدة لتجهيز دفتر أوامر ممتلئ (Warm-up)
fn setup_warm_orderbook(orders_count: u64) -> OrderBook {
    let mut book = OrderBook::new("BTCUSDT".to_string());
    
    // ملء الدفتر بأوامر بيع وشراء بعيدة عن السعر الحالي (لتجنب المطابقة الفورية أثناء التحضير)
    for i in 0..orders_count {
        // Asks: 50100, 50101, ...
        let ask_price = Decimal::from(50100) + Decimal::from(i);
        let ask = Order::new(
            i * 2, 
            "BENCH_STRAT".into(), 
            "BTCUSDT".into(), 
            "BINANCE".into(),
            OrderSide::Sell, 
            OrderType::Limit, 
            Decimal::from_f64(1.0).unwrap(), 
            Some(ask_price)
        );
        let _ = book.add_order(ask);

        // Bids: 49900, 49899, ...
        let bid_price = Decimal::from(49900) - Decimal::from(i);
        let bid = Order::new(
            (i * 2) + 1, 
            "BENCH_STRAT".into(), 
            "BTCUSDT".into(), 
            "BINANCE".into(),
            OrderSide::Buy, 
            OrderType::Limit, 
            Decimal::from_f64(1.0).unwrap(), 
            Some(bid_price)
        );
        let _ = book.add_order(bid);
    }
    
    book
}

fn bench_matching_engine(c: &mut Criterion) {
    let mut group = c.benchmark_group("MatchingEngine");
    
    // سيناريو 1: إدخال أمر محدد (Limit Order) في دفتر مزدحم (Insertion Latency)
    // هذا يقيس سرعة BTreeMap::insert
    group.bench_function("insert_limit_order_no_match", |b| {
        // نجهز دفتر بـ 10 آلاف أمر
        let book = setup_warm_orderbook(5000); 
        
        b.iter_batched(
            || {
                // في كل دورة نستخدم نسخة جديدة لضمان النزاهة
                (book.clone(), Order::new(
                    999999, 
                    "BENCH".into(), 
                    "BTCUSDT".into(), 
                    "BINANCE".into(),
                    OrderSide::Buy, 
                    OrderType::Limit, 
                    Decimal::from_f64(0.5).unwrap(), 
                    Some(Decimal::from(49950)) // سعر وسط الـ Spread (لا يطابق)
                ))
            },
            |(mut book, order)| {
                // القياس يبدأ هنا
                black_box(book.add_order(order));
            },
            BatchSize::SmallInput,
        );
    });

    // سيناريو 2: أمر سوق (Market Order) يلتهم السيولة (Matching Latency)
    // هذا يقيس سرعة التكرار والحذف (BTreeMap traversal & removal)
    group.bench_function("match_market_order_taker", |b| {
        let book = setup_warm_orderbook(5000);
        
        b.iter_batched(
            || {
                (book.clone(), Order::new(
                    888888, 
                    "BENCH".into(), 
                    "BTCUSDT".into(), 
                    "BINANCE".into(),
                    OrderSide::Buy, // شراء
                    OrderType::Market, 
                    Decimal::from_f64(10.0).unwrap(), // كمية كبيرة ستأكل 10 أوامر
                    None
                ))
            },
            |(mut book, order)| {
                black_box(book.add_order(order));
            },
            BatchSize::SmallInput,
        );
    });

    // سيناريو 3: إلغاء أمر (Cancel Latency)
    // قياس سرعة البحث عن ID في HashMap وإزالته من BTreeMap
    group.bench_function("cancel_order_by_id", |b| {
        let book = setup_warm_orderbook(1000);
        let target_id = 10; // أمر موجود بالتأكيد
        
        b.iter_batched(
            || book.clone(),
            |mut book| {
                black_box(book.cancel_order(target_id));
            },
            BatchSize::SmallInput,
        );
    });

    group.finish();
}

criterion_group!(benches, bench_matching_engine);
criterion_main!(benches);