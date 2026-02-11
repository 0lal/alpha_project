/*
 * ALPHA SOVEREIGN - MATCHING LOGIC DEEP DIVE
 * =================================================================
 * Component Name: engine/tests/matching_logic_test.rs
 * Core Responsibility: التحقق الصارم من قوانين المطابقة (Priority & Best Execution).
 * Design Pattern: Unit Testing / Edge Case Analysis
 * Forensic Impact: يضمن النزاهة المالية. أي خطأ هنا يعني أن النظام يسرق المستخدمين أو يوزع الأموال بالخطأ.
 * =================================================================
 */

use rust_decimal_macros::dec;
use alpha_engine::matching::orderbook::OrderBook;
use alpha_engine::models::order::{Order, OrderSide, OrderType};
use alpha_engine::utils::id;

// =================================================================
// أدوات المساعدة (Helpers)
// =================================================================
fn limit_buy(price: f64, qty: f64) -> Order {
    Order::new(id::next_id(), "TEST".into(), "BTC".into(), "BIN".into(), OrderSide::Buy, OrderType::Limit, dec!(qty), Some(dec!(price)))
}
fn limit_sell(price: f64, qty: f64) -> Order {
    Order::new(id::next_id(), "TEST".into(), "BTC".into(), "BIN".into(), OrderSide::Sell, OrderType::Limit, dec!(qty), Some(dec!(price)))
}

// =================================================================
// اختبارات المنطق (Logic Tests)
// =================================================================

#[test]
fn test_price_time_priority() {
    // القانون: السعر الأفضل أولاً، ثم الزمن الأقدم.
    let mut book = OrderBook::new("BTCUSDT".into());

    // 1. إضافة بائعين (Makers)
    // بائع قديم بسعر 100
    let seller_early = limit_sell(100.0, 1.0);
    let early_id = seller_early.id;
    book.add_order(seller_early).unwrap();

    // بائع جديد بسعر 100 (نفس السعر)
    let seller_late = limit_sell(100.0, 1.0);
    let late_id = seller_late.id;
    book.add_order(seller_late).unwrap();

    // بائع بسعر أفضل (أرخص) 99
    let seller_cheaper = limit_sell(99.0, 1.0);
    let cheap_id = seller_cheaper.id;
    book.add_order(seller_cheaper).unwrap();

    // 2. مشتري يريد 1 BTC
    // يجب أن يأخذ السعر الأرخص (99) أولاً رغم أنه وصل أخيراً
    let buyer_1 = limit_buy(110.0, 1.0);
    let trades_1 = book.add_order(buyer_1).unwrap();
    
    assert_eq!(trades_1.len(), 1);
    assert_eq!(trades_1[0].maker_order_id, cheap_id, "Should match best price (99) first");
    assert_eq!(trades_1[0].price, dec!(99.0), "Execution price should be maker price");

    // 3. مشتري آخر يريد 1 BTC
    // الآن السعر المتبقي هو 100. يجب أن يأخذ البائع القديم (Early) قبل الجديد (Late)
    let buyer_2 = limit_buy(110.0, 1.0);
    let trades_2 = book.add_order(buyer_2).unwrap();

    assert_eq!(trades_2.len(), 1);
    assert_eq!(trades_2[0].maker_order_id, early_id, "Should match oldest order at same price");
}

#[test]
fn test_best_execution_price_improvement() {
    // القانون: إذا كنت مستعداً للدفع أكثر، النظام يجب أن يعطيك أفضل سعر متاح في الدفتر.
    let mut book = OrderBook::new("ETHUSDT".into());

    // بائع يعرض بـ 2000
    book.add_order(limit_sell(2000.0, 1.0)).unwrap();

    // مشتري ساذج يطلب الشراء بـ 2050 (أعلى من السوق)
    let dumb_buyer = limit_buy(2050.0, 1.0);
    let trades = book.add_order(dumb_buyer).unwrap();

    assert_eq!(trades.len(), 1);
    // السعر يجب أن يكون 2000 (سعر البائع)، وليس 2050 (سعر المشتري)
    assert_eq!(trades[0].price, dec!(2000.0), "Price improvement failed! System stole the spread.");
}

#[test]
fn test_partial_fill_taker_remains() {
    // القانون: إذا لم تكفِ السيولة، المتبقي من أمر Taker يدخل الدفتر كـ Maker.
    let mut book = OrderBook::new("SOLUSDT".into());

    // بائع يعرض 5 حبات
    book.add_order(limit_sell(50.0, 5.0)).unwrap();

    // مشتري يريد 7 حبات
    let big_buyer = limit_buy(50.0, 7.0);
    let buyer_id = big_buyer.id;
    let trades = book.add_order(big_buyer).unwrap();

    // صفقة بـ 5 حبات
    assert_eq!(trades.len(), 1);
    assert_eq!(trades[0].quantity, dec!(5.0));

    // يجب أن يتبقى 2 حبة في جانب الشراء (Bids)
    let snapshot = book.get_snapshot();
    assert_eq!(snapshot.bids.len(), 1);
    assert_eq!(snapshot.bids[0].quantity, dec!(2.0));
    assert_eq!(snapshot.bids[0].id, buyer_id);
    assert_eq!(snapshot.asks.len(), 0); // البائع انتهى
}

#[test]
fn test_rounding_precision() {
    // اختبار الدقة المتناهية (Satoshi Level)
    let mut book = OrderBook::new("DOGE".into());

    // بيع كمية دقيقة جداً
    let tiny_sell = limit_sell(0.12345678, 3.00000001);
    book.add_order(tiny_sell).unwrap();

    // شراء نفس الكمية
    let tiny_buy = limit_buy(0.12345678, 3.00000001);
    let trades = book.add_order(tiny_buy).unwrap();

    assert_eq!(trades.len(), 1);
    assert_eq!(trades[0].quantity, dec!(3.00000001));
    
    // الدفتر يجب أن يكون فارغاً تماماً (لا بقايا عشرية)
    let snapshot = book.get_snapshot();
    assert!(snapshot.asks.is_empty(), "Ghost dust remains in orderbook!");
}

#[test]
fn test_market_order_no_liquidity() {
    // أمر سوق في دفتر فارغ
    let mut book = OrderBook::new("EMPTY".into());
    
    let market_buy = Order::new(
        id::next_id(), "T".into(), "S".into(), "E".into(), 
        OrderSide::Buy, OrderType::Market, dec!(1.0), None
    );

    let trades = book.add_order(market_buy).unwrap(); // يجب ألا ينهار النظام
    
    assert_eq!(trades.len(), 0);
    // أمر السوق عادة إما يلغى (IOC) أو يبقى معلقاً حسب السياسة.
    // في تصميمنا الأساسي، أوامر السوق بدون سيولة قد ترفض أو تبقى معلقة. 
    // هنا نفترض أنها لم تنفذ شيئاً.
}