/*
 * ALPHA SOVEREIGN - STATE-AWARE FIREWALL ENGINE
 * =================================================================
 * Component Name: shield/perimeter/firewall_rules_engine.rs
 * Core Responsibility: تصفية حركة المرور بناءً على حالة النظام الأمنية (Security Pillar).
 * Design Pattern: State Pattern / Chain of Responsibility
 * Forensic Impact: يسجل كل حزمة مرفوضة مع "السبب السياقي". (مثلاً: رُفضت لأن النظام في حالة إغلاق).
 * =================================================================
 */

use std::net::IpAddr;
use std::sync::{Arc, RwLock};
use std::collections::HashSet;
use tracing::{info, warn, error};
use crate::error::{AlphaError, AlphaResult};

/// حالات النظام الدفاعية (DEFCON Levels)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd)]
pub enum SystemDefcon {
    Level5_Normal = 5,   // الوضع الطبيعي: تداول مسموح
    Level4_HighAlert = 4,// تحذير: تداول مسموح مع قيود
    Level3_NoTrade = 3,  // إيقاف التداول: إلغاء الأوامر فقط
    Level2_Lockdown = 2, // إغلاق: مسموح فقط للمسؤول (Localhost + Admin IP)
    Level1_Omega = 1,    // النهاية: مسموح فقط لمحفظة التسييل
}

/// اتجاه الحركة
#[derive(Debug, Clone, PartialEq)]
pub enum TrafficDirection {
    Inbound,
    Outbound,
}

/// سياق الحزمة (Metadata)
#[derive(Debug)]
pub struct TrafficContext {
    pub source_ip: IpAddr,
    pub dest_port: u16,
    pub direction: TrafficDirection,
    pub protocol: String, // "TCP", "UDP", "gRPC"
}

/// قاعدة جدار ناري
#[derive(Clone)]
struct FirewallRule {
    name: String,
    allowed_ports: HashSet<u16>,
    // في التطبيق الفعلي نستخدم IpNetwork للتعامل مع CIDR
    allowed_ips: HashSet<IpAddr>, 
    min_defcon: SystemDefcon, // القاعدة فعالة فقط إذا كان النظام في هذا المستوى أو أعلى
}

pub struct FirewallRulesEngine {
    current_defcon: Arc<RwLock<SystemDefcon>>,
    rules: Arc<RwLock<Vec<FirewallRule>>>,
    blacklist: Arc<RwLock<HashSet<IpAddr>>>,
}

impl FirewallRulesEngine {
    pub fn new() -> Self {
        let engine = Self {
            current_defcon: Arc::new(RwLock::new(SystemDefcon::Level5_Normal)),
            rules: Arc::new(RwLock::new(Vec::new())),
            blacklist: Arc::new(RwLock::new(HashSet::new())),
        };

        // تحميل القواعد الافتراضية
        engine.load_default_rules();
        engine
    }

    fn load_default_rules(&self) {
        let mut rules = self.rules.write().unwrap();
        
        // القاعدة 1: السماح بـ Localhost دائماً (للإدارة الداخلية)
        // فعالة حتى في حالة Lockdown (Level 2)
        rules.push(FirewallRule {
            name: "Allow Localhost Internal".to_string(),
            allowed_ports: HashSet::from([5555, 50051, 8080]), // ZMQ, gRPC, Web
            allowed_ips: HashSet::from(["127.0.0.1".parse().unwrap()]),
            min_defcon: SystemDefcon::Level2_Lockdown,
        });

        // القاعدة 2: السماح بالبورصات (Binance API)
        // فعالة فقط في الوضع الطبيعي والتحذير (Level 4+)
        // ملاحظة: IPs البورصات تتغير، هنا نضع مثالاً
        rules.push(FirewallRule {
            name: "Allow Exchange API".to_string(),
            allowed_ports: HashSet::from([443]),
            allowed_ips: HashSet::from(["1.1.1.1".parse().unwrap()]), // Example IP
            min_defcon: SystemDefcon::Level4_HighAlert,
        });
    }

    /// تغيير مستوى الدفاع (State Transition)
    pub fn set_defcon(&self, level: SystemDefcon) {
        let mut defcon = self.current_defcon.write().unwrap();
        if *defcon != level {
            warn!("FIREWALL: DEFCON Level changed from {:?} to {:?}", *defcon, level);
            *defcon = level;
        }
    }

