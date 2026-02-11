// Atomic Safety Gate

/*
 * ALPHA SOVEREIGN - PRE-TRADE SANITY VALIDATOR
 * =================================================================
 * Component Name: engine/src/risk/pre_trade_check.rs
 * Core Responsibility: فحص نزاهة الأمر والامتثال للقواعد الصارمة (Governance Pillar).
 * Design Pattern: Chain of Responsibility / Validator
 * Forensic Impact: يمنع "الأوامر الشبحية" أو "أخطاء الإصبع" من الوصول للسوق وتشويه سمعة النظام.
 * =================================================================
 */

use rust_decimal::Decimal;
use rust_decimal::prelude::{FromPrimitive, ToPrimitive};
use tracing::{warn, error, info};
use crate::error::{AlphaError, AlphaResult};
use crate::matching::{Order, Side, OrderType};

/// قيود التداول (يتم تحميلها لكل زوج عملات)
#[derive(Debug, Clone)]
pub struct TradeConstraints {
    pub min_price: Decimal,
    pub max_price: Decimal,
    pub min_quantity: Decimal,
    pub max_quantity: Decimal,
    pub min_notional: Decimal,     // أقل قيمة للصفقة (Dust Limit)
    pub max_notional: Decimal,     // أقصى قيمة للصفقة (Fat Finger Limit)
    pub max_price_deviation: Decimal, // نسبة الانحراف المسموحة عن سعر السوق (e.g., 0.10 for 10%)
}

pub struct PreTradeCheck {
    constraints: TradeConstraints,
}

impl PreTradeCheck {
    pub fn new(constraints: TradeConstraints) -> Self {
        Self { constraints }
    }

    /// التحقق الشامل من الأمر
    /// reference_price: سعر السوق الحالي (Last Trade Price or Mid Price)
    pub fn validate(&self, order: &Order, reference_price: Option<Decimal>) -> AlphaResult<()> {
        
        // 1. الفحص الأساسي (Sanity Check)
        // لا يمكن أن يكون السعر أو الكمية صفر أو سالب (إلا في أوامر السوق قد يكون السعر 0)
        if order.quantity <= Decimal::ZERO {
            return Err(self.reject("Zero or Negative Quantity", order.quantity));
        }
        
        if order.order_type == OrderType::Limit && order.price <= Decimal::ZERO {
            return Err(self.reject("Zero or Negative Price for Limit Order", order.price));
        }

        // 2. فحص الحدود الكمية (Quantity Limits)
        if order.quantity < self.constraints.min_quantity {
            return Err(self.reject("Quantity below minimum allowed", order.quantity));
        }
        if order.quantity > self.constraints.max_quantity {
            return Err(self.reject("Quantity exceeds maximum allowed", order.quantity));
        }

        // 3. فحص القيمة الإسمية (Notional Value Check)
        // Notional = Price * Quantity
        // هذا أهم فحص لمنع "Fat Finger"
        let estimated_price = if order.price > Decimal::ZERO { 
            order.price 
        } else { 
            reference_price.unwrap_or(Decimal::ONE) // في حالة أمر السوق وعدم وجود مرجع
        };
        
        let notional = estimated_price * order.quantity;

        if notional < self.constraints.min_notional {
            return Err(self.reject("Order value too small (Dust)", notional));
        }

        if notional > self.constraints.max_notional {
            error!("FAT_FINGER_DETECTED: Attempted notional {} exceeds limit {}", notional, self.constraints.max_notional);
            return Err(self.reject("FAT FINGER PROTECTION: Order value too high", notional));
        }

        // 4. فحص الانحراف السعري (Price Band Check)
        // يمنع الشراء بسعر أعلى بكثير من السوق، أو البيع بسعر أقل بكثير
        if let Some(ref_price) = reference_price {
            if ref_price > Decimal::ZERO && order.order_type == OrderType::Limit {
                let deviation = (order.price - ref_price).abs() / ref_price;
                
                if deviation > self.constraints.max_price_deviation {
                    let msg = format!(
                        "Price deviation {:.2}% exceeds limit {:.2}% (Ref: {}, Order: {})",
                        deviation * Decimal::from(100),
                        self.constraints.max_price_deviation * Decimal::from(100),
                        ref_price,
                        order.price
                    );
                    warn!("PRICE_BAND_VIOLATION: {}", msg);
                    return Err(AlphaError::RiskViolation {
                        rule: "PRICE_BAND".into(),
                        limit: self.constraints.max_price_deviation.to_string(),
                        actual: deviation.to_string(),
                    });
                }
            }
        }

        Ok(())
    }

    /// مساعد لإنشاء خطأ الرفض
    fn reject(&self, reason: &str, value: Decimal) -> AlphaError {
        warn!("ORDER_REJECTED: {} (Value: {})", reason, value);
        AlphaError::RiskViolation {
            rule: "PRE_TRADE_VALIDATION".into(),
            limit: "See Constraints".into(),
            actual: value.to_string(),
        }
    }
}