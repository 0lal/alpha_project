// WebAssembly Isolation

/*
 * ALPHA SOVEREIGN - WASM HIGH-PERFORMANCE SANDBOX
 * =================================================================
 * Component Name: shield/sandbox/wasm_runtime.rs
 * Core Responsibility: تشغيل المنطق المولد ذاتياً بسرعة Native وعزل تام (Security Pillar).
 * Design Pattern: Virtual Machine / JIT Compiler
 * Forensic Impact: إذا انهار الكود، يوفر Stack Trace دقيقاً من داخل الـ VM يوضح سبب الانهيار (نفاد وقود، قسمة على صفر).
 * =================================================================
 */

use wasmtime::*;
use anyhow::Result;
use std::sync::{Arc, Mutex};
use tracing::{info, warn, error};
use crate::error::{AlphaError, AlphaResult};

/// سياق المتداول داخل الـ Wasm (يحتوي على الحالة والوقود)
struct TraderContext {
    wasi_ctx: wasi_common::WasiCtx,
    limits: StoreLimits,
    strategy_id: String,
}

pub struct WasmRuntime {
    engine: Engine,
    linker: Linker<TraderContext>,
}

pub struct ActiveStrategy {
    store: Store<TraderContext>,
    instance: Instance,
    // الدوال المصدرة من الـ Wasm (Exported Functions)
    on_tick_fn: TypedFunc<(f64, f64), i32>, // Input: (Price, Vol), Output: Decision
}

impl WasmRuntime {
    /// تهيئة بيئة التشغيل (JIT Compiler Setup)
    pub fn new() -> AlphaResult<Self> {
        let mut config = Config::new();
        config.consume_fuel(true); // تفعيل نظام الوقود لمنع الحلقات اللانهائية
        config.epoch_interruption(true); // السماح بالمقاطعة الخارجية

        let engine = Engine::new(&config)
            .map_err(|e| AlphaError::BootstrapError(format!("Wasm Engine Init Failed: {}", e)))?;

        let mut linker = Linker::new(&engine);
        
        // ربط مكتبة WASI (للسماح بالوظائف الأساسية المحدودة)
        wasi_common::sync::add_to_linker(&mut linker, |s: &mut TraderContext| &mut s.wasi_ctx)
            .map_err(|e| AlphaError::BootstrapError(format!("WASI Link Error: {}", e)))?;

        // تعريف دوال المضيف (Host Functions) - ما يسمح للـ Wasm بفعله
        // مثال: السماح للـ Wasm بالتسجيل في سجلات النظام
        linker.func_wrap("env", "host_log", |mut caller: Caller<'_, TraderContext>, ptr: i32, len: i32| {
            // منطق قراءة النص من ذاكرة Wasm وطباعته (معقد قليلاً ويتطلب Memory View)
            // للتبسيط: نسجل فقط أن الاستراتيجية نادت الدالة
            let id = &caller.data().strategy_id;
            info!("WASM_GUEST [{}]: Called host_log (ptr: {}, len: {})", id, ptr, len);
        }).unwrap();

        Ok(Self { engine, linker })
    }

    /// تحميل وتشغيل استراتيجية جديدة
    pub fn load_strategy(&self, strategy_id: &str, wasm_bytes: &[u8]) -> AlphaResult<ActiveStrategy> {
        info!("WASM_RUNTIME: JIT Compiling strategy '{}' ({} bytes)...", strategy_id, wasm_bytes.len());

        // 1. تجميع الكود (Compilation)
        let module = Module::new(&self.engine, wasm_bytes)
            .map_err(|e| AlphaError::RiskViolation { 
                rule: "Wasm Compilation".into(), limit: "Valid Wasm".into(), actual: e.to_string() 
            })?;

        // 2. إعداد المتجر والقيود (Store & Limits)
        let wasi = wasi_common::sync::WasiCtxBuilder::new().build();
        let limits = StoreLimitsBuilder::new()
            .memory_size(50 * 1024 * 1024) // حد أقصى 50 ميجا رام
            .instances(1)
            .build();

        let context = TraderContext {
            wasi_ctx: wasi,
            limits,
            strategy_id: strategy_id.to_string(),
        };

        let mut store = Store::new(&self.engine, context);
        
        // منح "وقود" للمعالجة (مثلاً 10 ملايين تعليمة)
        store.add_fuel(10_000_000).unwrap();
        store.limiter(|s| &mut s.limits);

        // 3. إنشاء النسخة (Instantiation)
        let instance = self.linker.instantiate(&mut store, &module)
            .map_err(|e| AlphaError::Internal(format!("Wasm Instantiation Error: {}", e)))?;

        // 4. استخراج الدوال (Function Binding)
        // نتوقع دالة اسمها "on_tick" تأخذ سعر وحجم وتعيد قرار
        let on_tick_fn = instance.get_typed_func::<(f64, f64), i32>(&mut store, "on_tick")
            .map_err(|_| AlphaError::Internal("Missing 'on_tick' export in Wasm module".into()))?;

        info!("WASM_RUNTIME: Strategy '{}' is LIVE in sandbox.", strategy_id);

        Ok(ActiveStrategy {
            store,
            instance,
            on_tick_fn,
        })
    }
}

impl ActiveStrategy {
    /// تنفيذ نبضة السوق (Hot Path)
    pub fn execute_tick(&mut self, price: f64, volume: f64) -> AlphaResult<i32> {
        // إعادة تعبئة الوقود لكل دورة (لكي لا يموت الكود مع الوقت)
        // لكننا نحدد الوقود *للدورة الواحدة* بـ 100,000 تعليمة فقط لضمان السرعة
        self.store.consume_fuel(0).unwrap(); // Reset logic (depends on Wasmtime version)
        self.store.add_fuel(100_000).unwrap();

        // استدعاء الدالة
        match self.on_tick_fn.call(&mut self.store, (price, volume)) {
            Ok(decision) => Ok(decision),
            Err(e) => {
                // التعامل مع الأخطاء (Traps)
                if let Some(trap) = e.downcast_ref::<Trap>() {
                    if trap == &Trap::OutOfFuel {
                        error!("WASM_TRAP: Strategy ran out of fuel (Infinite Loop detected)!");
                        return Err(AlphaError::RiskViolation {
                            rule: "CPU_QUOTA".into(), limit: "100k OPS".into(), actual: "EXCEEDED".into()
                        });
                    }
                }
                error!("WASM_CRASH: Runtime error: {}", e);
                Err(AlphaError::Internal(format!("Wasm Execution Failed: {}", e)))
            }
        }
    }
}