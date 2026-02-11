from collections import deque
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextBrowser
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QColor, QKeyEvent

# --- استيراد العقول المدبرة (للتنفيذ الفعلي) ---
from ui.core.logger_sink import logger_sink
from ui.core.theme_engine import theme_engine
from ui.core.state_store import state_store
from ui.managers.order_manager import order_manager
from ui.managers.logic_manager import logic_manager
from ui.managers.security_manager import security_manager
from ui.managers.service_manager import service_manager

class TerminalWindow(QWidget):
    """
    وحدة التحكم المركزية (The Command Console).
    
    المميزات:
    1. Direct Execution: تنفذ الأوامر مباشرة عبر المدراء (Managers).
    2. Command History: دعم الأسهم (Up/Down) لاستعادة الأوامر.
    3. Forensic Output: عرض النتائج بتنسيق ملون وواضح.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Internal State ---
        self.command_history = deque(maxlen=50)
        self.history_index = 0
        self.current_input_cache = ""

        # --- Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. شاشة العرض (Output)
        self.output_area = QTextBrowser()
        self.output_area.setReadOnly(True)
        self.output_area.setOpenExternalLinks(False)
        self.layout.addWidget(self.output_area)

        # 2. خط الأوامر (Input)
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Enter command (type /help)...")
        self.input_line.returnPressed.connect(self._on_enter_pressed)
        self.input_line.installEventFilter(self) # لاعتراض الأسهم
        self.layout.addWidget(self.input_line)

        # --- Styling ---
        self._apply_style()
        theme_engine.theme_changed.connect(self._apply_style)

        # رسالة ترحيب
        self._print_system("Alpha OS Sovereign Terminal v1.0")
        self._print_system("Type '/help' for available commands.")

    def _apply_style(self):
        """تطبيق ثيم الهاكر (Matrix/Terminal Style)"""
        bg = theme_engine.get_color("background")
        fg = theme_engine.get_color("text_primary")
        surface = theme_engine.get_color("surface")
        grid = theme_engine.get_color("grid_line")
        
        # خط ثابت العرض (Monospace) ضروري للتيرمينال
        font_family = "Consolas" 
        
        self.output_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {grid};
                border-bottom: none;
                font-family: "{font_family}";
                font-size: 10pt;
                padding: 5px;
            }}
        """)
        
        self.input_line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {surface};
                color: {theme_engine.get_color("primary")};
                border: 1px solid {grid};
                border-top: 1px solid {theme_engine.get_color("primary")};
                font-family: "{font_family}";
                font-size: 10pt;
                padding: 4px;
                font-weight: bold;
            }}
        """)

    # =========================================================================
    # Input Handling & History
    # =========================================================================
    def eventFilter(self, obj, event):
        """اعتراض ضغطات الكيبورد للتنقل في التاريخ"""
        if obj == self.input_line and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        return super().eventFilter(obj, event)

    def _navigate_history(self, direction):
        if not self.command_history:
            return

        # حفظ ما كتبه المستخدم حالياً إذا بدأ التنقل
        if self.history_index == len(self.command_history):
            self.current_input_cache = self.input_line.text()

        new_index = self.history_index + direction
        new_index = max(0, min(new_index, len(self.command_history)))

        if new_index != self.history_index:
            self.history_index = new_index
            if new_index == len(self.command_history):
                self.input_line.setText(self.current_input_cache)
            else:
                self.input_line.setText(self.command_history[new_index])

    def _on_enter_pressed(self):
        cmd = self.input_line.text().strip()
        if not cmd:
            return

        # 1. Forensic Logging: تسجيل الأمر قبل تنفيذه
        self._print_user(f"> {cmd}")
        logger_sink.log_system_event("Terminal", "INFO", f"USER_CMD: {cmd}")

        # 2. Add to History
        self.command_history.append(cmd)
        self.history_index = len(self.command_history)
        self.input_line.clear()

        # 3. Process Execution
        self._execute_command(cmd)

    # =========================================================================
    # Command Execution Engine (المحرك التنفيذي)
    # =========================================================================
    def _execute_command(self, cmd_str):
        """توجيه الأوامر إلى المدراء المناسبين"""
        parts = cmd_str.split()
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            # --- أوامر التداول (/buy, /sell, /close) ---
            if cmd in ["/buy", "/sell"]:
                self._handle_trade_cmd(cmd, args)

            # --- أوامر الاستراتيجية (/strategy) ---
            elif cmd == "/strategy":
                if not args:
                    self._print_error("Usage: /strategy [STRATEGY_ID]")
                    # عرض المتاح
                    avail = logic_manager.get_strategies_list()
                    self._print_info(f"Available: {', '.join(avail.keys())}")
                else:
                    logic_manager.set_strategy(args[0].upper())
                    self._print_success(f"Strategy switch requested: {args[0].upper()}")

            # --- أوامر الأمان (/panic, /unlock) ---
            elif cmd == "/panic":
                reason = " ".join(args) if args else "Terminal Command"
                security_manager.trigger_panic(reason)
                self._print_error("☢️ PANIC MODE TRIGGERED VIA TERMINAL ☢️")
            
            elif cmd == "/unlock":
                if not args:
                    self._print_error("Usage: /unlock [PIN]")
                else:
                    if security_manager.unlock_interface(args[0]):
                        self._print_success("Interface Unlocked.")
                    else:
                        self._print_error("Invalid PIN.")

            # --- أوامر النظام (/status, /restart) ---
            elif cmd == "/status":
                self._show_system_status()

            elif cmd == "/restart":
                self._print_warn("Restarting core services...")
                service_manager.start_full_system()

            # --- المساعدة (/help) ---
            elif cmd == "/help":
                self._show_help()

            else:
                self._print_error(f"Unknown command: {cmd}")

        except Exception as e:
            self._print_error(f"Execution Error: {str(e)}")
            logger_sink.log_system_event("Terminal", "ERROR", f"Cmd Failed: {e}")

    # =========================================================================
    # Command Handlers (معالجات فرعية)
    # =========================================================================
    def _handle_trade_cmd(self, cmd, args):
        """
        تفسير: /buy BTC 0.5 [LIMIT] [PRICE]
        """
        if len(args) < 2:
            self._print_error(f"Usage: {cmd} [SYMBOL] [QTY] (TYPE) (PRICE)")
            return

        side = "BUY" if cmd == "/buy" else "SELL"
        symbol = args[0].upper()
        
        try:
            qty = float(args[1])
        except ValueError:
            self._print_error("Invalid quantity.")
            return

        order_type = "MARKET"
        price = 0.0

        if len(args) > 2:
            order_type = args[2].upper()
            if order_type not in ["MARKET", "LIMIT"]:
                self._print_error("Type must be MARKET or LIMIT")
                return

        if len(args) > 3:
            try:
                price = float(args[3])
            except ValueError:
                self._print_error("Invalid price.")
                return

        # إرسال إلى OrderManager
        order_manager.submit_order(symbol, side, order_type, qty, price)
        self._print_info(f"Order Sent: {side} {qty} {symbol} ({order_type})")

    def _show_system_status(self):
        """عرض تقرير حالة سريع"""
        state = state_store.get_all_services()
        risk = state_store.get_value("risk_level")
        mode = state_store.get_value("system_mode")
        
        self._print_info(f"--- SYSTEM STATUS ---")
        self._print_info(f"Mode: {mode}")
        self._print_info(f"Risk Level: {risk}")
        for svc, status in state.items():
            color = "#00ff00" if status == "RUNNING" else "#ff0000"
            self._print_html(f"{svc}: <span style='color:{color}'>{status}</span>")

    def _show_help(self):
        help_text = """
        <b>Available Commands:</b><br>
        <span style='color:#00ffff'>/buy [SYM] [QTY]</span> - Place Buy Order<br>
        <span style='color:#ff5555'>/sell [SYM] [QTY]</span> - Place Sell Order<br>
        <span style='color:#bd93f9'>/strategy [ID]</span> - Switch Strategy<br>
        <span style='color:#ff0000'>/panic</span> - TRIGGER PANIC MODE<br>
        <span style='color:#f1fa8c'>/status</span> - Show System Health<br>
        <span style='color:#50fa7b'>/restart</span> - Restart Services<br>
        <span style='color:#8be9fd'>/unlock [PIN]</span> - Unlock Interface<br>
        """
        self._print_html(help_text)

    # =========================================================================
    # Output Helpers (أدوات العرض)
    # =========================================================================
    def _print_user(self, text):
        self._print_html(f"<span style='color:#00ffff; font-weight:bold;'>{text}</span>")

    def _print_system(self, text):
        self._print_html(f"<span style='color:#f8f8f2;'>{text}</span>")

    def _print_success(self, text):
        self._print_html(f"<span style='color:#50fa7b;'>✔ {text}</span>")

    def _print_error(self, text):
        self._print_html(f"<span style='color:#ff5555;'>✖ {text}</span>")
    
    def _print_warn(self, text):
        self._print_html(f"<span style='color:#ffb86c;'>⚠ {text}</span>")

    def _print_info(self, text):
        self._print_html(f"<span style='color:#8be9fd;'>ℹ {text}</span>")

    def _print_html(self, html):
        self.output_area.append(html)
        # Scroll to bottom
        sb = self.output_area.verticalScrollBar()
        sb.setValue(sb.maximum())