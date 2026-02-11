// SIMD Math Ops

/*
 * ALPHA SOVEREIGN - SIMD/AVX2 MATHEMATICAL ACCELERATOR
 * =================================================================
 * Component Name: engine/src/hardware/avx_accelerator.rs
 * Core Responsibility: تسريع العمليات الرياضية باستخدام تعليمات المعالج المتقدمة (Performance Pillar).
 * Design Pattern: Hardware Intrinsic Wrapper / Runtime Dispatch
 * Forensic Impact: لا يؤثر على المنطق، لكنه يقلل الـ Latency بشكل كبير. الفشل هنا يعني العودة للوضع البطيء (Fallback).
 * =================================================================
 */

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;
use tracing::{info, warn};

/// واجهة المسرع الرياضي
pub struct AvxAccelerator;

impl AvxAccelerator {
    /// حساب الضرب النقطي (Dot Product) لمتجهين بسرعة AVX.
    /// يستخدم بكثرة في حساب التشابه (Cosine Similarity) في الذاكرة المتجهة.
    pub fn dot_product(a: &[f64], b: &[f64]) -> f64 {
        if a.len() != b.len() {
            return 0.0; // أو يمكن إرجاع خطأ NaN
        }

        // الكشف الديناميكي عن دعم المعالج (Runtime Detection)
        if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
            unsafe { Self::dot_product_avx2(a, b) }
        } else {
            // fallback للأجهزة القديمة
            Self::dot_product_scalar(a, b)
        }
    }

    /// حساب التباين (Variance) والوسط الحسابي بسرعة AVX.
    /// يستخدم بكثرة في حسابات المخاطر (Bollinger Bands, Volatility).
    pub fn calculate_stats(data: &[f64]) -> (f64, f64) { // (Mean, Variance)
        if data.is_empty() {
            return (0.0, 0.0);
        }

        if is_x86_feature_detected!("avx2") {
            unsafe { Self::calculate_stats_avx2(data) }
        } else {
            Self::calculate_stats_scalar(data)
        }
    }

    // ----------------------------------------------------------------
    // التطبيق السكالار (البطيء / الآمن) - Reference Implementation
    // ----------------------------------------------------------------
    fn dot_product_scalar(a: &[f64], b: &[f64]) -> f64 {
        a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
    }

    fn calculate_stats_scalar(data: &[f64]) -> (f64, f64) {
        let sum: f64 = data.iter().sum();
        let mean = sum / data.len() as f64;
        let variance_sum: f64 = data.iter().map(|x| (x - mean).powi(2)).sum();
        (mean, variance_sum / data.len() as f64)
    }

    // ----------------------------------------------------------------
    // تطبيق AVX2 (السريع / Unsafe) - SIMD Implementation
    // ----------------------------------------------------------------
    
    #[target_feature(enable = "avx2", enable = "fma")]
    unsafe fn dot_product_avx2(a: &[f64], b: &[f64]) -> f64 {
        let len = a.len();
        let mut sum_vec = _mm256_setzero_pd(); // سجل التجميع [0.0, 0.0, 0.0, 0.0]
        
        let mut i = 0;
        // معالجة 4 عناصر في كل دورة (Unrolling Loop)
        while i + 4 <= len {
            // تحميل البيانات (Unaligned Load - أبطأ قليلاً من Aligned لكن أكثر أماناً مع Rust Slices)
            let va = _mm256_loadu_pd(a.as_ptr().add(i));
            let vb = _mm256_loadu_pd(b.as_ptr().add(i));
            
            // Fused Multiply-Add: res = (va * vb) + sum_vec
            // هذه تعليمة واحدة في المعالج!
            sum_vec = _mm256_fmadd_pd(va, vb, sum_vec);
            
            i += 4;
        }

        // تجميع النتائج الأربعة في رقم واحد
        // [x1, x2, x3, x4] -> x1+x2+x3+x4
        let mut temp_arr = [0.0; 4];
        _mm256_storeu_pd(temp_arr.as_mut_ptr(), sum_vec);
        let mut total_sum: f64 = temp_arr.iter().sum();

        // معالجة العناصر المتبقية (Tail Processing)
        // إذا كان الطول مثلاً 10، سيعالج 8 بالـ AVX و 2 بهذا اللوب
        while i < len {
            total_sum += a.get_unchecked(i) * b.get_unchecked(i);
            i += 1;
        }

        total_sum
    }

    #[target_feature(enable = "avx2")]
    unsafe fn calculate_stats_avx2(data: &[f64]) -> (f64, f64) {
        let len = data.len();
        
        // 1. حساب المجموع (للوسط الحسابي)
        let mut sum_vec = _mm256_setzero_pd();
        let mut i = 0;
        while i + 4 <= len {
            let v = _mm256_loadu_pd(data.as_ptr().add(i));
            sum_vec = _mm256_add_pd(sum_vec, v);
            i += 4;
        }
        
        let mut temp_arr = [0.0; 4];
        _mm256_storeu_pd(temp_arr.as_mut_ptr(), sum_vec);
        let mut total_sum: f64 = temp_arr.iter().sum();
        
        // الذيل
        let mut j = i;
        while j < len {
            total_sum += *data.get_unchecked(j);
            j += 1;
        }
        
        let mean = total_sum / len as f64;

        // 2. حساب التباين (Variance)
        // Variance = Sum((x - mean)^2) / N
        let mean_vec = _mm256_set1_pd(mean); // بث المتوسط لكل الخانات [mean, mean, mean, mean]
        let mut var_sum_vec = _mm256_setzero_pd();
        
        i = 0;
        while i + 4 <= len {
            let v = _mm256_loadu_pd(data.as_ptr().add(i));
            let diff = _mm256_sub_pd(v, mean_vec); // (x - mean)
            let sq_diff = _mm256_mul_pd(diff, diff); // ^2
            var_sum_vec = _mm256_add_pd(var_sum_vec, sq_diff); // Accumulate
            i += 4;
        }

        _mm256_storeu_pd(temp_arr.as_mut_ptr(), var_sum_vec);
        let mut total_var_sum: f64 = temp_arr.iter().sum();

        // الذيل
        while i < len {
            let diff = *data.get_unchecked(i) - mean;
            total_var_sum += diff * diff;
            i += 1;
        }

        (mean, total_var_sum / len as f64)
    }
}

// اختبار الأداء (Benchmark) عند التشغيل
pub fn benchmark_avx() {
    let size = 1_000_000;
    let v1: Vec<f64> = vec![1.0; size];
    let v2: Vec<f64> = vec![2.0; size];
    
    let start = std::time::Instant::now();
    let res = AvxAccelerator::dot_product(&v1, &v2);
    let duration = start.elapsed();
    
    if is_x86_feature_detected!("avx2") {
        info!("AVX2_BENCHMARK: 1M DotProduct in {:?} (Res: {}). Hardware Acceleration Active.", duration, res);
    } else {
        warn!("AVX2_BENCHMARK: AVX2 NOT ACTIVE. Using scalar fallback.");
    }
}