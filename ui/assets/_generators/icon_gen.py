import os
from pathlib import Path

class IconGenerator:
    """
    مولد الأيقونات المتجهات (SVG Icon Generator).
    
    الوظيفة:
    يقوم برسم أيقونات النظام الأساسية (Dashboard, Settings, etc.) باستخدام كود SVG.
    يضمن أن البرنامج يمتلك دائماً واجهة بصرية حتى لو حُذفت ملفات الصور.
    
    التقنية:
    يستخدم معيار SVG 24x24 px (Grid System) لضمان التناسق.
    """
    
    def __init__(self, output_dir: str = None):
        # تحديد مسار الإخراج (icons/nav و icons/actions)
        if output_dir:
            self.base_dir = Path(output_dir)
        else:
            self.base_dir = Path(__file__).parent.parent / "img" / "icons"
            
        self.nav_dir = self.base_dir / "nav"
        self.action_dir = self.base_dir / "actions"
        
        # إنشاء المجلدات
        self.nav_dir.mkdir(parents=True, exist_ok=True)
        self.action_dir.mkdir(parents=True, exist_ok=True)

    def _write_svg(self, folder: Path, filename: str, content: str):
        """كتابة ملف SVG قياسي"""
        filepath = folder / f"{filename}.svg"
        
        # قالب SVG القياسي (Modern, Feather-style)
        svg_template = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
{content}
</svg>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(svg_template)
        
        print(f"🎨 Generated Icon: {filepath}")

    # =========================================================================
    # 1. Navigation Icons (أيقونات القائمة الجانبية)
    # =========================================================================
    
    def create_dashboard_icon(self):
        """أيقونة لوحة القيادة (Grid)"""
        # رسم 4 مربعات صغيرة
        path = """
        <rect x="3" y="3" width="7" height="7"></rect>
        <rect x="14" y="3" width="7" height="7"></rect>
        <rect x="14" y="14" width="7" height="7"></rect>
        <rect x="3" y="14" width="7" height="7"></rect>
        """
        self._write_svg(self.nav_dir, "dashboard", path)

    def create_brain_icon(self):
        """أيقونة الاستراتيجية (Microchip / Brain)"""
        # رسم دائرة متصلة بشبكة (تمثيل تجريدي للذكاء)
        path = """
        <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
        <rect x="9" y="9" width="6" height="6"></rect>
        <line x1="9" y1="1" x2="9" y2="4"></line>
        <line x1="15" y1="1" x2="15" y2="4"></line>
        <line x1="9" y1="20" x2="9" y2="23"></line>
        <line x1="15" y1="20" x2="15" y2="23"></line>
        <line x1="20" y1="9" x2="23" y2="9"></line>
        <line x1="20" y1="14" x2="23" y2="14"></line>
        <line x1="1" y1="9" x2="4" y2="9"></line>
        <line x1="1" y1="14" x2="4" y2="14"></line>
        """
        self._write_svg(self.nav_dir, "brain", path)

    def create_flash_icon(self):
        """أيقونة التنفيذ السريع (Lightning Bolt)"""
        path = """
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        """
        self._write_svg(self.nav_dir, "flash", path)

    def create_lab_icon(self):
        """أيقونة المختبر (Flask)"""
        path = """
        <path d="M10 2v7.31"></path>
        <path d="M14 2v7.31"></path>
        <path d="M8.5 2h7"></path>
        <path d="M14 9.31L22 22H2l8-12.69"></path>
        """
        self._write_svg(self.nav_dir, "flask", path)

    def create_search_icon(self):
        """أيقونة التحقيق الجنائي (Magnifying Glass)"""
        path = """
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        """
        self._write_svg(self.nav_dir, "search", path)

    def create_settings_icon(self):
        """أيقونة الإعدادات (Slider/Cogs)"""
        # شكل مسننات تجريدي (Hexagon)
        path = """
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        """
        self._write_svg(self.nav_dir, "cogs", path)

    # =========================================================================
    # 2. Action Icons (أزرار التحكم)
    # =========================================================================

    def create_play_icon(self):
        """زر التشغيل"""
        path = '<polygon points="5 3 19 12 5 21 5 3"></polygon>'
        self._write_svg(self.action_dir, "play", path)

    def create_stop_icon(self):
        """زر الإيقاف"""
        path = '<rect x="4" y="4" width="16" height="16"></rect>'
        self._write_svg(self.action_dir, "stop", path)
        
    def create_trash_icon(self):
        """زر الحذف"""
        path = """
        <polyline points="3 6 5 6 21 6"></polyline>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        """
        self._write_svg(self.action_dir, "trash", path)

    # =========================================================================
    # 3. Master Trigger (المشغل الرئيسي)
    # =========================================================================
    def generate_defaults_if_missing(self):
        """
        توليد الأيقونات الناقصة فقط.
        """
        # قائمة بكل الأيقونات المطلوبة
        generators = {
            "nav": {
                "dashboard": self.create_dashboard_icon,
                "brain": self.create_brain_icon,
                "flash": self.create_flash_icon,
                "flask": self.create_lab_icon,
                "search": self.create_search_icon,
                "cogs": self.create_settings_icon
            },
            "actions": {
                "play": self.create_play_icon,
                "stop": self.create_stop_icon,
                "trash": self.create_trash_icon
            }
        }
        
        # الفحص والتوليد
        for category, icons in generators.items():
            folder = self.nav_dir if category == "nav" else self.action_dir
            for name, func in icons.items():
                if not (folder / f"{name}.svg").exists():
                    func()

# للاختبار المستقل
if __name__ == "__main__":
    gen = IconGenerator()
    print("🎨 Initializing Icon Factory...")
    gen.generate_defaults_if_missing()
    print("✅ All procedural icons generated.")