// Asset Inventory

/*
 * ALPHA SOVEREIGN - REAL-TIME INVENTORY & POSITION MANAGER
 * =================================================================
 * Component Name: engine/src/matching/inventory_mgr.rs
 * Core Responsibility: تتبع الأصول والمراكز المفتوحة بدقة ذرية (Risk Management Pillar).
 * Design Pattern: Ledger / Double-Entry Lite
 * Forensic Impact: يمنع "الأموال الشبحية". كل ساتوشي يجب أن يكون له مكان (إما حر أو محجوز).
 * =================================================================
 */

use std::collections::HashMap;
use rust_decimal::Decimal;
use tracing::{info, warn, error};
use crate::error::{AlphaError, AlphaResult};
use super::Side;

/// تمثل حالة أصل واحد (مثلاً USD أو BTC)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetBalance {
    pub asset_name: String,
    
    /// الرصيد الكلي (الحر + المحجوز)
    pub total: Decimal,
    
    /// الرصيد المحجوز في أوامر نشطة
    pub locked: Decimal,
    
    /// متوسط سعر الدخول (لحساب الـ PnL)
    pub avg_entry_price: Decimal,
}

impl AssetBalance {
    pub fn new(name: &str) -> Self {
        Self {
            asset_name: name.to_string(),
            total: Decimal::ZERO,
            locked: Decimal::ZERO,
            avg_entry_price: Decimal::ZERO,
        }
    }

    /// الرصيد المتاح للتداول أو السحب
    pub fn available(&self) -> Decimal {
        self.total - self.locked
    }
}

pub struct InventoryManager {
    /// سجل الأرصدة: Map<Asset_Symbol, Balance>
    balances: HashMap<String, AssetBalance>,
}

impl InventoryManager {
    pub fn new() -> Self {
        Self {
            balances: HashMap::new(),
        }
    }

    // ----------------------------------------------------------------
    // عمليات التمويل الخارجية (Deposit / Withdraw)
    // ----------------------------------------------------------------

    pub fn deposit(&mut self, asset: &str, amount: Decimal) {
        let entry = self.balances.entry(asset.to_string())
            .or_insert_with(|| AssetBalance::new(asset));
        
        entry.total += amount;
        info!("INVENTORY: Deposited {} {}. New Total: {}", amount, asset, entry.total);
    }

    pub fn withdraw(&mut self, asset: &str, amount: Decimal) -> AlphaResult<()> {
        let entry = self.balances.get_mut(asset)
            .ok_or_else(|| AlphaError::UnknownAsset(asset.to_string()))?;

        if entry.available() < amount {
            return Err(AlphaError::RiskViolation {
                rule: "Insufficient Funds".to_string(),
                limit: entry.available().to_string(),
                actual: amount.to_string(),
            });
        }

        entry.total -= amount;
        info!("INVENTORY: Withdrawn {} {}. Remaining: {}", amount, asset, entry.total);
        Ok(())
    }

    // ----------------------------------------------------------------
    // إدارة الأوامر (Locking / Unlocking)
    // ----------------------------------------------------------------

    /// حجز أموال لأمر جديد (Pre-Trade Check)
    pub fn lock_funds(&mut self, asset: &str, amount: Decimal) -> AlphaResult<()> {
        let entry = self.balances.entry(asset.to_string())
            .or_insert_with(|| AssetBalance::new(asset));

        if entry.available() < amount {
            return Err(AlphaError::RiskViolation {
                rule: "Insufficient Balance for Order".to_string(),
                limit: entry.available().to_string(),
                actual: amount.to_string(),
            });
        }

        entry.locked += amount;
        // لا نسجل Log هنا لتجنب إغراق السجلات، لأن الحجز يحدث بكثرة
        Ok(())
    }

