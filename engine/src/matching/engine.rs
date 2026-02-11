use crate::error::{AlphaError, AlphaResult};
use crate::models::order::{Order, OrderSide, OrderType, OrderStatus};
use crate::utils::logger::log_trade;
use rust_decimal::Decimal;
use parking_lot::RwLock;
use std::collections::{BTreeMap, HashMap, VecDeque};
use std::sync::Arc;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct MatchingResult {
    pub order: Order,
    pub trades: Vec<TradeExecution>,
}

#[derive(Debug, Clone)]
// FIX 1: Added missing fields to struct definition
pub struct TradeExecution {
    pub trade_id: String,
    pub symbol: String,
    pub price: Decimal,
    pub quantity: Decimal,
    pub side: OrderSide,
    pub timestamp: u64,
    pub maker_order_id: String,
    pub taker_order_id: String,
}

struct OrderBook {
    symbol: String,
    bids: BTreeMap<Decimal, VecDeque<Order>>,
    asks: BTreeMap<Decimal, VecDeque<Order>>,
}

impl OrderBook {
    fn new(symbol: &str) -> Self {
        Self {
            symbol: symbol.to_string(),
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
        }
    }

    fn process(&mut self, mut order: Order) -> MatchingResult {
        let mut trades = Vec::new();
        match order.side {
            OrderSide::Buy => self.match_bid(&mut order, &mut trades),
            OrderSide::Sell => self.match_ask(&mut order, &mut trades),
        }
        
        if !order.is_closed() {
            match order.order_type {
                OrderType::Limit => self.add_limit_order(order.clone()),
                OrderType::Market => { order.status = OrderStatus::Canceled; },
                _ => {}
            }
        }
        
        MatchingResult { order, trades }
    }

    fn match_bid(&mut self, order: &mut Order, trades: &mut Vec<TradeExecution>) {
        while order.is_active() {
            // FIX 2: Decouple borrow. Get the queue entry first.
            let mut best_ask_entry = self.asks.iter_mut().next();
            
            // We need to extract what we need to avoid holding 'self' borrow
            match best_ask_entry {
                Some((price, queue)) => {
                    // Check price condition
                    if let Some(limit) = order.price {
                        if *price > limit { break; }
                    }
                    
                    // Process the order in the queue
                    if let Some(maker) = queue.front_mut() {
                        // FIX 3: Inlined execution logic to satisfy borrow checker
                        // Instead of calling self.execute_match (which borrows self again)
                        // we do the logic right here.
                        
                        let match_qty = (order.original_qty - order.executed_qty).min(maker.original_qty - maker.executed_qty);
                        let exec_price = *price;
                        
                        // Update Maker
                        maker.executed_qty += match_qty;
                        if maker.executed_qty >= maker.original_qty {
                            maker.status = OrderStatus::Filled;
                        } else {
                            maker.status = OrderStatus::PartiallyFilled;
                        }
                        
                        // Update Taker (Order)
                        order.executed_qty += match_qty;
                        if order.executed_qty >= order.original_qty {
                            order.status = OrderStatus::Filled;
                        } else {
                            order.status = OrderStatus::PartiallyFilled;
                        }
                        
                        // Record Trade
                        let trade_id = Uuid::new_v4().simple().to_string();
                        log_trade(&order.symbol, "MATCH", &exec_price.to_string(), &match_qty.to_string(), &trade_id);
                        
                        trades.push(TradeExecution {
                            trade_id,
                            symbol: order.symbol.clone(),
                            price: exec_price,
                            quantity: match_qty,
                            side: order.side,
                            timestamp: chrono::Utc::now().timestamp_millis() as u64,
                            maker_order_id: maker.client_order_id.clone(),
                            taker_order_id: order.client_order_id.clone(),
                        });
                        
                        // Cleanup happens outside
                    }
                    
                    // Remove closed maker orders from queue
                    if let Some(maker) = queue.front() {
                        if maker.is_closed() {
                            queue.pop_front();
                        }
                    }
                },
                None => break,
            }
            
            // Garbage collect empty levels
            self.asks.retain(|_, queue| !queue.is_empty());
        }
    }

    fn match_ask(&mut self, order: &mut Order, trades: &mut Vec<TradeExecution>) {
        while order.is_active() {
            // FIX 2: Same fix for Ask side (Decouple borrow)
            let mut best_bid_entry = self.bids.iter_mut().rev().next();
            
            match best_bid_entry {
                Some((price, queue)) => {
                    if let Some(limit) = order.price {
                        if *price < limit { break; }
                    }
                    
                    if let Some(maker) = queue.front_mut() {
                        // FIX 3: Inlined execution logic
                        let match_qty = (order.original_qty - order.executed_qty).min(maker.original_qty - maker.executed_qty);
                        let exec_price = *price;
                        
                        maker.executed_qty += match_qty;
                        if maker.executed_qty >= maker.original_qty {
                            maker.status = OrderStatus::Filled;
                        } else {
                            maker.status = OrderStatus::PartiallyFilled;
                        }
                        
                        order.executed_qty += match_qty;
                        if order.executed_qty >= order.original_qty {
                            order.status = OrderStatus::Filled;
                        } else {
                            order.status = OrderStatus::PartiallyFilled;
                        }
                        
                        let trade_id = Uuid::new_v4().simple().to_string();
                        log_trade(&order.symbol, "MATCH", &exec_price.to_string(), &match_qty.to_string(), &trade_id);
                        
                        trades.push(TradeExecution {
                            trade_id,
                            symbol: order.symbol.clone(),
                            price: exec_price,
                            quantity: match_qty,
                            side: order.side,
                            timestamp: chrono::Utc::now().timestamp_millis() as u64,
                            maker_order_id: maker.client_order_id.clone(),
                            taker_order_id: order.client_order_id.clone(),
                        });
                    }
                    
                    if let Some(maker) = queue.front() {
                        if maker.is_closed() {
                            queue.pop_front();
                        }
                    }
                },
                None => break,
            }
            self.bids.retain(|_, queue| !queue.is_empty());
        }
    }

    fn add_limit_order(&mut self, order: Order) {
        if let Some(price) = order.price {
            let book = match order.side {
                OrderSide::Buy => &mut self.bids,
                OrderSide::Sell => &mut self.asks,
            };
            book.entry(price).or_insert_with(VecDeque::new).push_back(order);
        }
    }
}

pub struct MatchingEngine {
    order_books: HashMap<String, Arc<RwLock<OrderBook>>>,
}

impl MatchingEngine {
    pub fn new() -> Self {
        Self { order_books: HashMap::new() }
    }
    
    pub fn process_order(&mut self, order: Order) -> AlphaResult<MatchingResult> {
        let symbol = order.symbol.clone();
        let book = self.order_books.entry(symbol.clone())
            .or_insert_with(|| Arc::new(RwLock::new(OrderBook::new(&symbol))));
        
        Ok(book.write().process(order))
    }
}
