// FIFO Matching Logic

/*
 * ALPHA SOVEREIGN - CENTRAL MATCHING ENGINE CONTROLLER
 * =================================================================
 * Component Name: engine/src/matching/engine.rs
 * Core Responsibility: إدارة دفاتر الأوامر المتعددة وتوجيه الطلبات (Performance Pillar).
 * Design Pattern: Facade / Aggregator
 * Forensic Impact: نقطة الدخول الوحيدة لتعديل حالة السوق. إذا لم يمر الأمر من هنا، فهو لم يحدث.
 * =================================================================
 */

use std::collections::HashMap;
use tracing::{info, error, warn};
use crate::error::{AlphaError, AlphaResult};
use super::orderbook::OrderBook;
use super::{Order, MatchingResult, OrderStatus};

pub struct MatchEngine {
    /// خريطة لجميع دفاتر الأوامر النشطة.
    /// المفتاح هو symbol_id (e.g., 1 for BTC, 2 for ETH).
    books: HashMap<u32, OrderBook>,
}

impl MatchEngine {
    pub fn new() -> Self {
        info!("MATCH_ENGINE: Initializing core systems...");
        Self {
            books: HashMap::new(),
        }
    }

    /// إنشاء سوق جديد (Trading Pair)
    pub fn create_market(&mut self, symbol_id: u32, symbol_name: &str) -> AlphaResult<()> {
        if self.books.contains_key(&symbol_id) {
            warn!("MARKET_DUPLICATE: Attempted to create existing market {}", symbol_id);
            return Err(AlphaError::ConfigMissing(format!("Market {} already exists", symbol_id)));
        }

        let book = OrderBook::new(symbol_id);
        self.books.insert(symbol_id, book);
        
        info!("MARKET_OPENED: Created new order book for {} (ID: {})", symbol_name, symbol_id);
        Ok(())
    }

    /// استقبال أمر جديد وتوجيهه للدفتر المناسب
    pub fn place_limit_order(&mut self, order: Order) -> AlphaResult<MatchingResult> {
        // 1. التحقق من صحة الأمر (Sanity Check)
        if !order.validate() {
            return Err(AlphaError::MathError("Invalid price or quantity (must be > 0)".to_string()));
        }

        // 2. البحث عن الدفتر المناسب
        let book = self.books.get_mut(&order.symbol_id)
            .ok_or_else(|| AlphaError::UnknownAsset(format!("Symbol ID {} not found", order.symbol_id)))?;

        // 3. التنفيذ داخل الدفتر
        // العملية هنا تتم في الذاكرة (In-Memory) وهي سريعة جداً
        let result = book.process_order(order);

        // 4. تسجيل النتيجة (اختياري للتدقيق العالي)
        if !result.trades.is_empty() {
            info!("TRADE_MATCH: {} trades executed on Symbol {}", result.trades.len(), book.symbol_id);
        }

        Ok(result)
    }

    /// إلغاء أمر
    pub fn cancel_order(&mut self, symbol_id: u32, order_id: u64) -> AlphaResult<bool> {
        let book = self.books.get_mut(&symbol_id)
            .ok_or_else(|| AlphaError::UnknownAsset(format!("Symbol ID {} not found", symbol_id)))?;

        let success = book.cancel_order(order_id);
        
        if success {
            info!("ORDER_CANCEL: Successfully cancelled Order #{}", order_id);
        } else {
            warn!("CANCEL_FAIL: Order #{} not found in Symbol {}", order_id, symbol_id);
        }

        Ok(success)
    }

    /// الحصول على لقطة لعمق السوق (لإرسالها للدماغ/Dashboard)
    /// هذه العملية قد تكون مكلفة، لذا يجب استخدامها بحذر
    pub fn get_market_depth(&self, symbol_id: u32, depth: usize) -> AlphaResult<String> {
        let _book = self.books.get(&symbol_id)
            .ok_or_else(|| AlphaError::UnknownAsset(format!("Symbol ID {} not found", symbol_id)))?;

        // (هنا سنقوم بإرجاع JSON يمثل الـ Bids/Asks)
        // للتبسيط في هذا الملف، نرجع نصاً
        Ok(format!("Market Depth Snapshot for ID {} (Top {})", symbol_id, depth))
    }
}