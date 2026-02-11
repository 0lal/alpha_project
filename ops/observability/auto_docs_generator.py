# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - AUTOMATIC DOCUMENTATION GENERATOR
==========================================================
Component Name: ops/observability/auto_docs_generator.py
Core Responsibility: توليد التوثيق الفني تلقائياً عند تغير "جينوم" النظام (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (Scribe Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يضمن "استمرارية المعرفة".
في الأنظمة التي تتطور ذاتياً (Self-Evolving), يصبح الكود غامضاً مع مرور الوقت.
هذا المولد يقوم بـ:
1. تحليل الكود (Static Analysis).
2. استخراج الشروحات (Docstrings) والتوقيعات (Signatures).
3. بناء ملفات Markdown محدثة يمكن عرضها على GitHub أو MkDocs.
4. كشف المناطق "المظلمة" (Code without docs) والإبلاغ عنها.
"""

import ast
import os
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

# إعداد السجلات
logger = logging.getLogger("AlphaDocs")

@dataclass
class CodeEntity:
    """بنية بيانات تمثل كائناً برمجياً (دالة أو فئة)."""
    name: str
    type: str  # 'Class' or 'Function'
    docstring: str
    line_number: int
    args: str
    complexity: int = 0

@dataclass
class FileDocumentation:
    """تمثيل لملف كامل."""
    filepath: str
    module_doc: str
    entities: List[CodeEntity] = field(default_factory=list)

class AutoDocsGenerator:
    """
    المولد الآلي.
    يقرأ شجرة الملفات، يحلل ملفات Python، ويولد مرجع API كامل.
    """

    def __init__(self, root_dir: str = ".", output_dir: str = "docs/technical"):
        self.root_dir = Path(root_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # تجاهل المجلدات غير الهامة
        self.ignore_dirs = {'.git', '__pycache__', 'venv', 'env', '.idea', 'target'}

    def regenerate_all(self):
        """
        تشغيل دورة التوثيق الكاملة لكل المشروع.
        """
        logger.info("Starting Auto-Documentation Cycle...")
        start_time = time.time()
        
        doc_map = {}
        
        # 1. المسح (Scanning)
        for root, dirs, files in os.walk(self.root_dir):
            # تصفية المجلدات
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    relative_path = full_path.relative_to(self.root_dir)
                    
                    # 2. التحليل (Parsing)
                    doc_data = self._parse_file(full_path)
                    if doc_data:
                        doc_map[str(relative_path)] = doc_data

        # 3. التوليد (Generation)
        self._write_markdown_files(doc_map)
        
        duration = time.time() - start_time
        logger.info(f"Documentation Updated. Processed {len(doc_map)} files in {duration:.2f}s.")

    def _parse_file(self, filepath: Path) -> Optional[FileDocumentation]:
        """
        استخدام AST لقراءة هيكل الملف واستخراج المعلومات دون تنفيذه.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            module_doc = ast.get_docstring(tree) or "No description available."
            entities = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    entities.append(self._extract_function_info(node))
                elif isinstance(node, ast.ClassDef):
                    entities.append(self._extract_class_info(node))
            
            # ترتيب الكيانات حسب السطر
            entities.sort(key=lambda x: x.line_number)
            
            return FileDocumentation(
                filepath=str(filepath),
                module_doc=module_doc,
                entities=entities
            )
            
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            return None

    def _extract_function_info(self, node) -> CodeEntity:
        """استخراج بيانات الدالة."""
        args = [a.arg for a in node.args.args]
        return CodeEntity(
            name=node.name,
            type="Function",
            docstring=ast.get_docstring(node) or "*Documentation Missing*",
            line_number=node.lineno,
            args=f"({', '.join(args)})"
        )

    def _extract_class_info(self, node) -> CodeEntity:
        """استخراج بيانات الفئة."""
        return CodeEntity(
            name=node.name,
            type="Class",
            docstring=ast.get_docstring(node) or "*Documentation Missing*",
            line_number=node.lineno,
            args="(class)"
        )

    def _write_markdown_files(self, doc_map: Dict[str, FileDocumentation]):
        """
        كتابة ملفات Markdown منظمة.
        """
        index_content = ["# Alpha Sovereign - Technical API Reference\n"]
        index_content.append(f"> Auto-generated on {time.ctime()}\n")
        
        for rel_path, doc in doc_map.items():
            # إنشاء هيكل مجلدات مماثل داخل docs/technical
            # مثال: shield/core/brain.py -> docs/technical/shield/core/brain.md
            md_path = self.output_dir / Path(rel_path).with_suffix(".md")
            md_path.parent.mkdir(parents=True, exist_ok=True)
            
            # كتابة محتوى الملف
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Module: `{rel_path}`\n\n")
                f.write(f"**Description:**\n{doc.module_doc}\n\n")
                f.write("---\n\n")
                
                for entity in doc.entities:
                    icon = "📘" if entity.type == "Class" else "ƒ"
                    f.write(f"### {icon} {entity.type}: `{entity.name}`\n")
                    f.write(f"- **Signature:** `{entity.name}{entity.args}`\n")
                    f.write(f"- **Line:** {entity.line_number}\n")
                    f.write(f"\n{entity.docstring}\n\n")
                    f.write("---\n")
            
            # إضافة رابط في الفهرس
            link_path = Path(rel_path).with_suffix(".md")
            index_content.append(f"- [{rel_path}]({link_path})")

        # كتابة الفهرس الرئيسي
        with open(self.output_dir / "index.md", "w", encoding="utf-8") as f:
            f.write("\n".join(index_content))

# --- Unit Test ---
if __name__ == "__main__":
    # تشغيل المولد على مجلد العمليات (ops) كاختبار
    generator = AutoDocsGenerator(root_dir="ops", output_dir="docs/test_gen")
    
    print("--- Running Documentation Generator ---")
    generator.regenerate_all()
    
    print(f"[+] Docs generated in: {generator.output_dir.absolute()}")
    print("[+] Check 'index.md' to see the structure.")