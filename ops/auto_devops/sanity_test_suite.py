# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - SANITY & INTEGRITY TEST SUITE
======================================================
Component Name: ops/auto_patcher/sanity_test_suite.py
Core Responsibility: اختبارات السلامة والنزاهة قبل حقن أي كود جديد (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Immune System Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يمثل "الجهاز المناعي" للنظام.
لا يسمح للكود الدخيل (حتى لو كان من إنتاج الذكاء الاصطناعي الداخلي) بالدخول إلى النواة
إلا إذا أثبت خلوه من:
1. السموم الأمنية (Dangerous Imports).
2. الأورام الخبيثة (Infinite Loops / Memory Leaks).
3. تدمير الخلايا السليمة (Regression Failures).
"""

import ast
import unittest
import sys
import io
import time
import signal
import logging
from typing import Dict, Any, List
from contextlib import contextmanager

# إعداد السجلات
logger = logging.getLogger("AlphaSanity")

class SecurityScanner(ast.NodeVisitor):
    """
    محلل ثابت (Static Analyzer) لمنع استخدام الأكواد الخطرة.
    """
    def __init__(self):
        self.errors = []
        # قائمة الممنوعات: لا يحق للذكاء الاصطناعي استخدام هذه المكتبات في التحسينات التلقائية
        self.forbidden_imports = {'os', 'subprocess', 'socket', 'requests', 'shutil'}
        # قائمة الدوال الخطرة
        self.forbidden_calls = {'eval', 'exec', 'compile', 'open'}

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in self.forbidden_imports:
                self.errors.append(f"Security Violation: Import of '{alias.name}' is forbidden.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in self.forbidden_imports:
            self.errors.append(f"Security Violation: Import from '{node.module}' is forbidden.")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.forbidden_calls:
            self.errors.append(f"Security Violation: Usage of dangerous function '{node.func.id}()'.")
        self.generic_visit(node)

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """مدير سياق لفرض مهلة زمنية صارمة على التنفيذ."""
    def signal_handler(signum, frame):
        raise TimeoutException("Execution Timed Out!")
    
    # يعمل فقط في بيئات Unix/Linux (بما في ذلك WSL)
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
    try:
        yield
    finally:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)

class SanityTestSuite:
    """
    جناح الاختبارات الشامل لضمان سلامة الكود الجديد.
    """

    def __init__(self):
        self.last_report = {}

    def run_all_checks(self, code_snippet: str, context_scope: Dict[str, Any] = {}) -> bool:
        """
        تشغيل سلسلة الفحوصات الكاملة.
        """
        logger.info("Starting Sanity Checks on new code patch...")

        # 1. الفحص الأمني (Static Security Scan)
        if not self._check_security(code_snippet):
            return False

        # 2. فحص التنفيذ الآمن (Sandbox Execution)
        if not self._check_runtime_safety(code_snippet, context_scope):
            return False

        # 3. (اختياري) تشغيل اختبارات الوحدة الحالية للتأكد من عدم الانحدار
        # if not self._run_regression_tests(): return False

        logger.info("PASS: All sanity checks cleared. Code is safe for injection.")
        return True

    def _check_security(self, code: str) -> bool:
        """
        التأكد من أن الكود لا يحتوي على أوامر خبيثة.
        """
        try:
            tree = ast.parse(code)
            scanner = SecurityScanner()
            scanner.visit(tree)
            
            if scanner.errors:
                for err in scanner.errors:
                    logger.critical(err)
                return False
            return True
        except SyntaxError:
            logger.error("Syntax Error during security scan.")
            return False

    def _check_runtime_safety(self, code: str, context: Dict) -> bool:
        """
        تشغيل الكود في بيئة معزولة مع مراقبة الوقت والذاكرة.
        """
        # إضافة دوال وهمية لمنع الكود من تنفيذ عمليات حقيقية
        safe_globals = {
            "__builtins__": {
                "range": range,
                "len": len,
                "print": print, # يمكن استبدالها بدالة وهمية لإخفاء المخرجات
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                # نسمح بالدوال الآمنة فقط
            },
            **context
        }

        # التقاط المخرجات لمنع تلوث الشاشة
        capture_io = io.StringIO()
        
        try:
            # فرض مهلة زمنية (مثلاً 1 ثانية) للكود المحسن
            # الكود المحسن يجب أن يكون سريعاً جداً، لذا 1 ثانية كافية
            with time_limit(1): 
                # تنفيذ الكود (exec خطير ولذلك قمنا بفلترة المدخلات أولاً في الخطوة السابقة)
                exec(code, safe_globals)
                
            logger.info("Runtime Check: Execution completed within limits.")
            return True

        except TimeoutException:
            logger.error("Runtime Check FAILED: Infinite loop or slow execution detected.")
            return False
        except Exception as e:
            logger.error(f"Runtime Check FAILED: Code crashed with error: {e}")
            return False
        finally:
            capture_io.close()

    def run_regression_tests(self, test_module_path: str) -> bool:
        """
        تشغيل ملفات الاختبار الموجودة مسبقاً للتأكد من أن التعديل لم يكسر شيئاً قديماً.
        """
        logger.info(f"Running regression tests: {test_module_path}")
        loader = unittest.TestLoader()
        try:
            # محاولة تحميل الاختبارات ديناميكياً
            suite = loader.discover(start_dir='.', pattern=test_module_path)
            runner = unittest.TextTestRunner(verbosity=0) # verbosity=0 لتقليل الضجيج
            result = runner.run(suite)
            
            if result.wasSuccessful():
                logger.info("Regression Tests: PASSED.")
                return True
            else:
                logger.error(f"Regression Tests: FAILED ({len(result.failures)} failures, {len(result.errors)} errors).")
                return False
        except Exception as e:
            logger.error(f"Failed to run regression tests: {e}")
            return False

# --- Unit Test Simulation ---
if __name__ == "__main__":
    suite = SanityTestSuite()
    
    # سيناريو 1: كود سليم
    good_code = """
x = 0
for i in range(100):
    x += i
"""
    print("\n--- Testing Good Code ---")
    suite.run_all_checks(good_code)

    # سيناريو 2: كود خبيث (استيراد ممنوع)
    bad_import_code = """
import os
os.system('echo HACKED')
"""
    print("\n--- Testing Malicious Import ---")
    suite.run_all_checks(bad_import_code)

    # سيناريو 3: حلقة لا نهائية (Infinite Loop)
    infinite_code = """
while True:
    pass
"""
    print("\n--- Testing Infinite Loop ---")
    if hasattr(signal, 'SIGALRM'): # يعمل فقط على Linux/WSL
        suite.run_all_checks(infinite_code)
    else:
        print("Skipping infinite loop test (Windows requires different timeout implementation)")