// L3 Order Book Data Structure

/*
 * ALPHA SOVEREIGN - L3 ORDER BOOK DATA STRUCTURE
 * =================================================================
 * Component Name: engine/src/matching/order_book.rs
 * Core Responsibility: إدارة دفتر الأوامر وهياكل المطابقة (Performance Pillar).
 * Design Pattern: B-Tree Map + FIFO Queue + Hash Index
 * Forensic Impact: يضمن ترتيب الأوامر بدقة "السعر-الزمن". أي تلاعب في هذا الملف يعني تلاعباً في نزاهة السوق.
 * =================================================================
 */

use std::collections::{BTreeMap, HashMap, VecDeque};
use rust_decimal::Decimal;
use tracing::{info, warn};
use super::{Order, Side, Trade, MatchingResult, OrderStatus};

/// موقع الأمر داخل الدفتر (للسرعة في الإلغاء)
struct OrderLocation {
    price: Decimal,
    side: Side,
}

pub struct OrderBook {
    pub symbol_id: u32,

    // 1. جانب الشراء (Bids)
    // BTreeMap يرتب المفاتيح تصاعدياً.
    // للمشترين: نريد السعر الأعلى أولاً (نستخدم iter().rev()).
    // القيمة: طابور (FIFO) للأوامر بنفس السعر.
    bids: BTreeMap<Decimal, VecDeque<Order>>,

    // 2. جانب البيع (Asks)
    // للبائعين: نريد السعر الأقل أولاً (نستخدم iter()).
    asks: BTreeMap<Decimal, VecDeque<Order>>,

    // 3. الفهرس السريع (The Index)
    // يسمح بالوصول للأمر ومعرفة سعره بمجرد معرفة الـ ID.
    // يحول عملية الإلغاء من O(N) إلى O(1).
    order_index: HashMap<u64, OrderLocation>,
}

impl OrderBook {
    pub fn new(symbol_id: u32) -> Self {
        Self {
            symbol_id,
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
            order_index: HashMap::new(),
        }
    }

    /// المحرك الرئيسي: معالجة أمر جديد ومحاولة مطابقته
    pub fn process_order(&mut self, mut order: Order) -> MatchingResult {
        let mut trades = Vec::new();

        // 1. محاولة المطابقة (Crossing the Spread)
        // إذا كان الأمر شراء، نبحث في الـ Asks. إذا كان بيعاً، نبحث في الـ Bids.
        match order.side {
            Side::Bid => self.match_bid(&mut order, &mut trades),
            Side::Ask => self.match_ask(&mut order, &mut trades),
        }

        // 2. التعامل مع المتبقي (Resting Order)
        let mut status = OrderStatus::Filled;
        
        if order.quantity > Decimal::ZERO {
            // إذا لم ينفذ بالكامل، نضيف الباقي للدفتر (إلا إذا كان IOC/FOK)
            // (في هذا التنفيذ المبسط نفترض Limit عادي)
            self.add_limit_order(order.clone());
            status = if trades.is_empty() { OrderStatus::Queued } else { OrderStatus::PartiallyFilled };
        }

        MatchingResult {
            trades,
            remaining_qty: order.quantity,
            status,
        }
    }

    /// إلغاء أمر موجود
    pub fn cancel_order(&mut self, order_id: u64) -> bool {
        // 1. البحث في الفهرس
        if let Some(loc) = self.order_index.remove(&order_id) {
            // 2. تحديد الجانب والسعر
            let book_side = match loc.side {
                Side::Bid => &mut self.bids,
                Side::Ask => &mut self.asks,
            };

            // 3. الوصول للطابور وحذف الأمر
            if let Some(queue) = book_side.get_mut(&loc.price) {
                // ملاحظة: الحذف من وسط VecDeque مكلف O(k)، لكن الطابور عادة قصير
                if let Some(idx) = queue.iter().position(|o| o.id == order_id) {
                    queue.remove(idx);
                    
                    // تنظيف السعر إذا أصبح فارغاً لتوفير الذاكرة
                    if queue.is_empty() {
                        book_side.remove(&loc.price);
                    }
                    return true;
                }
            }
        }
        false
    }

