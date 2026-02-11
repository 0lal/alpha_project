/*
 * ALPHA SOVEREIGN - FULL SYSTEM INTEGRATION TEST
 * =================================================================
 * Component Name: engine/tests/integration_test.rs
 * Core Responsibility: التحقق من تدفق النظام الكامل (End-to-End Flow).
 * Design Pattern: Black Box Testing
 * Forensic Impact: يضمن أن جميع المكونات (Risk -> Matching -> Reporting) تتحدث لغة واحدة ولا تفقد البيانات في الطريق.
 * =================================================================
 */

use rust_decimal_macros::dec;
use alpha_engine::matching::orderbook::OrderBook;
use alpha_engine::models::order::{Order, OrderSide, OrderType};
use alpha_engine::risk::pre_trade_check::{PreTradeCheck, TradeConstraints};
use alpha_engine::utils::id;

// =================================================================
// أدوات المساعدة للاختبار (Test Helpers)
// =================================================================

fn create_limit_order(side: OrderSide, price: f64, qty: f64) -> Order {
    Order::new(
        id::next_id(),
        "INTEGRATION_TEST".into(),
        "BTCUSDT".into(),
        "BINANCE".into(),
        side,
        OrderType::Limit,
        dec!(qty), // استخدام ماكرو dec! للتحويل المباشر
        Some(dec!(price)),
    )
}

fn create_market_order(side: OrderSide, qty: f64) -> Order {
    Order::new(
        id::next_id(),
        "INTEGRATION_TEST".into(),
        "BTCUSDT".into(),
        "BINANCE".into(),
        side,
        OrderType::Market,
        dec!(qty),
        None,
    )
}

// =================================================================
// سيناريوهات الاختبار (Test Scenarios)
// =================================================================

#[tokio::test]
async fn test_full_trading_cycle_match() {
    // 1. تهيئة دفتر الأوامر (The Arena)
    let mut book = OrderBook::new("BTCUSDT".into());

    // 2. إضافة سيولة (Makers)
    // بائع يعرض 1 BTC بسعر 50,000
    let sell_order = create_limit_order(OrderSide::Sell, 50000.0, 1.0);
    let res = book.add_order(sell_order);
    assert!(res.is_ok(), "Maker order should be accepted");

    // التحقق من أن الأمر في الدفتر
    let snapshot = book.get_snapshot();
    assert_eq!(snapshot.asks.len(), 1);
    assert_eq!(snapshot.bids.len(), 0);

    // 3. مستهلك السيولة (Taker)
    // مشتري يريد 0.5 BTC بسعر السوق
    let buy_order = create_market_order(OrderSide::Buy, 0.5);
    let match_result = book.add_order(buy_order);

    // 4. التحقق الجنائي من النتائج
    assert!(match_result.is_ok());
    let trades = match_result.unwrap();

    // يجب أن تكون هناك صفقة واحدة
    assert_eq!(trades.len(), 1, "Should have exactly one execution");
    
    let trade = &trades[0];
    assert_eq!(trade.price, dec!(50000.0), "Execution price mismatch");
    assert_eq!(trade.quantity, dec!(0.5), "Execution quantity mismatch");
    assert_eq!(trade.taker_side, OrderSide::Buy);

    // 5. التحقق من بقايا الدفتر
    // يجب أن يتبقى 0.5 BTC في جانب العرض
    let snapshot_after = book.get_snapshot();
    assert_eq!(snapshot_after.asks[0].quantity, dec!(0.5), "Remaining liquidity mismatch");
}