    /// تقييم حركة المرور (Decision Core)
    /// Input: Traffic Context
    /// Output: Allowed (true) / Blocked (false)
    pub fn check_traffic(&self, ctx: &TrafficContext) -> bool {
        // 1. فحص القائمة السوداء أولاً (Fast Reject)
        let blacklist = self.blacklist.read().unwrap();
        if blacklist.contains(&ctx.source_ip) {
            warn!("FIREWALL_BLOCK: IP {:?} is blacklisted.", ctx.source_ip);
            return false;
        }

        // 2. الحصول على مستوى النظام الحالي
        let current_defcon = *self.current_defcon.read().unwrap();

        // 3. تقييم القواعد
        let rules = self.rules.read().unwrap();
        
        for rule in rules.iter() {
            // هل القاعدة نشطة في هذا المستوى الأمني؟
            // مثال: قاعدة "Exchange API" تتطلب Level 4. إذا كنا في Level 2، سنتجاهلها.
            if current_defcon < rule.min_defcon {
                continue;
            }

            // مطابقة القاعدة
            let ip_match = rule.allowed_ips.contains(&ctx.source_ip) || rule.allowed_ips.contains(&"0.0.0.0".parse().unwrap());
            let port_match = rule.allowed_ports.contains(&ctx.dest_port);

            if ip_match && port_match {
                // تم العثور على قاعدة تسمح بالمرور
                return true;
            }
        }

        // السياسة الافتراضية: المنع (Default Deny)
        // تسجيل جنائي للرفض
        info!(
            "FIREWALL_DENY: Blocked {:?} traffic from {:?}:{} [System State: {:?}]",
            ctx.direction, ctx.source_ip, ctx.dest_port, current_defcon
        );
        
        false
    }

    /// إضافة IP للقائمة السوداء (ديناميكياً من IDS)
    pub fn block_ip(&self, ip: IpAddr) {
        let mut blacklist = self.blacklist.write().unwrap();
        blacklist.insert(ip);
        warn!("FIREWALL: Added {:?} to dynamic blacklist.", ip);
    }
}

// =================================================================
// اختبارات الوحدة (Scenario Verification)
// =================================================================
#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[test]
    fn test_lockdown_blocks_external_traffic() {
        let fw = FirewallRulesEngine::new();
        
        // 1. الوضع الطبيعي (Normal)
        fw.set_defcon(SystemDefcon::Level5_Normal);
        
        // محاكاة اتصال من البورصة
        let exchange_ctx = TrafficContext {
            source_ip: IpAddr::from_str("1.1.1.1").unwrap(),
            dest_port: 443,
            direction: TrafficDirection::Outbound,
            protocol: "HTTPS".into(),
        };
        
        assert!(fw.check_traffic(&exchange_ctx), "Should allow exchange in Normal mode");

        // 2. تفعيل الإغلاق (Lockdown)
        fw.set_defcon(SystemDefcon::Level2_Lockdown);

        // الآن يجب منع البورصة
        assert!(!fw.check_traffic(&exchange_ctx), "Should BLOCK exchange in Lockdown mode");

        // ولكن يجب السماح بالـ Localhost
        let local_ctx = TrafficContext {
            source_ip: IpAddr::from_str("127.0.0.1").unwrap(),
            dest_port: 50051,
            direction: TrafficDirection::Inbound,
            protocol: "gRPC".into(),
        };
        assert!(fw.check_traffic(&local_ctx), "Should ALLOW localhost in Lockdown mode");
    }

    #[test]
    fn test_blacklist_enforcement() {
        let fw = FirewallRulesEngine::new();
        let attacker_ip = IpAddr::from_str("6.6.6.6").unwrap();
        
        // إضافة للقائمة السوداء
        fw.block_ip(attacker_ip);

        let ctx = TrafficContext {
            source_ip: attacker_ip,
            dest_port: 8080,
            direction: TrafficDirection::Inbound,
            protocol: "HTTP".into(),
        };

        assert!(!fw.check_traffic(&ctx), "Blacklisted IP should be blocked immediately");
    }
}