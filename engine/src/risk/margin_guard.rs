// Leverage Control

/*
 * ALPHA SOVEREIGN - REAL-TIME MARGIN & LEVERAGE GUARDIAN
 * =================================================================
 * Component Name: engine/src/risk/margin_guard.rs
 * Core Responsibility: مراقبة صحة الهامش ومنع التسييل القسري (Risk Management Pillar).
 * Design Pattern: Sentinel / Pre-Trade Validator
 * Forensic Impact: يوثق "نسبة الهامش" (Margin Ratio) لحظة اتخاذ القرار. يفسر لماذا رفض النظام زيادة الرافعة.
 * =================================================================
 */

use rust_decimal::Decimal;
use rust_decimal::prelude::{FromPrimitive, ToPrimitive};
use tracing::{warn, error, info};
use crate::error::{AlphaError, AlphaResult};

/// إعدادات حارس الهامش
#[derive(Debug, Clone)]
pub struct MarginConfig {
    /// الرافعة المالية القصوى المسموحة عالمياً للنظام (مثلاً 10x)
    pub max_global_leverage: Decimal,
    
    /// نسبة التحذير من التسييل (مثلاً 0.80)
    /// يعني: إذا وصلنا لـ 80% من المسافة نحو التسييل، ابدأ في تقليل المراكز.
    pub liquidation_safety_buffer: Decimal,
    
    /// الحد الأدنى للهامش المقبول (Maintenance Margin Rate)
    /// يختلف حسب العملة (مثلاً BTC تحتاج 0.5%، بينما ALTCOIN تحتاج 2%)
    pub default_maintenance_margin: Decimal,
}

/// لقطة لوضع المحفظة (تستخدم في الحسابات)
pub struct PortfolioHealth {
    pub total_equity: Decimal,      // الرصيد + الربح غير المحقق
    pub total_notional: Decimal,    // القيمة الإسمية لكل المراكز المفتوحة
    pub used_margin: Decimal,       // الهامش المحجوز حالياً
    pub margin_ratio: Decimal,      // نسبة الهامش (الخطر)
    pub effective_leverage: Decimal,// الرافعة الحقيقية المستخدمة
}

pub struct MarginGuard {
    config: MarginConfig,
}

impl MarginGuard {
    pub fn new(config: MarginConfig) -> Self {
        Self { config }
    }

    /// 1. فحص ما قبل التداول (Pre-Trade Check)
    /// هل سيؤدي هذا الأمر الجديد إلى كسر قواعد الرافعة المالية؟
    pub fn check_new_order(
        &self,
        current_equity: Decimal,
        current_position_notional: Decimal,
        new_order_notional: Decimal,
    ) -> AlphaResult<()> {
        
        let projected_notional = current_position_notional + new_order_notional;
        
        // حساب الرافعة المتوقعة: Notional / Equity
        if current_equity.is_zero() {
            return Err(AlphaError::RiskViolation {
                rule: "Zero Equity".into(),
                limit: "0".into(),
                actual: "0".into(),
            });
        }

        let projected_leverage = projected_notional / current_equity;

        // التحقق من الحد الأقصى للرافعة
        if projected_leverage > self.config.max_global_leverage {
            return Err(AlphaError::RiskViolation {
                rule: "MAX_LEVERAGE_EXCEEDED".to_string(),
                limit: self.config.max_global_leverage.to_string(),
                actual: projected_leverage.round_dp(2).to_string(),
            });
        }

        Ok(())
    }

    /// 2. تقييم الصحة العامة (Real-time Health Check)
    /// يتم استدعاؤه مع كل تحديث للسعر (Tick)
    pub fn evaluate_health(
        &self,
        equity: Decimal,
        maintenance_margin_required: Decimal,
        total_notional: Decimal,
    ) -> AlphaResult<PortfolioHealth> {
        
        if equity <= Decimal::ZERO {
            // حالة إفلاس (Bankruptcy)
            error!("MARGIN_CRITICAL: Negative Equity detected! Immediate liquidation protocol required.");
            return Err(AlphaError::Fatal("NEGATIVE_EQUITY".into()));
        }

        // نسبة الهامش = الهامش المطلوب للصيانة / الرصيد الحالي
        // إذا وصلت 100% (1.0)، فالبورصة ستقوم بالتسييل.
        let margin_ratio = if equity.is_zero() {
            Decimal::MAX
        } else {
            maintenance_margin_required / equity
        };

        let effective_leverage = if equity.is_zero() {
            Decimal::ZERO 
        } else {
            total_notional / equity
        };

        // التحقق من المناطق الخطرة
        if margin_ratio > self.config.liquidation_safety_buffer {
            warn!(
                "MARGIN_WARNING: Margin Ratio at {}% (Buffer: {}%). System is approaching liquidation.",
                (margin_ratio * Decimal::from(100)).round_dp(2),
                (self.config.liquidation_safety_buffer * Decimal::from(100)).round_dp(2)
            );
            
            // هنا يمكن إرسال إشارة لتقليل المراكز (De-leveraging Signal)
            // في النسخة الكاملة، سنعيد Enum يطلب Action معين
        }

        Ok(PortfolioHealth {
            total_equity: equity,
            total_notional,
            used_margin: maintenance_margin_required,
            margin_ratio,
            effective_leverage,
        })
    }

    /// 3. حساب سعر التسييل الداخلي (للتخطيط)
    /// يعيد السعر الذي يجب أن نخرج عنده قبل البورصة
    pub fn calculate_internal_liquidation_price(
        &self,
        entry_price: Decimal,
        leverage: Decimal,
        is_long: bool,
    ) -> Decimal {
        // معادلة تقريبية للتسييل:
        // Long: Entry * (1 - (1/Leverage) + MMR)
        // MMR = Maintenance Margin Rate (e.g., 0.5%)
        
        let mmr = self.config.default_maintenance_margin;
        let safety_pad = Decimal::from_f64(0.02).unwrap(); // نزيد 2% أمان إضافي

        if is_long {
            // Entry * (1 - 1/Lev + MMR + Pad)
            let risk_factor = (Decimal::ONE / leverage) - mmr - safety_pad;
            entry_price * (Decimal::ONE - risk_factor)
        } else {
            // Short: Entry * (1 + 1/Lev - MMR - Pad)
            let risk_factor = (Decimal::ONE / leverage) - mmr - safety_pad;
            entry_price * (Decimal::ONE + risk_factor)
        }
    }
}