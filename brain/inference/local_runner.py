# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - LOCAL INFERENCE ENGINE (THE REACTOR)
======================================================
Path: alpha_project/brain/inference/local_runner.py
Role: تشغيل النماذج الضخمة (LLMs) محلياً على العتاد المتاح (CPU/GPU).
Dependency: llama-cpp-python

Forensic Features:
  1. **Thread-Safe Inference**: استخدام قفل (Mutex) لمنع تداخل الطلبات وإتلاف الذاكرة.
  2. **Memory Guard**: يمنع التحميل المتكرر للموديل لتجنب استهلاك الرام (OOM Killer).
  3. **Hardware Acceleration**: مهيأ لاستخدام GPU (cuda) تلقائياً إذا توفرت التعريفات.
  4. **Strict Prompting**: يفرض هيكلية DeepSeek Coder لضمان جودة الكود الناتج.

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import os
import logging
import threading
import time
from typing import Dict, Any, Optional

# محاولة استيراد المكتبة مع معالجة الخطأ جنائياً
try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False

# استيراد الهيكل الأساسي
from alpha_project.brain.base_agent import BaseAgent
from alpha_project.core.registry import register_component
from alpha_project.ui.core.config_provider import config as sys_config

@register_component(name="brain.local", category="brain", is_critical=False)
class LocalRunner(BaseAgent):
    """
    المحرك المحلي.
    المسؤول عن تشغيل ملفات GGUF الموجودة على القرص الصلب.
    """
    
    # [Forensic Evidence]: المسار الثابت للموديل كما وجد في التحقيقات 
    # D:\my_deepseek_model\deepseek-coder-v2-16b-lite-instruct-q5_K_M.gguf
    DEFAULT_MODEL_PATH = r"D:\my_deepseek_model\deepseek-coder-v2-16b-lite-instruct-q5_K_M.gguf"

    def __init__(self):
        super().__init__(name="brain.local", category="brain")
        self._llm: Optional[Llama] = None
        self._lock = threading.Lock()  # قفل لمنع التضارب بين الخيوط
        self._model_path = self.DEFAULT_MODEL_PATH

    # =========================================================================
    # 1. Initialization (الإقلاع الآمن)
    # =========================================================================

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        تحميل الموديل في الذاكرة. هذه العملية ثقيلة وقد تستغرق وقتاً.
        """
        super().initialize(config)
        
        # 1. التحقق من وجود المكتبة
        if not HAS_LLAMA:
            self._logger.warning("⚠️ 'llama-cpp-python' not installed. Local brain disabled.")
            return False

        # 2. التحقق من مسار الملف (Digital Forensics)
        # يمكن للمستخدم تغيير المسار عبر system_manifest.yaml مستقبلاً
        custom_path = sys_config.get("brain.models.local.path")
        if custom_path:
            self._model_path = custom_path

        if not os.path.exists(self._model_path):
            self._logger.error(f"❌ Model file MISSING at: {self._model_path}")
            self._logger.error("   -> Please ensure the .gguf file exists in the drive.")
            return False

        # 3. التحميل الفعلي (Heavy Lifting)
        try:
            if self._llm:
                self._logger.info("♻️ Model already loaded via cache.")
                return True

            self._logger.info(f"☢️  Initializing Local Reactor (Loading GGUF)...")
            self._logger.info(f"    -> Path: {self._model_path}")
            
            start_time = time.time()
            
            # إعدادات الأداء (Performance Tuning)
            # n_gpu_layers=-1 : حاول نقل كل الطبقات للكارت (إذا وجد)
            # n_ctx=4096      : ذاكرة سياقية كافية للكود
            # n_threads=6     : استخدام 6 أنوية للمعالج (توازن بين السرعة واستجابة الويندوز)
            
            self._llm = Llama(
                model_path=self._model_path,
                n_ctx=4096, 
                n_threads=6,  
                n_gpu_layers=-1, 
                verbose=False # إخفاء ضجيج المكتبة في السجلات
            )
            
            load_time = round(time.time() - start_time, 2)
            self._logger.info(f"✅ Local Brain ONLINE in {load_time}s.")
            return True

        except Exception as e:
            self._logger.critical(f"💥 REACTOR CORE FAILURE: {e}")
            return False

    def shutdown(self) -> None:
        """تحرير الذاكرة عند الإغلاق"""
        if self._llm:
            self._logger.info("🛑 Unloading Local Model to free RAM...")
            del self._llm
            self._llm = None
        super().shutdown()

    # =========================================================================
    # 2. Reasoning Execution (التنفيذ المحمي)
    # =========================================================================

    def _execute_reasoning(self, prompt: str, context: Dict) -> str:
        """
        تنفيذ الاستنتاج.
        """
        if not self._llm:
            raise RuntimeError("Local model is not loaded (Initialization failed).")

        # 1. الحصول على القفل (Thread Safety)
        # هذا يمنع برنامجين من الكتابة في الموديل في نفس الوقت
        with self._lock:
            self._logger.debug("🧠 Local Brain is thinking...")
            
            # 2. هندسة الأوامر (Prompt Engineering)
            # DeepSeek Coder يتدرب على هذا الشكل تحديداً 
            formatted_prompt = self._apply_template(prompt)
            
            try:
                # 3. التوليد (Generation)
                output = self._llm(
                    formatted_prompt,
                    max_tokens=2000,   # السماح بإجابات طويلة للكود
                    temperature=0.2,   # حرارة منخفضة للكود (نريد دقة لا إبداع)
                    stop=["### Instruction:", "### User:"], # علامات التوقف
                    echo=False
                )
                
                # استخراج النص
                result_text = output['choices'][0]['text'].strip()
                
                # تسجيل استهلاك التوكنز للأغراض الجنائية
                usage = output.get('usage', {})
                self._logger.info(f"⚡ Generated {usage.get('completion_tokens', 0)} tokens.")
                
                return result_text

            except Exception as e:
                self._logger.error(f"❌ Generation Error: {e}")
                raise e

    def _apply_template(self, prompt: str) -> str:
        """
        تطبيق قالب DeepSeek-Coder.
        """
        # القالب القياسي:
        # ### Instruction:
        # {prompt}
        #
        # ### Response:
        return f"### Instruction:\n{prompt}\n\n### Response:"

# =============================================================================
# Self-Diagnostic (للاختبار المنفصل)
# =============================================================================
if __name__ == "__main__":
    print("🔍 Testing LocalRunner independently...")
    runner = LocalRunner()
    
    # محاكاة إعدادات
    if runner.initialize({}):
        print("✅ Init Success. Testing Generation...")
        response = runner._execute_reasoning("Write a Python function to merge two lists.", {})
        print("\n--- OUTPUT ---\n")
        print(response)
        print("\n--------------")
    else:
        print("❌ Init Failed.")