    // ----------------------------------------------------------------
    // المنطق الداخلي للمطابقة (Matching Logic)
    // ----------------------------------------------------------------

    fn match_bid(&mut self, order: &mut Order, trades: &mut Vec<Trade>) {
        // للمشتري: نبحث عن أرخص بائع (Iterate normal: Low -> High)
        while order.quantity > Decimal::ZERO {
            // نأخذ نظرة على أفضل عرض (Best Ask) دون حذفه
            let mut best_ask_entry = match self.asks.first_entry() {
                Some(e) => e,
                None => break, // لا يوجد بائعون
            };

            let ask_price = *best_ask_entry.key();

            // شرط الحد: هل سعر البائع أعلى مما أريد دفعه؟
            if ask_price > order.price {
                break; // لا يمكن المطابقة، السعر غالي
            }

            let ask_queue = best_ask_entry.get_mut();
            
            // تنفيذ الأوامر في الطابور (FIFO)
            while order.quantity > Decimal::ZERO && !ask_queue.is_empty() {
                let best_ask = ask_queue.front_mut().unwrap();
                
                // حساب الكمية المتطابقة
                let matched_qty = std::cmp::min(order.quantity, best_ask.quantity);

                // تسجيل الصفقة
                trades.push(Trade {
                    taker_order_id: order.id,
                    maker_order_id: best_ask.id,
                    price: ask_price, // السعر دائماً هو سعر الـ Maker (صانع السوق)
                    quantity: matched_qty,
                    taker_side: Side::Bid,
                    executed_at: chrono::Utc::now().timestamp_nanos() as u64, // أو نستخدم timestamp النظام
                });

                // تحديث الكميات
                order.quantity -= matched_qty;
                best_ask.quantity -= matched_qty;

                // إذا انتهى أمر الـ Maker، نحذفه من الدفتر والفهرس
                if best_ask.quantity == Decimal::ZERO {
                    let removed = ask_queue.pop_front().unwrap();
                    self.order_index.remove(&removed.id);
                }
            }

            // إذا فرغ الطابور، نحذف مستوى السعر بالكامل
            if ask_queue.is_empty() {
                best_ask_entry.remove();
            }
        }
    }

    fn match_ask(&mut self, order: &mut Order, trades: &mut Vec<Trade>) {
        // للبائع: نبحث عن أغلى مشتري (Iterate Reversed: High -> Low)
        while order.quantity > Decimal::ZERO {
            let mut best_bid_entry = match self.bids.last_entry() {
                Some(e) => e,
                None => break,
            };

            let bid_price = *best_bid_entry.key();

            if bid_price < order.price {
                break; // لا يوجد مشترون بهذا السعر
            }

            let bid_queue = best_bid_entry.get_mut();

            while order.quantity > Decimal::ZERO && !bid_queue.is_empty() {
                let best_bid = bid_queue.front_mut().unwrap();
                let matched_qty = std::cmp::min(order.quantity, best_bid.quantity);

                trades.push(Trade {
                    taker_order_id: order.id,
                    maker_order_id: best_bid.id,
                    price: bid_price,
                    quantity: matched_qty,
                    taker_side: Side::Ask,
                    executed_at: chrono::Utc::now().timestamp_nanos() as u64,
                });

                order.quantity -= matched_qty;
                best_bid.quantity -= matched_qty;

                if best_bid.quantity == Decimal::ZERO {
                    let removed = bid_queue.pop_front().unwrap();
                    self.order_index.remove(&removed.id);
                }
            }

            if bid_queue.is_empty() {
                best_bid_entry.remove();
            }
        }
    }

    fn add_limit_order(&mut self, order: Order) {
        // إضافة للفهرس
        self.order_index.insert(order.id, OrderLocation {
            price: order.price,
            side: order.side,
        });

        // إضافة للدفتر
        let book_side = match order.side {
            Side::Bid => &mut self.bids,
            Side::Ask => &mut self.asks,
        };

        // الحصول على الطابور أو إنشاءه
        book_side
            .entry(order.price)
            .or_insert_with(VecDeque::new)
            .push_back(order);
            
        // info!("ORDER_BOOK: Added order {} @ {}", order.id, order.price);
    }
}