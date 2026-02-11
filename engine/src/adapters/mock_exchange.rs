// Internal Simulator

/*
 * ALPHA SOVEREIGN - HIGH-FIDELITY MARKET SIMULATOR
 * =================================================================
 * Component Name: engine/src/adapters/mock_exchange.rs
 * Core Responsibility: محاكاة بورصة كاملة للاختبار والتطوير (Testing Pillar).
 * Design Pattern: Mock Object / Stochastic Simulator
 * Forensic Impact: يولد بيانات "نظيفة" ومعروفة مسبقاً، مما يجعل اكتشاف الأخطاء الحسابية (Rounding Errors) سهلاً.
 * =================================================================
 */

use async_trait::async_trait;
use tokio::time::{sleep, Duration};
use tokio::sync::Mutex;
use rand::Rng;
use rust_decimal::Decimal;
use rust_decimal::prelude::FromPrimitive;
use tracing::{info, warn, debug};
use std::sync::Arc;

use crate::error::AlphaResult;
use crate::matching::{Order, Trade, Side};
use crate::transport::{EventTx, IngressEvent};
use super::{ExchangeAdapter, ConnectionStatus};

/// إعدادات المحاكي
#[derive(Debug, Clone)]
pub struct MockConfig {
    pub min_latency_ms: u64,    // أقل تأخير للشبكة
    pub max_latency_ms: u64,    // أقصى تأخير (لمحاكاة Jitter)
    pub fill_probability: f64,  // احتمالية تنفيذ الأمر (لمحاكاة السيولة)
    pub slippage_rate: f64,     // نسبة الانزلاق السعري
}

impl Default for MockConfig {
    fn default() -> Self {
        Self {
            min_latency_ms: 10,
            max_latency_ms: 50,
            fill_probability: 1.0, // تنفيذ دائم افتراضياً
            slippage_rate: 0.0,
        }
    }
}

pub struct MockExchange {
    event_bus: EventTx,
    config: MockConfig,
    connected: Mutex<bool>,
}

impl MockExchange {
    pub fn new(event_bus: EventTx, config: Option<MockConfig>) -> Self {
        Self {
            event_bus,
            config: config.unwrap_or_default(),
            connected: Mutex::new(false),
        }
    }

    /// محاكاة تأخير الشبكة (Artificial Latency)
    async fn simulate_network_delay(&self) {
        let mut rng = rand::thread_rng();
        let delay = rng.gen_range(self.config.min_latency_ms..=self.config.max_latency_ms);
        sleep(Duration::from_millis(delay)).await;
    }
}

#[async_trait]
impl ExchangeAdapter for MockExchange {
    fn id(&self) -> &str {
        "MOCK_EXCHANGE_SIMULATOR"
    }

    async fn connect(&mut self) -> AlphaResult<()> {
        info!("MOCK: Initializing virtual connection...");
        sleep(Duration::from_millis(500)).await; // محاكاة المصافحة
        *self.connected.lock().await = true;
        info!("MOCK: Connected. Virtual Market is OPEN.");
        Ok(())
    }

    async fn health_check(&self) -> ConnectionStatus {
        if *self.connected.lock().await {
            ConnectionStatus::Connected
        } else {
            ConnectionStatus::Disconnected
        }
    }

    async fn place_order(&self, order: &Order) -> AlphaResult<String> {
        self.simulate_network_delay().await;

        let order_id = format!("MOCK-{}", order.id);
        let bus = self.event_bus.clone();
        let cfg = self.config.clone();
        let order_clone = order.clone();

        // محاكاة التنفيذ في الخلفية (Matching Engine Simulation)
        tokio::spawn(async move {
            // محاكاة وقت المطابقة
            sleep(Duration::from_millis(10)).await;

            let mut rng = rand::thread_rng();
            
            // هل سينفذ الأمر؟
            if rng.gen::<f64>() <= cfg.fill_probability {
                // حساب الانزلاق (Slippage)
                let slippage_factor = 1.0 + (rng.gen_range(-cfg.slippage_rate..=cfg.slippage_rate));
                let exec_price = order_clone.price * Decimal::from_f64(slippage_factor).unwrap();

                // إنشاء حدث تنفيذ صفقة
                let trade = Trade {
                    taker_order_id: order_clone.id,
                    maker_order_id: 0, // Mock maker
                    price: exec_price,
                    quantity: order_clone.quantity,
                    taker_side: order_clone.side,
                    executed_at: chrono::Utc::now().timestamp_nanos() as u64,
                };

                // إرسال النتيجة للمحرك
                let _ = bus.send(IngressEvent::OrderExecution(trade)).await;
                debug!("MOCK: Order {} FILLED at {}", order_clone.id, exec_price);
            } else {
                debug!("MOCK: Order {} missed liquidity (No Fill).", order_clone.id);
            }
        });

        Ok(order_id)
    }

    async fn cancel_order(&self, _symbol: &str, order_id: &str) -> AlphaResult<()> {
        self.simulate_network_delay().await;
        debug!("MOCK: Order {} Cancelled.", order_id);
        Ok(())
    }

    async fn cancel_all(&self, _symbol: Option<&str>) -> AlphaResult<()> {
        debug!("MOCK: All orders cancelled (Panic Protocol Simulated).");
        Ok(())
    }

    async fn subscribe_ticker(&self, symbol: &str) -> AlphaResult<()> {
        info!("MOCK: Starting random walk market data generator for {}", symbol);
        let bus = self.event_bus.clone();
        let symbol_owned = symbol.to_string();

        // تشغيل مولد أسعار عشوائي (Geometric Brownian Motion Lite)
        tokio::spawn(async move {
            let mut price = Decimal::from(50000); // Start Price BTC
            let mut rng = rand::thread_rng();

            loop {
                // تغيير السعر بنسبة عشوائية +/- 0.1%
                let change_pct = rng.gen_range(-0.001..=0.001);
                let change = price * Decimal::from_f64(change_pct).unwrap();
                price += change;

                let event = IngressEvent::MarketData {
                    symbol: symbol_owned.clone(),
                    price,
                    timestamp: chrono::Utc::now().timestamp_millis() as u64,
                };

                if bus.send(event).await.is_err() {
                    break; // Stop if engine is dead
                }

                // تحديث كل 100ms
                sleep(Duration::from_millis(100)).await;
            }
        });

        Ok(())
    }

    async fn subscribe_user_stream(&self) -> AlphaResult<()> {
        Ok(()) // لا نحتاج لمحاكاة هذا حالياً
    }
}