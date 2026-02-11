/*
 * ALPHA SOVEREIGN - SYSTEM ENTRY POINT (LIVE SERVER)
 * =================================================================
 * Component: engine/src/main.rs
 * Responsibility: تشغيل الخادم وربط العقل (Python) بالقلب (Rust Engine).
 * Status: LIVE OPERATION (gRPC Enabled)
 * =================================================================
 */

use std::net::SocketAddr;
use std::sync::Arc;
use tokio::signal;
use tracing::{info, error, warn};
use parking_lot::RwLock;
use tonic::transport::Server;

// 1. استيراد مكونات المكتبة الأساسية
use alpha_engine::utils::logger::init_logger;
use alpha_engine::risk::engine::{RiskEngine, RiskConfig};
use alpha_engine::matching::engine::MatchingEngine;
use alpha_engine::hardware;

// 2. استيراد طبقة الاتصال (API Layer)
// هذه المكونات أصبحت متاحة لأننا أضفنا pub mod api في lib.rs
use alpha_engine::api::AlphaServiceImpl;
use alpha_engine::interfaces::control::engine_control_server::EngineControlServer;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // أ. تهيئة الصندوق الأسود (Logging)
    let _guard = init_logger("./logs", "alpha_core.log", "info");
    
    info!("🚀 ALPHA ENGINE: Boot sequence initiated...");
    info!("   - Version: 1.0.0 (Sovereign Edition)");
    info!("   - Mode: High-Frequency Production");

    // ب. تحسين العتاد (Hardware Optimization)
    // محاولة حجز النواة رقم 0 بالكامل لهذا الخادم
    if let Err(e) = hardware::apply_affinity(0) {
        warn!("⚠️ Failed to apply CPU affinity: {}. Running in standard mode.", e);
    } else {
        info!("✅ CPU Affinity applied. Main thread pinned to Core 0.");
    }

    // ج. تهيئة المحركات (Core Engines)
    
    // 1. درع المخاطر
    info!("🛡️ Initializing Risk Engine...");
    // ملاحظة: نحتفظ به هنا للتوسعات المستقبلية، حتى لو لم يتم ربطه بالـ API حالياً
    let _risk_engine = Arc::new(RiskEngine::new(Some(RiskConfig::default())));

    // 2. محرك المطابقة (القلب النابض)
    info!("⚙️ Initializing Matching Engine...");
    let matching_engine = Arc::new(RwLock::new(MatchingEngine::new()));

    // د. إعداد الخدمة (Service Injection)
    // نقوم بحقن محرك المطابقة داخل طبقة الـ API
    let alpha_service = AlphaServiceImpl::new(matching_engine.clone());

    // هـ. إعداد الشبكة (Network Binding)
    let port = std::env::var("ENGINE_PORT").unwrap_or_else(|_| "50051".to_string());
    let addr: SocketAddr = format!("0.0.0.0:{}", port).parse()?;

    info!("🌐 ALPHA ENGINE: gRPC Server STARTING on {}", addr);
    info!("   -> Waiting for Brain (Python) connection...");

    // و. إطلاق الخادم الفعلي (Real Server Launch)
    Server::builder()
        .add_service(EngineControlServer::new(alpha_service))
        .serve_with_shutdown(addr, async {
            // انتظار إشارة الإغلاق (Ctrl+C)
            match signal::ctrl_c().await {
                Ok(()) => {
                    warn!("\n🛑 SHUTDOWN SIGNAL RECEIVED: Initiating emergency landing protocols...");
                },
                Err(err) => {
                    error!("Unable to listen for shutdown signal: {}", err);
                },
            }
        })
        .await?;

    info!("ALPHA ENGINE: Shutdown Complete. Goodbye.");
    Ok(())
}