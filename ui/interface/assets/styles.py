# -*- coding: utf-8 -*-
class AlphaColors:
    BG = "#050505"; SURFACE = "#09090B"; ACCENT = "#00E5FF"; TEXT = "#FFFFFF"

class AlphaStyles:
    MASTER = f"QMainWindow {{ background: {AlphaColors.BG}; }} QWidget {{ color: {AlphaColors.TEXT}; font-family: Segoe UI; font-size: 14px; }}"
    BTN_SIDEBAR = f"QPushButton {{ background: transparent; border: none; text-align: right; padding: 15px; color: #888; }} QPushButton:hover {{ color: {AlphaColors.ACCENT}; }} QPushButton[active='true'] {{ color: {AlphaColors.ACCENT}; border-right: 3px solid {AlphaColors.ACCENT}; background: #111; }}"