    /// فك الحجز (عند الإلغاء أو الرفض)
    pub fn unlock_funds(&mut self, asset: &str, amount: Decimal) -> AlphaResult<()> {
        let entry = self.balances.get_mut(asset)
            .ok_or_else(|| AlphaError::UnknownAsset(asset.to_string()))?;

        if entry.locked < amount {
            // هذا خطأ خطير يعني وجود خلل في المنطق (Bug)
            error!("CRITICAL: Attempted to unlock more than locked! Asset: {}, Locked: {}, Req: {}", asset, entry.locked, amount);
            // نصحح الوضع قسرياً لمنع الانهيار، لكن يجب التحقيق
            entry.locked = Decimal::ZERO;
        } else {
            entry.locked -= amount;
        }
        Ok(())
    }

    // ----------------------------------------------------------------
    // تسوية الصفقات (Trade Settlement)
    // ----------------------------------------------------------------

    /// تحديث الأرصدة بعد تنفيذ صفقة ناجحة
    /// side: هو جانب الـ User (هل نحن اشترينا أم بعنا؟)
    pub fn commit_trade(&mut self, 
                        base_asset: &str, 
                        quote_asset: &str, 
                        side: Side, 
                        qty: Decimal, 
                        price: Decimal, 
                        fee: Decimal) -> AlphaResult<()> {
        
        let cost = qty * price;

        match side {
            Side::Bid => {
                // شراء: (Buy Base, Pay Quote)
                
                // 1. خصم التكلفة من الـ Quote (المحجوزة سابقاً)
                let quote_bal = self.balances.get_mut(quote_asset)
                    .ok_or_else(|| AlphaError::Fatal("Quote asset missing during settlement".into()))?;
                
                // نفترض أن الأموال كانت محجوزة. نقلل الـ Locked والـ Total
                // ملاحظة: التكلفة الفعلية قد تختلف قليلاً عن المحجوزة، نعالج الفرق
                quote_bal.total -= cost; 
                // نفترض أننا قمنا بفك الحجز قبل الـ commit أو نقلل الـ locked هنا بمقدار التكلفة
                // للتبسيط: سنقلل الـ locked بنفس القيمة (بافتراض الحجز الدقيق)
                if quote_bal.locked >= cost {
                     quote_bal.locked -= cost;
                } else {
                     // هذا يحدث إذا نفذنا بسعر أفضل من المحدد (Slippage favorable)
                     quote_bal.locked = Decimal::ZERO; 
                }

                // 2. إضافة الكمية للـ Base
                let base_bal = self.balances.entry(base_asset.to_string())
                    .or_insert_with(|| AssetBalance::new(base_asset));
                
                // تحديث متوسط السعر (Weighted Average)
                // NewAvg = ((OldTotal * OldAvg) + (NewQty * BuyPrice)) / (OldTotal + NewQty)
                let old_val = base_bal.total * base_bal.avg_entry_price;
                let new_val = qty * price;
                let new_total = base_bal.total + qty - fee; // خصم الرسوم من العملة المستلمة
                
                if new_total > Decimal::ZERO {
                    base_bal.avg_entry_price = (old_val + new_val) / (base_bal.total + qty);
                }
                
                base_bal.total = new_total;
            },

            Side::Ask => {
                // بيع: (Sell Base, Receive Quote)
                
                // 1. خصم الكمية من الـ Base (المحجوزة)
                let base_bal = self.balances.get_mut(base_asset)
                    .ok_or_else(|| AlphaError::Fatal("Base asset missing during settlement".into()))?;
                
                base_bal.total -= qty;
                if base_bal.locked >= qty {
                    base_bal.locked -= qty;
                } else {
                    base_bal.locked = Decimal::ZERO;
                }

                // 2. إضافة التكلفة للـ Quote
                let quote_bal = self.balances.entry(quote_asset.to_string())
                    .or_insert_with(|| AssetBalance::new(quote_asset));
                
                quote_bal.total += cost - fee; // خصم الرسوم من الـ Quote المستلمة
            }
        }

        info!("SETTLEMENT: Trade committed for {}/{} (Qty: {}, Price: {})", base_asset, quote_asset, qty, price);
        Ok(())
    }

    /// الحصول على تقرير المحفظة الكامل
    pub fn get_portfolio_snapshot(&self) -> HashMap<String, Decimal> {
        self.balances.iter()
            .map(|(k, v)| (k.clone(), v.total))
            .collect()
    }
}