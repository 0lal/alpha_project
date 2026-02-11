# Model Compression

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DYNAMIC QUANTIZATION MANAGER
# =================================================================
# Component Name: brain/inference/quantization_mgr.py
# Core Responsibility: ضغط النماذج لتعمل بأقصى سرعة على العتاد المتاح دون فقدان الدقة المعرفية (Performance Pillar).
# Design Pattern: Factory / Configuration Builder
# Forensic Impact: يوثق "دقة النموذج" المستخدمة. إذا أخطأ النظام، هل كان السبب هو ضغط 4-bit الذي فقد التفاصيل؟
# =================================================================

import logging
import torch
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# محاولة استيراد التكوينات المتقدمة، مع التعامل مع عدم وجود المكتبات
try:
    from transformers import BitsAndBytesConfig
    HAS_BNB = True
except ImportError:
    HAS_BNB = False

@dataclass
class HardwareProfile:
    device_name: str
    total_vram_gb: float
    free_vram_gb: float
    compute_capability: Tuple[int, int]

class QuantizationManager:
    """
    مدير التكميم (Quantization Manager).
    يقوم بفحص العتاد (GPU VRAM) وتوليد إعدادات التحميل المثلى (4-bit vs 8-bit vs FP16).
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Inference.Quantize")
        self.hardware_profile = self._detect_hardware()

    def get_optimization_config(self, model_size_param_b: float) -> Dict[str, Any]:
        """
        تحديد إعدادات التكميم المناسبة لحجم النموذج والعتاد المتاح.
        
        Args:
            model_size_param_b: حجم النموذج بالمليار (e.g., 7.0 for Llama-3-8B).
            
        Returns:
            قاموس إعدادات (load_in_4bit, quantization_config, etc.)
        """
        if not torch.cuda.is_available():
            self.logger.warning("HARDWARE_LIMIT: No GPU detected. Forcing CPU mode (Slow!).")
            return {"device_map": "cpu"}

        # حساب الذاكرة المطلوبة تقريباً (بالجيجابايت)
        # FP16 يحتاج 2GB لكل مليار بارامتر
        # 8-bit يحتاج 1GB لكل مليار
        # 4-bit يحتاج 0.7GB لكل مليار (مع الـ Overhead)
        req_fp16 = model_size_param_b * 2.0
        req_int8 = model_size_param_b * 1.0
        req_nf4 = model_size_param_b * 0.75

        free_vram = self.hardware_profile.free_vram_gb
        
        # استراتيجية الاختيار (Selection Strategy)
        config = {}
        quant_mode = "FP16" # الافتراضي: دقة كاملة
        
        if free_vram > req_fp16 * 1.2: # نترك 20% هامش أمان للسياق (Context)
            # لدينا ذاكرة وفيرة، استخدم الدقة العالية
            config = {
                "torch_dtype": torch.float16,
                "device_map": "auto"
            }
            quant_mode = "FP16 (Full Precision)"

        elif free_vram > req_int8 * 1.2:
            # ضغط متوسط (8-bit)
            if HAS_BNB:
                config = {
                    "load_in_8bit": True,
                    "device_map": "auto"
                }
                quant_mode = "INT8"
            else:
                self.logger.error("LIB_MISSING: BitsAndBytes not installed but needed for INT8.")
                quant_mode = "FP16_FORCED_RISKY"

        elif free_vram > req_nf4 * 1.1:
            # ضغط عالي (4-bit NF4) - هذا هو الشائع للنماذج الكبيرة محلياً
            if HAS_BNB:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4", # Normal Float 4 (أفضل من Int4)
                    bnb_4bit_use_double_quant=True, # ضغط ثوابت الضغط (توفير إضافي)
                    bnb_4bit_compute_dtype=torch.float16
                )
                config = {
                    "quantization_config": bnb_config,
                    "device_map": "auto"
                }
                quant_mode = "NF4 (4-bit Double Quant)"
            else:
                quant_mode = "FAIL_OOM_RISK"
        else:
            # لا توجد ذاكرة كافية حتى للـ 4-bit
            self.logger.critical(f"OOM_PREVENT: Model requires {req_nf4:.1f}GB, but only {free_vram:.1f}GB available.")
            raise MemoryError("Insufficient VRAM for model loading even with 4-bit quantization.")

        self.logger.info(f"QUANTIZATION_DECISION: Selected {quant_mode} for {model_size_param_b}B model on {self.hardware_profile.device_name} ({free_vram:.1f}GB Free).")
        
        return config

    def _detect_hardware(self) -> HardwareProfile:
        """فحص العتاد وتحديث البروفايل."""
        if not torch.cuda.is_available():
            return HardwareProfile("CPU", 0, 0, (0, 0))
            
        try:
            # استخدام GPU 0 كمعيار
            props = torch.cuda.get_device_properties(0)
            total_mem = props.total_memory / (1024**3) # GB
            
            # الذاكرة الحرة والمستخدمة
            # ملاحظة: torch.cuda.mem_get_info() تعيد (free, total)
            free_mem, _ = torch.cuda.mem_get_info(0)
            free_mem = free_mem / (1024**3)
            
            return HardwareProfile(
                device_name=props.name,
                total_vram_gb=total_mem,
                free_vram_gb=free_mem,
                compute_capability=(props.major, props.minor)
            )
        except Exception as e:
            self.logger.error(f"HARDWARE_DETECT_FAIL: {e}")
            return HardwareProfile("UNKNOWN_GPU", 0, 0, (0, 0))

    def estimate_perplexity_loss(self, quant_mode: str) -> float:
        """
        تقدير نسبة فقدان الدقة (Heuristic).
        يفيد في تقارير الثقة (Confidence Scoring).
        """
        loss_map = {
            "FP16": 0.0,
            "INT8": 0.02, # فقدان 2% من جودة التوليد
            "NF4": 0.05,  # فقدان 5%
            "INT4": 0.08  # فقدان 8%
        }
        return loss_map.get(quant_mode.split()[0], 0.1)