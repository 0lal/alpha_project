// =================================================================
// ALPHA SOVEREIGN ORGANISM - UNIFIED BUILD SYSTEM
// =================================================================
// File: engine/build.rs
// Status: PRODUCTION (Hybrid Compiler: Proto + FlatBuffers)
// Version: 35.0.2-UNIFIED
// Pillar: Integration & Automation (التكامل والأتمتة)
// Forensic Purpose: تحويل العقود (Proto/FlatBuffers) إلى كود Rust قابل للتنفيذ أوتوماتيكياً.
// Note: هذا الملف هو "المصنع" الذي يضمن أن الكود يعكس العقود بنسبة 100%.
// =================================================================

use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("cargo:warning=Starting Alpha Sovereign Build Process...");

    // =================================================================
    // CONFIGURATION: PATHS & ROOTS
    // =================================================================
    let proto_root = "../schemas/proto";
    let fbs_root = "../schemas/flatbuffers";
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());

    // =================================================================
    // PART 1: gRPC PROTOCOL COMPILATION (TONIC)
    // المسؤلية: تجميع عقود الخدمات (Control Plane)
    // =================================================================
    let protos = &[
        "../schemas/proto/brain_service.proto",
        "../schemas/proto/engine_control.proto",
        "../schemas/proto/shield_alert.proto",
        "../schemas/proto/swarm_consensus.proto",
        "../schemas/proto/telemetry_stream.proto",
        "../schemas/proto/auth_handshake.proto",
        "../schemas/proto/evolution_manifest.proto",
    ];

    // إعداد المترجم وتفعيل Serde للمراقبة وتصحيح الأخطاء
    tonic_build::configure()
        .build_server(true) // تفعيل كود السيرفر للمحرك
        .build_client(true) // تفعيل كود العميل (للتواصل مع Brain)
        .type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]")
        .compile(protos, &[proto_root])?;

    // إعلام Cargo بإعادة البناء إذا تغيرت ملفات الـ Proto
    for proto in protos {
        println!("cargo:rerun-if-changed={}", proto);
    }

    // =================================================================
    // PART 2: FLATBUFFERS COMPILATION (HIGH FREQUENCY)
    // المسؤلية: تجميع هياكل البيانات السريعة (Data Plane)
    // =================================================================
    let fbs_files = &[
        "market_tick",
        "order_book_depth",
        "trade_event",
        "order_update",
        "risk_report",
        "heartbeat",
    ];

    for file_name in fbs_files {
        let file_path = format!("{}/{}.fbs", fbs_root, file_name);
        
        // التحقق من وجود الملف قبل محاولة تجميعه
        if !std::path::Path::new(&file_path).exists() {
             // تحذير ولكن لا نوقف البناء إذا كان الملف غير موجود (قد يكون تحت التطوير)
             // في بيئة Production صارمة، يمكنك تغيير هذا إلى panic!
            println!("cargo:warning=FlatBuffer file not found: {}", file_path);
            continue;
        }

        // تنفيذ أمر flatc الخارجي
        // المتطلبات: يجب تثبيت flatc وإضافته للـ PATH
        let status = Command::new("flatc")
            .arg("--rust")
            .arg("--gen-onefile") // توليد ملف واحد لكل Schema
            .arg("-o")
            .arg(&out_dir)
            .arg(&file_path)
            .status();

        match status {
            Ok(s) if s.success() => {
                // نجاح التوليد
            }
            _ => {
                // فشل حرج: إذا فشل توليد كود البيانات، النظام لا يجب أن يعمل
                // هذا يطبق قانون "إما كمال النظام أو التوقف"
                panic!(
                    "CRITICAL ERROR: Failed to compile FlatBuffer: {}. Ensure 'flatc' is installed and in PATH.", 
                    file_name
                );
            }
        }

        // إعادة البناء إذا تغير ملف الـ fbs
        println!("cargo:rerun-if-changed={}", file_path);
    }

    println!("cargo:warning=Build Process Completed Successfully.");
    Ok(())
}