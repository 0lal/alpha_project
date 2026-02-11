/*
 * ALPHA SOVEREIGN - TRANSPORT LAYER BENCHMARK
 * =================================================================
 * Component Name: engine/benches/transport_bench.rs
 * Core Responsibility: مقارنة بروتوكولات النقل والتسلسل (Performance Pillar).
 * Design Pattern: Comparative Benchmarking
 * Forensic Impact: يثبت بالأرقام لماذا اخترنا Shared Memory للتداول و JSON للمرونة.
 * =================================================================
 */

use criterion::{black_box, criterion_group, criterion_main, Criterion, BatchSize};
use rust_decimal::Decimal;
use rust_decimal::prelude::FromPrimitive;
use serde::{Serialize, Deserialize};
use std::sync::atomic::{AtomicUsize, Ordering};

// =================================================================
// 1. هياكل البيانات للمحاكاة (Dummy Structures)
// =================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MarketData {
    symbol: String,
    price: Decimal,
    volume: Decimal,
    timestamp: u64,
    flags: u8,
}

// محاكاة لهيكل الرأس في الذاكرة المشتركة
struct MockShmHeader {
    write_cursor: AtomicUsize,
    sequence: AtomicUsize,
}

fn setup_data() -> MarketData {
    MarketData {
        symbol: "BTCUSDT".to_string(),
        price: Decimal::from_f64(50123.45).unwrap(),
        volume: Decimal::from_f64(1.5).unwrap(),
        timestamp: 1678888888000,
        flags: 1,
    }
}

fn bench_transport_layer(c: &mut Criterion) {
    let mut group = c.benchmark_group("TransportLayer");

    // =================================================================
    // 1. معركة التسلسل: JSON (لـ Python) ضد Bincode (لـ Telemetry)
    // =================================================================
    
    group.bench_function("serialize_json_zmq", |b| {
        let data = setup_data();
        b.iter(|| {
            // هذا ما يحدث عند الإرسال عبر ZMQ
            let json = serde_json::to_string(black_box(&data)).unwrap();
            black_box(json);
        });
    });

    group.bench_function("serialize_bincode_telemetry", |b| {
        let data = setup_data();
        b.iter(|| {
            // هذا ما يحدث عند الإرسال للمسجل الأسود
            let bytes = bincode::serialize(black_box(&data)).unwrap();
            black_box(bytes);
        });
    });

    // =================================================================
    // 2. محاكاة الذاكرة المشتركة (Shared Memory Write)
    // نقيس سرعة Atomic Operation + Memcpy
    // =================================================================
    
    group.bench_function("shm_ring_buffer_write", |b| {
        // تجهيز منطقة ذاكرة وهمية
        let mut buffer = vec![0u8; 1024]; 
        let header = MockShmHeader {
            write_cursor: AtomicUsize::new(0),
            sequence: AtomicUsize::new(0),
        };
        let payload = vec![1u8; 256]; // بيانات بحجم 256 بايت

        b.iter(|| {
            // 1. حساب الموقع (Load Atomic)
            let cursor = header.write_cursor.load(Ordering::Acquire);
            let next = (cursor + 1) % 4; // فرضاً أن البفر يسع 4 عناصر
            
            // 2. النسخ (Memcpy) - جوهر الذاكرة المشتركة
            // unsafe { std::ptr::copy_nonoverlapping(...) }
            // نستخدم copy_from_slice للمحاكاة الآمنة هنا
            buffer[0..256].copy_from_slice(black_box(&payload));

            // 3. التحديث (Store Atomic)
            header.sequence.fetch_add(1, Ordering::Release);
            header.write_cursor.store(next, Ordering::Release);
        });
    });

    // =================================================================
    // 3. قنوات الاتصال (Channels): Crossbeam vs Tokio
    // =================================================================
    
    group.bench_function("channel_crossbeam_send", |b| {
        let (tx, rx) = crossbeam::channel::unbounded();
        let data = setup_data();
        
        b.iter_batched(
            || (tx.clone(), data.clone()),
            |(tx, val)| {
                tx.send(val).unwrap();
            },
            BatchSize::SmallInput,
        );
        // تنظيف القناة لمنع تسرب الذاكرة أثناء الاختبار
        while rx.try_recv().is_ok() {} 
    });

    group.finish();
}

criterion_group!(benches, bench_transport_layer);
criterion_main!(benches);