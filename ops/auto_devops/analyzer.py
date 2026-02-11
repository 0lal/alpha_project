# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - SELF-OPTIMIZATION ANALYZER
===================================================
Component Name: ops/auto_patcher/analyzer.py
Core Responsibility: تحليل الكود الحي وسجلات الأداء لاكتشاف فرص التحسين (Pillar: Adaptability).
Creation Date: 2026-02-03
Version: 1.0.0 (Forensic Edition)
Author: Chief System Architect

Forensic Note:
يقوم هذا المديول بدور "الطبيب الشرعي الرقمي". فهو يحلل جثث العمليات البطيئة
ويفحص هيكل الكود بحثاً عن "السرطان البرمجي" (Code Smells) مثل الحلقات المتداخلة
أو الدوال ذات التعقيد الدائري (Cyclomatic Complexity) المرتفع.
"""

import ast
import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# إعداد نظام التسجيل الخاص بالمحلل
logger = logging.getLogger("AlphaAnalyzer")

@dataclass
class OptimizationOpportunity:
    """
    بنية بيانات تمثل فرصة تحسين مكتشفة.
    يستخدم هذا الهيكل لتوحيد التقارير الصادرة من المحلل.
    """
    file_path: str          # مسار الملف المصاب
    function_name: str      # اسم الدالة
    issue_type: str         # نوع المشكلة (e.g., HighComplexity, SlowExecution)
    severity: str           # الخطورة (CRITICAL, HIGH, MEDIUM, LOW)
    details: Dict[str, Any] # تفاصيل تقنية (زمن التنفيذ، عدد الحلقات، إلخ)
    timestamp: float        # وقت الاكتشاف

class ComplexityVisitor(ast.NodeVisitor):
    """
    زائر لشجرة الكود (AST) لحساب التعقيد البرمجي.
    يقوم بحساب عدد القرارات (If, For, While) داخل الدالة.
    """
    def __init__(self):
        self.complexity = 0
        self.loops = 0

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.loops += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.loops += 1
        self.generic_visit(node)
    
    # يمكن توسيع هذا ليشمل AsyncFor وغيرها

class CodeAnalyzer:
    """
    المحلل الرئيسي للنظام.
    يدمج بين التحليل الساكن (الكود) والتحليل الديناميكي (السجلات).
    """

    def __init__(self, root_path: str, threshold_ms: int = 100):
        """
        تهيئة المحلل.
        :param root_path: المسار الجذري للمشروع.
        :param threshold_ms: الحد الأقصى المسموح به للتنفيذ قبل اعتبار الدالة "بطيئة".
        """
        self.root_path = Path(root_path)
        self.threshold_ms = threshold_ms
        self.opportunities: List[OptimizationOpportunity] = []

    def scan_file_structure(self, file_path: str) -> List[OptimizationOpportunity]:
        """
        تحليل ثابت (Static Analysis) لملف بايثون.
        يستخدم AST لقراءة الكود دون تشغيله واكتشاف التعقيد الزائد.
        """
        detected_issues = []
        try:
            with open(file_path, "r", encoding="utf-8") as source:
                tree = ast.parse(source.read())
            
            # المرور على كل دالة في الملف
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    visitor = ComplexityVisitor()
                    visitor.visit(node)
                    
                    # قاعدة: إذا زاد التعقيد عن 10، فهذه دالة صعبة الصيانة
                    if visitor.complexity > 10:
                        issue = OptimizationOpportunity(
                            file_path=file_path,
                            function_name=node.name,
                            issue_type="HighCyclomaticComplexity",
                            severity="MEDIUM",
                            details={
                                "complexity_score": visitor.complexity,
                                "loop_count": visitor.loops
                            },
                            timestamp=time.time()
                        )
                        detected_issues.append(issue)
                        logger.warning(f"Complexity detected in {node.name}: Score {visitor.complexity}")

        except Exception as e:
            logger.error(f"Failed to analyze file structure {file_path}: {e}")
        
        return detected_issues

    def analyze_performance_logs(self, log_entries: List[Dict[str, Any]]) -> List[OptimizationOpportunity]:
        """
        تحليل ديناميكي (Dynamic Analysis) لسجلات الأداء.
        يبحث عن الدوال التي تتجاوز حد الزمن المسموح به (Threshold).
        """
        detected_issues = []
        
        for entry in log_entries:
            try:
                execution_time = entry.get("execution_time_ms", 0)
                component = entry.get("component", "unknown")
                
                # قاعدة: إذا كان الزمن أبطأ من الحد المسموح
                if execution_time > self.threshold_ms:
                    severity = "HIGH" if execution_time > (self.threshold_ms * 3) else "MEDIUM"
                    
                    issue = OptimizationOpportunity(
                        file_path=f"UNKNOWN (Component: {component})", # السجلات قد لا تحتوي على مسار الملف بدقة
                        function_name=entry.get("function", "unknown"),
                        issue_type="SlowExecutionBottleneck",
                        severity=severity,
                        details={
                            "actual_time_ms": execution_time,
                            "threshold_ms": self.threshold_ms,
                            "overhead_percentage": ((execution_time - self.threshold_ms) / self.threshold_ms) * 100
                        },
                        timestamp=time.time()
                    )
                    detected_issues.append(issue)
            except Exception as e:
                logger.error(f"Error parsing log entry: {e}")

        return detected_issues

    def run_full_diagnostic(self, target_files: List[str], live_logs: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        تشغيل دورة فحص كاملة (ثابتة وديناميكية).
        هذه الدالة هي التي يستدعيها النظام المركزي (Alpha Main Loop).
        """
        logger.info("Starting Full Diagnostic Analysis...")
        all_opportunities = []

        # 1. التحليل الهيكلي (Code Structure)
        for f_path in target_files:
            if f_path.endswith(".py") and os.path.exists(f_path):
                results = self.scan_file_structure(f_path)
                all_opportunities.extend(results)

        # 2. تحليل الأداء الحي (Live Performance)
        if live_logs:
            perf_results = self.analyze_performance_logs(live_logs)
            all_opportunities.extend(perf_results)

        # إعداد التقرير النهائي
        report = {
            "timestamp": time.time(),
            "total_issues_found": len(all_opportunities),
            "critical_issues": len([x for x in all_opportunities if x.severity == "CRITICAL"]),
            "opportunities": [x.__dict__ for x in all_opportunities]
        }
        
        logger.info(f"Analysis Complete. Found {report['total_issues_found']} optimization opportunities.")
        return report

# --- اختبار الوحدة البسيط (للتأكد من عمل المحلل عند تشغيله منفرداً) ---
if __name__ == "__main__":
    # إعداد بيئة اختبار وهمية
    import sys
    
    # 1. إنشاء محلل
    analyzer = CodeAnalyzer(root_path=".")
    
    # 2. فحص هذا الملف نفسه! (Self-Analysis)
    current_file = __file__
    print(f"--- Analyzing Self: {current_file} ---")
    
    issues = analyzer.scan_file_structure(current_file)
    
    if issues:
        print("DETECTED ISSUES:")
        for i in issues:
            print(f"[-] Function: {i.function_name} | Complexity: {i.details['complexity_score']}")
    else:
        print("[+] Code structure is clean and optimized.")