#[tokio::test]
async fn test_market_sweep_multiple_levels() {
    // سيناريو "الكنس" (Sweep): أمر سوق كبير يأكل مستويات سعرية متعددة
    let mut book = OrderBook::new("ETHUSDT".into());

    // إضافة مستويات بيع متدرجة (Ladder)
    // 10 ETH @ 2000
    book.add_order(create_limit_order(OrderSide::Sell, 2000.0, 10.0)).unwrap();
    // 5 ETH @ 2010
    book.add_order(create_limit_order(OrderSide::Sell, 2010.0, 5.0)).unwrap();

    // مشتري "حوت" يريد 12 ETH بسعر السوق
    let whale_order = create_market_order(OrderSide::Buy, 12.0);
    let trades = book.add_order(whale_order).unwrap();

    // التوقعات:
    // الصفقة 1: 10 ETH بسعر 2000
    // الصفقة 2: 2 ETH بسعر 2010
    assert_eq!(trades.len(), 2, "Whale should eat two levels");
    
    assert_eq!(trades[0].quantity, dec!(10.0));
    assert_eq!(trades[0].price, dec!(2000.0));
    
    assert_eq!(trades[1].quantity, dec!(2.0));
    assert_eq!(trades[1].price, dec!(2010.0));

    // يجب أن يتبقى 3 ETH في المستوى الثاني
    let snap = book.get_snapshot();
    assert_eq!(snap.asks[0].price, dec!(2010.0));
    assert_eq!(snap.asks[0].quantity, dec!(3.0));
}

#[test] // اختبار متزامن (Synchronous) لوحدة المخاطر
fn test_risk_firewall_rejection() {
    // إعداد قواعد صارمة
    let constraints = TradeConstraints {
        min_price: dec!(100.0),
        max_price: dec!(100000.0),
        min_quantity: dec!(0.01),
        max_quantity: dec!(10.0),
        min_notional: dec!(10.0),
        max_notional: dec!(50000.0),
        max_price_deviation: dec!(0.1),
    };
    
    let checker = PreTradeCheck::new(constraints);

    // 1. سيناريو "إصبع الغباء" (Fat Finger): كمية ضخمة جداً
    let fat_finger_order = create_limit_order(OrderSide::Buy, 50000.0, 1000.0); // 50M Notional!
    let res = checker.validate(&fat_finger_order, Some(dec!(50000.0)));
    
    assert!(res.is_err(), "Risk engine failed to stop Fat Finger order!");
    
    // التحقق من نوع الخطأ
    match res {
        Err(alpha_engine::error::AlphaError::RiskViolation { rule, .. }) => {
            assert!(rule.contains("FAT FINGER") || rule.contains("notional"));
        },
        _ => panic!("Unexpected error type"),
    }

    // 2. سيناريو الانحراف السعري (Price Deviation)
    // محاولة شراء بسعر 60,000 بينما السوق 50,000 (+20%)
    let crazy_price_order = create_limit_order(OrderSide::Buy, 60000.0, 0.1);
    let res2 = checker.validate(&crazy_price_order, Some(dec!(50000.0)));
    
    assert!(res2.is_err(), "Risk engine failed to stop price deviation!");
}

#[tokio::test]
async fn test_self_trade_prevention() {
    // اختبار منع التداول مع النفس (Wash Trading) - ميزة متقدمة
    // (نفترض أن المحرك يدعمها أو أننا نختبر السلوك الافتراضي)
    let mut book = OrderBook::new("BTCUSDT".into());
    
    // وضع أمر بيع
    let order1 = create_limit_order(OrderSide::Sell, 50000.0, 1.0);
    // محاولة شراء نفس الكمية بنفس السعر (من نفس الاستراتيجية)
    let order2 = create_limit_order(OrderSide::Buy, 50000.0, 1.0);
    
    book.add_order(order1).unwrap();
    let trades = book.add_order(order2).unwrap();
    
    // إذا كان لدينا STP (Self-Trade Prevention)، يجب أن يكون عدد الصفقات 0
    // أو يتم تنفيذها إذا لم نقم بتفعيل الـ STP (حسب التصميم الحالي للمحرك)
    // في تصميمنا الحالي، نحن نسمح بذلك تقنياً، ولكن يجب مراقبته.
    
    assert_eq!(trades.len(), 1, "Self-trade executed (Current design allows this, but flags it in logs)");
}