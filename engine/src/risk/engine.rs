use crate::error::{AlphaError, AlphaResult};
use crate::models::order::Order;
use crate::utils::logger::log_risk_reject;
use rust_decimal::Decimal;
use rust_decimal::prelude::Zero;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Debug, Clone)]
pub struct RiskConfig {
    pub max_daily_loss: Decimal,
    pub max_order_value: Decimal,
}

impl Default for RiskConfig {
    fn default() -> Self {
        Self {
            max_daily_loss: Decimal::new(1000, 0),
            max_order_value: Decimal::new(5000, 0),
        }
    }
}

pub struct RiskEngine {
    config: RiskConfig,
    current_loss: Arc<RwLock<Decimal>>,
}

impl RiskEngine {
    pub fn new(config: Option<RiskConfig>) -> Self {
        Self { 
            config: config.unwrap_or_default(),
            current_loss: Arc::new(RwLock::new(Decimal::ZERO)),
        }
    }

    pub fn check_order(&self, order: &Order) -> AlphaResult<()> {
        // 1. Validation
        if order.original_qty <= Decimal::ZERO {
            return Err(AlphaError::ValidationFailed("Quantity must be positive".into()));
        }

        // 2. Notional Value Check
        let price = order.price.unwrap_or(Decimal::ZERO);
        let value = order.original_qty * price;
        
        if value > self.config.max_order_value {
            log_risk_reject("MAX_ORDER_VALUE", &self.config.max_order_value.to_string(), &value.to_string());
            return Err(AlphaError::RiskViolation {
                rule: "Max Order Value".into(),
                limit: self.config.max_order_value.to_string(),
                actual: value.to_string(),
            });
        }

        // 3. Daily Loss Check
        let loss = self.current_loss.read();
        if *loss >= self.config.max_daily_loss {
            return Err(AlphaError::RiskViolation {
                rule: "Max Daily Loss".into(),
                limit: self.config.max_daily_loss.to_string(),
                actual: loss.to_string(),
            });
        }

        Ok(())
    }
}
