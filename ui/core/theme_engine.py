import logging
from typing import Dict, Any, Optional
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont, QColor, QPalette
from PyQt6.QtCore import QObject, pyqtSignal, QFile, QTextStream

# استيراد مدير الإعدادات لتحديد المسارات بدقة
from ui.core.config_provider import config

# إعداد السجل
logger = logging.getLogger("Alpha.Core.ThemeEngine")

class ThemeEngine(QObject):
    """
    The Visual Cortex of Alpha.
    """
    
    # إشارة تنطلق عند تغيير الثيم بنجاح
    theme_changed = pyqtSignal(str, dict)

    # تعريف الألوان البرمجية
    THEME_PALETTES = {
        "sovereign_dark": {
            "background": "#0b0c15",
            "surface": "#161b22",
            "primary": "#00ff41",       # Hacker Green
            "secondary": "#00ccff",     # Cyan
            "danger": "#ff3333",
            "warning": "#ffb86c",
            "text_primary": "#e6edf3",
            "text_secondary": "#8b949e",
            "grid_line": "#30363d",
            "chart_up": "#00ff41",
            "chart_down": "#ff3333",
            "selection": "#1f2937"
        },
        "matrix_green": {
            "background": "#000000",
            "surface": "#0d1117",
            "primary": "#00ff00",
            "secondary": "#008f11",
            "danger": "#ff0000",
            "warning": "#ffff00",
            "text_primary": "#00ff00",
            "text_secondary": "#003b00",
            "grid_line": "#001a00",
            "chart_up": "#00ff00",
            "chart_down": "#005500",
            "selection": "#003300"
        }
    }

    _instance = None

    def __init__(self):
        super().__init__()
        if ThemeEngine._instance is not None:
            raise Exception("ThemeEngine is a Singleton!")
        
        self._current_theme = "sovereign_dark"  # الافتراضي
        self._current_palette = self.THEME_PALETTES["sovereign_dark"]
        
        # تحميل خطوط الرموز الخاصة عند البدء
        self._load_symbol_fonts()
        
        logger.info("🎨 ThemeEngine Initialized.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ThemeEngine()
        return cls._instance

    def apply_theme(self, theme_name: str):
        """
        تطبيق ثيم جديد مع الحقن الديناميكي للألوان.
        """
        logger.info(f"🔄 Switching theme to: {theme_name}")
        
        if theme_name not in self.THEME_PALETTES:
            logger.error(f"❌ Unknown palette: {theme_name}")
            return

        self._current_theme = theme_name
        self._current_palette = self.THEME_PALETTES[theme_name]

        base_path = config.project_root / "ui" / "assets" / "themes"
        qss_file_path = base_path / f"{theme_name}.qss"

        if not qss_file_path.exists():
            logger.error(f"❌ Theme file not found: {qss_file_path}")
        else:
            try:
                with open(qss_file_path, "r", encoding="utf-8") as f:
                    stylesheet_template = f.read()
                    
                    final_stylesheet = stylesheet_template
                    for key, value in self._current_palette.items():
                        placeholder = f"@{key}"
                        final_stylesheet = final_stylesheet.replace(placeholder, value)
                    
                    app = QApplication.instance()
                    if app:
                        app.setStyleSheet(final_stylesheet)
                        self._set_app_palette()
                    else:
                        logger.warning("⚠️ No QApplication instance found.")
            
            except Exception as e:
                logger.critical(f"☠️ Failed to process QSS: {e}")

        self.theme_changed.emit(theme_name, self._current_palette)
        logger.info(f"✅ Theme '{theme_name}' applied successfully.")

    def get_color(self, key: str) -> str:
        return self._current_palette.get(key, "#ffffff")

    def get_palette(self) -> Dict[str, str]:
        return self._current_palette

    def _set_app_palette(self):
        app = QApplication.instance()
        if not app: return

        palette = QPalette()
        colors = self._current_palette
        
        bg = QColor(colors["background"])
        fg = QColor(colors["text_primary"])
        surface = QColor(colors["surface"])
        
        palette.setColor(QPalette.ColorRole.Window, bg)
        palette.setColor(QPalette.ColorRole.WindowText, fg)
        palette.setColor(QPalette.ColorRole.Base, surface)
        palette.setColor(QPalette.ColorRole.AlternateBase, bg)
        palette.setColor(QPalette.ColorRole.ToolTipBase, surface)
        palette.setColor(QPalette.ColorRole.ToolTipText, fg)
        palette.setColor(QPalette.ColorRole.Text, fg)
        palette.setColor(QPalette.ColorRole.Button, surface)
        palette.setColor(QPalette.ColorRole.ButtonText, fg)
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["danger"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["selection"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, fg)

        app.setPalette(palette)

    def _load_symbol_fonts(self):
        font_dir = config.project_root / "ui" / "assets" / "fonts" / "symbols"
        
        if not font_dir.exists():
            return

        for font_file in font_dir.glob("*.ttf"):
            # تصحيح: الدالة هنا ثابتة (Static) وهذا صحيح
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
                logger.info(f"🔤 Symbol Font loaded: {family}")
            else:
                logger.warning(f"⚠️ Failed to load symbol font: {font_file.name}")

    def get_system_font(self) -> QFont:
        """
        دالة مساعدة للحصول على أفضل خط متاح في النظام.
        """
        priorities = ["Segoe UI", "Roboto", "Arial", "Tahoma"]
        
        # ---------------------------------------------------------
        # FIX FOR PyQt6: Use static method directly without instantiation
        # ---------------------------------------------------------
        available = QFontDatabase.families()
        
        for family in priorities:
            if family in available:
                return QFont(family)
        
        return QFont("Sans Serif")

# Global Access Point
theme_engine = ThemeEngine.get_instance()