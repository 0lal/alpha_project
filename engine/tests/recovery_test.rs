/*
 * ALPHA SOVEREIGN - DISASTER RECOVERY & STATE RECONSTRUCTION TEST
 * =================================================================
 * Component Name: engine/tests/recovery_test.rs
 * Core Responsibility: التحقق من قدرة النظام على إعادة بناء حالته بدقة بعد الانهيار (Stability Pillar).
 * Design Pattern: Event Sourcing Replay / Deterministic State Test
 * Forensic Impact: يضمن أن "الحقيقة" لا تضيع بذهاب الكهرباء. السجلات هي الحقيقة، والذاكرة مجرد انعكاس لها.
 * =================================================================
 */

use rust_decimal_macros::dec;
use alpha_engine::matching::orderbook::OrderBook;
use alpha_engine::models::order::{Order, OrderSide, OrderType};
use alpha_engine::utils::id;

// =================================================================
// محاكاة سجل الأحداث (The Write-Ahead Log Simulation)
// =================================================================

#[derive(Clone)]
enum LogEvent {
    PlaceOrder(Order),
    CancelOrder(u64), // Order ID
}

// أداة مساعدة لإنشاء الأوامر
fn make_order(side: OrderSide, price: f64, qty: f64) -> Order {
    Order::new(
        id::next_id(),
        "RECOVERY_TEST".into(),
        "ETHUSDT".into(),
        "BINANCE".into(),
        side,
        OrderType::Limit,
        dec!(qty),
        Some(dec!(price)),
    )
}

#[test]
fn test_state_reconstruction_determinism() {
    // 1. المحرك الأصلي (قبل الانهيار)
    // =================================================
    let mut original_book = OrderBook::new("ETHUSDT".into());
    let mut wal_log: Vec<LogEvent> = Vec::new();

    // السيناريو: نشاط تداول مكثف
    
    // أ: إضافة سيولة
    let o1 = make_order(OrderSide::Sell, 2000.0, 10.0);
    let o2 = make_order(OrderSide::Sell, 2010.0, 5.0);
    let o3 = make_order(OrderSide::Buy, 1900.0, 20.0);

    original_book.add_order(o1.clone()).unwrap();
    wal_log.push(LogEvent::PlaceOrder(o1));

    original_book.add_order(o2.clone()).unwrap();
    wal_log.push(LogEvent::PlaceOrder(o2));

    original_book.add_order(o3.clone()).unwrap();
    wal_log.push(LogEvent::PlaceOrder(o3));

    // ب: تنفيذ صفقة (تغيير الحالة الداخلية)
    let taker_order = make_order(OrderSide::Buy, 2005.0, 3.0); // سيأكل 3 من o1
    original_book.add_order(taker_order.clone()).unwrap();
    wal_log.push(LogEvent::PlaceOrder(taker_order));

    // ج: إلغاء أمر
    let cancel_id = o2.id;
    original_book.cancel_order(cancel_id).unwrap();
    wal_log.push(LogEvent::CancelOrder(cancel_id));

    // حفظ الحالة النهائية للمقارنة (Snapshot A)
    let snapshot_original = original_book.get_snapshot();

    // 2. المحرك المستعاد (بعد إعادة التشغيل)
    // =================================================
    // نبدأ بدفتر فارغ تماماً (Fresh Start)
    let mut recovered_book = OrderBook::new("ETHUSDT".into());

    // إعادة تشغيل الأحداث من السجل (Replay)
    for event in wal_log {
        match event {
            LogEvent::PlaceOrder(order) => {
                // يجب أن يعطي نفس النتائج (Ok/Err)
                let _ = recovered_book.add_order(order);
            },
            LogEvent::CancelOrder(order_id) => {
                let _ = recovered_book.cancel_order(order_id);
            }
        }
    }

    // حفظ الحالة المستعادة (Snapshot B)
    let snapshot_recovered = recovered_book.get_snapshot();

    // 3. التحقق الجنائي (The Verdict)
    // =================================================
    
    // التحقق من جانب العرض (Asks)
    assert_eq!(
        snapshot_original.asks.len(), 
        snapshot_recovered.asks.len(), 
        "Ask side depth mismatch"
    );
    if !snapshot_original.asks.is_empty() {
        assert_eq!(
            snapshot_original.asks[0].quantity, 
            snapshot_recovered.asks[0].quantity, 
            "Ask quantity mismatch (Execution replay failed)"
        );
    }

    // التحقق من جانب الطلب (Bids)
    assert_eq!(
        snapshot_original.bids.len(), 
        snapshot_recovered.bids.len(), 
        "Bid side depth mismatch"
    );

    // التحقق من سجل التداول (Last Price)
    // (نفترض وجود حقل آخر صفقة في الدفتر، أو نقارن حالة الدفتر فقط)
    
    // تطابق تام
    // نحن نعتمد على Eq implementation للـ Decimal والهياكل
    // وللتأكد أكثر، نتحقق يدوياً من القيم الحرجة
    // o1 كان 10.0، أكلنا منه 3.0، الباقي يجب أن يكون 7.0 في كلا الدفترين
    let expected_qty = dec!(7.0);
    assert_eq!(snapshot_recovered.asks[0].quantity, expected_qty, "Recovered logic failed to deduct trade quantity");
}

#[test]
fn test_recovery_from_corrupted_sequence() {
    // اختبار متقدم: ماذا لو حاولنا إلغاء أمر غير موجود أثناء الاستعادة؟
    // (يحدث هذا إذا فقدنا جزءاً من السجل)
    
    let mut recovered_book = OrderBook::new("CORRUPT_TEST".into());
    
    // حدث 1: إلغاء أمر شبح (غير موجود في الدفتر)
    let ghost_cancel = LogEvent::CancelOrder(99999);
    
    // أثناء التشغيل العادي، هذا يرجع خطأ.
    // أثناء الاستعادة، يجب ألا يسبب Panic يوقف النظام.
    match ghost_cancel {
        LogEvent::CancelOrder(id) => {
            let res = recovered_book.cancel_order(id);
            assert!(res.is_err()); // نتوقع خطأ، لكن النظام يستمر
        },
        _ => {}
    }

    // حدث 2: أمر سليم
    let valid_order = make_order(OrderSide::Buy, 100.0, 1.0);
    let res = recovered_book.add_order(valid_order);
    assert!(res.is_ok(), "System should remain operational after handling ghost event");
}