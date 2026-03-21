import sys
import subprocess
import os
import socket
import re
import shlex
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QListWidget, QListWidgetItem, QFrame, QMessageBox,
                             QTextEdit, QComboBox, QLineEdit, QDialog, QGridLayout,
                             QGroupBox, QRadioButton, QButtonGroup, QCheckBox,
                             QFileDialog, QProgressBar, QAbstractItemView, QHeaderView,
                             QTableWidget, QTableWidgetItem, QStyleFactory)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QIcon, QPixmap, QKeySequence, QKeyEvent, QPalette, QColor
from PyQt6.QtGui import QDesktopServices


# -------------------- Thread for running commands without blocking UI --------------------
class CommandThread(QThread):
    finished = pyqtSignal(int, str, str)  # returncode, stdout, stderr

    def __init__(self, cmd, use_pkexec=False):
        super().__init__()
        self.cmd = cmd
        self.use_pkexec = use_pkexec

    def run(self):
        try:
            if self.use_pkexec:
                actual_cmd = self.cmd.replace("sudo ", "")
                full_cmd = ["pkexec", "bash", "-c", actual_cmd]
            else:
                full_cmd = ["bash", "-c", self.cmd]
            proc = subprocess.run(full_cmd, capture_output=True, text=True)
            self.finished.emit(proc.returncode, proc.stdout, proc.stderr)
        except Exception as e:
            self.finished.emit(-1, "", str(e))


# -------------------- Thread for loading network info --------------------
class NetworkInfoLoader(QThread):
    info_loaded = pyqtSignal(str, str)  # ip_output, arp_output

    def run(self):
        try:
            ip_output = subprocess.run(['ip', 'addr'], capture_output=True, text=True).stdout
            arp_output = subprocess.run(['ip', 'neigh'], capture_output=True, text=True).stdout
            self.info_loaded.emit(ip_output, arp_output)
        except Exception as e:
            self.info_loaded.emit(f"Error: {e}", "")


# -------------------- Thread for loading installed packages --------------------
class AppListLoader(QThread):
    apps_loaded = pyqtSignal(list)  # list of (name, version, description)

    def run(self):
        try:
            result = subprocess.run(
                ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${binary:Summary}\t${Status}\n'],
                capture_output=True, text=True
            )
            apps = []
            for line in result.stdout.splitlines():
                parts = line.split('\t')
                if len(parts) >= 4 and 'install ok installed' in parts[3]:
                    name = parts[0].strip()
                    version = parts[1].strip()
                    desc = parts[2].strip()
                    if name:
                        apps.append((name, version, desc))
            apps.sort(key=lambda x: x[0].lower())
            self.apps_loaded.emit(apps)
        except Exception as e:
            self.apps_loaded.emit([])


# -------------------- Thread for uninstalling a package --------------------
class UninstallThread(QThread):
    finished = pyqtSignal(int, str, str)

    def __init__(self, package_name):
        super().__init__()
        self.package_name = package_name

    def run(self):
        try:
            cmd = ['pkexec', 'apt-get', 'remove', '-y', self.package_name]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.finished.emit(proc.returncode, proc.stdout, proc.stderr)
        except Exception as e:
            self.finished.emit(-1, '', str(e))


# -------------------- Key Grabber Dialog --------------------
class KeyGrabberDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ตั้งค่าคีย์ลัด / Set Keybinding")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.key_sequence = None
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.key = 0

        layout = QVBoxLayout(self)

        self.instruction = QLabel("กรุณากดคีย์ผสมที่ต้องการใช้สลับภาษา\n(เช่น Ctrl+Space, Alt+Shift, Grave)")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instruction)

        self.key_label = QLabel("ยังไม่ได้กดคีย์")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #58A6FF; padding: 10px; border: 1px solid #21262D; border-radius: 6px; background: #161B22;")
        layout.addWidget(self.key_label)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("ตกลง")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("ยกเลิก")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QKeyEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_Super_L, Qt.Key.Key_Super_R):
            return

        self.modifiers = modifiers
        self.key = key
        self.key_sequence = QKeySequence(int(modifiers) | key).toString(QKeySequence.SequenceFormat.NativeText)
        self.key_label.setText(self.key_sequence)
        self.ok_btn.setEnabled(True)

    def get_key_combination(self):
        return self.modifiers, self.key

    def get_gsettings_string(self):
        if not self.key_sequence:
            return None

        modifier_map = {
            Qt.KeyboardModifier.ControlModifier: "Control",
            Qt.KeyboardModifier.AltModifier: "Alt",
            Qt.KeyboardModifier.ShiftModifier: "Shift",
            Qt.KeyboardModifier.MetaModifier: "Super",
        }
        key_map = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_QuoteLeft: "grave",
            Qt.Key.Key_AsciiTilde: "grave",
            Qt.Key.Key_Dead_Grave: "grave",
            Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Escape: "Escape",
            Qt.Key.Key_Return: "Return",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_Backspace: "BackSpace",
            Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Home: "Home",
            Qt.Key.Key_End: "End",
            Qt.Key.Key_Left: "Left",
            Qt.Key.Key_Up: "Up",
            Qt.Key.Key_Right: "Right",
            Qt.Key.Key_Down: "Down",
            Qt.Key.Key_PageUp: "Page_Up",
            Qt.Key.Key_PageDown: "Page_Down",
            Qt.Key.Key_F1: "F1",
            Qt.Key.Key_F2: "F2",
            Qt.Key.Key_F3: "F3",
            Qt.Key.Key_F4: "F4",
            Qt.Key.Key_F5: "F5",
            Qt.Key.Key_F6: "F6",
            Qt.Key.Key_F7: "F7",
            Qt.Key.Key_F8: "F8",
            Qt.Key.Key_F9: "F9",
            Qt.Key.Key_F10: "F10",
            Qt.Key.Key_F11: "F11",
            Qt.Key.Key_F12: "F12",
        }
        if 0x41 <= self.key <= 0x5A:
            key_name = chr(self.key).lower()
        elif 0x30 <= self.key <= 0x39:
            key_name = chr(self.key)
        else:
            key_name = key_map.get(self.key, None)
            if not key_name:
                return self.key_sequence.lower()

        mods = []
        for mod, name in modifier_map.items():
            if self.modifiers & mod:
                mods.append(f"<{name}>")
        if mods:
            return ''.join(mods) + key_name
        else:
            return key_name


# -------------------- Main Window --------------------
class GengSettingsTools(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = 'en-US'
        self.strings = self.load_strings(self.current_lang)
        self.setWindowTitle(self.tr("window_title"))

        self.resize(1000, 750)
        self.setMinimumSize(800, 600)

        self.icon_path = "/usr/share/gst-assets/icon.png"
        self.qr_path = "/usr/share/gst-assets/qrcode.png"

        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.apply_global_style()

        self.active_threads = []

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #0D1117; border-bottom: 1px solid #21262D; padding: 0px;")
        header_widget.setFixedHeight(64)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        if os.path.exists(self.icon_path):
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QPixmap(self.icon_path).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            header_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Geng Tools")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #E6EDF3; background: transparent; border: none; letter-spacing: 0.3px;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        sidebar_layout.addWidget(header_widget)

        # Language selector
        lang_widget = QWidget()
        lang_widget.setStyleSheet("background: transparent;")
        lang_layout = QHBoxLayout(lang_widget)
        lang_layout.setContentsMargins(12, 8, 12, 4)
        lang_label = QLabel("🌐")
        lang_label.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        self.lang_combo = QComboBox()
        # Language list in requested order (code, display name)
        languages = [
            ("en-US", "🇺🇸 English (US)"),
            ("th", "🇹🇭 ไทย"),
            ("de", "🇩🇪 Deutsch"),
            ("fr", "🇫🇷 Français"),
            ("ga", "🇮🇪 Gaeilge (Ireland)"),
            ("nl", "🇳🇱 Nederlands"),
            ("sv", "🇸🇪 Svenska"),
            ("da", "🇩🇰 Dansk"),
            ("nb", "🇳🇴 Norsk"),
            ("cs", "🇨🇿 Čeština"),
            ("pl", "🇵🇱 Polski"),
            ("de-AT", "🇦🇹 Österreichisches Deutsch"),
            ("en-AU", "🇦🇺 English (Australia)"),
            ("en-GB", "🇬🇧 English (UK)"),
            ("es", "🇪🇸 Español"),
            ("de-CH", "🇨🇭 Schweizerdeutsch"),
            ("en-CA", "🇨🇦 English (Canada)"),
            ("fr-CA", "🇨🇦 Français (Canada)"),
            ("it", "🇮🇹 Italiano"),
            ("hi", "🇮🇳 हिन्दी"),
            ("id", "🇮🇩 Bahasa Indonesia"),
            ("pt", "🇵🇹 Português"),
            ("pt-BR", "🇧🇷 Português (Brasil)"),
            ("ja", "🇯🇵 日本語"),
            ("zh", "🇨🇳 中文 (普通话)"),
            ("ru", "🇷🇺 Русский"),
            ("tr", "🇹🇷 Türkçe"),
            ("uk", "🇺🇦 Українська"),
            ("ar", "🇸🇦 العربية"),
            ("ko", "🇰🇷 한국어"),
            ("vi", "🇻🇳 Tiếng Việt"),
            ("lo", "🇱🇦 ລາວ"),
            ("ms", "🇲🇾 Bahasa Melayu"),
            ("hmn", "🇱🇦 Hmoob (Hmong)"),
            ("ca", "🇦🇩 Català (Andorra)"),
            ("ar-SD", "🇸🇩 العربية (السودان)"),
            ("es-CU", "🇨🇺 Español (Cuba)"),
        ]
        # Remove duplicates by using a dict to preserve order
        seen = set()
        unique_languages = []
        for code, name in languages:
            if code not in seen:
                seen.add(code)
                unique_languages.append((code, name))
        for code, name in unique_languages:
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(0)  # default to English (US)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        sidebar_layout.addWidget(lang_widget)

        self.nav_label = QLabel(self.tr('navigation'))
        self.nav_label.setStyleSheet("color: #484F58; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; padding: 6px 20px 2px 20px; background: transparent;")
        sidebar_layout.addWidget(self.nav_label)

        self.menu_list = QListWidget()
        self.update_menu_titles()
        self.menu_list.currentRowChanged.connect(self.display_page)
        sidebar_layout.addWidget(self.menu_list)

        version_lbl = QLabel("v2.0.6")
        version_lbl.setStyleSheet("color: #30363D; font-size: 11px; padding: 10px 16px; background: transparent;")
        sidebar_layout.addWidget(version_lbl)

        layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("ContentArea")
        layout.addWidget(self.pages)

        self.create_pages()
        self.menu_list.setCurrentRow(0)

    def apply_global_style(self):
        # (your existing style sheet - unchanged)
        self.setStyleSheet("""
            /* ── Global ── */
            QMainWindow {
                background-color: #0D1117;
            }
            QWidget {
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
                font-size: 13px;
            }

            /* ── Sidebar ── */
            QWidget#Sidebar {
                background-color: #161B22;
                border-right: 1px solid #21262D;
            }

            /* ── Menu List ── */
            QListWidget {
                background-color: #161B22;
                border: none;
                color: #8B949E;
                font-size: 13px;
                outline: none;
                padding: 4px 0px;
            }
            QListWidget::item {
                padding: 11px 16px;
                border-radius: 6px;
                margin: 2px 8px;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #1C2128;
                color: #C9D1D9;
            }
            QListWidget::item:selected {
                background-color: #1F6FEB22;
                color: #58A6FF;
                border-left: 3px solid #58A6FF;
                padding-left: 13px;
            }

            /* ── Content Area ── */
            QWidget#ContentArea {
                background-color: #0D1117;
            }

            /* ── Labels ── */
            QLabel {
                color: #C9D1D9;
                background: transparent;
            }

            /* ── Buttons ── */
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                padding: 7px 16px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
                color: #58A6FF;
            }
            QPushButton:pressed {
                background-color: #1F6FEB;
                border-color: #1F6FEB;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #161B22;
                color: #484F58;
                border-color: #21262D;
            }

            /* ── Card Frame ── */
            QFrame#Card {
                background-color: #161B22;
                border: 1px solid #21262D;
                border-radius: 10px;
            }
            QFrame#Card:hover {
                border-color: #30363D;
            }

            /* ── GroupBox ── */
            QGroupBox {
                color: #8B949E;
                border: 1px solid #21262D;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 6px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #58A6FF;
            }

            /* ── Text Edit ── */
            QTextEdit {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #21262D;
                border-radius: 6px;
                padding: 6px;
                selection-background-color: #1F6FEB;
            }

            /* ── ComboBox ── */
            QComboBox {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QComboBox:hover {
                border-color: #58A6FF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #8B949E;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 6px;
                selection-background-color: #1F6FEB;
                outline: none;
            }

            /* ── Line Edit ── */
            QLineEdit {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #21262D;
                padding: 7px 10px;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #58A6FF;
                background-color: #1C2128;
            }

            /* ── Table ── */
            QTableWidget {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #21262D;
                border-radius: 6px;
                gridline-color: #21262D;
            }
            QTableWidget::item {
                padding: 6px 8px;
            }
            QTableWidget::item:selected {
                background-color: #1F6FEB33;
                color: #58A6FF;
            }
            QHeaderView::section {
                background-color: #161B22;
                color: #8B949E;
                border: none;
                border-bottom: 1px solid #21262D;
                padding: 6px 8px;
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 0.5px;
            }

            /* ── Progress Bar ── */
            QProgressBar {
                border: 1px solid #21262D;
                border-radius: 4px;
                text-align: center;
                color: #C9D1D9;
                background-color: #161B22;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #1F6FEB;
                border-radius: 4px;
            }

            /* ── Scrollbar ── */
            QScrollBar:vertical {
                background: #0D1117;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363D;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #484F58;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }

            /* ── Dialogs ── */
            QDialog {
                background-color: #161B22;
            }
            QMessageBox {
                background-color: #161B22;
            }
            QMessageBox QLabel {
                color: #C9D1D9;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #1F6FEB;
                color: #FFFFFF;
                border: none;
                min-width: 80px;
                padding: 7px 16px;
            }
            QMessageBox QPushButton:hover {
                background-color: #388BFD;
                border: none;
                color: white;
            }

            /* ── CheckBox & RadioButton ── */
            QCheckBox, QRadioButton {
                color: #C9D1D9;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #30363D;
                border-radius: 3px;
                background-color: #21262D;
            }
            QCheckBox::indicator:checked {
                background-color: #1F6FEB;
                border-color: #1F6FEB;
            }
            QRadioButton::indicator {
                border-radius: 8px;
            }
            QRadioButton::indicator:checked {
                background-color: #1F6FEB;
                border-color: #1F6FEB;
            }
        """)

    def load_strings(self, lang):
        # Base English (US) strings – also used as fallback for unsupported languages
        strings_en = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Home',
            'keyboard': 'Keyboard & Language',
            'system_tools': 'System Tools',
            'network': 'Network',
            'entertainment': 'Entertainment',
            'theme': 'Theme',
            'backup': 'Backup',
            'about': 'About',
            'navigation': 'NAVIGATION',
            # Home
            'welcome': 'Welcome to Geng Settings Tools',
            'current_user': 'Current user',
            'hostname': 'Hostname',
            'home_desc': 'Your all‑in‑one configuration toolbox for Linux Mint Cinnamon 22.3.\n'
                         'Easily tweak keyboard shortcuts, manage apps, clean your system, download media, and more.\n'
                         'Select a category from the sidebar to get started — everything is just a click away!',
            # Keyboard
            'keyboard_title': 'Keyboard & Language Settings',
            'grave_title': 'Switch language with Grave Accent (~)',
            'grave_desc': 'Use Grave Accent key to switch input methods',
            'alt_shift_title': 'Switch language with Alt+Shift',
            'alt_shift_desc': 'Use Alt + Shift keys to switch input methods',
            'custom_key_title': 'Custom keybinding',
            'custom_key_desc': 'Press the button below to capture desired key combination',
            'capture_key': 'Capture Key',
            'apply_now': 'Apply Now',
            # System Tools
            'system_title': 'System Tools',
            'clean_system': 'Clean System Junk',
            'clean_system_desc': 'Remove unused packages and cache',
            'clear_ram': 'Clear RAM/Cache',
            'clear_ram_desc': 'Clear memory cache (sync && drop_caches)',
            'driver_manager': 'Driver Manager',
            'driver_manager_desc': 'Open Driver Manager',
            'flatpak': 'Flatpak Manager',
            'flatpak_desc': 'Update Flatpak and install apps',
            'apt_repair': 'APT Repair',
            'apt_repair_desc': 'Fix broken packages',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'Open system monitor',
            # Network
            'network_title': 'Network Management',
            'network_status': 'Network Status',
            'refresh': 'Refresh',
            'restart_network': 'Restart Network',
            'flush_dns': 'Flush DNS',
            'renew_dhcp': 'Renew DHCP',
            'interfaces': 'Network Interfaces',
            'connections': 'Connections',
            # Entertainment
            'entertainment_title': 'Entertainment',
            'install_steam': 'Install Steam',
            'install_steam_desc': 'Install Steam for gaming',
            'install_wine': 'Install Wine',
            'install_wine_desc': 'Install Wine to run Windows apps',
            'download_media': 'Download Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Download',
            'install_ytdlp': 'Install yt-dlp',
            # Theme
            'theme_title': 'Theme Customization',
            'dark_mode': 'Dark Mode',
            'light_mode': 'Light Mode',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'Apply Theme',
            # Backup
            'backup_title': 'Backup',
            'select_drive': 'Select Destination Drive',
            'backup_now': 'Backup Now',
            'backup_progress': 'Backing up...',
            'backup_complete': 'Backup Complete',
            'backup_failed': 'Backup Failed',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclude',
            # About
            'about_title': 'About',
            'developer': 'Developer',
            'email': 'Email',
            'thanks': 'This tool helps Thai people use Linux easily\nThank you for being part of the Open Source family',
            'donate_sentence': 'No beer, no code. Help a thirsty dev out!',
            'donate_button': 'Sponsor my booze',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Account name',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Account number',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            # Messages
            'success': 'Success',
            'error': 'Error',
            'settings_applied': 'Settings applied!',
            'command_failed': 'Command failed: {}',
            'need_sudo': 'Root privileges required',
            'no_ytdlp': 'yt-dlp not found, please install first',
            # App Manager
            'app_manager': 'App Manager',
            'app_manager_title': 'Manage Installed Apps',
            'app_search_hint': '🔍  Search packages...',
            'app_col_name': 'Package',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑  Uninstall',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Loading packages...',
            'app_count': 'Installed packages',
            'app_reload': '🔄  Reload',
            'app_confirm_uninstall': 'Confirm Uninstall',
            'app_confirm_msg': 'Remove "{}" from the system?\n\nThis action cannot be undone.',
            'app_uninstalling': 'Uninstalling {}...',
            'app_uninstall_ok': '{} has been removed successfully.',
            'app_uninstall_fail': 'Uninstall failed:\n{}',
            'app_select_first': 'Please select a package first',
            'app_info_title': 'Package Info',
        }

        # Thai (th) – updated with new donation strings
        strings_th = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'หน้าแรก',
            'keyboard': 'คีย์บอร์ด & ภาษา',
            'system_tools': 'จัดการระบบ',
            'network': 'เครือข่าย',
            'entertainment': 'ความบันเทิง',
            'theme': 'ปรับแต่งธีม',
            'backup': 'สำรองข้อมูล',
              'about': 'เกี่ยวกับ',
            'navigation': 'เมนูหลัก',
            'welcome': 'ยินดีต้อนรับสู่ Geng Settings Tools',
            'current_user': 'ผู้ใช้ปัจจุบัน',
            'hostname': 'เครื่องคอมพิวเตอร์',
            'home_desc': 'เครื่องมือช่วยตั้งค่าพื้นฐานสำหรับ Linux Mint Cinnamon 22.3\nเลือกเมนูทางด้านซ้ายเพื่อเริ่มการตั้งค่า',
            'keyboard_title': 'การตั้งค่าคีย์บอร์ด & ภาษา',
            'grave_title': 'สลับภาษาด้วยปุ่ม Grave Accent (~)',
            'grave_desc': 'ตั้งค่าให้ใช้ปุ่มตัวหนอน (Grave Accent) ในการสลับภาษา',
            'alt_shift_title': 'สลับภาษาด้วยปุ่ม Alt+Shift',
            'alt_shift_desc': 'ตั้งค่าให้ใช้ปุ่ม Alt + Shift ในการสลับภาษา',
            'custom_key_title': 'ตั้งค่าคีย์ลัดเอง',
            'custom_key_desc': 'กดปุ่มด้านล่างเพื่อบันทึกคีย์ผสมที่ต้องการ',
            'capture_key': 'จับคีย์',
            'apply_now': 'ตั้งค่าทันที',
            'system_title': 'เครื่องมือจัดการระบบ',
            'clean_system': 'ล้างไฟล์ขยะ',
            'clean_system_desc': 'ลบแพ็กเกจที่ไม่ได้ใช้งานและแคช',
            'clear_ram': 'เคลียร์แรม/แคช',
            'clear_ram_desc': 'ล้างแคชหน่วยความจำ (sync && drop_caches)',
            'driver_manager': 'ตัวจัดการไดรเวอร์',
            'driver_manager_desc': 'เปิด Driver Manager เพื่อติดตั้ง/ถอนไดรเวอร์',
            'flatpak': 'จัดการ Flatpak',
            'flatpak_desc': 'อัปเดต Flatpak และติดตั้งแอปพลิเคชัน',
            'apt_repair': 'ซ่อมแซม APT',
            'apt_repair_desc': 'ซ่อมแซมแพ็กเกจที่เสียหาย',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'เปิดโปรแกรมตรวจสอบระบบ',
            'network_title': 'จัดการเครือข่าย',
            'network_status': 'สถานะเครือข่าย',
            'refresh': 'รีเฟรช',
            'restart_network': 'รีสตาร์ทเครือข่าย',
            'flush_dns': 'ล้าง DNS',
            'renew_dhcp': 'ต่ออายุ DHCP',
            'interfaces': 'อุปกรณ์เครือข่าย',
            'connections': 'การเชื่อมต่อ',
            'entertainment_title': 'ความบันเทิง',
            'install_steam': 'ติดตั้ง Steam',
            'install_steam_desc': 'ติดตั้ง Steam สำหรับเล่นเกม',
            'install_wine': 'ติดตั้ง Wine',
            'install_wine_desc': 'ติดตั้ง Wine เพื่อรันโปรแกรม Windows',
            'download_media': 'ดาวน์โหลดคลิป/เสียง',
            'url_label': 'URL',
            'format_label': 'รูปแบบ',
            'video': 'วิดีโอ MP4',
            'audio': 'เสียง M4A',
            'download': 'ดาวน์โหลด',
            'install_ytdlp': 'ติดตั้ง yt-dlp',
            'theme_title': 'ปรับแต่งธีม',
            'dark_mode': 'โหมดมืด',
            'light_mode': 'โหมดสว่าง',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'ใช้ธีม',
            'backup_title': 'สำรองข้อมูล',
            'select_drive': 'เลือกไดรฟ์ปลายทาง',
            'backup_now': 'เริ่มสำรองข้อมูล',
            'backup_progress': 'กำลังสำรองข้อมูล...',
            'backup_complete': 'สำรองข้อมูลเสร็จสมบูรณ์',
            'backup_failed': 'สำรองข้อมูลล้มเหลว',
            'source': 'แหล่งข้อมูล',
            'destination': 'ปลายทาง',
            'exclude': 'ไม่รวม',
            'about_title': 'เกี่ยวกับ',
            'developer': 'ผู้พัฒนา',
            'email': 'Email',
            'thanks': 'เครื่องมือนี้สร้างขึ้นเพื่อช่วยให้คนไทยใช้งาน Linux ได้ง่ายขึ้น\nขอขอบคุณที่ร่วมเป็นส่วนหนึ่งของครอบครัว Open Source',
            'donate_sentence': 'ไม่มีเบียร์ โค้ดไม่เดิน สงเคราะห์โปรแกรมเมอร์คอแห้งหน่อย!',
            'donate_button': 'บริจาคค่าเหล้า',
            'bank_label': 'ธนาคาร',
            'bank_name': 'กสิกรไทย',
            'account_name_label': 'ชื่อบัญชี',
            'account_name': 'นาย ธรรมสรณ์ มุสิกพันธ์',
            'account_number_label': 'เลขที่บัญชี',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'สำเร็จ',
            'error': 'ข้อผิดพลาด',
            'settings_applied': 'ตั้งค่าเรียบร้อยแล้ว!',
            'command_failed': 'ไม่สามารถดำเนินการได้: {}',
            'need_sudo': 'ต้องการสิทธิ์ผู้ดูแลระบบ',
            'no_ytdlp': 'ไม่พบ yt-dlp กรุณาติดตั้งก่อน',
            'app_manager': 'จัดการโปรแกรม',
            'app_manager_title': 'จัดการโปรแกรมที่ติดตั้ง',
            'app_search_hint': '🔍  ค้นหาชื่อโปรแกรม...',
            'app_col_name': 'ชื่อโปรแกรม',
            'app_col_version': 'เวอร์ชัน',
            'app_col_desc': 'คำอธิบาย',
            'app_uninstall': '🗑  ถอนการติดตั้ง',
            'app_info': 'ℹ  ข้อมูล',
            'app_loading': '⏳  กำลังโหลดรายการโปรแกรม...',
            'app_count': 'โปรแกรมที่ติดตั้ง',
            'app_reload': '🔄  โหลดใหม่',
            'app_confirm_uninstall': 'ยืนยันถอนการติดตั้ง',
            'app_confirm_msg': 'ต้องการถอนการติดตั้ง "{}" ออกจากระบบ?\n\nการกระทำนี้ไม่สามารถยกเลิกได้',
            'app_uninstalling': 'กำลังถอนการติดตั้ง {}...',
            'app_uninstall_ok': 'ถอนการติดตั้ง {} เรียบร้อยแล้ว',
            'app_uninstall_fail': 'ถอนการติดตั้งล้มเหลว:\n{}',
            'app_select_first': 'กรุณาเลือกโปรแกรมก่อน',
            'app_info_title': 'ข้อมูลโปรแกรม',
        }

        # Lao (lo)
        strings_lo = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'ໜ້າຫຼັກ',
            'keyboard': 'ຄີບອດ & ພາສາ',
            'system_tools': 'ຈັດການລະບົບ',
            'network': 'ເຄືອຂ່າຍ',
            'entertainment': 'ຄວາມບັນເທີງ',
            'theme': 'ປັບແຕ່ງທີມ',
            'backup': 'ສຳຮອງຂໍ້ມູນ',
            'about': 'ກ່ຽວກັບ',
            'navigation': 'ເມນູຫຼັກ',
            'welcome': 'ຍິນດີຕ້ອນຮັບເຂົ້າສູ່ Geng Settings Tools',
            'current_user': 'ຜູ້ໃຊ້ປັດຈຸບັນ',
            'hostname': 'ຊື່ເຄື່ອງ',
            'home_desc': 'ເຄື່ອງມືຊ່ວຍຕັ້ງຄ່າພື້ນຖານສຳລັບ Linux Mint Cinnamon 22.3\nເລືອກເມນູທາງດ້ານຊ້າຍເພື່ອເລີ່ມການຕັ້ງຄ່າ',
            'keyboard_title': 'ການຕັ້ງຄ່າຄີບອດ & ພາສາ',
            'grave_title': 'ສະຫຼັບພາສາດ້ວຍປຸ່ມ Grave Accent (~)',
            'grave_desc': 'ຕັ້ງຄ່າໃຫ້ໃຊ້ປຸ່ມ Grave Accent ໃນການສະຫຼັບພາສາ',
            'alt_shift_title': 'ສະຫຼັບພາສາດ້ວຍປຸ່ມ Alt+Shift',
            'alt_shift_desc': 'ຕັ້ງຄ່າໃຫ້ໃຊ້ປຸ່ມ Alt + Shift ໃນການສະຫຼັບພາສາ',
            'custom_key_title': 'ຕັ້ງຄ່າຄີລັດເອງ',
            'custom_key_desc': 'ກົດປຸ່ມດ້ານລຸ່ມເພື່ອບັນທຶກຄີປະສົມທີ່ຕ້ອງການ',
            'capture_key': 'ຈັບຄີ',
            'apply_now': 'ຕັ້ງຄ່າທັນທີ',
            'system_title': 'ເຄື່ອງມືຈັດການລະບົບ',
            'clean_system': 'ລ້າງໄຟລ໌ຂີ້ເຫຍື້ອ',
            'clean_system_desc': 'ລົບແພັກເກັດທີ່ບໍ່ໄດ້ໃຊ້ງານແລະແຄຊ',
            'clear_ram': 'ເຄລຍແຮມ/ແຄຊ',
            'clear_ram_desc': 'ລ້າງແຄຊໜ່ວຍຄວາມຈຳ (sync && drop_caches)',
            'driver_manager': 'ຕົວຈັດການໄດເວີ',
            'driver_manager_desc': 'ເປີດ Driver Manager ເພື່ອຕິດຕັ້ງ/ຖອນໄດເວີ',
            'flatpak': 'ຈັດການ Flatpak',
            'flatpak_desc': 'ອັບເດດ Flatpak ແລະຕິດຕັ້ງແອັບພລິເຄຊັນ',
            'apt_repair': 'ສ້ອມແຊມ APT',
            'apt_repair_desc': 'ສ້ອມແຊມແພັກເກັດທີ່ເສຍຫາຍ',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'ເປີດໂປຣແກຣມກວດສອບລະບົບ',
            'network_title': 'ຈັດການເຄືອຂ່າຍ',
            'network_status': 'ສະຖານະເຄືອຂ່າຍ',
            'refresh': 'ຣີເຟຣຊ',
            'restart_network': 'ຣີສະຕາດເຄືອຂ່າຍ',
            'flush_dns': 'ລ້າງ DNS',
            'renew_dhcp': 'ຕໍ່ອາຍຸ DHCP',
            'interfaces': 'ອຸປະກອນເຄືອຂ່າຍ',
            'connections': 'ການເຊື່ອມຕໍ່',
            'entertainment_title': 'ຄວາມບັນເທີງ',
            'install_steam': 'ຕິດຕັ້ງ Steam',
            'install_steam_desc': 'ຕິດຕັ້ງ Steam ສຳລັບຫຼິ້ນເກມ',
            'install_wine': 'ຕິດຕັ້ງ Wine',
            'install_wine_desc': 'ຕິດຕັ້ງ Wine ເພື່ອຣັນໂປຣແກຣມ Windows',
            'download_media': 'ດາວໂຫຼດວິດີໂອ/ສຽງ',
            'url_label': 'URL',
            'format_label': 'ຮູບແບບ',
            'video': 'ວິດີໂອ MP4',
            'audio': 'ສຽງ M4A',
            'download': 'ດາວໂຫຼດ',
            'install_ytdlp': 'ຕິດຕັ້ງ yt-dlp',
            'theme_title': 'ປັບແຕ່ງທີມ',
            'dark_mode': 'ໂໝດມືດ',
            'light_mode': 'ໂໝດສະຫວ່າງ',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'ໃຊ້ທີມ',
            'backup_title': 'ສຳຮອງຂໍ້ມູນ',
            'select_drive': 'ເລືອກໄດຣຟ໌ປາຍທາງ',
            'backup_now': 'ເລີ່ມສຳຮອງຂໍ້ມູນ',
            'backup_progress': 'ກຳລັງສຳຮອງຂໍ້ມູນ...',
            'backup_complete': 'ສຳຮອງຂໍ້ມູນສຳເລັດ',
            'backup_failed': 'ສຳຮອງຂໍ້ມູນລົ້ມເຫຼວ',
            'source': 'ແຫຼ່ງຂໍ້ມູນ',
            'destination': 'ປາຍທາງ',
            'exclude': 'ບໍ່ລວມ',
            'about_title': 'ກ່ຽວກັບ',
            'developer': 'ຜູ້ພັດທະນາ',
            'email': 'Email',
            'thanks': 'ເຄື່ອງມືນີ້ສ້າງຂຶ້ນເພື່ອຊ່ວຍໃຫ້ຄົນລາວໃຊ້ງານ Linux ໄດ້ງ່າຍຂຶ້ນ\nຂໍຂອບໃຈທີ່ຮ່ວມເປັນສ່ວນໜຶ່ງຂອງຄອບຄົວ Open Source',
            'donate_sentence': 'ບໍ່ມີເບຍ ໂຄ້ດບໍ່ເດີນ ສົງເຄາະໂປຣແກຣມເມີຄໍແຫ້ງແດ່!',
            'donate_button': 'ບໍລິຈາກຄ່າເຫຼົ້າ',
            'bank_label': 'ທະນາຄານ',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'ຊື່ບັນຊີ',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'ເລກບັນຊີ',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'ສຳເລັດ',
            'error': 'ຂໍ້ຜິດພາດ',
            'settings_applied': 'ຕັ້ງຄ່າຮຽບຮ້ອຍແລ້ວ!',
            'command_failed': 'ບໍ່ສາມາດດຳເນີນການໄດ້: {}',
            'need_sudo': 'ຕ້ອງການສິດຜູ້ດູແລລະບົບ',
            'no_ytdlp': 'ບໍ່ພົບ yt-dlp ກະລຸນາຕິດຕັ້ງກ່ອນ',
            'app_manager': 'ຈັດການໂປຣແກຣມ',
            'app_manager_title': 'ຈັດການໂປຣແກຣມທີ່ຕິດຕັ້ງ',
            'app_search_hint': '🔍  ຄົ້ນຫາຊື່ໂປຣແກຣມ...',
            'app_col_name': 'ຊື່ໂປຣແກຣມ',
            'app_col_version': 'ເວີຊັນ',
            'app_col_desc': 'ຄຳອະທິບາຍ',
            'app_uninstall': '🗑  ຖອນການຕິດຕັ້ງ',
            'app_info': 'ℹ  ຂໍ້ມູນ',
            'app_loading': '⏳  ກຳລັງໂຫຼດລາຍການໂປຣແກຣມ...',
            'app_count': 'ໂປຣແກຣມທີ່ຕິດຕັ້ງ',
            'app_reload': '🔄  ໂຫຼດໃໝ່',
            'app_confirm_uninstall': 'ຢືນຢັນຖອນການຕິດຕັ້ງ',
            'app_confirm_msg': 'ຕ້ອງການຖອນການຕິດຕັ້ງ \"{}\" ອອກຈາກລະບົບ?\n\nການກະທຳນີ້ບໍ່ສາມາດຍົກເລີກໄດ້',
            'app_uninstalling': 'ກຳລັງຖອນການຕິດຕັ້ງ {}...',
            'app_uninstall_ok': 'ຖອນການຕິດຕັ້ງ {} ຮຽບຮ້ອຍແລ້ວ',
            'app_uninstall_fail': 'ຖອນການຕິດຕັ້ງລົ້ມເຫຼວ:\n{}',
            'app_select_first': 'ກະລຸນາເລືອກໂປຣແກຣມກ່ອນ',
            'app_info_title': 'ຂໍ້ມູນໂປຣແກຣມ',
        }

        # de
        strings_de = {
            'window_title': 'Geng Einstellungen Werkzeuge v2.0.6',
            'home': 'Startseite',
            'keyboard': 'Tastatur & Sprache',
            'system_tools': 'Systemwerkzeuge',
            'network': 'Netzwerk',
            'entertainment': 'Unterhaltung',
            'theme': 'Thema',
            'backup': 'Sicherung',
            'about': 'Über',
            'navigation': 'NAVIGATION',
            'welcome': 'Willkommen bei Geng Einstellungen Werkzeuge',
            'current_user': 'Aktueller Benutzer',
            'hostname': 'Hostname',
            'home_desc': 'Ihr All-in-One Konfigurationstoolbox für Linux Mint Cinnamon 22.3.\nPassen Sie Tastenkürzel einfach an, verwalten Sie Apps, reinigen Sie Ihr System, laden Sie Medien herunter und mehr.\nWählen Sie eine Kategorie aus der Seitenleiste, um zu starten – alles ist nur einen Klick entfernt!',
            'keyboard_title': 'Tastatur- & Spracheinstellungen',
            'grave_title': 'Sprache mit Gravis (`~`) wechseln',
            'grave_desc': 'Verwenden Sie die Gravis-Taste, um Eingabemethoden zu wechseln',
            'alt_shift_title': 'Sprache mit Alt+Shift wechseln',
            'alt_shift_desc': 'Verwenden Sie Alt + Shift, um Eingabemethoden zu wechseln',
            'custom_key_title': 'Benutzerdefinierte Tastenkombination',
            'custom_key_desc': 'Drücken Sie die Schaltfläche unten, um die gewünschte Tastenkombination aufzunehmen',
            'capture_key': 'Taste erfassen',
            'apply_now': 'Jetzt anwenden',
            'system_title': 'Systemverwaltungswerkzeuge',
            'clean_system': 'Junk-Dateien bereinigen',
            'clean_system_desc': 'Nicht verwendete Pakete entfernen und Cache leeren',
            'clear_ram': 'RAM/Cache leeren',
            'clear_ram_desc': 'Systemspeichercache leeren (sync && drop_caches)',
            'driver_manager': 'Treiberverwaltung',
            'driver_manager_desc': 'Treiberverwaltung öffnen, um Treiber zu installieren/entfernen',
            'flatpak': 'Flatpak verwalten',
            'flatpak_desc': 'Flatpak aktualisieren und Anwendungen verwalten',
            'apt_repair': 'APT Reparatur',
            'apt_repair_desc': 'Beschädigte Pakete reparieren und Listen aktualisieren',
            'system_monitor': 'Systemmonitor',
            'system_monitor_desc': 'Systemüberwachungstool öffnen',
            'network_title': 'Netzwerkverwaltung',
            'network_status': 'Netzwerkstatus',
            'refresh': 'Aktualisieren',
            'restart_network': 'Netzwerk neu starten',
            'flush_dns': 'DNS leeren',
            'renew_dhcp': 'DHCP erneuern',
            'interfaces': 'Netzwerkschnittstellen',
            'connections': 'Verbindungen',
            'entertainment_title': 'Unterhaltung',
            'install_steam': 'Steam installieren',
            'install_steam_desc': 'Steam zum Spielen installieren',
            'install_wine': 'Wine installieren',
            'install_wine_desc': 'Wine installieren, um Windows-Programme auszuführen',
            'download_media': 'Video/Audio herunterladen',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Herunterladen',
            'install_ytdlp': 'yt-dlp installieren',
            'theme_title': 'Themenanpassung',
            'dark_mode': 'Dunkler Modus',
            'light_mode': 'Heller Modus',
            'mint_y': 'Mint-Y (Hell)',
            'mint_y_dark': 'Mint-Y-Dunkel',
            'mint_y_dark_aqua': 'Mint-Y-Dunkel-Aqua',
            'apply_theme': 'Thema anwenden',
            'backup_title': 'Datensicherung',
            'select_drive': 'Zieldatenträger auswählen',
            'backup_now': 'Sicherung starten',
            'backup_progress': 'Sicherung läuft...',
            'backup_complete': 'Sicherung abgeschlossen',
            'backup_failed': 'Sicherung fehlgeschlagen',
            'source': 'Quelle',
            'destination': 'Ziel',
            'exclude': 'Ausschließen',
            'about_title': 'Über',
            'developer': 'Entwickler',
            'email': 'E-Mail',
            'thanks': 'Dieses Werkzeug wurde entwickelt, um die Nutzung von Linux zu erleichtern.\nDanke, dass Sie Teil der Open-Source-Familie sind!',
            'donate_sentence': 'Kein Bier, kein Code. Bitte unterstützen Sie einen durstigen Programmierer!',
            'donate_button': 'Biergeld spenden',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontoinhaber',
            'account_name': 'Herr Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Erfolg',
            'error': 'Fehler',
            'settings_applied': 'Einstellungen erfolgreich angewendet!',
            'command_failed': 'Befehl fehlgeschlagen: {}',
            'need_sudo': 'Administratorrechte erforderlich',
            'no_ytdlp': 'yt-dlp nicht gefunden. Bitte zuerst installieren.',
            'app_manager': 'App-Manager',
            'app_manager_title': 'Installierte Anwendungen verwalten',
            'app_search_hint': '🔍 App-Namen suchen...',
            'app_col_name': 'App-Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Beschreibung',
            'app_uninstall': '🗑 Deinstallieren',
            'app_info': 'ℹ Info',
            'app_loading': '⏳ Anwendungen werden geladen...',
            'app_count': 'Installierte Apps',
            'app_reload': '🔄 Neu laden',
            'app_confirm_uninstall': 'Deinstallation bestätigen',
            'app_confirm_msg': '„{}“ vom System deinstallieren?\n\nDiese Aktion kann nicht rückgängig gemacht werden.',
            'app_uninstalling': 'Deinstalliere {}...',
            'app_uninstall_ok': '{} erfolgreich deinstalliert',
            'app_uninstall_fail': 'Deinstallation fehlgeschlagen:\n{}',
            'app_select_first': 'Bitte wählen Sie zuerst eine Anwendung aus',
            'app_info_title': 'App-Informationen',
        }

        # fr
        strings_fr = {
            'window_title': 'Outils de Configuration Geng v2.0.6',
            'home': 'Accueil',
            'keyboard': 'Clavier & Langue',
            'system_tools': 'Outils Système',
            'network': 'Réseau',
            'entertainment': 'Divertissement',
            'theme': 'Thème',
            'backup': 'Sauvegarde',
            'about': 'À propos',
            'navigation': 'NAVIGATION',
            'welcome': 'Bienvenue dans les Outils de Configuration Geng',
            'current_user': 'Utilisateur actuel',
            'hostname': 'Nom d\'hôte',
            'home_desc': 'Votre boîte à outils de configuration tout-en-un pour Linux Mint Cinnamon 22.3.\nModifiez facilement les raccourcis clavier, gérez les applications, nettoyez votre système, téléchargez des médias, et plus encore.\nSélectionnez une catégorie depuis la barre latérale pour commencer — tout est à portée de clic !',
            'keyboard_title': 'Paramètres Clavier & Langue',
            'grave_title': 'Changer de langue avec l’Accent Grave (~)',
            'grave_desc': 'Utilisez la touche Accent Grave pour changer les méthodes de saisie',
            'alt_shift_title': 'Changer de langue avec Alt+Maj',
            'alt_shift_desc': 'Utilisez les touches Alt + Maj pour changer les méthodes de saisie',
            'custom_key_title': 'Raccourci clavier personnalisé',
            'custom_key_desc': 'Appuyez sur le bouton ci-dessous pour capturer la combinaison de touches souhaitée',
            'capture_key': 'Capturer la touche',
            'apply_now': 'Appliquer maintenant',
            'system_title': 'Outils de Gestion du Système',
            'clean_system': 'Nettoyer les fichiers inutiles',
            'clean_system_desc': 'Supprimer les paquets inutilisés et vider le cache',
            'clear_ram': 'Libérer RAM/Cache',
            'clear_ram_desc': 'Vider le cache mémoire système (sync && drop_caches)',
            'driver_manager': 'Gestionnaire de Pilotes',
            'driver_manager_desc': 'Ouvrir le gestionnaire de pilotes pour installer/supprimer des pilotes',
            'flatpak': 'Gérer Flatpak',
            'flatpak_desc': 'Mettre à jour Flatpak et gérer les applications',
            'apt_repair': 'Réparation APT',
            'apt_repair_desc': 'Réparer les paquets cassés et mettre à jour les listes',
            'system_monitor': 'Moniteur Système',
            'system_monitor_desc': 'Ouvrir l’outil de surveillance système',
            'network_title': 'Gestion du Réseau',
            'network_status': 'Statut du réseau',
            'refresh': 'Rafraîchir',
            'restart_network': 'Redémarrer le réseau',
            'flush_dns': 'Vider le DNS',
            'renew_dhcp': 'Renouveler DHCP',
            'interfaces': 'Interfaces Réseau',
            'connections': 'Connexions',
            'entertainment_title': 'Divertissement',
            'install_steam': 'Installer Steam',
            'install_steam_desc': 'Installer Steam pour les jeux',
            'install_wine': 'Installer Wine',
            'install_wine_desc': 'Installer Wine pour exécuter des programmes Windows',
            'download_media': 'Télécharger Vidéo/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Vidéo MP4',
            'audio': 'Audio M4A',
            'download': 'Télécharger',
            'install_ytdlp': 'Installer yt-dlp',
            'theme_title': 'Personnalisation du Thème',
            'dark_mode': 'Mode Sombre',
            'light_mode': 'Mode Clair',
            'mint_y': 'Mint-Y (Clair)',
            'mint_y_dark': 'Mint-Y-Sombre',
            'mint_y_dark_aqua': 'Mint-Y-Sombre-Aqua',
            'apply_theme': 'Appliquer le thème',
            'backup_title': 'Sauvegarde des Données',
            'select_drive': 'Sélectionner le disque de destination',
            'backup_now': 'Démarrer la sauvegarde',
            'backup_progress': 'Sauvegarde en cours...',
            'backup_complete': 'Sauvegarde terminée',
            'backup_failed': 'Sauvegarde échouée',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclure',
            'about_title': 'À propos',
            'developer': 'Développeur',
            'email': 'Email',
            'thanks': 'Cet outil a été créé pour aider les personnes à utiliser Linux plus facilement.\nMerci de faire partie de la famille Open Source !',
            'donate_sentence': 'Pas de bière, pas de code. Merci de soutenir un programmeur assoiffé !',
            'donate_button': 'Faire un don pour la bière',
            'bank_label': 'Banque',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nom du compte',
            'account_name': 'M. Thammasorn Musikapan',
            'account_number_label': 'Numéro de compte',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Succès',
            'error': 'Erreur',
            'settings_applied': 'Paramètres appliqués avec succès !',
            'command_failed': 'Échec de la commande : {}',
            'need_sudo': 'Privilèges administrateur requis',
            'no_ytdlp': 'yt-dlp introuvable. Veuillez l’installer d’abord.',
            'app_manager': 'Gestionnaire d’Applications',
            'app_manager_title': 'Gérer les Applications Installées',
            'app_search_hint': '🔍  Rechercher le nom de l’application...',
            'app_col_name': 'Nom de l’application',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑  Désinstaller',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Chargement des applications...',
            'app_count': 'Applications installées',
            'app_reload': '🔄  Recharger',
            'app_confirm_uninstall': 'Confirmer la désinstallation',
            'app_confirm_msg': 'Désinstaller "{}" du système ?\n\nCette action est irréversible.',
            'app_uninstalling': 'Désinstallation de {}...',
            'app_uninstall_ok': 'Désinstallation réussie de {}',
            'app_uninstall_fail': 'Échec de la désinstallation :\n{}',
            'app_select_first': 'Veuillez d’abord sélectionner une application',
            'app_info_title': 'Informations sur l’application',
        }

        # ga
        strings_ga = {
            'window_title': 'Geng Nsa Nye Nɛi v2.0.6',
            'home': 'Fie',
            'keyboard': 'Ntɔkyerɛnne & Kasa',
            'system_tools': 'Ntɛnyɛsɛm Nsa Nye Nɛi',
            'network': 'Ntɔkwa',
            'entertainment': 'Dwanei',
            'theme': 'Nkakɛɛm',
            'backup': 'Bukap',
            'about': 'Fa Ho',
            'navigation': 'DWUMADEN',
            'welcome': 'Akwaaba aba Geng Nsa Nye Nɛi mu',
            'current_user': 'Ɔde Nsa Yɛ Ammɔnten',
            'hostname': 'Dɛkyee Din',
            'home_desc': 'Wo nsa nyeɛ mu kɔkɔɔ no nyinaa hyɛ deɛ yɛreyeɛ ma Linux Mint Cinnamon 22.3.\nNtɛm a, to nsa so no ntɔkyerɛnne kwan, bɔ dwumadie ho ban, yɛ sistema no ho hyeɛ, fa video ne dwom tow, ne sɛnea ɛbɛyɛ a wo bɛda so a, ɛkɔm de wo wɔ he! \nPaw baako fi sidebar mu na fi ase yɛ adwuma — deɛ hono nyinaa yɛ nsa baako so!',
            'keyboard_title': 'Ntɔkyerɛnne & Kasa Nsa Nye Nɛi',
            'grave_title': 'Sesaa kasa de Grave Accent (~)',
            'grave_desc': 'Fa Grave Accent mframa nsa sesaa ntɔkyerɛnne kwan no',
            'alt_shift_title': 'Sesaa kasa de Alt+Shift',
            'alt_shift_desc': 'Fa Alt + Shift mframa nsa sesaa ntɔkyerɛnne kwan no',
            'custom_key_title': 'Ntɔkyerɛne a Wopɛ Ara',
            'custom_key_desc': 'Paw botoom a ɛwɔ he de besua ntɔkyerɛne a wopɛ no',
            'capture_key': 'Fa Ntɔkyerɛnne No',
            'apply_now': 'Fa So Seisei',
            'system_title': 'Sistema Nhwɛso Nsa Nye Nɛi',
            'clean_system': 'Pɛe Gyaado Nnwuma',
            'clean_system_desc': 'Yi nnɔbae a wɔankɔ so na pɛ nneɛma fi hɔ',
            'clear_ram': 'Pɛ RAM/Cache',
            'clear_ram_desc': 'Pɛ sistema ka no mu pɛ (sync && drop_caches)',
            'driver_manager': 'Ntɔn Mpɔnni Hwɛfo',
            'driver_manager_desc': 'Bue Ntɔn Mpɔnni Hwɛfo na hyɛ/yi mpɔnni no',
            'flatpak': 'Hwɛ Flatpak',
            'flatpak_desc': 'Nkan Flatpak na hwɛ dwumadie no so',
            'apt_repair': 'APT Nsa So',
            'apt_repair_desc': 'Sua nnɔbae a wɔawuwu na hyɛ nsɛm ho',
            'system_monitor': 'Sistema Ahwɛ',
            'system_monitor_desc': 'Bue sistema ahwɛ nsa nye nɛi',
            'network_title': 'Ntɔkwa Hwɛso',
            'network_status': 'Ntɔkwa So',
            'refresh': 'San Kɔ So',
            'restart_network': 'San Hyɛ Ntɔkwa No Bio',
            'flush_dns': 'Pɛ DNS',
            'renew_dhcp': 'San Hyɛ DHCP',
            'interfaces': 'Ntɔkwa Ntɔkwakwaa',
            'connections': 'Ntɔkwani',
            'entertainment_title': 'Dwanei',
            'install_steam': 'Hyɛ Steam',
            'install_steam_desc': 'Hyɛ Steam de bɔ agoru',
            'install_wine': 'Hyɛ Wine',
            'install_wine_desc': 'Hyɛ Wine de bɔ Windows dwumadie',
            'download_media': 'Tow Video/Dwom',
            'url_label': 'URL',
            'format_label': 'Ntɛmfaho',
            'video': 'Video MP4',
            'audio': 'Dwom M4A',
            'download': 'Tow',
            'install_ytdlp': 'Hyɛ yt-dlp',
            'theme_title': 'Nkakɛɛm Bɔho',
            'dark_mode': 'Anadwo Mu',
            'light_mode': 'Anɔpa Mu',
            'mint_y': 'Mint-Y (Anɔpa Mu)',
            'mint_y_dark': 'Mint-Y-Anadwo',
            'mint_y_dark_aqua': 'Mint-Y-Anadwo-Akwaka',
            'apply_theme': 'Fa Nkakɛɛm No So',
            'backup_title': 'Data Bukap',
            'select_drive': 'Paw baabi a wobɛde akɔ',
            'backup_now': 'Fi Bukap So',
            'backup_progress': 'Rebukap...',
            'backup_complete': 'Bukap Asi Pi',
            'backup_failed': 'Bukap Antumi Annɔ',
            'source': 'Fi',
            'destination': 'Baabi',
            'exclude': 'Gyae',
            'about_title': 'Fa Ho',
            'developer': 'Nwonwafo',
            'email': 'Email',
            'thanks': 'Yi nsa nyeɛ yi yɛɛ no sɛnea ɛbɛboa nnipa a wɔde Linux bɛyɛ adwuma no yiye.\nMedase sɛ wo yɛ Open Source abusua mu!',
            'donate_sentence': 'Nni nsuo a, nni kɔd. Mesrɛ boa obi a ɔpɛ nsuo no!',
            'donate_button': 'Ma Nsuo Sika',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Akaunt Din',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Akaunt No',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Ɛyɛ Fine',
            'error': 'Mfomso',
            'settings_applied': 'Nsa Nyeɛ no deɛ a wɔde soo ho no abɛyɛ!',
            'command_failed': 'Ahyɛde no antumi anyɛ: {}',
            'need_sudo': 'Wopɛ administrator tumi',
            'no_ytdlp': 'yt-dlp nhui. Mesrɛ w\'ahyɛ no kan.',
            'app_manager': 'Dwumadie Hwɛfo',
            'app_manager_title': 'Hwɛ Dwumadie Awo Ho',
            'app_search_hint': '🔍  Hwehwɛ dwumadie din...',
            'app_col_name': 'Dwumadie Din',
            'app_col_version': 'Nsiesie',
            'app_col_desc': 'Nkyerɛkyerɛ',
            'app_uninstall': '🗑  Yi',
            'app_info': 'ℹ  Nsɛm',
            'app_loading': '⏳  Resɔ dwumadie no...',
            'app_count': 'Awo Dwumadie',
            'app_reload': '🔄  San So',
            'app_confirm_uninstall': 'Hwɛ Yi Ho',
            'app_confirm_msg': 'Paw "{}" afi sistema no mu?\n\nDeɛ eyi yɛ no, ɛntumi nsi bio.',
            'app_uninstalling': 'Regyina so yi {}...',
            'app_uninstall_ok': 'Yi sɛ nea ɛbɛyɛ a ɛyɛ fine {}',
            'app_uninstall_fail': 'Yi no annye:\n{}',
            'app_select_first': 'Mesrɛ, paw dwumadie kan',
            'app_info_title': 'Dwumadie Nsɛm',
        }

        # nl
        strings_nl = {
            'window_title': 'Geng Instellingen Tools v2.0.6',
            'home': 'Startpagina',
            'keyboard': 'Toetsenbord & Taal',
            'system_tools': 'Systeemtools',
            'network': 'Netwerk',
            'entertainment': 'Entertainment',
            'theme': 'Thema',
            'backup': 'Back-up',
            'about': 'Over',
            'navigation': 'NAVIGATIE',
            'welcome': 'Welkom bij Geng Instellingen Tools',
            'current_user': 'Huidige gebruiker',
            'hostname': 'Hostnaam',
            'home_desc': 'Uw alles-in-één configuratie gereedschapskist voor Linux Mint Cinnamon 22.3.\nPas gemakkelijk sneltoetsen aan, beheer apps, maak uw systeem schoon, download media en meer.\nSelecteer een categorie in de zijbalk om te beginnen — alles is met één klik bereikbaar!',
            'keyboard_title': 'Toetsenbord- & taalinstellingen',
            'grave_title': 'Schakel taal met Grave Accent (~)',
            'grave_desc': 'Gebruik de Grave Accent-toets om invoermethoden te wisselen',
            'alt_shift_title': 'Schakel taal met Alt+Shift',
            'alt_shift_desc': 'Gebruik Alt + Shift-toetsen om invoermethoden te wisselen',
            'custom_key_title': 'Aangepaste toetscombinatie',
            'custom_key_desc': 'Druk op de knop hieronder om de gewenste toetscombinatie vast te leggen',
            'capture_key': 'Toets vastleggen',
            'apply_now': 'Nu toepassen',
            'system_title': 'Systeembeheerhulpmiddelen',
            'clean_system': 'Opschonen van ongewenste bestanden',
            'clean_system_desc': 'Verwijder ongebruikte pakketten en wis cache',
            'clear_ram': 'RAM/Cache wissen',
            'clear_ram_desc': 'Wis systeemgeheugencache (sync && drop_caches)',
            'driver_manager': 'Driverbeheerder',
            'driver_manager_desc': 'Open Driverbeheerder om drivers te installeren/verwijderen',
            'flatpak': 'Beheer Flatpak',
            'flatpak_desc': 'Update Flatpak en beheer applicaties',
            'apt_repair': 'APT Reparatie',
            'apt_repair_desc': 'Repareer kapotte pakketten en update lijsten',
            'system_monitor': 'Systeemmonitor',
            'system_monitor_desc': 'Open systeemmonitorhulpmiddel',
            'network_title': 'Netwerkbeheer',
            'network_status': 'Netwerkstatus',
            'refresh': 'Vernieuwen',
            'restart_network': 'Netwerk herstarten',
            'flush_dns': 'DNS legen',
            'renew_dhcp': 'DHCP vernieuwen',
            'interfaces': 'Netwerkinterfaces',
            'connections': 'Verbindingen',
            'entertainment_title': 'Entertainment',
            'install_steam': 'Installeer Steam',
            'install_steam_desc': 'Installeer Steam voor gamen',
            'install_wine': 'Installeer Wine',
            'install_wine_desc': 'Installeer Wine om Windows-programma\'s te draaien',
            'download_media': 'Download Video/Audio',
            'url_label': 'URL',
            'format_label': 'Formaat',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Downloaden',
            'install_ytdlp': 'Installeer yt-dlp',
            'theme_title': 'Thema Aanpassingen',
            'dark_mode': 'Donkere modus',
            'light_mode': 'Lichte modus',
            'mint_y': 'Mint-Y (Licht)',
            'mint_y_dark': 'Mint-Y-Donker',
            'mint_y_dark_aqua': 'Mint-Y-Donker-Aqua',
            'apply_theme': 'Thema toepassen',
            'backup_title': 'Gegevensback-up',
            'select_drive': 'Selecteer doelstation',
            'backup_now': 'Back-up starten',
            'backup_progress': 'Bezig met back-uppen...',
            'backup_complete': 'Back-up voltooid',
            'backup_failed': 'Back-up mislukt',
            'source': 'Bron',
            'destination': 'Bestemming',
            'exclude': 'Uitsluiten',
            'about_title': 'Over',
            'developer': 'Ontwikkelaar',
            'email': 'E-mail',
            'thanks': 'Dit hulpmiddel is gemaakt om mensen te helpen Linux gemakkelijker te gebruiken.\nBedankt dat u deel uitmaakt van de Open Source familie!',
            'donate_sentence': 'Geen bier, geen code. Steun alstublieft een dorstige programmeur!',
            'donate_button': 'Doneer biergeld',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Rekeninghouder',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Rekeningnummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Succes',
            'error': 'Fout',
            'settings_applied': 'Instellingen succesvol toegepast!',
            'command_failed': 'Commando mislukt: {}',
            'need_sudo': 'Beheerderrechten vereist',
            'no_ytdlp': 'yt-dlp niet gevonden. Installeer het eerst.',
            'app_manager': 'App-beheerder',
            'app_manager_title': 'Beheer geïnstalleerde applicaties',
            'app_search_hint': '🔍  Zoek applicatienaam...',
            'app_col_name': 'App-naam',
            'app_col_version': 'Versie',
            'app_col_desc': 'Beschrijving',
            'app_uninstall': '🗑  Verwijderen',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Applicaties laden...',
            'app_count': 'Geïnstalleerde apps',
            'app_reload': '🔄  Opnieuw laden',
            'app_confirm_uninstall': 'Verwijderen bevestigen',
            'app_confirm_msg': 'Verwijder "{}" van het systeem?\n\nDeze actie kan niet ongedaan gemaakt worden.',
            'app_uninstalling': 'Bezig met verwijderen van {}...',
            'app_uninstall_ok': '{}',
            'app_uninstall_fail': 'Verwijderen mislukt:\n{}',
            'app_select_first': 'Selecteer eerst een applicatie',
            'app_info_title': 'App-informatie',
        }

        # sv
        strings_sv = {
            'window_title': 'Geng Inställningsverktyg v2.0.6',
            'home': 'Hem',
            'keyboard': 'Tangentbord & Språk',
            'system_tools': 'Systemverktyg',
            'network': 'Nätverk',
            'entertainment': 'Underhållning',
            'theme': 'Tema',
            'backup': 'Säkerhetskopiering',
            'about': 'Om',
            'navigation': 'NAVIGATION',
            'welcome': 'Välkommen till Geng Inställningsverktyg',
            'current_user': 'Aktuell användare',
            'hostname': 'Värdnamn',
            'home_desc': 'Din allt-i-ett konfigurationsverktygslåda för Linux Mint Cinnamon 22.3.\nJustera enkelt tangentbordsgenvägar, hantera appar, rensa ditt system, ladda ner media och mer.\nVälj en kategori från sidofältet för att komma igång — allt är bara ett klick bort!',
            'keyboard_title': 'Tangentbords- & språkinställningar',
            'grave_title': 'Byt språk med grav accent (~)',
            'grave_desc': 'Använd grav accent-tangenten för att byta inmatningsmetoder',
            'alt_shift_title': 'Byt språk med Alt+Shift',
            'alt_shift_desc': 'Använd Alt + Shift-tangenterna för att byta inmatningsmetoder',
            'custom_key_title': 'Egen kortkommando',
            'custom_key_desc': 'Tryck på knappen nedan för att fånga önskad tangentkombination',
            'capture_key': 'Fånga tangent',
            'apply_now': 'Verkställ nu',
            'system_title': 'Systemhanteringsverktyg',
            'clean_system': 'Rensa skräpfiler',
            'clean_system_desc': 'Ta bort oanvända paket och rensa cache',
            'clear_ram': 'Rensa RAM/Cache',
            'clear_ram_desc': 'Rensa systemets minnescache (sync && drop_caches)',
            'driver_manager': 'Drivrutinsadministratör',
            'driver_manager_desc': 'Öppna drivrutinsadministratören för att installera/ta bort drivrutiner',
            'flatpak': 'Hantera Flatpak',
            'flatpak_desc': 'Uppdatera Flatpak och hantera applikationer',
            'apt_repair': 'APT Reparation',
            'apt_repair_desc': 'Reparera trasiga paket och uppdatera listor',
            'system_monitor': 'Systemövervakare',
            'system_monitor_desc': 'Öppna systemövervakningsverktyget',
            'network_title': 'Nätverkshantering',
            'network_status': 'Nätverksstatus',
            'refresh': 'Uppdatera',
            'restart_network': 'Starta om nätverket',
            'flush_dns': 'Rensa DNS',
            'renew_dhcp': 'Förnya DHCP',
            'interfaces': 'Nätverksgränssnitt',
            'connections': 'Anslutningar',
            'entertainment_title': 'Underhållning',
            'install_steam': 'Installera Steam',
            'install_steam_desc': 'Installera Steam för spel',
            'install_wine': 'Installera Wine',
            'install_wine_desc': 'Installera Wine för att köra Windows-program',
            'download_media': 'Ladda ner video/ljud',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Ljud M4A',
            'download': 'Ladda ner',
            'install_ytdlp': 'Installera yt-dlp',
            'theme_title': 'Temaanpassning',
            'dark_mode': 'Mörkt läge',
            'light_mode': 'Ljust läge',
            'mint_y': 'Mint-Y (Ljust)',
            'mint_y_dark': 'Mint-Y-Mörkt',
            'mint_y_dark_aqua': 'Mint-Y-Mörkt-Aqua',
            'apply_theme': 'Använd tema',
            'backup_title': 'Datasäkerhetskopiering',
            'select_drive': 'Välj måldisk',
            'backup_now': 'Starta säkerhetskopiering',
            'backup_progress': 'Säkerhetskopierar...',
            'backup_complete': 'Säkerhetskopiering klar',
            'backup_failed': 'Säkerhetskopiering misslyckades',
            'source': 'Källa',
            'destination': 'Destination',
            'exclude': 'Exkludera',
            'about_title': 'Om',
            'developer': 'Utvecklare',
            'email': 'E-post',
            'thanks': 'Detta verktyg skapades för att hjälpa människor att använda Linux enklare.\nTack för att du är en del av Open Source-familjen!',
            'donate_sentence': 'Inget öl, ingen kod. Stöd en törstig programmerare!',
            'donate_button': 'Donera ölpengar',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontonamn',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Framgång',
            'error': 'Fel',
            'settings_applied': 'Inställningar tillämpade framgångsrikt!',
            'command_failed': 'Kommandot misslyckades: {}',
            'need_sudo': 'Administratörsrättigheter krävs',
            'no_ytdlp': 'yt-dlp hittades inte. Vänligen installera det först.',
            'app_manager': 'Apphanterare',
            'app_manager_title': 'Hantera installerade applikationer',
            'app_search_hint': '🔍  Sök appnamn...',
            'app_col_name': 'Appnamn',
            'app_col_version': 'Version',
            'app_col_desc': 'Beskrivning',
            'app_uninstall': '🗑  Avinstallera',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Laddar applikationer...',
            'app_count': 'Installerade appar',
            'app_reload': '🔄  Ladda om',
            'app_confirm_uninstall': 'Bekräfta avinstallation',
            'app_confirm_msg': 'Avinstallera "{}" från systemet?\n\nDen här åtgärden kan inte ångras.',
            'app_uninstalling': 'Avinstallerar {}...',
            'app_uninstall_ok': 'Avinstallerade {} framgångsrikt',
            'app_uninstall_fail': 'Avinstallationen misslyckades:\n{}',
            'app_select_first': 'Vänligen välj en applikation först',
            'app_info_title': 'Appinformation',
        }

        # da
        strings_da = {
            'window_title': 'Geng Indstillinger Værktøjer v2.0.6',
            'home': 'Hjem',
            'keyboard': 'Tastatur & Sprog',
            'system_tools': 'Systemværktøjer',
            'network': 'Netværk',
            'entertainment': 'Underholdning',
            'theme': 'Tema',
            'backup': 'Backup',
            'about': 'Om',
            'navigation': 'NAVIGATION',
            'welcome': 'Velkommen til Geng Indstillinger Værktøjer',
            'current_user': 'Nuværende bruger',
            'hostname': 'Værtsnavn',
            'home_desc': 'Din alt‑i‑én konfigurationsværktøjskasse til Linux Mint Cinnamon 22.3.\nTilpas hurtigt tastaturgenveje, administrer apps, rens dit system, download medier og meget mere.\nVælg en kategori i sidebaren for at komme i gang – alt er kun et klik væk!',
            'keyboard_title': 'Indstillinger for Tastatur & Sprog',
            'grave_title': 'Skift sprog med Grav Accent (~)',
            'grave_desc': 'Brug Grav Accent-tasten til at skifte indtastningsmetoder',
            'alt_shift_title': 'Skift sprog med Alt+Shift',
            'alt_shift_desc': 'Brug Alt + Shift-tasterne til at skifte indtastningsmetoder',
            'custom_key_title': 'Brugerdefineret tastaturgenvej',
            'custom_key_desc': 'Tryk på knappen nedenfor for at optage ønsket tastkombination',
            'capture_key': 'Optag Tast',
            'apply_now': 'Anvend Nu',
            'system_title': 'Systemadministrationsværktøjer',
            'clean_system': 'Rens skraldefiler',
            'clean_system_desc': 'Fjern ubrugte pakker og ryd cache',
            'clear_ram': 'Ryd RAM/Cache',
            'clear_ram_desc': 'Ryd systemets hukommelsescache (sync && drop_caches)',
            'driver_manager': 'Driver Manager',
            'driver_manager_desc': 'Åbn Driver Manager for at installere/fjerne drivere',
            'flatpak': 'Administrer Flatpak',
            'flatpak_desc': 'Opdater Flatpak og administrer applikationer',
            'apt_repair': 'APT Reparation',
            'apt_repair_desc': 'Reparer ødelagte pakker og opdater lister',
            'system_monitor': 'Systemovervågning',
            'system_monitor_desc': 'Åbn systemovervågningsværktøj',
            'network_title': 'Netværksadministration',
            'network_status': 'Netværksstatus',
            'refresh': 'Opdater',
            'restart_network': 'Genstart Netværk',
            'flush_dns': 'Ryd DNS',
            'renew_dhcp': 'Forny DHCP',
            'interfaces': 'Netværksinterface',
            'connections': 'Forbindelser',
            'entertainment_title': 'Underholdning',
            'install_steam': 'Installer Steam',
            'install_steam_desc': 'Installer Steam til spil',
            'install_wine': 'Installer Wine',
            'install_wine_desc': 'Installer Wine for at køre Windows-programmer',
            'download_media': 'Download Video/Lyd',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Lyd M4A',
            'download': 'Download',
            'install_ytdlp': 'Installer yt-dlp',
            'theme_title': 'Tema Tilpasning',
            'dark_mode': 'Mørk Tilstand',
            'light_mode': 'Lys Tilstand',
            'mint_y': 'Mint-Y (Lys)',
            'mint_y_dark': 'Mint-Y-Mørk',
            'mint_y_dark_aqua': 'Mint-Y-Mørk-Aqua',
            'apply_theme': 'Anvend Tema',
            'backup_title': 'Data Backup',
            'select_drive': 'Vælg destinationsdrev',
            'backup_now': 'Start Backup',
            'backup_progress': 'Backup i gang...',
            'backup_complete': 'Backup fuldført',
            'backup_failed': 'Backup fejlede',
            'source': 'Kilde',
            'destination': 'Destination',
            'exclude': 'Ekskluder',
            'about_title': 'Om',
            'developer': 'Udvikler',
            'email': 'Email',
            'thanks': 'Dette værktøj blev skabt for at hjælpe folk med at bruge Linux nemmere.\nTak fordi du er en del af Open Source familien!',
            'donate_sentence': 'Ingen øl, ingen kode. Støt venligst en tørstig programmør!',
            'donate_button': 'Doner Ølpenge',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontonavn',
            'account_name': 'Hr. Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Succes',
            'error': 'Fejl',
            'settings_applied': 'Indstillinger anvendt succesfuldt!',
            'command_failed': 'Kommando fejlede: {}',
            'need_sudo': 'Administratorrettigheder kræves',
            'no_ytdlp': 'yt-dlp ikke fundet. Installer det venligst først.',
            'app_manager': 'App Manager',
            'app_manager_title': 'Administrer Installerede Applikationer',
            'app_search_hint': '🔍  Søg på app-navn...',
            'app_col_name': 'App Navn',
            'app_col_version': 'Version',
            'app_col_desc': 'Beskrivelse',
            'app_uninstall': '🗑  Afinstaller',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Indlæser applikationer...',
            'app_count': 'Installerede Apps',
            'app_reload': '🔄  Genindlæs',
            'app_confirm_uninstall': 'Bekræft Afinstallation',
            'app_confirm_msg': 'Afinstaller "{}" fra systemet?\n\nDenne handling kan ikke fortrydes.',
            'app_uninstalling': 'Afinstallerer {}...',
            'app_uninstall_ok': 'Succesfuldt afinstalleret {}',
            'app_uninstall_fail': 'Afinstallation fejlede:\n{}',
            'app_select_first': 'Vælg venligst en applikation først',
            'app_info_title': 'App Information',
        }

        # nb
        strings_nb = {
            'window_title': 'Geng Innstillingsverktøy v2.0.6',
            'home': 'Hjem',
            'keyboard': 'Tastatur & Språk',
            'system_tools': 'Systemverktøy',
            'network': 'Nettverk',
            'entertainment': 'Underholdning',
            'theme': 'Tema',
            'backup': 'Sikkerhetskopi',
            'about': 'Om',
            'navigation': 'NAVIGASJON',
            'welcome': 'Velkommen til Geng Innstillingsverktøy',
            'current_user': 'Nåværende bruker',
            'hostname': 'Vertsnavn',
            'home_desc': 'Din alt-i-ett konfigurasjonsverktøykasse for Linux Mint Cinnamon 22.3.\nJuster enkelt hurtigtaster, administrer apper, rydd opp i systemet, last ned media og mer.\nVelg en kategori fra sidepanelet for å starte — alt er bare et klikk unna!',
            'keyboard_title': 'Tastatur- og språkinnstillinger',
            'grave_title': 'Bytt språk med grav aksent (~)',
            'grave_desc': 'Bruk grav aksent-tasten for å bytte inndatametoder',
            'alt_shift_title': 'Bytt språk med Alt+Shift',
            'alt_shift_desc': 'Bruk Alt + Shift-tastene for å bytte inndatametoder',
            'custom_key_title': 'Egendefinert hurtigtast',
            'custom_key_desc': 'Trykk på knappen under for å fange ønsket tastekombinasjon',
            'capture_key': 'Fang tast',
            'apply_now': 'Bruk nå',
            'system_title': 'Systemadministrasjonsverktøy',
            'clean_system': 'Rydd opp søppel filer',
            'clean_system_desc': 'Fjern ubrukte pakker og tøm hurtigbuffer',
            'clear_ram': 'Tøm RAM/Hurtigbuffer',
            'clear_ram_desc': 'Tøm systemminnets hurtigbuffer (sync && drop_caches)',
            'driver_manager': 'Driverbehandling',
            'driver_manager_desc': 'Åpne Driverbehandling for å installere/fjerne drivere',
            'flatpak': 'Administrer Flatpak',
            'flatpak_desc': 'Oppdater Flatpak og administrer applikasjoner',
            'apt_repair': 'APT Reparasjon',
            'apt_repair_desc': 'Reparer ødelagte pakker og oppdater lister',
            'system_monitor': 'Systemovervåkning',
            'system_monitor_desc': 'Åpne systemovervåkningsverktøy',
            'network_title': 'Nettverksadministrasjon',
            'network_status': 'Nettverksstatus',
            'refresh': 'Oppdater',
            'restart_network': 'Start nettverk på nytt',
            'flush_dns': 'Tøm DNS',
            'renew_dhcp': 'Forny DHCP',
            'interfaces': 'Nettverksgrensesnitt',
            'connections': 'Tilkoblinger',
            'entertainment_title': 'Underholdning',
            'install_steam': 'Installer Steam',
            'install_steam_desc': 'Installer Steam for spill',
            'install_wine': 'Installer Wine',
            'install_wine_desc': 'Installer Wine for å kjøre Windows-programmer',
            'download_media': 'Last ned video/lyd',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Lyd M4A',
            'download': 'Last ned',
            'install_ytdlp': 'Installer yt-dlp',
            'theme_title': 'Tematilpasning',
            'dark_mode': 'Mørk modus',
            'light_mode': 'Lys modus',
            'mint_y': 'Mint-Y (Lys)',
            'mint_y_dark': 'Mint-Y-Mørk',
            'mint_y_dark_aqua': 'Mint-Y-Mørk-Aqua',
            'apply_theme': 'Bruk tema',
            'backup_title': 'Datasikkerhetskopiering',
            'select_drive': 'Velg destinasjonsstasjon',
            'backup_now': 'Start sikkerhetskopiering',
            'backup_progress': 'Sikkerhetskopierer...',
            'backup_complete': 'Sikkerhetskopiering fullført',
            'backup_failed': 'Sikkerhetskopiering mislyktes',
            'source': 'Kilde',
            'destination': 'Destinasjon',
            'exclude': 'Ekskluder',
            'about_title': 'Om',
            'developer': 'Utvikler',
            'email': 'E-post',
            'thanks': 'Dette verktøyet ble laget for å hjelpe folk med å bruke Linux enklere.\nTakk for at du er en del av Open Source-familien!',
            'donate_sentence': 'Ingen øl, ingen kode. Vennligst støtt en tørst programmerer!',
            'donate_button': 'Doner ølpenger',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontonavn',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Suksess',
            'error': 'Feil',
            'settings_applied': 'Innstillinger brukt vellykket!',
            'command_failed': 'Kommando mislyktes: {}',
            'need_sudo': 'Administratorrettigheter kreves',
            'no_ytdlp': 'yt-dlp ikke funnet. Vennligst installer det først.',
            'app_manager': 'Appbehandling',
            'app_manager_title': 'Administrer installerte applikasjoner',
            'app_search_hint': '🔍  Søk etter appnavn...',
            'app_col_name': 'Appnavn',
            'app_col_version': 'Versjon',
            'app_col_desc': 'Beskrivelse',
            'app_uninstall': '🗑  Avinstaller',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Laster applikasjoner...',
            'app_count': 'Installerte apper',
            'app_reload': '🔄  Last inn på nytt',
            'app_confirm_uninstall': 'Bekreft avinstallasjon',
            'app_confirm_msg': 'Avinstaller "{}" fra systemet?\n\nDenne handlingen kan ikke angres.',
            'app_uninstalling': 'Avinstallerer {}...',
            'app_uninstall_ok': 'Vellykket avinstallasjon av {}',
            'app_uninstall_fail': 'Avinstallasjon mislyktes:\n{}',
            'app_select_first': 'Vennligst velg en applikasjon først',
            'app_info_title': 'Appinformasjon',
        }

        # cs
        strings_cs = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Domů',
            'keyboard': 'Klávesnice a jazyk',
            'system_tools': 'Nástroje systému',
            'network': 'Síť',
            'entertainment': 'Zábava',
            'theme': 'Téma',
            'backup': 'Záloha',
            'about': 'O aplikaci',
            'navigation': 'NAVIGACE',
            'welcome': 'Vítejte v Geng Settings Tools',
            'current_user': 'Aktuální uživatel',
            'hostname': 'Název počítače',
            'home_desc': 'Vaše vše-v-jednom konfigurační sada nástrojů pro Linux Mint Cinnamon 22.3.\nSnadno upravujte klávesové zkratky, spravujte aplikace, čistěte systém, stahujte média a další.\nVyberte kategorii ze sidebaru a začněte — vše máte na dosah jediného kliknutí!',
            'keyboard_title': 'Nastavení klávesnice a jazyka',
            'grave_title': 'Přepínání jazyka pomocí klávesy Grave Accent (~)',
            'grave_desc': 'Použijte klávesu Grave Accent pro přepínání vstupních metod',
            'alt_shift_title': 'Přepínání jazyka pomocí Alt+Shift',
            'alt_shift_desc': 'Použijte klávesy Alt + Shift k přepínání vstupních metod',
            'custom_key_title': 'Vlastní klávesová zkratka',
            'custom_key_desc': 'Stiskněte tlačítko níže pro zachycení požadované kombinace kláves',
            'capture_key': 'Zachytit klávesu',
            'apply_now': 'Použít nyní',
            'system_title': 'Nástroje pro správu systému',
            'clean_system': 'Vyčistit nepotřebné soubory',
            'clean_system_desc': 'Odstraňte nepoužívané balíčky a vyčistěte cache',
            'clear_ram': 'Vyčistit RAM/Cache',
            'clear_ram_desc': 'Vyčistit paměťový cache systému (sync && drop_caches)',
            'driver_manager': 'Správce ovladačů',
            'driver_manager_desc': 'Otevřít správce ovladačů pro instalaci/odebrání ovladačů',
            'flatpak': 'Spravovat Flatpak',
            'flatpak_desc': 'Aktualizovat Flatpak a spravovat aplikace',
            'apt_repair': 'Oprava APT',
            'apt_repair_desc': 'Opravit poškozené balíčky a aktualizovat seznamy',
            'system_monitor': 'Sledování systému',
            'system_monitor_desc': 'Otevřít nástroj pro sledování systému',
            'network_title': 'Správa sítě',
            'network_status': 'Stav sítě',
            'refresh': 'Aktualizovat',
            'restart_network': 'Restartovat síť',
            'flush_dns': 'Vyprázdnit DNS',
            'renew_dhcp': 'Obnovit DHCP',
            'interfaces': 'Síťové rozhraní',
            'connections': 'Připojení',
            'entertainment_title': 'Zábava',
            'install_steam': 'Nainstalovat Steam',
            'install_steam_desc': 'Nainstalovat Steam pro hry',
            'install_wine': 'Nainstalovat Wine',
            'install_wine_desc': 'Nainstalovat Wine pro spuštění Windows programů',
            'download_media': 'Stáhnout video/audio',
            'url_label': 'URL',
            'format_label': 'Formát',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Stáhnout',
            'install_ytdlp': 'Nainstalovat yt-dlp',
            'theme_title': 'Přizpůsobení tématu',
            'dark_mode': 'Tmavý režim',
            'light_mode': 'Světlý režim',
            'mint_y': 'Mint-Y (světlý)',
            'mint_y_dark': 'Mint-Y-tmavý',
            'mint_y_dark_aqua': 'Mint-Y-tmavý-aqua',
            'apply_theme': 'Použít téma',
            'backup_title': 'Zálohování dat',
            'select_drive': 'Vyberte cílový disk',
            'backup_now': 'Spustit zálohu',
            'backup_progress': 'Probíhá zálohování...',
            'backup_complete': 'Záloha dokončena',
            'backup_failed': 'Záloha se nezdařila',
            'source': 'Zdroj',
            'destination': 'Cíl',
            'exclude': 'Vyloučit',
            'about_title': 'O aplikaci',
            'developer': 'Vývojář',
            'email': 'Email',
            'thanks': 'Tento nástroj byl vytvořen, aby pomohl lidem snadněji používat Linux.\nDěkujeme, že jste součástí rodiny Open Source!',
            'donate_sentence': 'Bez piva není kód. Podpořte prosím žíznivého programátora!',
            'donate_button': 'Darujte peníze na pivo',
            'bank_label': 'Banka',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Jméno účtu',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Číslo účtu',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Úspěch',
            'error': 'Chyba',
            'settings_applied': 'Nastavení úspěšně použito!',
            'command_failed': 'Příkaz se nezdařil: {}',
            'need_sudo': 'Vyžadována oprávnění správce',
            'no_ytdlp': 'yt-dlp nebyl nalezen. Nejprve jej prosím nainstalujte.',
            'app_manager': 'Správce aplikací',
            'app_manager_title': 'Správa nainstalovaných aplikací',
            'app_search_hint': '🔍  Hledat název aplikace...',
            'app_col_name': 'Název aplikace',
            'app_col_version': 'Verze',
            'app_col_desc': 'Popis',
            'app_uninstall': '🗑  Odinstalovat',
            'app_info': 'ℹ  Informace',
            'app_loading': '⏳  Načítání aplikací...',
            'app_count': 'Nainstalované aplikace',
            'app_reload': '🔄  Znovu načíst',
            'app_confirm_uninstall': 'Potvrzení odinstalace',
            'app_confirm_msg': 'Odinstalovat "{}" ze systému?\n\nTuto akci nelze vrátit zpět.',
            'app_uninstalling': 'Probíhá odinstalace {}...',
            'app_uninstall_ok': 'Úspěšně odinstalováno {}',
            'app_uninstall_fail': 'Odinstalace selhala:\n{}',
            'app_select_first': 'Nejprve vyberte aplikaci',
            'app_info_title': 'Informace o aplikaci',
        }

        # pl
        strings_pl = {
            'window_title': 'Narzędzia Ustawień Geng v2.0.6',
            'home': 'Strona główna',
            'keyboard': 'Klawiatura i Język',
            'system_tools': 'Narzędzia Systemowe',
            'network': 'Sieć',
            'entertainment': 'Rozrywka',
            'theme': 'Motyw',
            'backup': 'Kopia zapasowa',
            'about': 'O programie',
            'navigation': 'NAWIGACJA',
            'welcome': 'Witamy w Narzędziach Ustawień Geng',
            'current_user': 'Aktualny użytkownik',
            'hostname': 'Nazwa hosta',
            'home_desc': 'Twoje wielofunkcyjne narzędzie konfiguracyjne dla Linux Mint Cinnamon 22.3.\nŁatwo dostosuj skróty klawiszowe, zarządzaj aplikacjami, czyść system, pobieraj media i więcej.\nWybierz kategorię z paska bocznego, aby rozpocząć — wszystko jest na wyciągnięcie kliknięcia!',
            'keyboard_title': 'Ustawienia Klawiatury i Języka',
            'grave_title': 'Przełącz język klawiszem Akcentu Greckiego (~)',
            'grave_desc': 'Użyj klawisza Akcentu Greckiego do przełączania metod wprowadzania',
            'alt_shift_title': 'Przełącz język za pomocą Alt+Shift',
            'alt_shift_desc': 'Użyj klawiszy Alt + Shift do przełączania metod wprowadzania',
            'custom_key_title': 'Własne przypisanie klawisza',
            'custom_key_desc': 'Naciśnij przycisk poniżej, aby wychwycić żądaną kombinację klawiszy',
            'capture_key': 'Wychwyć klawisz',
            'apply_now': 'Zastosuj teraz',
            'system_title': 'Narzędzia zarządzania systemem',
            'clean_system': 'Wyczyść niepotrzebne pliki',
            'clean_system_desc': 'Usuń nieużywane pakiety i wyczyść pamięć podręczną',
            'clear_ram': 'Wyczyść RAM/Pamięć podręczną',
            'clear_ram_desc': 'Wyczyść pamięć podręczną systemu (sync && drop_caches)',
            'driver_manager': 'Menedżer sterowników',
            'driver_manager_desc': 'Otwórz Menedżera sterowników, aby instalować/usunąć sterowniki',
            'flatpak': 'Zarządzaj Flatpak',
            'flatpak_desc': 'Aktualizuj Flatpak i zarządzaj aplikacjami',
            'apt_repair': 'Naprawa APT',
            'apt_repair_desc': 'Napraw uszkodzone pakiety i aktualizuj listy',
            'system_monitor': 'Monitor systemu',
            'system_monitor_desc': 'Otwórz narzędzie do monitorowania systemu',
            'network_title': 'Zarządzanie siecią',
            'network_status': 'Status sieci',
            'refresh': 'Odśwież',
            'restart_network': 'Restartuj sieć',
            'flush_dns': 'Wyczyść DNS',
            'renew_dhcp': 'Odnów DHCP',
            'interfaces': 'Interfejsy sieciowe',
            'connections': 'Połączenia',
            'entertainment_title': 'Rozrywka',
            'install_steam': 'Zainstaluj Steam',
            'install_steam_desc': 'Zainstaluj Steam do grania',
            'install_wine': 'Zainstaluj Wine',
            'install_wine_desc': 'Zainstaluj Wine, aby uruchamiać programy Windows',
            'download_media': 'Pobierz wideo/audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Wideo MP4',
            'audio': 'Dźwięk M4A',
            'download': 'Pobierz',
            'install_ytdlp': 'Zainstaluj yt-dlp',
            'theme_title': 'Dostosowanie motywu',
            'dark_mode': 'Tryb ciemny',
            'light_mode': 'Tryb jasny',
            'mint_y': 'Mint-Y (jasny)',
            'mint_y_dark': 'Mint-Y-Ciemny',
            'mint_y_dark_aqua': 'Mint-Y-Ciemny-Aqua',
            'apply_theme': 'Zastosuj motyw',
            'backup_title': 'Kopia zapasowa danych',
            'select_drive': 'Wybierz dysk docelowy',
            'backup_now': 'Rozpocznij tworzenie kopii',
            'backup_progress': 'Tworzenie kopii zapasowej...',
            'backup_complete': 'Kopia zapasowa ukończona',
            'backup_failed': 'Tworzenie kopii zapasowej nie powiodło się',
            'source': 'Źródło',
            'destination': 'Cel',
            'exclude': 'Wyklucz',
            'about_title': 'O programie',
            'developer': 'Deweloper',
            'email': 'E-mail',
            'thanks': 'To narzędzie zostało stworzone, aby pomóc ludziom łatwiej korzystać z Linux.\nDziękujemy, że jesteś częścią rodziny Open Source!',
            'donate_sentence': 'Bez piwa, bez kodu. Prosimy, wesprzyj spragnionego programistę!',
            'donate_button': 'Przekaż na piwo',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nazwa konta',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Numer konta',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Sukces',
            'error': 'Błąd',
            'settings_applied': 'Ustawienia zostały pomyślnie zastosowane!',
            'command_failed': 'Polecenie nie powiodło się: {}',
            'need_sudo': 'Wymagane uprawnienia administratora',
            'no_ytdlp': 'Nie znaleziono yt-dlp. Proszę najpierw zainstalować.',
            'app_manager': 'Menedżer aplikacji',
            'app_manager_title': 'Zarządzaj zainstalowanymi aplikacjami',
            'app_search_hint': '🔍  Wyszukaj nazwę aplikacji...',
            'app_col_name': 'Nazwa aplikacji',
            'app_col_version': 'Wersja',
            'app_col_desc': 'Opis',
            'app_uninstall': '🗑  Odinstaluj',
            'app_info': 'ℹ  Informacje',
            'app_loading': '⏳  Ładowanie aplikacji...',
            'app_count': 'Zainstalowane aplikacje',
            'app_reload': '🔄  Przeładuj',
            'app_confirm_uninstall': 'Potwierdź odinstalowanie',
            'app_confirm_msg': 'Odinstalować "{}" z systemu?\n\nTej akcji nie można cofnąć.',
            'app_uninstalling': 'Odinstalowywanie {}...',
            'app_uninstall_ok': 'Pomyślnie odinstalowano {}',
            'app_uninstall_fail': 'Odinstalowanie nie powiodło się:\n{}',
            'app_select_first': 'Najpierw wybierz aplikację',
            'app_info_title': 'Informacje o aplikacji',
        }

        # de-AT
        strings_de_at = {
            'window_title': 'Geng Einstellungen Tools v2.0.6',
            'home': 'Startseite',
            'keyboard': 'Tastatur & Sprache',
            'system_tools': 'Systemwerkzeuge',
            'network': 'Netzwerk',
            'entertainment': 'Unterhaltung',
            'theme': 'Design',
            'backup': 'Sicherung',
            'about': 'Über',
            'navigation': 'NAVIGATION',
            'welcome': 'Willkommen bei Geng Einstellungen Tools',
            'current_user': 'Aktueller Benutzer',
            'hostname': 'Hostname',
            'home_desc': 'Ihr All-in-One Konfigurationstool für Linux Mint Cinnamon 22.3.\nPassen Sie Tastenkombinationen einfach an, verwalten Sie Apps, bereinigen Sie Ihr System, laden Sie Medien herunter und mehr.\nWählen Sie eine Kategorie aus der Seitenleiste, um zu starten – alles ist nur einen Klick entfernt!',
            'keyboard_title': 'Tastatur- & Spracheinstellungen',
            'grave_title': 'Sprache mit Akzentzeichen (~) umschalten',
            'grave_desc': 'Verwenden Sie die Akzentzeichen-Taste, um Eingabemethoden zu wechseln',
            'alt_shift_title': 'Sprache mit Alt+Shift wechseln',
            'alt_shift_desc': 'Nutzen Sie Alt + Shift, um Eingabemethoden zu wechseln',
            'custom_key_title': 'Benutzerdefinierte Tastenkombination',
            'custom_key_desc': 'Drücken Sie die Taste unten, um die gewünschte Tastenkombination zu erfassen',
            'capture_key': 'Taste erfassen',
            'apply_now': 'Jetzt anwenden',
            'system_title': 'Systemverwaltungswerkzeuge',
            'clean_system': 'Junk-Dateien bereinigen',
            'clean_system_desc': 'Entfernen Sie ungenutzte Pakete und leeren Sie den Cache',
            'clear_ram': 'RAM/Cache leeren',
            'clear_ram_desc': 'Systemarbeitsspeicher-Cache leeren (sync && drop_caches)',
            'driver_manager': 'Treiber-Manager',
            'driver_manager_desc': 'Treiber-Manager öffnen, um Treiber zu installieren/entfernen',
            'flatpak': 'Flatpak verwalten',
            'flatpak_desc': 'Flatpak aktualisieren und Anwendungen verwalten',
            'apt_repair': 'APT-Reparatur',
            'apt_repair_desc': 'Beschädigte Pakete reparieren und Listen aktualisieren',
            'system_monitor': 'Systemmonitor',
            'system_monitor_desc': 'Systemüberwachungstool öffnen',
            'network_title': 'Netzwerkverwaltung',
            'network_status': 'Netzwerkstatus',
            'refresh': 'Aktualisieren',
            'restart_network': 'Netzwerk neu starten',
            'flush_dns': 'DNS leeren',
            'renew_dhcp': 'DHCP erneuern',
            'interfaces': 'Netzwerkschnittstellen',
            'connections': 'Verbindungen',
            'entertainment_title': 'Unterhaltung',
            'install_steam': 'Steam installieren',
            'install_steam_desc': 'Steam für Spiele installieren',
            'install_wine': 'Wine installieren',
            'install_wine_desc': 'Wine installieren, um Windows-Programme auszuführen',
            'download_media': 'Video/Audio herunterladen',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Herunterladen',
            'install_ytdlp': 'yt-dlp installieren',
            'theme_title': 'Theme-Anpassung',
            'dark_mode': 'Dunkler Modus',
            'light_mode': 'Heller Modus',
            'mint_y': 'Mint-Y (Hell)',
            'mint_y_dark': 'Mint-Y-Dunkel',
            'mint_y_dark_aqua': 'Mint-Y-Dunkel-Aqua',
            'apply_theme': 'Theme anwenden',
            'backup_title': 'Datensicherung',
            'select_drive': 'Zieldatenträger auswählen',
            'backup_now': 'Sicherung starten',
            'backup_progress': 'Sicherung läuft...',
            'backup_complete': 'Sicherung abgeschlossen',
            'backup_failed': 'Sicherung fehlgeschlagen',
            'source': 'Quelle',
            'destination': 'Ziel',
            'exclude': 'Ausschließen',
            'about_title': 'Über',
            'developer': 'Entwickler',
            'email': 'E-Mail',
            'thanks': 'Dieses Tool wurde erstellt, um Menschen die Nutzung von Linux zu erleichtern.\nDanke, dass Sie Teil der Open-Source-Familie sind!',
            'donate_sentence': 'Kein Bier, kein Code. Bitte unterstützen Sie einen durstigen Programmierer!',
            'donate_button': 'Biergeld spenden',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontoinhaber',
            'account_name': 'Herr Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Erfolg',
            'error': 'Fehler',
            'settings_applied': 'Einstellungen erfolgreich angewendet!',
            'command_failed': 'Befehl fehlgeschlagen: {}',
            'need_sudo': 'Administratorrechte erforderlich',
            'no_ytdlp': 'yt-dlp nicht gefunden. Bitte zuerst installieren.',
            'app_manager': 'App-Manager',
            'app_manager_title': 'Installierte Anwendungen verwalten',
            'app_search_hint': '🔍  App-Namen suchen...',
            'app_col_name': 'App-Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Beschreibung',
            'app_uninstall': '🗑  Deinstallieren',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Anwendungen werden geladen...',
            'app_count': 'Installierte Apps',
            'app_reload': '🔄  Neu laden',
            'app_confirm_uninstall': 'Deinstallation bestätigen',
            'app_confirm_msg': '„{}“ vom System deinstallieren?\n\nDieser Vorgang kann nicht rückgängig gemacht werden.',
            'app_uninstalling': 'Deinstalliere {}...',
            'app_uninstall_ok': '{} erfolgreich deinstalliert',
            'app_uninstall_fail': 'Deinstallation fehlgeschlagen:\n{}',
            'app_select_first': 'Bitte zuerst eine Anwendung auswählen',
            'app_info_title': 'App-Informationen',
        }

        # en-AU
        strings_en_au = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Home',
            'keyboard': 'Keyboard & Language',
            'system_tools': 'System Tools',
            'network': 'Network',
            'entertainment': 'Entertainment',
            'theme': 'Theme',
            'backup': 'Backup',
            'about': 'About',
            'navigation': 'NAVIGATION',
            'welcome': 'Welcome to Geng Settings Tools',
            'current_user': 'Current user',
            'hostname': 'Hostname',
            'home_desc': 'Your all‑in‑one configuration toolbox for Linux Mint Cinnamon 22.3.\nEasily tweak keyboard shortcuts, manage apps, clean your system, download media, and more.\nSelect a category from the sidebar to get started — everything is just a click away!',
            'keyboard_title': 'Keyboard & Language Settings',
            'grave_title': 'Switch language with Grave Accent (~)',
            'grave_desc': 'Use Grave Accent key to switch input methods',
            'alt_shift_title': 'Switch language with Alt+Shift',
            'alt_shift_desc': 'Use Alt + Shift keys to switch input methods',
            'custom_key_title': 'Custom keybinding',
            'custom_key_desc': 'Press the button below to capture desired key combination',
            'capture_key': 'Capture Key',
            'apply_now': 'Apply Now',
            'system_title': 'System Management Tools',
            'clean_system': 'Clean Junk Files',
            'clean_system_desc': 'Remove unused packages and clear cache',
            'clear_ram': 'Clear RAM/Cache',
            'clear_ram_desc': 'Clear system memory cache (sync && drop_caches)',
            'driver_manager': 'Driver Manager',
            'driver_manager_desc': 'Open Driver Manager to install/remove drivers',
            'flatpak': 'Manage Flatpak',
            'flatpak_desc': 'Update Flatpak and manage applications',
            'apt_repair': 'APT Repair',
            'apt_repair_desc': 'Repair broken packages and update lists',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'Open system monitoring tool',
            'network_title': 'Network Management',
            'network_status': 'Network Status',
            'refresh': 'Refresh',
            'restart_network': 'Restart Network',
            'flush_dns': 'Flush DNS',
            'renew_dhcp': 'Renew DHCP',
            'interfaces': 'Network Interfaces',
            'connections': 'Connections',
            'entertainment_title': 'Entertainment',
            'install_steam': 'Install Steam',
            'install_steam_desc': 'Install Steam for gaming',
            'install_wine': 'Install Wine',
            'install_wine_desc': 'Install Wine to run Windows programmes',
            'download_media': 'Download Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Download',
            'install_ytdlp': 'Install yt-dlp',
            'theme_title': 'Theme Customisation',
            'dark_mode': 'Dark Mode',
            'light_mode': 'Light Mode',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'Apply Theme',
            'backup_title': 'Data Backup',
            'select_drive': 'Select destination drive',
            'backup_now': 'Start Backup',
            'backup_progress': 'Backing up...',
            'backup_complete': 'Backup Complete',
            'backup_failed': 'Backup Failed',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclude',
            'about_title': 'About',
            'developer': 'Developer',
            'email': 'Email',
            'thanks': 'This tool was created to help people use Linux more easily.\nThank you for being part of the Open Source family!',
            'donate_sentence': 'No beer, no code. Please support a thirsty programmer!',
            'donate_button': 'Donate Beer Money',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Account Name',
            'account_name': 'Mr Thammasorn Musikapan',
            'account_number_label': 'Account Number',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Success',
            'error': 'Error',
            'settings_applied': 'Settings applied successfully!',
            'command_failed': 'Command failed: {}',
            'need_sudo': 'Administrator privileges required',
            'no_ytdlp': 'yt-dlp not found. Please install it first.',
            'app_manager': 'App Manager',
            'app_manager_title': 'Manage Installed Applications',
            'app_search_hint': '🔍  Search app name...',
            'app_col_name': 'App Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑  Uninstall',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Loading applications...',
            'app_count': 'Installed Apps',
            'app_reload': '🔄  Reload',
            'app_confirm_uninstall': 'Confirm Uninstall',
            'app_confirm_msg': 'Uninstall "{}" from system?\n\nThis action cannot be undone.',
            'app_uninstalling': 'Uninstalling {}...',
            'app_uninstall_ok': 'Successfully uninstalled {}',
            'app_uninstall_fail': 'Uninstall failed:\n{}',
            'app_select_first': 'Please select an application first',
            'app_info_title': 'App Information',
        }

        # en-GB
        strings_en_gb = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Home',
            'keyboard': 'Keyboard & Language',
            'system_tools': 'System Tools',
            'network': 'Network',
            'entertainment': 'Entertainment',
            'theme': 'Theme',
            'backup': 'Backup',
            'about': 'About',
            'navigation': 'NAVIGATION',
            'welcome': 'Welcome to Geng Settings Tools',
            'current_user': 'Current user',
            'hostname': 'Hostname',
            'home_desc': 'Your all-in-one configuration toolbox for Linux Mint Cinnamon 22.3.\nEasily tweak keyboard shortcuts, manage apps, clean your system, download media, and more.\nSelect a category from the sidebar to get started — everything is just a click away!',
            'keyboard_title': 'Keyboard & Language Settings',
            'grave_title': 'Switch language with Grave Accent (~)',
            'grave_desc': 'Use Grave Accent key to switch input methods',
            'alt_shift_title': 'Switch language with Alt+Shift',
            'alt_shift_desc': 'Use Alt + Shift keys to switch input methods',
            'custom_key_title': 'Custom keybinding',
            'custom_key_desc': 'Press the button below to capture desired key combination',
            'capture_key': 'Capture Key',
            'apply_now': 'Apply Now',
            'system_title': 'System Management Tools',
            'clean_system': 'Clean Junk Files',
            'clean_system_desc': 'Remove unused packages and clear cache',
            'clear_ram': 'Clear RAM/Cache',
            'clear_ram_desc': 'Clear system memory cache (sync && drop_caches)',
            'driver_manager': 'Driver Manager',
            'driver_manager_desc': 'Open Driver Manager to install/remove drivers',
            'flatpak': 'Manage Flatpak',
            'flatpak_desc': 'Update Flatpak and manage applications',
            'apt_repair': 'APT Repair',
            'apt_repair_desc': 'Repair broken packages and update lists',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'Open system monitoring tool',
            'network_title': 'Network Management',
            'network_status': 'Network Status',
            'refresh': 'Refresh',
            'restart_network': 'Restart Network',
            'flush_dns': 'Flush DNS',
            'renew_dhcp': 'Renew DHCP',
            'interfaces': 'Network Interfaces',
            'connections': 'Connections',
            'entertainment_title': 'Entertainment',
            'install_steam': 'Install Steam',
            'install_steam_desc': 'Install Steam for gaming',
            'install_wine': 'Install Wine',
            'install_wine_desc': 'Install Wine to run Windows programmes',
            'download_media': 'Download Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Download',
            'install_ytdlp': 'Install yt-dlp',
            'theme_title': 'Theme Customisation',
            'dark_mode': 'Dark Mode',
            'light_mode': 'Light Mode',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'Apply Theme',
            'backup_title': 'Data Backup',
            'select_drive': 'Select destination drive',
            'backup_now': 'Start Backup',
            'backup_progress': 'Backing up...',
            'backup_complete': 'Backup Complete',
            'backup_failed': 'Backup Failed',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclude',
            'about_title': 'About',
            'developer': 'Developer',
            'email': 'Email',
            'thanks': 'This tool was created to help people use Linux more easily.\nThank you for being part of the Open Source family!',
            'donate_sentence': 'No beer, no code. Please support a thirsty programmer!',
            'donate_button': 'Donate Beer Money',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Account Name',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Account Number',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Success',
            'error': 'Error',
            'settings_applied': 'Settings applied successfully!',
            'command_failed': 'Command failed: {}',
            'need_sudo': 'Administrator privileges required',
            'no_ytdlp': 'yt-dlp not found. Please install it first.',
            'app_manager': 'App Manager',
            'app_manager_title': 'Manage Installed Applications',
            'app_search_hint': '🔍  Search app name...',
            'app_col_name': 'App Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑  Uninstall',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Loading applications...',
            'app_count': 'Installed Apps',
            'app_reload': '🔄  Reload',
            'app_confirm_uninstall': 'Confirm Uninstall',
            'app_confirm_msg': 'Uninstall "{}" from system?\n\nThis action cannot be undone.',
            'app_uninstalling': 'Uninstalling {}...',
            'app_uninstall_ok': 'Successfully uninstalled {}',
            'app_uninstall_fail': 'Uninstall failed:\n{}',
            'app_select_first': 'Please select an application first',
            'app_info_title': 'App Information',
        }

        # es
        strings_es = {
            'window_title': 'Herramientas de Configuración Geng v2.0.6',
            'home': 'Inicio',
            'keyboard': 'Teclado y Idioma',
            'system_tools': 'Herramientas del Sistema',
            'network': 'Red',
            'entertainment': 'Entretenimiento',
            'theme': 'Tema',
            'backup': 'Respaldo',
            'about': 'Acerca de',
            'navigation': 'NAVEGACIÓN',
            'welcome': 'Bienvenido a Herramientas de Configuración Geng',
            'current_user': 'Usuario actual',
            'hostname': 'Nombre del equipo',
            'home_desc': 'Tu caja de herramientas de configuración todo en uno para Linux Mint Cinnamon 22.3.\nAjusta fácilmente los atajos de teclado, administra aplicaciones, limpia tu sistema, descarga medios y más.\nSelecciona una categoría en la barra lateral para comenzar — ¡todo está a un clic!',
            'keyboard_title': 'Configuración de Teclado e Idioma',
            'grave_title': 'Cambiar idioma con Acento Grave (~)',
            'grave_desc': 'Usa la tecla de Acento Grave para cambiar métodos de entrada',
            'alt_shift_title': 'Cambiar idioma con Alt+Shift',
            'alt_shift_desc': 'Usa las teclas Alt + Shift para cambiar métodos de entrada',
            'custom_key_title': 'Asignación de tecla personalizada',
            'custom_key_desc': 'Presiona el botón abajo para capturar la combinación de teclas deseada',
            'capture_key': 'Capturar Tecla',
            'apply_now': 'Aplicar Ahora',
            'system_title': 'Herramientas de Gestión del Sistema',
            'clean_system': 'Limpiar Archivos Inútiles',
            'clean_system_desc': 'Eliminar paquetes no usados y limpiar caché',
            'clear_ram': 'Limpiar RAM/Caché',
            'clear_ram_desc': 'Limpiar caché de memoria del sistema (sync && drop_caches)',
            'driver_manager': 'Administrador de Controladores',
            'driver_manager_desc': 'Abrir el Administrador de Controladores para instalar/eliminar controladores',
            'flatpak': 'Gestionar Flatpak',
            'flatpak_desc': 'Actualizar Flatpak y administrar aplicaciones',
            'apt_repair': 'Reparar APT',
            'apt_repair_desc': 'Reparar paquetes rotos y actualizar listas',
            'system_monitor': 'Monitor del Sistema',
            'system_monitor_desc': 'Abrir herramienta de monitoreo del sistema',
            'network_title': 'Gestión de Red',
            'network_status': 'Estado de la Red',
            'refresh': 'Actualizar',
            'restart_network': 'Reiniciar Red',
            'flush_dns': 'Vaciar DNS',
            'renew_dhcp': 'Renovar DHCP',
            'interfaces': 'Interfaces de Red',
            'connections': 'Conexiones',
            'entertainment_title': 'Entretenimiento',
            'install_steam': 'Instalar Steam',
            'install_steam_desc': 'Instalar Steam para juegos',
            'install_wine': 'Instalar Wine',
            'install_wine_desc': 'Instalar Wine para ejecutar programas de Windows',
            'download_media': 'Descargar Video/Audio',
            'url_label': 'URL',
            'format_label': 'Formato',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Descargar',
            'install_ytdlp': 'Instalar yt-dlp',
            'theme_title': 'Personalización de Tema',
            'dark_mode': 'Modo Oscuro',
            'light_mode': 'Modo Claro',
            'mint_y': 'Mint-Y (Claro)',
            'mint_y_dark': 'Mint-Y-Oscuro',
            'mint_y_dark_aqua': 'Mint-Y-Oscuro-Aqua',
            'apply_theme': 'Aplicar Tema',
            'backup_title': 'Respaldo de Datos',
            'select_drive': 'Seleccionar unidad de destino',
            'backup_now': 'Iniciar Respaldo',
            'backup_progress': 'Respaldando...',
            'backup_complete': 'Respaldo Completo',
            'backup_failed': 'Respaldo Fallido',
            'source': 'Origen',
            'destination': 'Destino',
            'exclude': 'Excluir',
            'about_title': 'Acerca de',
            'developer': 'Desarrollador',
            'email': 'Correo electrónico',
            'thanks': 'Esta herramienta fue creada para ayudar a las personas a usar Linux más fácilmente.\n¡Gracias por ser parte de la familia de Código Abierto!',
            'donate_sentence': 'Sin cerveza, no hay código. ¡Por favor apoya a un programador sediento!',
            'donate_button': 'Donar Dinero para Cerveza',
            'bank_label': 'Banco',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nombre de la Cuenta',
            'account_name': 'Sr. Thammasorn Musikapan',
            'account_number_label': 'Número de Cuenta',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Éxito',
            'error': 'Error',
            'settings_applied': '¡Configuración aplicada con éxito!',
            'command_failed': 'Comando falló: {}',
            'need_sudo': 'Se requieren privilegios de administrador',
            'no_ytdlp': 'yt-dlp no encontrado. Por favor instálalo primero.',
            'app_manager': 'Administrador de Aplicaciones',
            'app_manager_title': 'Gestionar Aplicaciones Instaladas',
            'app_search_hint': '🔍  Buscar nombre de la app...',
            'app_col_name': 'Nombre de la App',
            'app_col_version': 'Versión',
            'app_col_desc': 'Descripción',
            'app_uninstall': '🗑  Desinstalar',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Cargando aplicaciones...',
            'app_count': 'Apps Instaladas',
            'app_reload': '🔄  Recargar',
            'app_confirm_uninstall': 'Confirmar Desinstalación',
            'app_confirm_msg': '¿Desinstalar "{}" del sistema?\n\nEsta acción no se puede deshacer.',
            'app_uninstalling': 'Desinstalando {}...',
            'app_uninstall_ok': 'Desinstalado exitosamente {}',
            'app_uninstall_fail': 'Error al desinstalar:\n{}',
            'app_select_first': 'Por favor selecciona una aplicación primero',
            'app_info_title': 'Información de la App',
        }

        # de-CH
        strings_de_ch = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Startseite',
            'keyboard': 'Tastatur & Sprache',
            'system_tools': 'Systemwerkzeuge',
            'network': 'Netzwerk',
            'entertainment': 'Unterhaltung',
            'theme': 'Thema',
            'backup': 'Backup',
            'about': 'Über',
            'navigation': 'NAVIGATION',
            'welcome': 'Willkommen bei Geng Settings Tools',
            'current_user': 'Aktueller Benutzer',
            'hostname': 'Hostname',
            'home_desc': 'Ihr All-in-One-Konfigurationstoolbox für Linux Mint Cinnamon 22.3.\nPassen Sie Tastenkombinationen einfach an, verwalten Sie Apps, reinigen Sie Ihr System, laden Sie Medien herunter und mehr.\nWählen Sie eine Kategorie aus der Seitenleiste, um zu starten — alles ist nur einen Klick entfernt!',
            'keyboard_title': 'Tastatur- & Spracheinstellungen',
            'grave_title': 'Sprache mit Gravis-Akzent (~) wechseln',
            'grave_desc': 'Verwenden Sie die Gravis-Taste, um Eingabemethoden zu wechseln',
            'alt_shift_title': 'Sprache mit Alt+Shift wechseln',
            'alt_shift_desc': 'Verwenden Sie die Tasten Alt + Shift, um Eingabemethoden zu wechseln',
            'custom_key_title': 'Benutzerdefinierte Tastenkombination',
            'custom_key_desc': 'Drücken Sie die untenstehende Taste, um die gewünschte Tastenkombination zu erfassen',
            'capture_key': 'Taste erfassen',
            'apply_now': 'Jetzt anwenden',
            'system_title': 'Systemverwaltungstools',
            'clean_system': 'Junk-Dateien bereinigen',
            'clean_system_desc': 'Entfernen Sie unbenutzte Pakete und leeren Sie den Cache',
            'clear_ram': 'RAM/Cache leeren',
            'clear_ram_desc': 'Systemspeicher-Cache leeren (sync && drop_caches)',
            'driver_manager': 'Treiberverwaltung',
            'driver_manager_desc': 'Öffnen Sie den Treiber-Manager, um Treiber zu installieren/entfernen',
            'flatpak': 'Flatpak verwalten',
            'flatpak_desc': 'Flatpak aktualisieren und Anwendungen verwalten',
            'apt_repair': 'APT-Reparatur',
            'apt_repair_desc': 'Beschädigte Pakete reparieren und Listen aktualisieren',
            'system_monitor': 'Systemmonitor',
            'system_monitor_desc': 'Öffnen Sie das Systemüberwachungstool',
            'network_title': 'Netzwerkverwaltung',
            'network_status': 'Netzwerkstatus',
            'refresh': 'Aktualisieren',
            'restart_network': 'Netzwerk neu starten',
            'flush_dns': 'DNS leeren',
            'renew_dhcp': 'DHCP erneuern',
            'interfaces': 'Netzwerkschnittstellen',
            'connections': 'Verbindungen',
            'entertainment_title': 'Unterhaltung',
            'install_steam': 'Steam installieren',
            'install_steam_desc': 'Installieren Sie Steam für Spiele',
            'install_wine': 'Wine installieren',
            'install_wine_desc': 'Installieren Sie Wine, um Windows-Programme auszuführen',
            'download_media': 'Video/Audio herunterladen',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Herunterladen',
            'install_ytdlp': 'yt-dlp installieren',
            'theme_title': 'Thema-Anpassung',
            'dark_mode': 'Dunkelmodus',
            'light_mode': 'Hellmodus',
            'mint_y': 'Mint-Y (Hell)',
            'mint_y_dark': 'Mint-Y-Dunkel',
            'mint_y_dark_aqua': 'Mint-Y-Dunkel-Aqua',
            'apply_theme': 'Thema anwenden',
            'backup_title': 'Daten-Backup',
            'select_drive': 'Ziel-Laufwerk auswählen',
            'backup_now': 'Backup starten',
            'backup_progress': 'Backup läuft...',
            'backup_complete': 'Backup abgeschlossen',
            'backup_failed': 'Backup fehlgeschlagen',
            'source': 'Quelle',
            'destination': 'Ziel',
            'exclude': 'Ausschliessen',
            'about_title': 'Über',
            'developer': 'Entwickler',
            'email': 'E-Mail',
            'thanks': 'Dieses Tool wurde entwickelt, um Menschen die Nutzung von Linux zu erleichtern.\nDanke, dass Sie Teil der Open-Source-Familie sind!',
            'donate_sentence': 'Kein Bier, kein Code. Bitte unterstützen Sie einen durstigen Programmierer!',
            'donate_button': 'Biergeld spenden',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Kontoinhaber',
            'account_name': 'Herr Thammasorn Musikapan',
            'account_number_label': 'Kontonummer',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Erfolg',
            'error': 'Fehler',
            'settings_applied': 'Einstellungen erfolgreich angewendet!',
            'command_failed': 'Befehl fehlgeschlagen: {}',
            'need_sudo': 'Administratorrechte erforderlich',
            'no_ytdlp': 'yt-dlp nicht gefunden. Bitte zuerst installieren.',
            'app_manager': 'Anwendungsmanager',
            'app_manager_title': 'Installierte Anwendungen verwalten',
            'app_search_hint': '🔍  App-Namen suchen...',
            'app_col_name': 'App-Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Beschreibung',
            'app_uninstall': '🗑  Deinstallieren',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Anwendungen werden geladen...',
            'app_count': 'Installierte Apps',
            'app_reload': '🔄  Neu laden',
            'app_confirm_uninstall': 'Deinstallation bestätigen',
            'app_confirm_msg': '„{}“ vom System deinstallieren?\n\nDiese Aktion kann nicht rückgängig gemacht werden.',
            'app_uninstalling': 'Deinstalliere {}...',
            'app_uninstall_ok': 'Erfolgreich deinstalliert: {}',
            'app_uninstall_fail': 'Deinstallation fehlgeschlagen:\n{}',
            'app_select_first': 'Bitte zuerst eine Anwendung auswählen',
            'app_info_title': 'App-Informationen',
        }

        # en-CA
        strings_en_ca = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Home',
            'keyboard': 'Keyboard & Language',
            'system_tools': 'System Tools',
            'network': 'Network',
            'entertainment': 'Entertainment',
            'theme': 'Theme',
            'backup': 'Backup',
            'about': 'About',
            'navigation': 'NAVIGATION',
            'welcome': 'Welcome to Geng Settings Tools',
            'current_user': 'Current user',
            'hostname': 'Hostname',
            'home_desc': 'Your all‑in‑one configuration toolbox for Linux Mint Cinnamon 22.3.\nEasily tweak keyboard shortcuts, manage apps, clean your system, download media, and more.\nSelect a category from the sidebar to get started — everything is just a click away!',
            'keyboard_title': 'Keyboard & Language Settings',
            'grave_title': 'Switch language with Grave Accent (~)',
            'grave_desc': 'Use Grave Accent key to switch input methods',
            'alt_shift_title': 'Switch language with Alt+Shift',
            'alt_shift_desc': 'Use Alt + Shift keys to switch input methods',
            'custom_key_title': 'Custom keybinding',
            'custom_key_desc': 'Press the button below to capture desired key combination',
            'capture_key': 'Capture Key',
            'apply_now': 'Apply Now',
            'system_title': 'System Management Tools',
            'clean_system': 'Clean Junk Files',
            'clean_system_desc': 'Remove unused packages and clear cache',
            'clear_ram': 'Clear RAM/Cache',
            'clear_ram_desc': 'Clear system memory cache (sync && drop_caches)',
            'driver_manager': 'Driver Manager',
            'driver_manager_desc': 'Open Driver Manager to install/remove drivers',
            'flatpak': 'Manage Flatpak',
            'flatpak_desc': 'Update Flatpak and manage applications',
            'apt_repair': 'APT Repair',
            'apt_repair_desc': 'Repair broken packages and update lists',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'Open system monitoring tool',
            'network_title': 'Network Management',
            'network_status': 'Network Status',
            'refresh': 'Refresh',
            'restart_network': 'Restart Network',
            'flush_dns': 'Flush DNS',
            'renew_dhcp': 'Renew DHCP',
            'interfaces': 'Network Interfaces',
            'connections': 'Connections',
            'entertainment_title': 'Entertainment',
            'install_steam': 'Install Steam',
            'install_steam_desc': 'Install Steam for gaming',
            'install_wine': 'Install Wine',
            'install_wine_desc': 'Install Wine to run Windows programs',
            'download_media': 'Download Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Download',
            'install_ytdlp': 'Install yt-dlp',
            'theme_title': 'Theme Customization',
            'dark_mode': 'Dark Mode',
            'light_mode': 'Light Mode',
            'mint_y': 'Mint-Y (Light)',
            'mint_y_dark': 'Mint-Y-Dark',
            'mint_y_dark_aqua': 'Mint-Y-Dark-Aqua',
            'apply_theme': 'Apply Theme',
            'backup_title': 'Data Backup',
            'select_drive': 'Select destination drive',
            'backup_now': 'Start Backup',
            'backup_progress': 'Backing up...',
            'backup_complete': 'Backup Complete',
            'backup_failed': 'Backup Failed',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclude',
            'about_title': 'About',
            'developer': 'Developer',
            'email': 'Email',
            'thanks': 'This tool was created to help people use Linux more easily.\nThank you for being part of the Open Source family!',
            'donate_sentence': 'No beer, no code. Please support a thirsty programmer!',
            'donate_button': 'Donate Beer Money',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Account Name',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Account Number',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Success',
            'error': 'Error',
            'settings_applied': 'Settings applied successfully!',
            'command_failed': 'Command failed: {}',
            'need_sudo': 'Administrator privileges required',
            'no_ytdlp': 'yt-dlp not found. Please install it first.',
            'app_manager': 'App Manager',
            'app_manager_title': 'Manage Installed Applications',
            'app_search_hint': '🔍  Search app name...',
            'app_col_name': 'App Name',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑  Uninstall',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Loading applications...',
            'app_count': 'Installed Apps',
            'app_reload': '🔄  Reload',
            'app_confirm_uninstall': 'Confirm Uninstall',
            'app_confirm_msg': 'Uninstall "{}" from system?\n\nThis action cannot be undone.',
            'app_uninstalling': 'Uninstalling {}...',
            'app_uninstall_ok': 'Successfully uninstalled {}',
            'app_uninstall_fail': 'Uninstall failed:\n{}',
            'app_select_first': 'Please select an application first',
            'app_info_title': 'App Information',
        }

        # fr-CA
        strings_fr_ca = {
            'window_title': 'Outils de réglage Geng v2.0.6',
            'home': 'Accueil',
            'keyboard': 'Clavier & Langue',
            'system_tools': 'Outils Système',
            'network': 'Réseau',
            'entertainment': 'Divertissement',
            'theme': 'Thème',
            'backup': 'Sauvegarde',
            'about': 'À propos',
            'navigation': 'NAVIGATION',
            'welcome': 'Bienvenue dans les Outils de réglage Geng',
            'current_user': 'Utilisateur actuel',
            'hostname': 'Nom d\'hôte',
            'home_desc': 'Votre boîte à outils de configuration tout-en-un pour Linux Mint Cinnamon 22.3.\nAjustez facilement les raccourcis clavier, gérez les applications, nettoyez votre système, téléchargez des médias, et plus encore.\nSélectionnez une catégorie dans la barre latérale pour débuter — tout est à portée de clic !',
            'keyboard_title': 'Paramètres Clavier & Langue',
            'grave_title': 'Changer de langue avec l\'accent grave (~)',
            'grave_desc': 'Utilisez la touche Accent Grave pour changer les méthodes de saisie',
            'alt_shift_title': 'Changer de langue avec Alt+Maj',
            'alt_shift_desc': 'Utilisez les touches Alt + Maj pour changer les méthodes de saisie',
            'custom_key_title': 'Raccourci personnalisé',
            'custom_key_desc': 'Appuyez sur le bouton ci-dessous pour capturer la combinaison de touches désirée',
            'capture_key': 'Capturer la touche',
            'apply_now': 'Appliquer maintenant',
            'system_title': 'Outils de gestion du système',
            'clean_system': 'Nettoyer les fichiers indésirables',
            'clean_system_desc': 'Supprimer les paquets inutilisés et vider le cache',
            'clear_ram': 'Vider la RAM/Cache',
            'clear_ram_desc': 'Vider le cache mémoire système (sync && drop_caches)',
            'driver_manager': 'Gestionnaire de pilotes',
            'driver_manager_desc': 'Ouvrir le gestionnaire de pilotes pour installer/supprimer des pilotes',
            'flatpak': 'Gérer Flatpak',
            'flatpak_desc': 'Mettre à jour Flatpak et gérer les applications',
            'apt_repair': 'Réparation APT',
            'apt_repair_desc': 'Réparer les paquets cassés et mettre à jour les listes',
            'system_monitor': 'Moniteur système',
            'system_monitor_desc': 'Ouvrir l\'outil de surveillance système',
            'network_title': 'Gestion réseau',
            'network_status': 'État du réseau',
            'refresh': 'Rafraîchir',
            'restart_network': 'Redémarrer le réseau',
            'flush_dns': 'Vider le DNS',
            'renew_dhcp': 'Renouveler le DHCP',
            'interfaces': 'Interfaces réseau',
            'connections': 'Connexions',
            'entertainment_title': 'Divertissement',
            'install_steam': 'Installer Steam',
            'install_steam_desc': 'Installer Steam pour jouer',
            'install_wine': 'Installer Wine',
            'install_wine_desc': 'Installer Wine pour exécuter des programmes Windows',
            'download_media': 'Télécharger vidéo/audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Vidéo MP4',
            'audio': 'Audio M4A',
            'download': 'Télécharger',
            'install_ytdlp': 'Installer yt-dlp',
            'theme_title': 'Personnalisation du thème',
            'dark_mode': 'Mode sombre',
            'light_mode': 'Mode clair',
            'mint_y': 'Mint-Y (clair)',
            'mint_y_dark': 'Mint-Y-Sombre',
            'mint_y_dark_aqua': 'Mint-Y-Sombre-Aqua',
            'apply_theme': 'Appliquer le thème',
            'backup_title': 'Sauvegarde des données',
            'select_drive': 'Sélectionnez le disque de destination',
            'backup_now': 'Démarrer la sauvegarde',
            'backup_progress': 'Sauvegarde en cours...',
            'backup_complete': 'Sauvegarde terminée',
            'backup_failed': 'Échec de la sauvegarde',
            'source': 'Source',
            'destination': 'Destination',
            'exclude': 'Exclure',
            'about_title': 'À propos',
            'developer': 'Développeur',
            'email': 'Courriel',
            'thanks': 'Cet outil a été créé pour aider les gens à utiliser Linux plus facilement.\nMerci de faire partie de la famille Open Source !',
            'donate_sentence': 'Pas de bière, pas de code. Merci de soutenir un programmeur assoiffé !',
            'donate_button': 'Faire un don pour une bière',
            'bank_label': 'Banque',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nom du titulaire',
            'account_name': 'M. Thammasorn Musikapan',
            'account_number_label': 'Numéro de compte',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Succès',
            'error': 'Erreur',
            'settings_applied': 'Paramètres appliqués avec succès !',
            'command_failed': 'Commande échouée : {}',
            'need_sudo': 'Privilèges administrateur requis',
            'no_ytdlp': 'yt-dlp introuvable. Veuillez l\'installer d\'abord.',
            'app_manager': 'Gestionnaire d\'applications',
            'app_manager_title': 'Gérer les applications installées',
            'app_search_hint': '🔍 Chercher le nom de l\'app...',
            'app_col_name': 'Nom de l\'app',
            'app_col_version': 'Version',
            'app_col_desc': 'Description',
            'app_uninstall': '🗑 Désinstaller',
            'app_info': 'ℹ Info',
            'app_loading': '⏳ Chargement des applications...',
            'app_count': 'Applications installées',
            'app_reload': '🔄 Recharger',
            'app_confirm_uninstall': 'Confirmer la désinstallation',
            'app_confirm_msg': 'Désinstaller "{}" du système ?\n\nCette action est irréversible.',
            'app_uninstalling': 'Désinstallation de {}...',
            'app_uninstall_ok': '{} désinstallé avec succès',
            'app_uninstall_fail': 'Échec de la désinstallation :\n{}',
            'app_select_first': 'Veuillez d\'abord sélectionner une application',
            'app_info_title': 'Informations sur l\'application',
        }

        # it
        strings_it = {
            'window_title': 'Strumenti Impostazioni Geng v2.0.6',
            'home': 'Home',
            'keyboard': 'Tastiera e lingua',
            'system_tools': 'Strumenti di sistema',
            'network': 'Rete',
            'entertainment': 'Intrattenimento',
            'theme': 'Tema',
            'backup': 'Backup',
            'about': 'Informazioni',
            'navigation': 'NAVIGAZIONE',
            'welcome': 'Benvenuto negli Strumenti Impostazioni Geng',
            'current_user': 'Utente corrente',
            'hostname': 'Nome host',
            'home_desc': 'La tua cassetta degli attrezzi per la configurazione tutto-in-uno per Linux Mint Cinnamon 22.3.\nRegola facilmente le scorciatoie da tastiera, gestisci le app, pulisci il sistema, scarica media e altro.\nSeleziona una categoria dalla barra laterale per iniziare — tutto è a portata di clic!',
            'keyboard_title': 'Impostazioni Tastiera e Lingua',
            'grave_title': 'Cambia lingua con l\'accento grave (~)',
            'grave_desc': 'Usa il tasto Accento grave per cambiare i metodi di input',
            'alt_shift_title': 'Cambia lingua con Alt+Shift',
            'alt_shift_desc': 'Usa i tasti Alt + Shift per cambiare i metodi di input',
            'custom_key_title': 'Scorciatoia personalizzata',
            'custom_key_desc': 'Premi il pulsante qui sotto per catturare la combinazione di tasti desiderata',
            'capture_key': 'Cattura tasto',
            'apply_now': 'Applica ora',
            'system_title': 'Strumenti di gestione del sistema',
            'clean_system': 'Pulisci file inutili',
            'clean_system_desc': 'Rimuovi pacchetti inutilizzati e svuota la cache',
            'clear_ram': 'Svuota RAM/Cache',
            'clear_ram_desc': 'Svuota la cache di memoria del sistema (sync && drop_caches)',
            'driver_manager': 'Gestore driver',
            'driver_manager_desc': 'Apri il Gestore driver per installare/rimuovere driver',
            'flatpak': 'Gestisci Flatpak',
            'flatpak_desc': 'Aggiorna Flatpak e gestisci le applicazioni',
            'apt_repair': 'Riparazione APT',
            'apt_repair_desc': 'Ripara pacchetti danneggiati e aggiorna le liste',
            'system_monitor': 'Monitor di sistema',
            'system_monitor_desc': 'Apri lo strumento di monitoraggio del sistema',
            'network_title': 'Gestione della rete',
            'network_status': 'Stato della rete',
            'refresh': 'Aggiorna',
            'restart_network': 'Riavvia rete',
            'flush_dns': 'Svuota DNS',
            'renew_dhcp': 'Rinnova DHCP',
            'interfaces': 'Interfacce di rete',
            'connections': 'Connessioni',
            'entertainment_title': 'Intrattenimento',
            'install_steam': 'Installa Steam',
            'install_steam_desc': 'Installa Steam per giocare',
            'install_wine': 'Installa Wine',
            'install_wine_desc': 'Installa Wine per eseguire programmi Windows',
            'download_media': 'Scarica video/audio',
            'url_label': 'URL',
            'format_label': 'Formato',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Scarica',
            'install_ytdlp': 'Installa yt-dlp',
            'theme_title': 'Personalizzazione tema',
            'dark_mode': 'Modalità scura',
            'light_mode': 'Modalità chiara',
            'mint_y': 'Mint-Y (chiaro)',
            'mint_y_dark': 'Mint-Y-scuro',
            'mint_y_dark_aqua': 'Mint-Y-scuro-acqua',
            'apply_theme': 'Applica tema',
            'backup_title': 'Backup dati',
            'select_drive': 'Seleziona unità destinazione',
            'backup_now': 'Avvia backup',
            'backup_progress': 'Backup in corso...',
            'backup_complete': 'Backup completato',
            'backup_failed': 'Backup fallito',
            'source': 'Origine',
            'destination': 'Destinazione',
            'exclude': 'Escludi',
            'about_title': 'Informazioni',
            'developer': 'Sviluppatore',
            'email': 'Email',
            'thanks': 'Questo strumento è stato creato per aiutare le persone a usare Linux più facilmente.\nGrazie per far parte della famiglia Open Source!',
            'donate_sentence': 'Niente birra, niente codice. Supporta un programmatore assetato!',
            'donate_button': 'Dona soldi per la birra',
            'bank_label': 'Banca',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nome conto',
            'account_name': 'Sig. Thammasorn Musikapan',
            'account_number_label': 'Numero conto',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Successo',
            'error': 'Errore',
            'settings_applied': 'Impostazioni applicate con successo!',
            'command_failed': 'Comando fallito: {}',
            'need_sudo': 'Privilegi di amministratore richiesti',
            'no_ytdlp': 'yt-dlp non trovato. Per favore installalo prima.',
            'app_manager': 'Gestore applicazioni',
            'app_manager_title': 'Gestisci applicazioni installate',
            'app_search_hint': '🔍  Cerca nome app...',
            'app_col_name': 'Nome app',
            'app_col_version': 'Versione',
            'app_col_desc': 'Descrizione',
            'app_uninstall': '🗑  Disinstalla',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Caricamento applicazioni...',
            'app_count': 'App installate',
            'app_reload': '🔄  Ricarica',
            'app_confirm_uninstall': 'Conferma Disinstallazione',
            'app_confirm_msg': 'Disinstallare "{}" dal sistema?\n\nQuesta azione non può essere annullata.',
            'app_uninstalling': 'Disinstallazione di {}...',
            'app_uninstall_ok': 'Disinstallazione di {} riuscita',
            'app_uninstall_fail': 'Disinstallazione fallita:\n{}',
            'app_select_first': 'Seleziona prima un\'applicazione',
            'app_info_title': 'Informazioni app',
        }

        # hi
        strings_hi = {
            'window_title': 'जेंग सेटिंग्स टूल्स v2.0.6',
            'home': 'मुखपृष्ठ',
            'keyboard': 'कीबोर्ड और भाषा',
            'system_tools': 'सिस्टम टूल्स',
            'network': 'नेटवर्क',
            'entertainment': 'मनोरंजन',
            'theme': 'थीम',
            'backup': 'बैकअप',
            'about': 'के बारे में',
            'navigation': 'नेविगेशन',
            'welcome': 'जेंग सेटिंग्स टूल्स में आपका स्वागत है',
            'current_user': 'वर्तमान उपयोगकर्ता',
            'hostname': 'होस्टनाम',
            'home_desc': 'Linux Mint Cinnamon 22.3 के लिए आपका ऑल-इन-वन कॉन्फ़िगरेशन टूलबॉक्स।\nकीबोर्ड शॉर्टकट्स को आसानी से बदलें, ऐप्स प्रबंधित करें, सिस्टम साफ़ करें, मीडिया डाउनलोड करें, और भी बहुत कुछ।\nशुरू करने के लिए साइडबार से एक श्रेणी चुनें — सब कुछ सिर्फ एक क्लिक दूर है!',
            'keyboard_title': 'कीबोर्ड और भाषा सेटिंग्स',
            'grave_title': 'ग्रेव एक्सेंट (~) के साथ भाषा बदलें',
            'grave_desc': 'इनपुट मेथड्स बदलने के लिए ग्रेव एक्सेंट कुंजी का उपयोग करें',
            'alt_shift_title': 'Alt+Shift के साथ भाषा बदलें',
            'alt_shift_desc': 'इनपुट मेथड्स बदलने के लिए Alt + Shift कुंजियों का उपयोग करें',
            'custom_key_title': 'कस्टम कीबाइंडिंग',
            'custom_key_desc': 'अपनी इच्छित कुंजी संयोजन कैप्चर करने के लिए नीचे का बटन दबाएं',
            'capture_key': 'कुंजी कैप्चर करें',
            'apply_now': 'अब लागू करें',
            'system_title': 'सिस्टम प्रबंधन उपकरण',
            'clean_system': 'जंक फ़ाइलें साफ़ करें',
            'clean_system_desc': 'अप्रयुक्त पैकेज हटाएं और कैश साफ़ करें',
            'clear_ram': 'रैम/कैश साफ़ करें',
            'clear_ram_desc': 'सिस्टम मेमोरी कैश साफ़ करें (sync && drop_caches)',
            'driver_manager': 'ड्राइवर प्रबंधक',
            'driver_manager_desc': 'ड्राइवर स्थापित/हटाने के लिए ड्राइवर प्रबंधक खोलें',
            'flatpak': 'फ्लैटपैक प्रबंधित करें',
            'flatpak_desc': 'फ्लैटपैक अपडेट करें और ऐप्लिकेशन प्रबंधित करें',
            'apt_repair': 'APT मरम्मत',
            'apt_repair_desc': 'टूटे हुए पैकेजों की मरम्मत करें और सूचियां अपडेट करें',
            'system_monitor': 'सिस्टम मॉनिटर',
            'system_monitor_desc': 'सिस्टम मॉनिटरिंग टूल खोलें',
            'network_title': 'नेटवर्क प्रबंधन',
            'network_status': 'नेटवर्क स्थिति',
            'refresh': 'रीफ्रेश करें',
            'restart_network': 'नेटवर्क पुनः प्रारंभ करें',
            'flush_dns': 'DNS फ्लश करें',
            'renew_dhcp': 'DHCP नवीनीकरण करें',
            'interfaces': 'नेटवर्क इंटरफेस',
            'connections': 'कनेक्शन्स',
            'entertainment_title': 'मनोरंजन',
            'install_steam': 'Steam इंस्टॉल करें',
            'install_steam_desc': 'गेमिंग के लिए Steam इंस्टॉल करें',
            'install_wine': 'Wine इंस्टॉल करें',
            'install_wine_desc': 'Windows प्रोग्राम चलाने के लिए Wine इंस्टॉल करें',
            'download_media': 'वीडियो/ऑडियो डाउनलोड करें',
            'url_label': 'URL',
            'format_label': 'फॉर्मेट',
            'video': 'वीडियो MP4',
            'audio': 'ऑडियो M4A',
            'download': 'डाउनलोड करें',
            'install_ytdlp': 'yt-dlp इंस्टॉल करें',
            'theme_title': 'थीम कस्टमाइज़ेशन',
            'dark_mode': 'डार्क मोड',
            'light_mode': 'लाइट मोड',
            'mint_y': 'मिंट-वाई (लाइट)',
            'mint_y_dark': 'मिंट-वाई-डार्क',
            'mint_y_dark_aqua': 'मिंट-वाई-डार्क-एक्वा',
            'apply_theme': 'थीम लागू करें',
            'backup_title': 'डेटा बैकअप',
            'select_drive': 'गंतव्य ड्राइव चुनें',
            'backup_now': 'बैकअप शुरू करें',
            'backup_progress': 'बैकअप हो रहा है...',
            'backup_complete': 'बैकअप पूर्ण',
            'backup_failed': 'बैकअप विफल',
            'source': 'स्रोत',
            'destination': 'गंतव्य',
            'exclude': 'बहिष्कृत करें',
            'about_title': 'के बारे में',
            'developer': 'डेवलपर',
            'email': 'ईमेल',
            'thanks': 'यह टूल लोगों को Linux अधिक आसानी से उपयोग करने में मदद करने के लिए बनाया गया था।\nओपन सोर्स परिवार का हिस्सा बनने के लिए धन्यवाद!',
            'donate_sentence': 'कोई बीयर नहीं, कोई कोड नहीं। कृपया एक प्यासे प्रोग्रामर को समर्थन दें!',
            'donate_button': 'बीयर मनी दान करें',
            'bank_label': 'बैंक',
            'bank_name': 'कासिकॉर्न थाई',
            'account_name_label': 'खाता नाम',
            'account_name': 'श्री थम्मासोर्न मुसिकापन',
            'account_number_label': 'खाता संख्या',
            'account_number': '1192455177',
            'paypal_label': 'पेपैल',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'बिटकॉइन (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'सफलता',
            'error': 'त्रुटि',
            'settings_applied': 'सेटिंग्स सफलतापूर्वक लागू हो गईं!',
            'command_failed': 'कमांड विफल: {}',
            'need_sudo': 'प्रशासक विशेषाधिकार आवश्यक हैं',
            'no_ytdlp': 'yt-dlp नहीं मिला। कृपया पहले इसे इंस्टॉल करें।',
            'app_manager': 'ऐप प्रबंधक',
            'app_manager_title': 'इंस्टॉल किए गए ऐप्स प्रबंधित करें',
            'app_search_hint': '🔍  ऐप नाम खोजें...',
            'app_col_name': 'ऐप नाम',
            'app_col_version': 'संस्करण',
            'app_col_desc': 'विवरण',
            'app_uninstall': '🗑  अनइंस्टॉल करें',
            'app_info': 'ℹ  जानकारी',
            'app_loading': '⏳  ऐप्लिकेशन लोड हो रहे हैं...',
            'app_count': 'इंस्टॉल ऐप्स',
            'app_reload': '🔄  रीलोड करें',
            'app_confirm_uninstall': 'अनइंस्टॉल की पुष्टि करें',
            'app_confirm_msg': '"{}" को सिस्टम से अनइंस्टॉल करें?\n\nयह क्रिया पूर्ववत नहीं की जा सकती।',
            'app_uninstalling': '{} को अनइंस्टॉल किया जा रहा है...',
            'app_uninstall_ok': '{} सफलतापूर्वक अनइंस्टॉल हो गया',
            'app_uninstall_fail': 'अनइंस्टॉल विफल:\n{}',
            'app_select_first': 'कृपया पहले एक ऐप्लिकेशन चुनें',
            'app_info_title': 'ऐप जानकारी',
        }

        # id
        strings_id = {
            'window_title': 'Alat Pengaturan Geng v2.0.6',
            'home': 'Beranda',
            'keyboard': 'Keyboard & Bahasa',
            'system_tools': 'Alat Sistem',
            'network': 'Jaringan',
            'entertainment': 'Hiburan',
            'theme': 'Tema',
            'backup': 'Cadangan',
            'about': 'Tentang',
            'navigation': 'NAVIGASI',
            'welcome': 'Selamat datang di Alat Pengaturan Geng',
            'current_user': 'Pengguna saat ini',
            'hostname': 'Nama host',
            'home_desc': 'Kotak alat konfigurasi serbaguna Anda untuk Linux Mint Cinnamon 22.3.\nMudah mengubah pintasan keyboard, mengelola aplikasi, membersihkan sistem Anda, mengunduh media, dan lainnya.\nPilih kategori dari bilah sisi untuk memulai — semuanya hanya dengan sekali klik!',
            'keyboard_title': 'Pengaturan Keyboard & Bahasa',
            'grave_title': 'Beralih bahasa dengan Grave Accent (~)',
            'grave_desc': 'Gunakan tombol Grave Accent untuk beralih metode input',
            'alt_shift_title': 'Beralih bahasa dengan Alt+Shift',
            'alt_shift_desc': 'Gunakan tombol Alt + Shift untuk beralih metode input',
            'custom_key_title': 'Kombinasi tombol khusus',
            'custom_key_desc': 'Tekan tombol di bawah untuk menangkap kombinasi tombol yang diinginkan',
            'capture_key': 'Tangkap Tombol',
            'apply_now': 'Terapkan Sekarang',
            'system_title': 'Alat Manajemen Sistem',
            'clean_system': 'Bersihkan File Sampah',
            'clean_system_desc': 'Hapus paket yang tidak digunakan dan bersihkan cache',
            'clear_ram': 'Bersihkan RAM/Cache',
            'clear_ram_desc': 'Bersihkan cache memori sistem (sync && drop_caches)',
            'driver_manager': 'Manajer Driver',
            'driver_manager_desc': 'Buka Manajer Driver untuk menginstal/menghapus driver',
            'flatpak': 'Kelola Flatpak',
            'flatpak_desc': 'Perbarui Flatpak dan kelola aplikasi',
            'apt_repair': 'Perbaikan APT',
            'apt_repair_desc': 'Perbaiki paket rusak dan perbarui daftar',
            'system_monitor': 'Monitor Sistem',
            'system_monitor_desc': 'Buka alat pemantauan sistem',
            'network_title': 'Manajemen Jaringan',
            'network_status': 'Status Jaringan',
            'refresh': 'Segarkan',
            'restart_network': 'Mulai Ulang Jaringan',
            'flush_dns': 'Bersihkan DNS',
            'renew_dhcp': 'Perbarui DHCP',
            'interfaces': 'Antarmuka Jaringan',
            'connections': 'Koneksi',
            'entertainment_title': 'Hiburan',
            'install_steam': 'Pasang Steam',
            'install_steam_desc': 'Pasang Steam untuk bermain game',
            'install_wine': 'Pasang Wine',
            'install_wine_desc': 'Pasang Wine untuk menjalankan program Windows',
            'download_media': 'Unduh Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Unduh',
            'install_ytdlp': 'Pasang yt-dlp',
            'theme_title': 'Kustomisasi Tema',
            'dark_mode': 'Mode Gelap',
            'light_mode': 'Mode Terang',
            'mint_y': 'Mint-Y (Terang)',
            'mint_y_dark': 'Mint-Y-Gelap',
            'mint_y_dark_aqua': 'Mint-Y-Gelap-Aqua',
            'apply_theme': 'Terapkan Tema',
            'backup_title': 'Cadangan Data',
            'select_drive': 'Pilih drive tujuan',
            'backup_now': 'Mulai Cadangan',
            'backup_progress': 'Sedang mencadangkan...',
            'backup_complete': 'Cadangan Selesai',
            'backup_failed': 'Cadangan Gagal',
            'source': 'Sumber',
            'destination': 'Tujuan',
            'exclude': 'Kecualikan',
            'about_title': 'Tentang',
            'developer': 'Pengembang',
            'email': 'Email',
            'thanks': 'Alat ini dibuat untuk membantu orang menggunakan Linux dengan lebih mudah.\nTerima kasih telah menjadi bagian dari keluarga Open Source!',
            'donate_sentence': 'Tanpa bir, tidak ada kode. Silakan dukung programmer yang haus!',
            'donate_button': 'Donasi Uang Bir',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nama Rekening',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Nomor Rekening',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Berhasil',
            'error': 'Kesalahan',
            'settings_applied': 'Pengaturan berhasil diterapkan!',
            'command_failed': 'Perintah gagal: {}',
            'need_sudo': 'Dibutuhkan hak istimewa administrator',
            'no_ytdlp': 'yt-dlp tidak ditemukan. Silakan pasang terlebih dahulu.',
            'app_manager': 'Manajer Aplikasi',
            'app_manager_title': 'Kelola Aplikasi Terpasang',
            'app_search_hint': '🔍  Cari nama aplikasi...',
            'app_col_name': 'Nama Aplikasi',
            'app_col_version': 'Versi',
            'app_col_desc': 'Deskripsi',
            'app_uninstall': '🗑  Copot Pemasangan',
            'app_info': 'ℹ  Info',
            'app_loading': '⏳  Memuat aplikasi...',
            'app_count': 'Aplikasi Terpasang',
            'app_reload': '🔄  Muat Ulang',
            'app_confirm_uninstall': 'Konfirmasi Copot Pemasangan',
            'app_confirm_msg': 'Copot pemasangan "{}" dari sistem?\n\nTindakan ini tidak dapat dibatalkan.',
            'app_uninstalling': 'Sedang mencopot pemasangan {}...',
            'app_uninstall_ok': 'Berhasil mencopot pemasangan {}',
            'app_uninstall_fail': 'Gagal mencopot pemasangan:\n{}',
            'app_select_first': 'Silakan pilih aplikasi terlebih dahulu',
            'app_info_title': 'Informasi Aplikasi',
        }

        # pt
        strings_pt = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Início',
            'keyboard': 'Teclado e Idioma',
            'system_tools': 'Ferramentas do Sistema',
            'network': 'Rede',
            'entertainment': 'Entretenimento',
            'theme': 'Tema',
            'backup': 'Backup',
            'about': 'Sobre',
            'navigation': 'NAVEGAÇÃO',
            'welcome': 'Bem-vindo ao Geng Settings Tools',
            'current_user': 'Usuário atual',
            'hostname': 'Nome do host',
            'home_desc': 'Sua caixa de ferramentas de configuração tudo em um para Linux Mint Cinnamon 22.3.\nFacilmente ajuste atalhos de teclado, gerencie aplicativos, limpe seu sistema, baixe mídia e mais.\nSelecione uma categoria na barra lateral para começar — tudo está a um clique de distância!',
            'keyboard_title': 'Configurações de Teclado e Idioma',
            'grave_title': 'Mudar idioma com Acento Grave (~)',
            'grave_desc': 'Use a tecla Acento Grave para alternar métodos de entrada',
            'alt_shift_title': 'Mudar idioma com Alt+Shift',
            'alt_shift_desc': 'Use as teclas Alt + Shift para alternar métodos de entrada',
            'custom_key_title': 'Atalho personalizado',
            'custom_key_desc': 'Pressione o botão abaixo para capturar a combinação de teclas desejada',
            'capture_key': 'Capturar Tecla',
            'apply_now': 'Aplicar Agora',
            'system_title': 'Ferramentas de Gerenciamento do Sistema',
            'clean_system': 'Limpar Arquivos Lixo',
            'clean_system_desc': 'Remover pacotes não usados e limpar cache',
            'clear_ram': 'Limpar RAM/Cache',
            'clear_ram_desc': 'Limpar cache da memória do sistema (sync && drop_caches)',
            'driver_manager': 'Gerenciador de Drivers',
            'driver_manager_desc': 'Abrir Gerenciador de Drivers para instalar/remover drivers',
            'flatpak': 'Gerenciar Flatpak',
            'flatpak_desc': 'Atualizar Flatpak e gerenciar aplicações',
            'apt_repair': 'Reparar APT',
            'apt_repair_desc': 'Reparar pacotes quebrados e atualizar listas',
            'system_monitor': 'Monitor do Sistema',
            'system_monitor_desc': 'Abrir ferramenta de monitoramento do sistema',
            'network_title': 'Gerenciamento de Rede',
            'network_status': 'Status da Rede',
            'refresh': 'Atualizar',
            'restart_network': 'Reiniciar Rede',
            'flush_dns': 'Limpar DNS',
            'renew_dhcp': 'Renovar DHCP',
            'interfaces': 'Interfaces de Rede',
            'connections': 'Conexões',
            'entertainment_title': 'Entretenimento',
            'install_steam': 'Instalar Steam',
            'install_steam_desc': 'Instalar Steam para jogos',
            'install_wine': 'Instalar Wine',
            'install_wine_desc': 'Instalar Wine para rodar programas Windows',
            'download_media': 'Baixar Vídeo/Áudio',
            'url_label': 'URL',
            'format_label': 'Formato',
            'video': 'Vídeo MP4',
            'audio': 'Áudio M4A',
            'download': 'Baixar',
            'install_ytdlp': 'Instalar yt-dlp',
            'theme_title': 'Personalização do Tema',
            'dark_mode': 'Modo Escuro',
            'light_mode': 'Modo Claro',
            'mint_y': 'Mint-Y (Claro)',
            'mint_y_dark': 'Mint-Y-Escuro',
            'mint_y_dark_aqua': 'Mint-Y-Escuro-Aqua',
            'apply_theme': 'Aplicar Tema',
            'backup_title': 'Backup de Dados',
            'select_drive': 'Selecionar unidade de destino',
            'backup_now': 'Iniciar Backup',
            'backup_progress': 'Fazendo backup...',
            'backup_complete': 'Backup Concluído',
            'backup_failed': 'Backup Falhou',
            'source': 'Origem',
            'destination': 'Destino',
            'exclude': 'Excluir',
            'about_title': 'Sobre',
            'developer': 'Desenvolvedor',
            'email': 'E-mail',
            'thanks': 'Esta ferramenta foi criada para ajudar as pessoas a usar Linux mais facilmente.\nObrigado por fazer parte da família Open Source!',
            'donate_sentence': 'Sem cerveja, sem código. Por favor, apoie um programador sedento!',
            'donate_button': 'Doar Dinheiro para Cerveja',
            'bank_label': 'Banco',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nome da Conta',
            'account_name': 'Sr. Thammasorn Musikapan',
            'account_number_label': 'Número da Conta',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Sucesso',
            'error': 'Erro',
            'settings_applied': 'Configurações aplicadas com sucesso!',
            'command_failed': 'Comando falhou: {}',
            'need_sudo': 'Privilégios de administrador necessários',
            'no_ytdlp': 'yt-dlp não encontrado. Por favor, instale primeiro.',
            'app_manager': 'Gerenciador de Aplicativos',
            'app_manager_title': 'Gerenciar Aplicações Instaladas',
            'app_search_hint': '🔍  Pesquisar nome do app...',
            'app_col_name': 'Nome do App',
            'app_col_version': 'Versão',
            'app_col_desc': 'Descrição',
            'app_uninstall': '🗑  Desinstalar',
            'app_info': 'ℹ  Informações',
            'app_loading': '⏳  Carregando aplicações...',
            'app_count': 'Apps Instalados',
            'app_reload': '🔄  Recarregar',
            'app_confirm_uninstall': 'Confirmar Desinstalação',
            'app_confirm_msg': 'Desinstalar "{}" do sistema?\n\nEsta ação não pode ser desfeita.',
            'app_uninstalling': 'Desinstalando {}...',
            'app_uninstall_ok': 'Desinstalado com sucesso {}',
            'app_uninstall_fail': 'Falha na desinstalação:\n{}',
            'app_select_first': 'Por favor, selecione uma aplicação primeiro',
            'app_info_title': 'Informações do App',
        }

        # pt-BR
        strings_pt_br = {
            'window_title': 'Ferramentas de Configuração Geng v2.0.6',
            'home': 'Início',
            'keyboard': 'Teclado e Idioma',
            'system_tools': 'Ferramentas do Sistema',
            'network': 'Rede',
            'entertainment': 'Entretenimento',
            'theme': 'Tema',
            'backup': 'Backup',
            'about': 'Sobre',
            'navigation': 'NAVEGAÇÃO',
            'welcome': 'Bem-vindo às Ferramentas de Configuração Geng',
            'current_user': 'Usuário atual',
            'hostname': 'Nome do host',
            'home_desc': 'Sua caixa de ferramentas tudo-em-um para configuração do Linux Mint Cinnamon 22.3.\nAltere facilmente atalhos de teclado, gerencie aplicativos, limpe seu sistema, baixe mídia e mais.\nSelecione uma categoria na barra lateral para começar — tudo está a um clique de distância!',
            'keyboard_title': 'Configurações de Teclado e Idioma',
            'grave_title': 'Mudar idioma com o Acento Grave (~)',
            'grave_desc': 'Use a tecla Acento Grave para trocar métodos de entrada',
            'alt_shift_title': 'Mudar idioma com Alt+Shift',
            'alt_shift_desc': 'Use as teclas Alt + Shift para trocar métodos de entrada',
            'custom_key_title': 'Atalho personalizado',
            'custom_key_desc': 'Pressione o botão abaixo para capturar a combinação de teclas desejada',
            'capture_key': 'Capturar tecla',
            'apply_now': 'Aplicar agora',
            'system_title': 'Ferramentas de Gerenciamento do Sistema',
            'clean_system': 'Limpar arquivos inúteis',
            'clean_system_desc': 'Remover pacotes não usados e limpar cache',
            'clear_ram': 'Limpar RAM/Cache',
            'clear_ram_desc': 'Limpar cache de memória do sistema (sync && drop_caches)',
            'driver_manager': 'Gerenciador de Drivers',
            'driver_manager_desc': 'Abrir Gerenciador de Drivers para instalar/remover drivers',
            'flatpak': 'Gerenciar Flatpak',
            'flatpak_desc': 'Atualizar Flatpak e gerenciar aplicações',
            'apt_repair': 'Reparo APT',
            'apt_repair_desc': 'Reparar pacotes quebrados e atualizar listas',
            'system_monitor': 'Monitor do Sistema',
            'system_monitor_desc': 'Abrir ferramenta de monitoramento do sistema',
            'network_title': 'Gerenciamento de Rede',
            'network_status': 'Status da Rede',
            'refresh': 'Atualizar',
            'restart_network': 'Reiniciar Rede',
            'flush_dns': 'Limpar DNS',
            'renew_dhcp': 'Renovar DHCP',
            'interfaces': 'Interfaces de Rede',
            'connections': 'Conexões',
            'entertainment_title': 'Entretenimento',
            'install_steam': 'Instalar Steam',
            'install_steam_desc': 'Instalar Steam para jogos',
            'install_wine': 'Instalar Wine',
            'install_wine_desc': 'Instalar Wine para rodar programas do Windows',
            'download_media': 'Baixar Vídeo/Áudio',
            'url_label': 'URL',
            'format_label': 'Formato',
            'video': 'Vídeo MP4',
            'audio': 'Áudio M4A',
            'download': 'Baixar',
            'install_ytdlp': 'Instalar yt-dlp',
            'theme_title': 'Personalização de Tema',
            'dark_mode': 'Modo Escuro',
            'light_mode': 'Modo Claro',
            'mint_y': 'Mint-Y (Claro)',
            'mint_y_dark': 'Mint-Y-Escuro',
            'mint_y_dark_aqua': 'Mint-Y-Escuro-Aqua',
            'apply_theme': 'Aplicar Tema',
            'backup_title': 'Backup de Dados',
            'select_drive': 'Selecionar disco de destino',
            'backup_now': 'Iniciar Backup',
            'backup_progress': 'Fazendo backup...',
            'backup_complete': 'Backup Completo',
            'backup_failed': 'Backup Falhou',
            'source': 'Origem',
            'destination': 'Destino',
            'exclude': 'Excluir',
            'about_title': 'Sobre',
            'developer': 'Desenvolvedor',
            'email': 'Email',
            'thanks': 'Esta ferramenta foi criada para ajudar as pessoas a usar Linux de forma mais fácil.\nObrigado por fazer parte da família Open Source!',
            'donate_sentence': 'Sem cerveja, sem código. Por favor, apoie um programador sedento!',
            'donate_button': 'Doar Dinheiro para Cerveja',
            'bank_label': 'Banco',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nome da Conta',
            'account_name': 'Sr. Thammasorn Musikapan',
            'account_number_label': 'Número da Conta',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Sucesso',
            'error': 'Erro',
            'settings_applied': 'Configurações aplicadas com sucesso!',
            'command_failed': 'Comando falhou: {}',
            'need_sudo': 'Privilégios de administrador necessários',
            'no_ytdlp': 'yt-dlp não encontrado. Por favor, instale-o primeiro.',
            'app_manager': 'Gerenciador de Aplicativos',
            'app_manager_title': 'Gerenciar Aplicativos Instalados',
            'app_search_hint': '🔍  Procurar nome do app...',
            'app_col_name': 'Nome do App',
            'app_col_version': 'Versão',
            'app_col_desc': 'Descrição',
            'app_uninstall': '🗑  Desinstalar',
            'app_info': 'ℹ  Informações',
            'app_loading': '⏳  Carregando aplicativos...',
            'app_count': 'Apps Instalados',
            'app_reload': '🔄  Recarregar',
            'app_confirm_uninstall': 'Confirmar Desinstalação',
            'app_confirm_msg': 'Desinstalar "{}" do sistema?\n\nEsta ação não pode ser desfeita.',
            'app_uninstalling': 'Desinstalando {}...',
            'app_uninstall_ok': 'Desinstalado com sucesso {}',
            'app_uninstall_fail': 'Falha na desinstalação:\n{}',
            'app_select_first': 'Por favor, selecione um aplicativo primeiro',
            'app_info_title': 'Informações do App',
        }

        # ja
        strings_ja = {
            'window_title': 'Geng 設定ツール v2.0.6',
            'home': 'ホーム',
            'keyboard': 'キーボードと言語',
            'system_tools': 'システムツール',
            'network': 'ネットワーク',
            'entertainment': 'エンターテインメント',
            'theme': 'テーマ',
            'backup': 'バックアップ',
            'about': 'アバウト',
            'navigation': 'ナビゲーション',
            'welcome': 'Geng 設定ツールへようこそ',
            'current_user': '現在のユーザー',
            'hostname': 'ホスト名',
            'home_desc': 'Linux Mint Cinnamon 22.3 向けのオールインワン設定ツールボックスです。\nキーボードショートカットの簡単な調整、アプリの管理、システムクリーニング、メディアのダウンロードなどができます。\nサイドバーからカテゴリを選択して始めましょう — すべてがクリックひとつで簡単に操作できます！',
            'keyboard_title': 'キーボードと言語の設定',
            'grave_title': 'Grave Accent (~) で言語を切り替え',
            'grave_desc': 'Grave Accent キーを使って入力方式を切り替えます',
            'alt_shift_title': 'Alt+Shift で言語を切り替え',
            'alt_shift_desc': 'Alt + Shift キーを使って入力方式を切り替えます',
            'custom_key_title': 'カスタムキー割り当て',
            'custom_key_desc': '下のボタンを押して希望のキーコンビネーションを登録してください',
            'capture_key': 'キーをキャプチャ',
            'apply_now': '今すぐ適用',
            'system_title': 'システム管理ツール',
            'clean_system': '不要ファイルのクリーニング',
            'clean_system_desc': '未使用パッケージを削除しキャッシュをクリアします',
            'clear_ram': 'RAM/キャッシュのクリア',
            'clear_ram_desc': 'システムメモリキャッシュをクリアします（sync && drop_caches）',
            'driver_manager': 'ドライバーマネージャー',
            'driver_manager_desc': 'ドライバーマネージャーを開いてドライバーをインストール/削除',
            'flatpak': 'Flatpakの管理',
            'flatpak_desc': 'Flatpakの更新とアプリケーションの管理',
            'apt_repair': 'APT 修復',
            'apt_repair_desc': '壊れたパッケージの修復とリストの更新',
            'system_monitor': 'システムモニター',
            'system_monitor_desc': 'システム監視ツールを開く',
            'network_title': 'ネットワーク管理',
            'network_status': 'ネットワーク状態',
            'refresh': '更新',
            'restart_network': 'ネットワーク再起動',
            'flush_dns': 'DNSをフラッシュ',
            'renew_dhcp': 'DHCPを更新',
            'interfaces': 'ネットワークインターフェース',
            'connections': '接続',
            'entertainment_title': 'エンターテインメント',
            'install_steam': 'Steamをインストール',
            'install_steam_desc': 'ゲーム用にSteamをインストールします',
            'install_wine': 'Wineをインストール',
            'install_wine_desc': 'Windowsプログラムを動かすためにWineをインストールします',
            'download_media': '動画/音声をダウンロード',
            'url_label': 'URL',
            'format_label': 'フォーマット',
            'video': '動画 MP4',
            'audio': '音声 M4A',
            'download': 'ダウンロード',
            'install_ytdlp': 'yt-dlpをインストール',
            'theme_title': 'テーマカスタマイズ',
            'dark_mode': 'ダークモード',
            'light_mode': 'ライトモード',
            'mint_y': 'Mint-Y（ライト）',
            'mint_y_dark': 'Mint-Y-ダーク',
            'mint_y_dark_aqua': 'Mint-Y-ダーク-アクア',
            'apply_theme': 'テーマを適用',
            'backup_title': 'データバックアップ',
            'select_drive': '保存先ドライブを選択',
            'backup_now': 'バックアップ開始',
            'backup_progress': 'バックアップ中...',
            'backup_complete': 'バックアップ完了',
            'backup_failed': 'バックアップ失敗',
            'source': 'ソース',
            'destination': '保存先',
            'exclude': '除外',
            'about_title': 'アバウト',
            'developer': '開発者',
            'email': 'メールアドレス',
            'thanks': 'このツールはLinuxをより簡単に使えるようにするために作成されました。\nオープンソースファミリーの一員でいてくれてありがとうございます！',
            'donate_sentence': 'ビールなしにコードなし。渇いたプログラマーを応援してください！',
            'donate_button': 'ビール代を寄付',
            'bank_label': '銀行',
            'bank_name': 'カシコーンタイ銀行',
            'account_name_label': '口座名義',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': '口座番号',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'ビットコイン (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': '成功',
            'error': 'エラー',
            'settings_applied': '設定が正常に適用されました！',
            'command_failed': 'コマンド失敗: {}',
            'need_sudo': '管理者権限が必要です',
            'no_ytdlp': 'yt-dlpが見つかりません。先にインストールしてください。',
            'app_manager': 'アプリマネージャー',
            'app_manager_title': 'インストール済みアプリ管理',
            'app_search_hint': '🔍  アプリ名を検索...',
            'app_col_name': 'アプリ名',
            'app_col_version': 'バージョン',
            'app_col_desc': '説明',
            'app_uninstall': '🗑  アンインストール',
            'app_info': 'ℹ  情報',
            'app_loading': '⏳  アプリを読み込み中...',
            'app_count': 'インストール済みアプリ',
            'app_reload': '🔄  再読み込み',
            'app_confirm_uninstall': 'アンインストール確認',
            'app_confirm_msg': '"{}" をシステムからアンインストールしますか？\n\nこの操作は元に戻せません。',
            'app_uninstalling': '{} をアンインストール中...',
            'app_uninstall_ok': '{} のアンインストールに成功しました',
            'app_uninstall_fail': 'アンインストールに失敗しました:\n{}',
            'app_select_first': 'まずアプリを選択してください',
            'app_info_title': 'アプリ情報',
        }

        # zh-CN
        strings_zh_cn = {
            'window_title': '耿设置工具 v2.0.6',
            'home': '首页',
            'keyboard': '键盘与语言',
            'system_tools': '系统工具',
            'network': '网络',
            'entertainment': '娱乐',
            'theme': '主题',
            'backup': '备份',
            'about': '关于',
            'navigation': '导航',
            'welcome': '欢迎使用耿设置工具',
            'current_user': '当前用户',
            'hostname': '主机名',
            'home_desc': '您的一体化 Linux Mint Cinnamon 22.3 配置工具箱。\n轻松调整键盘快捷键，管理应用，清理系统，下载媒体等。\n从侧边栏选择一个分类开始——一切尽在点击之间！',
            'keyboard_title': '键盘与语言设置',
            'grave_title': '使用重音符号（~）切换语言',
            'grave_desc': '使用重音符键切换输入法',
            'alt_shift_title': '使用 Alt+Shift 切换语言',
            'alt_shift_desc': '使用 Alt + Shift 键切换输入法',
            'custom_key_title': '自定义快捷键',
            'custom_key_desc': '按下下面按钮捕捉所需按键组合',
            'capture_key': '捕获按键',
            'apply_now': '立即应用',
            'system_title': '系统管理工具',
            'clean_system': '清理垃圾文件',
            'clean_system_desc': '移除未使用的软件包并清理缓存',
            'clear_ram': '清理内存/缓存',
            'clear_ram_desc': '清理系统内存缓存（同步 && 清除缓存）',
            'driver_manager': '驱动管理器',
            'driver_manager_desc': '打开驱动管理器以安装/移除驱动程序',
            'flatpak': '管理 Flatpak',
            'flatpak_desc': '更新 Flatpak 并管理应用',
            'apt_repair': 'APT 修复',
            'apt_repair_desc': '修复损坏的软件包并更新列表',
            'system_monitor': '系统监视器',
            'system_monitor_desc': '打开系统监视工具',
            'network_title': '网络管理',
            'network_status': '网络状态',
            'refresh': '刷新',
            'restart_network': '重启网络',
            'flush_dns': '清除 DNS 缓存',
            'renew_dhcp': '续租 DHCP',
            'interfaces': '网络接口',
            'connections': '连接',
            'entertainment_title': '娱乐',
            'install_steam': '安装 Steam',
            'install_steam_desc': '安装 Steam 进行游戏',
            'install_wine': '安装 Wine',
            'install_wine_desc': '安装 Wine 运行 Windows 程序',
            'download_media': '下载视频/音频',
            'url_label': '链接',
            'format_label': '格式',
            'video': '视频 MP4',
            'audio': '音频 M4A',
            'download': '下载',
            'install_ytdlp': '安装 yt-dlp',
            'theme_title': '主题定制',
            'dark_mode': '黑暗模式',
            'light_mode': '明亮模式',
            'mint_y': 'Mint-Y（浅色）',
            'mint_y_dark': 'Mint-Y-暗色',
            'mint_y_dark_aqua': 'Mint-Y-暗色-水蓝',
            'apply_theme': '应用主题',
            'backup_title': '数据备份',
            'select_drive': '选择目标盘',
            'backup_now': '开始备份',
            'backup_progress': '备份中...',
            'backup_complete': '备份完成',
            'backup_failed': '备份失败',
            'source': '源',
            'destination': '目标',
            'exclude': '排除',
            'about_title': '关于',
            'developer': '开发者',
            'email': '电子邮件',
            'thanks': '此工具旨在帮助人们更轻松地使用 Linux。\n感谢您成为开源大家庭的一员！',
            'donate_sentence': '没有啤酒就没有代码。请支持一位口渴的程序员！',
            'donate_button': '捐赠啤酒钱',
            'bank_label': '银行',
            'bank_name': '泰国开泰银行',
            'account_name_label': '账户名',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': '账户号码',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': '比特币 (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': '成功',
            'error': '错误',
            'settings_applied': '设置应用成功！',
            'command_failed': '命令失败：{}',
            'need_sudo': '需要管理员权限',
            'no_ytdlp': '未找到 yt-dlp，请先安装。',
            'app_manager': '应用管理器',
            'app_manager_title': '管理已安装的应用',
            'app_search_hint': '🔍  搜索应用名称...',
            'app_col_name': '应用名称',
            'app_col_version': '版本',
            'app_col_desc': '描述',
            'app_uninstall': '🗑  卸载',
            'app_info': 'ℹ  信息',
            'app_loading': '⏳  加载应用中...',
            'app_count': '已安装应用',
            'app_reload': '🔄  重新加载',
            'app_confirm_uninstall': '确认卸载',
            'app_confirm_msg': '是否从系统卸载“{}”？\n\n此操作不可撤销。',
            'app_uninstalling': '正在卸载 {}...',
            'app_uninstall_ok': '成功卸载 {}',
            'app_uninstall_fail': '卸载失败：\n{}',
            'app_select_first': '请先选择一个应用',
            'app_info_title': '应用信息',
        }

        # ru
        strings_ru = {
            'window_title': 'Инструменты настроек Geng v2.0.6',
            'home': 'Главная',
            'keyboard': 'Клавиатура и язык',
            'system_tools': 'Системные инструменты',
            'network': 'Сеть',
            'entertainment': 'Развлечения',
            'theme': 'Тема',
            'backup': 'Резервное копирование',
            'about': 'О программе',
            'navigation': 'НАВИГАЦИЯ',
            'welcome': 'Добро пожаловать в Инструменты настроек Geng',
            'current_user': 'Текущий пользователь',
            'hostname': 'Имя хоста',
            'home_desc': 'Ваш универсальный набор инструментов конфигурации для Linux Mint Cinnamon 22.3.\nЛегко настраивайте сочетания клавиш, управляйте приложениями, очищайте систему, загружайте медиа и многое другое.\nВыберите категорию в боковой панели, чтобы начать — всё в одном клике!',
            'keyboard_title': 'Настройки клавиатуры и языка',
            'grave_title': 'Переключение языка клавишей с Grave Accent (~)',
            'grave_desc': 'Используйте клавишу Grave Accent для переключения методов ввода',
            'alt_shift_title': 'Переключение языка с Alt+Shift',
            'alt_shift_desc': 'Используйте клавиши Alt + Shift для переключения методов ввода',
            'custom_key_title': 'Пользовательская комбинация клавиш',
            'custom_key_desc': 'Нажмите кнопку ниже, чтобы захватить желаемую комбинацию клавиш',
            'capture_key': 'Захватить клавишу',
            'apply_now': 'Применить сейчас',
            'system_title': 'Инструменты управления системой',
            'clean_system': 'Очистка ненужных файлов',
            'clean_system_desc': 'Удаление неиспользуемых пакетов и очистка кеша',
            'clear_ram': 'Очистить ОЗУ/кэш',
            'clear_ram_desc': 'Очистить кеш системной памяти (sync && drop_caches)',
            'driver_manager': 'Менеджер драйверов',
            'driver_manager_desc': 'Открыть менеджер драйверов для установки/удаления драйверов',
            'flatpak': 'Управление Flatpak',
            'flatpak_desc': 'Обновить Flatpak и управлять приложениями',
            'apt_repair': 'Восстановление APT',
            'apt_repair_desc': 'Исправить повреждённые пакеты и обновить списки',
            'system_monitor': 'Монитор системы',
            'system_monitor_desc': 'Открыть инструмент мониторинга системы',
            'network_title': 'Управление сетью',
            'network_status': 'Состояние сети',
            'refresh': 'Обновить',
            'restart_network': 'Перезапустить сеть',
            'flush_dns': 'Очистить DNS',
            'renew_dhcp': 'Обновить DHCP',
            'interfaces': 'Сетевые интерфейсы',
            'connections': 'Подключения',
            'entertainment_title': 'Развлечения',
            'install_steam': 'Установить Steam',
            'install_steam_desc': 'Установить Steam для игр',
            'install_wine': 'Установить Wine',
            'install_wine_desc': 'Установить Wine для запуска программ Windows',
            'download_media': 'Скачать видео/аудио',
            'url_label': 'URL',
            'format_label': 'Формат',
            'video': 'Видео MP4',
            'audio': 'Аудио M4A',
            'download': 'Скачать',
            'install_ytdlp': 'Установить yt-dlp',
            'theme_title': 'Настройка темы',
            'dark_mode': 'Тёмный режим',
            'light_mode': 'Светлый режим',
            'mint_y': 'Mint-Y (светлая)',
            'mint_y_dark': 'Mint-Y-тёмная',
            'mint_y_dark_aqua': 'Mint-Y-тёмная-Aqua',
            'apply_theme': 'Применить тему',
            'backup_title': 'Резервное копирование данных',
            'select_drive': 'Выберите диск назначения',
            'backup_now': 'Начать резервное копирование',
            'backup_progress': 'Резервное копирование...',
            'backup_complete': 'Резервное копирование завершено',
            'backup_failed': 'Резервное копирование не выполнено',
            'source': 'Источник',
            'destination': 'Назначение',
            'exclude': 'Исключить',
            'about_title': 'О программе',
            'developer': 'Разработчик',
            'email': 'Электронная почта',
            'thanks': 'Этот инструмент создан, чтобы помочь людям проще использовать Linux.\nСпасибо, что вы часть семьи Open Source!',
            'donate_sentence': 'Без пива нет кода. Пожалуйста, поддержите жаждущего программиста!',
            'donate_button': 'Пожертвовать на пиво',
            'bank_label': 'Банк',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Имя владельца счёта',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Номер счёта',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Успех',
            'error': 'Ошибка',
            'settings_applied': 'Настройки успешно применены!',
            'command_failed': 'Команда не выполнена: {}',
            'need_sudo': 'Требуются права администратора',
            'no_ytdlp': 'yt-dlp не найден. Пожалуйста, установите его сначала.',
            'app_manager': 'Менеджер приложений',
            'app_manager_title': 'Управление установленными приложениями',
            'app_search_hint': '🔍  Поиск по имени приложения...',
            'app_col_name': 'Название приложения',
            'app_col_version': 'Версия',
            'app_col_desc': 'Описание',
            'app_uninstall': '🗑  Удалить',
            'app_info': 'ℹ  Информация',
            'app_loading': '⏳  Загрузка приложений...',
            'app_count': 'Установленные приложения',
            'app_reload': '🔄  Перезагрузить',
            'app_confirm_uninstall': 'Подтверждение удаления',
            'app_confirm_msg': 'Удалить "{}" из системы?\n\nЭто действие невозможно отменить.',
            'app_uninstalling': 'Удаление {}...',
            'app_uninstall_ok': '«{}» успешно удалён',
            'app_uninstall_fail': 'Ошибка удаления:\n{}',
            'app_select_first': 'Пожалуйста, сначала выберите приложение',
            'app_info_title': 'Информация о приложении',
        }

        # tr
        strings_tr = {
            'window_title': 'Geng Ayar Araçları v2.0.6',
            'home': 'Ana Sayfa',
            'keyboard': 'Klavye ve Dil',
            'system_tools': 'Sistem Araçları',
            'network': 'Ağ',
            'entertainment': 'Eğlence',
            'theme': 'Tema',
            'backup': 'Yedekleme',
            'about': 'Hakkında',
            'navigation': 'GEZİNME',
            'welcome': 'Geng Ayar Araçlarına Hoşgeldiniz',
            'current_user': 'Şu anki kullanıcı',
            'hostname': 'Ana bilgisayar adı',
            'home_desc': 'Linux Mint Cinnamon 22.3 için hepsi bir arada yapılandırma araç kutunuz.\nKlavye kısayollarını kolayca ayarlayın, uygulamaları yönetin, sisteminizi temizleyin, medya indirin ve daha fazlasını yapın.\nBaşlamak için kenar çubuğundan bir kategori seçin — her şey bir tık uzağınızda!',
            'keyboard_title': 'Klavye ve Dil Ayarları',
            'grave_title': 'Dil geçişi için Grave Accent (~) kullanın',
            'grave_desc': 'Giriş yöntemlerini değiştirmek için Grave Accent tuşunu kullanın',
            'alt_shift_title': 'Alt+Shift ile dil değiştir',
            'alt_shift_desc': 'Giriş yöntemlerini değiştirmek için Alt + Shift tuşlarını kullanın',
            'custom_key_title': 'Özel tuş ataması',
            'custom_key_desc': 'İstenen tuş kombinasyonunu yakalamak için aşağıdaki düğmeye basın',
            'capture_key': 'Tuşu Yakala',
            'apply_now': 'Şimdi Uygula',
            'system_title': 'Sistem Yönetim Araçları',
            'clean_system': 'Gereksiz Dosyaları Temizle',
            'clean_system_desc': 'Kullanılmayan paketleri kaldır ve önbelleği temizle',
            'clear_ram': 'RAM/Önbelleği Temizle',
            'clear_ram_desc': 'Sistem bellek önbelleğini temizle (sync && drop_caches)',
            'driver_manager': 'Sürücü Yöneticisi',
            'driver_manager_desc': 'Sürücüleri yüklemek/kaldırmak için Sürücü Yöneticisini açın',
            'flatpak': 'Flatpak Yönetimi',
            'flatpak_desc': 'Flatpak’ı güncelle ve uygulamaları yönet',
            'apt_repair': 'APT Onarımı',
            'apt_repair_desc': 'Kırık paketleri onar ve listeleri güncelle',
            'system_monitor': 'Sistem Monitörü',
            'system_monitor_desc': 'Sistem izleme aracını aç',
            'network_title': 'Ağ Yönetimi',
            'network_status': 'Ağ Durumu',
            'refresh': 'Yenile',
            'restart_network': 'Ağı Yeniden Başlat',
            'flush_dns': 'DNS’yi Temizle',
            'renew_dhcp': 'DHCP’yi Yenile',
            'interfaces': 'Ağ Arayüzleri',
            'connections': 'Bağlantılar',
            'entertainment_title': 'Eğlence',
            'install_steam': 'Steam Kur',
            'install_steam_desc': 'Oyun oynamak için Steam’i kur',
            'install_wine': 'Wine Kur',
            'install_wine_desc': 'Windows programlarını çalıştırmak için Wine’i kur',
            'download_media': 'Video/Audio İndir',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'İndir',
            'install_ytdlp': 'yt-dlp Kur',
            'theme_title': 'Tema Özelleştirme',
            'dark_mode': 'Karanlık Mod',
            'light_mode': 'Aydınlık Mod',
            'mint_y': 'Mint-Y (Aydınlık)',
            'mint_y_dark': 'Mint-Y-Karanlık',
            'mint_y_dark_aqua': 'Mint-Y-Karanlık-Aqua',
            'apply_theme': 'Temayı Uygula',
            'backup_title': 'Veri Yedekleme',
            'select_drive': 'Hedef sürücüyü seç',
            'backup_now': 'Yedeklemeyi Başlat',
            'backup_progress': 'Yedekleniyor...',
            'backup_complete': 'Yedekleme Tamamlandı',
            'backup_failed': 'Yedekleme Başarısız',
            'source': 'Kaynak',
            'destination': 'Hedef',
            'exclude': 'Hariç Tut',
            'about_title': 'Hakkında',
            'developer': 'Geliştirici',
            'email': 'E-posta',
            'thanks': 'Bu araç, insanların Linux’u daha kolay kullanabilmesi için oluşturuldu.\nAçık Kaynak ailesinin bir parçası olduğunuz için teşekkürler!',
            'donate_sentence': 'Birasız kod olmaz. Lütfen susamış bir programcıyı destekleyin!',
            'donate_button': 'Bira Parası Bağışla',
            'bank_label': 'Banka',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Hesap Adı',
            'account_name': 'Bay Thammasorn Musikapan',
            'account_number_label': 'Hesap Numarası',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Başarılı',
            'error': 'Hata',
            'settings_applied': 'Ayarlar başarıyla uygulandı!',
            'command_failed': 'Komut başarısız oldu: {}',
            'need_sudo': 'Yönetici ayrıcalıkları gerekli',
            'no_ytdlp': 'yt-dlp bulunamadı. Lütfen önce kurunuz.',
            'app_manager': 'Uygulama Yöneticisi',
            'app_manager_title': 'Yüklü Uygulamaları Yönet',
            'app_search_hint': '🔍  Uygulama adını ara...',
            'app_col_name': 'Uygulama Adı',
            'app_col_version': 'Sürüm',
            'app_col_desc': 'Açıklama',
            'app_uninstall': '🗑  Kaldır',
            'app_info': 'ℹ  Bilgi',
            'app_loading': '⏳  Uygulamalar yükleniyor...',
            'app_count': 'Yüklü Uygulamalar',
            'app_reload': '🔄  Yeniden Yükle',
            'app_confirm_uninstall': 'Kaldırmayı Onayla',
            'app_confirm_msg': '"{}" sistemden kaldırılsın mı?\n\nBu işlem geri alınamaz.',
            'app_uninstalling': '{} kaldırılıyor...',
            'app_uninstall_ok': '{} başarıyla kaldırıldı',
            'app_uninstall_fail': 'Kaldırma başarısız:\n{}',
            'app_select_first': 'Lütfen önce bir uygulama seçin',
            'app_info_title': 'Uygulama Bilgisi',
        }

        # uk
        strings_uk = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Головна',
            'keyboard': 'Клавіатура та мова',
            'system_tools': 'Системні інструменти',
            'network': 'Мережа',
            'entertainment': 'Розваги',
            'theme': 'Тема',
            'backup': 'Резервне копіювання',
            'about': 'Про програму',
            'navigation': 'НАВІГАЦІЯ',
            'welcome': 'Ласкаво просимо до Geng Settings Tools',
            'current_user': 'Поточний користувач',
            'hostname': 'Ім’я хоста',
            'home_desc': 'Ваш універсальний набір інструментів для налаштування Linux Mint Cinnamon 22.3.\nЛегко змінюйте комбінації клавіш, керуйте програмами, очищуйте систему, завантажуйте медіафайли та багато іншого.\nВиберіть категорію на бічній панелі, щоб почати — все доступно в один клік!',
            'keyboard_title': 'Налаштування клавіатури та мови',
            'grave_title': 'Переключення мови за допомогою клавіші Grave Accent (~)',
            'grave_desc': 'Використовуйте клавішу Grave Accent щоб перемикати методи введення',
            'alt_shift_title': 'Переключення мови за допомогою Alt+Shift',
            'alt_shift_desc': 'Використовуйте комбінацію клавіш Alt + Shift для перемикання методів введення',
            'custom_key_title': 'Власне призначення клавіш',
            'custom_key_desc': 'Натисніть кнопку нижче, щоб захопити бажану комбінацію клавіш',
            'capture_key': 'Захопити клавішу',
            'apply_now': 'Застосувати зараз',
            'system_title': 'Інструменти керування системою',
            'clean_system': 'Очистити непотрібні файли',
            'clean_system_desc': 'Видалити невикористовувані пакети і очистити кеш',
            'clear_ram': 'Очистити ОЗП/кеш',
            'clear_ram_desc': 'Очистити кеш оперативної пам’яті системи (sync && drop_caches)',
            'driver_manager': 'Менеджер драйверів',
            'driver_manager_desc': 'Відкрити Менеджер драйверів для встановлення/видалення драйверів',
            'flatpak': 'Керувати Flatpak',
            'flatpak_desc': 'Оновлення Flatpak та керування додатками',
            'apt_repair': 'Відновлення APT',
            'apt_repair_desc': 'Відновлення пошкоджених пакетів та оновлення списків',
            'system_monitor': 'Монітор системи',
            'system_monitor_desc': 'Відкрити інструмент моніторингу системи',
            'network_title': 'Керування мережею',
            'network_status': 'Статус мережі',
            'refresh': 'Оновити',
            'restart_network': 'Перезапустити мережу',
            'flush_dns': 'Оновити DNS',
            'renew_dhcp': 'Оновити DHCP',
            'interfaces': 'Мережеві інтерфейси',
            'connections': 'З’єднання',
            'entertainment_title': 'Розваги',
            'install_steam': 'Встановити Steam',
            'install_steam_desc': 'Встановити Steam для ігор',
            'install_wine': 'Встановити Wine',
            'install_wine_desc': 'Встановити Wine для запуску програм Windows',
            'download_media': 'Завантажити відео/аудіо',
            'url_label': 'URL',
            'format_label': 'Формат',
            'video': 'Відео MP4',
            'audio': 'Аудіо M4A',
            'download': 'Завантажити',
            'install_ytdlp': 'Встановити yt-dlp',
            'theme_title': 'Налаштування теми',
            'dark_mode': 'Темний режим',
            'light_mode': 'Світлий режим',
            'mint_y': 'Mint-Y (Світла)',
            'mint_y_dark': 'Mint-Y-Темна',
            'mint_y_dark_aqua': 'Mint-Y-Темна-Аква',
            'apply_theme': 'Застосувати тему',
            'backup_title': 'Резервне копіювання даних',
            'select_drive': 'Виберіть диск призначення',
            'backup_now': 'Почати резервне копіювання',
            'backup_progress': 'Виконується резервне копіювання...',
            'backup_complete': 'Резервне копіювання завершено',
            'backup_failed': 'Резервне копіювання не вдалося',
            'source': 'Джерело',
            'destination': 'Призначення',
            'exclude': 'Виключити',
            'about_title': 'Про програму',
            'developer': 'Розробник',
            'email': 'Електронна пошта',
            'thanks': 'Цей інструмент був створений, щоб допомогти людям легше користуватися Linux.\nДякуємо, що ви є частиною сім’ї Open Source!',
            'donate_sentence': 'Без пива – немає коду. Будь ласка, підтримайте спраглого програміста!',
            'donate_button': 'Пожертвувати на пиво',
            'bank_label': 'Банк',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Ім’я рахунку',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Номер рахунку',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Успішно',
            'error': 'Помилка',
            'settings_applied': 'Налаштування успішно застосовано!',
            'command_failed': 'Команда не виконана: {}',
            'need_sudo': 'Потрібні права адміністратора',
            'no_ytdlp': 'yt-dlp не знайдено. Будь ласка, встановіть його спочатку.',
            'app_manager': 'Менеджер додатків',
            'app_manager_title': 'Керування встановленими додатками',
            'app_search_hint': '🔍  Пошук за назвою додатку...',
            'app_col_name': 'Назва додатку',
            'app_col_version': 'Версія',
            'app_col_desc': 'Опис',
            'app_uninstall': '🗑  Видалити',
            'app_info': 'ℹ  Інформація',
            'app_loading': '⏳  Завантаження додатків...',
            'app_count': 'Встановлені додатки',
            'app_reload': '🔄  Оновити',
            'app_confirm_uninstall': 'Підтвердити видалення',
            'app_confirm_msg': 'Видалити "{}" з системи?\n\nЦю дію не можна скасувати.',
            'app_uninstalling': 'Видалення {}...',
            'app_uninstall_ok': 'Успішно видалено {}',
            'app_uninstall_fail': 'Не вдалося видалити:\n{}',
            'app_select_first': 'Будь ласка, спочатку виберіть додаток',
            'app_info_title': 'Інформація про додаток',
        }

        # ar
        strings_ar = {
            'window_title': 'أدوات إعدادات Geng الإصدار 2.0.6',
            'home': 'الرئيسية',
            'keyboard': 'لوحة المفاتيح واللغة',
            'system_tools': 'أدوات النظام',
            'network': 'الشبكة',
            'entertainment': 'الترفيه',
            'theme': 'الثيم',
            'backup': 'النسخ الاحتياطي',
            'about': 'حول',
            'navigation': 'التنقل',
            'welcome': 'مرحباً بك في أدوات إعدادات Geng',
            'current_user': 'المستخدم الحالي',
            'hostname': 'اسم المضيف',
            'home_desc': 'صندوق أدوات التكوين الشامل لنظام Linux Mint Cinnamon 22.3.\nقم بسهولة بضبط اختصارات لوحة المفاتيح، إدارة التطبيقات، تنظيف النظام، تنزيل الوسائط، وأكثر.\nاختر فئة من الشريط الجانبي للبدء — كل شيء على بعد نقرة واحدة!',
            'keyboard_title': 'إعدادات لوحة المفاتيح واللغة',
            'grave_title': 'تبديل اللغة بمفتاح التاكيد المائل (~)',
            'grave_desc': 'استخدم مفتاح التاكيد المائل لتبديل طرق الإدخال',
            'alt_shift_title': 'تبديل اللغة بمفتاح Alt+Shift',
            'alt_shift_desc': 'استخدم مفتاحي Alt + Shift لتبديل طرق الإدخال',
            'custom_key_title': 'اختصار مخصص',
            'custom_key_desc': 'اضغط الزر أدناه لالتقاط تركيبة المفاتيح المطلوبة',
            'capture_key': 'التقاط مفتاح',
            'apply_now': 'تطبيق الآن',
            'system_title': 'أدوات إدارة النظام',
            'clean_system': 'تنظيف الملفات غير المرغوب فيها',
            'clean_system_desc': 'إزالة الحزم غير المستخدمة وتنظيف الكاش',
            'clear_ram': 'تنظيف الذاكرة العشوائية/الكاش',
            'clear_ram_desc': 'تنظيف ذاكرة النظام المؤقتة (sync && drop_caches)',
            'driver_manager': 'مدير التعريفات',
            'driver_manager_desc': 'فتح مدير التعريفات لتثبيت/إزالة التعريفات',
            'flatpak': 'إدارة Flatpak',
            'flatpak_desc': 'تحديث Flatpak وإدارة التطبيقات',
            'apt_repair': 'إصلاح APT',
            'apt_repair_desc': 'إصلاح الحزم التالفة وتحديث القوائم',
            'system_monitor': 'مراقب النظام',
            'system_monitor_desc': 'فتح أداة مراقبة النظام',
            'network_title': 'إدارة الشبكة',
            'network_status': 'حالة الشبكة',
            'refresh': 'تحديث',
            'restart_network': 'إعادة تشغيل الشبكة',
            'flush_dns': 'تفريغ DNS',
            'renew_dhcp': 'تجديد DHCP',
            'interfaces': 'واجهات الشبكة',
            'connections': 'الاتصالات',
            'entertainment_title': 'الترفيه',
            'install_steam': 'تثبيت Steam',
            'install_steam_desc': 'تثبيت Steam للألعاب',
            'install_wine': 'تثبيت Wine',
            'install_wine_desc': 'تثبيت Wine لتشغيل برامج ويندوز',
            'download_media': 'تحميل فيديو/صوت',
            'url_label': 'الرابط',
            'format_label': 'الصيغة',
            'video': 'فيديو MP4',
            'audio': 'صوت M4A',
            'download': 'تحميل',
            'install_ytdlp': 'تثبيت yt-dlp',
            'theme_title': 'تخصيص الثيم',
            'dark_mode': 'الوضع الداكن',
            'light_mode': 'الوضع الفاتح',
            'mint_y': 'Mint-Y (فاتح)',
            'mint_y_dark': 'Mint-Y-داكن',
            'mint_y_dark_aqua': 'Mint-Y-داكن-أكوا',
            'apply_theme': 'تطبيق الثيم',
            'backup_title': 'النسخ الاحتياطي للبيانات',
            'select_drive': 'اختر القرص الوجهة',
            'backup_now': 'ابدأ النسخ الاحتياطي',
            'backup_progress': 'جارٍ النسخ الاحتياطي...',
            'backup_complete': 'اكتمل النسخ الاحتياطي',
            'backup_failed': 'فشل النسخ الاحتياطي',
            'source': 'المصدر',
            'destination': 'الوجهة',
            'exclude': 'استثناء',
            'about_title': 'حول',
            'developer': 'المطور',
            'email': 'البريد الإلكتروني',
            'thanks': 'تم إنشاء هذه الأداة لمساعدة الناس على استخدام لينكس بسهولة أكبر.\nشكراً لكونك جزءًا من عائلة المصدر المفتوح!',
            'donate_sentence': 'لا بيرة، لا كود. من فضلك ادعم مبرمجاً عطشاناً!',
            'donate_button': 'تبرع بمال للبيرة',
            'bank_label': 'البنك',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'اسم الحساب',
            'account_name': 'السيد ثاماسورن موسيكابان',
            'account_number_label': 'رقم الحساب',
            'account_number': '1192455177',
            'paypal_label': 'باي بال',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'بيتكوين (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'نجاح',
            'error': 'خطأ',
            'settings_applied': 'تم تطبيق الإعدادات بنجاح!',
            'command_failed': 'فشل الأمر: {}',
            'need_sudo': 'مطلوبة صلاحيات المشرف',
            'no_ytdlp': 'لم يتم العثور على yt-dlp. الرجاء تثبيته أولاً.',
            'app_manager': 'مدير التطبيقات',
            'app_manager_title': 'إدارة التطبيقات المثبتة',
            'app_search_hint': '🔍  ابحث عن اسم التطبيق...',
            'app_col_name': 'اسم التطبيق',
            'app_col_version': 'الإصدار',
            'app_col_desc': 'الوصف',
            'app_uninstall': '🗑  إلغاء التثبيت',
            'app_info': 'ℹ  معلومات',
            'app_loading': '⏳  جاري تحميل التطبيقات...',
            'app_count': 'التطبيقات المثبتة',
            'app_reload': '🔄  إعادة تحميل',
            'app_confirm_uninstall': 'تأكيد إلغاء التثبيت',
            'app_confirm_msg': 'هل تود إلغاء تثبيت "{}" من النظام؟\n\nلا يمكن التراجع عن هذا الإجراء.',
            'app_uninstalling': 'جارٍ إلغاء التثبيت {}...',
            'app_uninstall_ok': 'تم إلغاء التثبيت بنجاح {}',
            'app_uninstall_fail': 'فشل إلغاء التثبيت:\n{}',
            'app_select_first': 'يرجى اختيار تطبيق أولاً',
            'app_info_title': 'معلومات التطبيق',
        }

        # ko
        strings_ko = {
            'window_title': 'Geng 설정 도구 v2.0.6',
            'home': '홈',
            'keyboard': '키보드 및 언어',
            'system_tools': '시스템 도구',
            'network': '네트워크',
            'entertainment': '엔터테인먼트',
            'theme': '테마',
            'backup': '백업',
            'about': '정보',
            'navigation': '내비게이션',
            'welcome': 'Geng 설정 도구에 오신 것을 환영합니다',
            'current_user': '현재 사용자',
            'hostname': '호스트 이름',
            'home_desc': 'Linux Mint Cinnamon 22.3용 올인원 구성 도구 상자입니다.\n키보드 단축키를 쉽게 조정하고, 앱을 관리하며, 시스템을 정리하고, 미디어를 다운로드하는 등 다양한 기능을 제공합니다.\n사이드바에서 카테고리를 선택하여 시작하세요 — 모든 것이 클릭 한 번으로 가능합니다!',
            'keyboard_title': '키보드 및 언어 설정',
            'grave_title': 'Grave Accent (~)로 언어 전환',
            'grave_desc': 'Grave Accent 키를 사용하여 입력 방식을 전환합니다',
            'alt_shift_title': 'Alt+Shift로 언어 전환',
            'alt_shift_desc': 'Alt + Shift 키를 사용하여 입력 방식을 전환합니다',
            'custom_key_title': '사용자 지정 키 바인딩',
            'custom_key_desc': '아래 버튼을 눌러 원하는 키 조합을 캡처하세요',
            'capture_key': '키 캡처',
            'apply_now': '지금 적용',
            'system_title': '시스템 관리 도구',
            'clean_system': '정크 파일 정리',
            'clean_system_desc': '사용하지 않는 패키지 제거 및 캐시 정리',
            'clear_ram': 'RAM/캐시 정리',
            'clear_ram_desc': '시스템 메모리 캐시 정리(sync && drop_caches)',
            'driver_manager': '드라이버 관리자',
            'driver_manager_desc': '드라이버 설치/제거를 위해 드라이버 관리자를 엽니다',
            'flatpak': 'Flatpak 관리',
            'flatpak_desc': 'Flatpak 업데이트 및 애플리케이션 관리',
            'apt_repair': 'APT 수리',
            'apt_repair_desc': '손상된 패키지 수리 및 목록 업데이트',
            'system_monitor': '시스템 모니터',
            'system_monitor_desc': '시스템 모니터링 도구 열기',
            'network_title': '네트워크 관리',
            'network_status': '네트워크 상태',
            'refresh': '새로고침',
            'restart_network': '네트워크 재시작',
            'flush_dns': 'DNS 플러시',
            'renew_dhcp': 'DHCP 갱신',
            'interfaces': '네트워크 인터페이스',
            'connections': '연결',
            'entertainment_title': '엔터테인먼트',
            'install_steam': 'Steam 설치',
            'install_steam_desc': '게임을 위한 Steam 설치',
            'install_wine': 'Wine 설치',
            'install_wine_desc': 'Windows 프로그램 실행을 위한 Wine 설치',
            'download_media': '비디오/오디오 다운로드',
            'url_label': 'URL',
            'format_label': '포맷',
            'video': '비디오 MP4',
            'audio': '오디오 M4A',
            'download': '다운로드',
            'install_ytdlp': 'yt-dlp 설치',
            'theme_title': '테마 맞춤 설정',
            'dark_mode': '다크 모드',
            'light_mode': '라이트 모드',
            'mint_y': 'Mint-Y (라이트)',
            'mint_y_dark': 'Mint-Y-다크',
            'mint_y_dark_aqua': 'Mint-Y-다크-아쿠아',
            'apply_theme': '테마 적용',
            'backup_title': '데이터 백업',
            'select_drive': '대상 드라이브 선택',
            'backup_now': '백업 시작',
            'backup_progress': '백업 진행 중...',
            'backup_complete': '백업 완료',
            'backup_failed': '백업 실패',
            'source': '원본',
            'destination': '대상',
            'exclude': '제외',
            'about_title': '정보',
            'developer': '개발자',
            'email': '이메일',
            'thanks': '이 도구는 사람들이 Linux를 더 쉽게 사용할 수 있도록 제작되었습니다.\n오픈 소스 가족의 일원이 되어 주셔서 감사합니다!',
            'donate_sentence': '맥주 없이는 코드도 없습니다. 갈증 나는 프로그래머를 지원해 주세요!',
            'donate_button': '맥주 기부하기',
            'bank_label': '은행',
            'bank_name': '카시콘 타이',
            'account_name_label': '계좌 이름',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': '계좌 번호',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': '비트코인 (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': '성공',
            'error': '오류',
            'settings_applied': '설정이 성공적으로 적용되었습니다!',
            'command_failed': '명령 실패: {}',
            'need_sudo': '관리자 권한이 필요합니다',
            'no_ytdlp': 'yt-dlp를 찾을 수 없습니다. 먼저 설치해 주세요.',
            'app_manager': '앱 관리자',
            'app_manager_title': '설치된 애플리케이션 관리',
            'app_search_hint': '🔍  앱 이름 검색...',
            'app_col_name': '앱 이름',
            'app_col_version': '버전',
            'app_col_desc': '설명',
            'app_uninstall': '🗑  제거',
            'app_info': 'ℹ  정보',
            'app_loading': '⏳  애플리케이션 로딩 중...',
            'app_count': '설치된 앱 수',
            'app_reload': '🔄  새로고침',
            'app_confirm_uninstall': '제거 확인',
            'app_confirm_msg': '"{}"을(를) 시스템에서 제거하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.',
            'app_uninstalling': '{} 제거 중...',
            'app_uninstall_ok': '{}이(가) 성공적으로 제거되었습니다',
            'app_uninstall_fail': '제거 실패:\n{}',
            'app_select_first': '먼저 애플리케이션을 선택해 주세요',
            'app_info_title': '앱 정보',
        }

        # vi
        strings_vi = {
            'window_title': 'Công cụ Cài đặt Geng v2.0.6',
            'home': 'Trang chủ',
            'keyboard': 'Bàn phím & Ngôn ngữ',
            'system_tools': 'Công cụ Hệ thống',
            'network': 'Mạng',
            'entertainment': 'Giải trí',
            'theme': 'Chủ đề',
            'backup': 'Sao lưu',
            'about': 'Thông tin',
            'navigation': 'ĐỊNH HƯỚNG',
            'welcome': 'Chào mừng đến với Công cụ Cài đặt Geng',
            'current_user': 'Người dùng hiện tại',
            'hostname': 'Tên máy',
            'home_desc': 'Bộ công cụ cấu hình tích hợp dành cho Linux Mint Cinnamon 22.3.\nDễ dàng tùy chỉnh phím tắt, quản lý ứng dụng, dọn dẹp hệ thống, tải media, và nhiều hơn nữa.\nChọn một danh mục từ thanh bên để bắt đầu — mọi thứ chỉ với một cú nhấp chuột!',
            'keyboard_title': 'Cài đặt Bàn phím & Ngôn ngữ',
            'grave_title': 'Chuyển ngôn ngữ bằng phím Grave Accent (~)',
            'grave_desc': 'Sử dụng phím Grave Accent để chuyển phương thức nhập',
            'alt_shift_title': 'Chuyển ngôn ngữ bằng Alt+Shift',
            'alt_shift_desc': 'Sử dụng phím Alt + Shift để chuyển phương thức nhập',
            'custom_key_title': 'Phím tắt tùy chỉnh',
            'custom_key_desc': 'Nhấn nút bên dưới để ghi lại tổ hợp phím mong muốn',
            'capture_key': 'Ghi lại phím',
            'apply_now': 'Áp dụng ngay',
            'system_title': 'Công cụ Quản lý Hệ thống',
            'clean_system': 'Dọn dẹp Tệp rác',
            'clean_system_desc': 'Loại bỏ các gói không sử dụng và xóa bộ nhớ đệm',
            'clear_ram': 'Xóa RAM/Bộ đệm',
            'clear_ram_desc': 'Xóa bộ nhớ đệm hệ thống (sync && drop_caches)',
            'driver_manager': 'Quản lý Driver',
            'driver_manager_desc': 'Mở Quản lý Driver để cài đặt/gỡ bỏ driver',
            'flatpak': 'Quản lý Flatpak',
            'flatpak_desc': 'Cập nhật Flatpak và quản lý ứng dụng',
            'apt_repair': 'Sửa chữa APT',
            'apt_repair_desc': 'Sửa chữa gói hỏng và cập nhật danh sách',
            'system_monitor': 'Giám sát Hệ thống',
            'system_monitor_desc': 'Mở công cụ giám sát hệ thống',
            'network_title': 'Quản lý Mạng',
            'network_status': 'Trạng thái Mạng',
            'refresh': 'Làm mới',
            'restart_network': 'Khởi động lại Mạng',
            'flush_dns': 'Xóa DNS',
            'renew_dhcp': 'Gia hạn DHCP',
            'interfaces': 'Giao diện Mạng',
            'connections': 'Kết nối',
            'entertainment_title': 'Giải trí',
            'install_steam': 'Cài đặt Steam',
            'install_steam_desc': 'Cài đặt Steam để chơi game',
            'install_wine': 'Cài đặt Wine',
            'install_wine_desc': 'Cài đặt Wine để chạy chương trình Windows',
            'download_media': 'Tải Video/Âm thanh',
            'url_label': 'URL',
            'format_label': 'Định dạng',
            'video': 'Video MP4',
            'audio': 'Âm thanh M4A',
            'download': 'Tải về',
            'install_ytdlp': 'Cài đặt yt-dlp',
            'theme_title': 'Tùy chỉnh Chủ đề',
            'dark_mode': 'Chế độ Tối',
            'light_mode': 'Chế độ Sáng',
            'mint_y': 'Mint-Y (Sáng)',
            'mint_y_dark': 'Mint-Y-Tối',
            'mint_y_dark_aqua': 'Mint-Y-Tối-Aqua',
            'apply_theme': 'Áp dụng Chủ đề',
            'backup_title': 'Sao lưu Dữ liệu',
            'select_drive': 'Chọn ổ đĩa đích',
            'backup_now': 'Bắt đầu Sao lưu',
            'backup_progress': 'Đang sao lưu...',
            'backup_complete': 'Sao lưu hoàn tất',
            'backup_failed': 'Sao lưu thất bại',
            'source': 'Nguồn',
            'destination': 'Đích',
            'exclude': 'Loại trừ',
            'about_title': 'Thông tin',
            'developer': 'Nhà phát triển',
            'email': 'Email',
            'thanks': 'Công cụ này được tạo ra để giúp mọi người sử dụng Linux dễ dàng hơn.\nCảm ơn bạn đã là một phần của gia đình Mã Nguồn Mở!',
            'donate_sentence': 'Không bia, không code. Vui lòng ủng hộ một lập trình viên đang khát!',
            'donate_button': 'Ủng hộ tiền bia',
            'bank_label': 'Ngân hàng',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Tên tài khoản',
            'account_name': 'Ông Thammasorn Musikapan',
            'account_number_label': 'Số tài khoản',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Thành công',
            'error': 'Lỗi',
            'settings_applied': 'Cài đặt đã được áp dụng thành công!',
            'command_failed': 'Lệnh thất bại: {}',
            'need_sudo': 'Yêu cầu quyền quản trị',
            'no_ytdlp': 'Không tìm thấy yt-dlp. Vui lòng cài đặt trước.',
            'app_manager': 'Quản lý Ứng dụng',
            'app_manager_title': 'Quản lý Ứng dụng đã cài đặt',
            'app_search_hint': '🔍  Tìm kiếm tên ứng dụng...',
            'app_col_name': 'Tên ứng dụng',
            'app_col_version': 'Phiên bản',
            'app_col_desc': 'Mô tả',
            'app_uninstall': '🗑  Gỡ cài đặt',
            'app_info': 'ℹ  Thông tin',
            'app_loading': '⏳  Đang tải ứng dụng...',
            'app_count': 'Ứng dụng đã cài đặt',
            'app_reload': '🔄  Tải lại',
            'app_confirm_uninstall': 'Xác nhận Gỡ cài đặt',
            'app_confirm_msg': 'Gỡ cài đặt "{}" khỏi hệ thống?\n\nHành động này không thể hoàn tác.',
            'app_uninstalling': 'Đang gỡ cài đặt {}...',
            'app_uninstall_ok': 'Đã gỡ cài đặt thành công {}',
            'app_uninstall_fail': 'Gỡ cài đặt thất bại:\n{}',
            'app_select_first': 'Vui lòng chọn ứng dụng trước',
            'app_info_title': 'Thông tin Ứng dụng',
        }

        # ms
        strings_ms = {
            'window_title': 'Alat Tetapan Geng v2.0.6',
            'home': 'Laman Utama',
            'keyboard': 'Papan Kekunci & Bahasa',
            'system_tools': 'Alat Sistem',
            'network': 'Rangkaian',
            'entertainment': 'Hiburan',
            'theme': 'Tema',
            'backup': 'Sandaran',
            'about': 'Mengenai',
            'navigation': 'NAVIGASI',
            'welcome': 'Selamat datang ke Alat Tetapan Geng',
            'current_user': 'Pengguna semasa',
            'hostname': 'Hostname',
            'home_desc': 'Kotak alat konfigurasi serba guna anda untuk Linux Mint Cinnamon 22.3.\nLaraskan pintasan papan kekunci dengan mudah, urus aplikasi, bersihkan sistem anda, muat turun media, dan banyak lagi.\nPilih kategori dari bar sisi untuk bermula — semuanya hanya dengan satu klik!',
            'keyboard_title': 'Tetapan Papan Kekunci & Bahasa',
            'grave_title': 'Tukar bahasa dengan Accent Grave (~)',
            'grave_desc': 'Gunakan kunci Accent Grave untuk menukar kaedah input',
            'alt_shift_title': 'Tukar bahasa dengan Alt+Shift',
            'alt_shift_desc': 'Gunakan kekunci Alt + Shift untuk menukar kaedah input',
            'custom_key_title': 'Pementasan Kekunci Tersuai',
            'custom_key_desc': 'Tekan butang di bawah untuk rakam gabungan kekunci yang dikehendaki',
            'capture_key': 'Rakaman Kekunci',
            'apply_now': 'Terapkan Sekarang',
            'system_title': 'Alat Pengurusan Sistem',
            'clean_system': 'Bersihkan Fail Sampah',
            'clean_system_desc': 'Alih keluar pakej tidak digunakan dan kosongkan cache',
            'clear_ram': 'Kosongkan RAM/Cache',
            'clear_ram_desc': 'Kosongkan cache memori sistem (sync && drop_caches)',
            'driver_manager': 'Pengurus Pemacu',
            'driver_manager_desc': 'Buka Pengurus Pemacu untuk pasang/tanggalkan pemacu',
            'flatpak': 'Urus Flatpak',
            'flatpak_desc': 'Kemas kini Flatpak dan urus aplikasi',
            'apt_repair': 'Pembaikan APT',
            'apt_repair_desc': 'Betulkan pakej rosak dan kemas kini senarai',
            'system_monitor': 'Pemantau Sistem',
            'system_monitor_desc': 'Buka alat pemantauan sistem',
            'network_title': 'Pengurusan Rangkaian',
            'network_status': 'Status Rangkaian',
            'refresh': 'Segarkan',
            'restart_network': 'Mulakan Semula Rangkaian',
            'flush_dns': 'Kosongkan DNS',
            'renew_dhcp': 'Perbaharui DHCP',
            'interfaces': 'Antara Muka Rangkaian',
            'connections': 'Sambungan',
            'entertainment_title': 'Hiburan',
            'install_steam': 'Pasang Steam',
            'install_steam_desc': 'Pasang Steam untuk permainan',
            'install_wine': 'Pasang Wine',
            'install_wine_desc': 'Pasang Wine untuk jalankan program Windows',
            'download_media': 'Muat Turun Video/Audio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Muat Turun',
            'install_ytdlp': 'Pasang yt-dlp',
            'theme_title': 'Penyesuaian Tema',
            'dark_mode': 'Mod Gelap',
            'light_mode': 'Mod Terang',
            'mint_y': 'Mint-Y (Terang)',
            'mint_y_dark': 'Mint-Y-Gelap',
            'mint_y_dark_aqua': 'Mint-Y-Gelap-Aqua',
            'apply_theme': 'Terapkan Tema',
            'backup_title': 'Sandaran Data',
            'select_drive': 'Pilih pemacu destinasi',
            'backup_now': 'Mula Sandaran',
            'backup_progress': 'Sedang membuat sandaran...',
            'backup_complete': 'Sandaran Selesai',
            'backup_failed': 'Sandaran Gagal',
            'source': 'Sumber',
            'destination': 'Destinasi',
            'exclude': 'Kecualikan',
            'about_title': 'Mengenai',
            'developer': 'Pembangun',
            'email': 'Emel',
            'thanks': 'Alat ini dicipta untuk membantu orang menggunakan Linux dengan lebih mudah.\nTerima kasih kerana menjadi sebahagian daripada keluarga Sumber Terbuka!',
            'donate_sentence': 'Tanpa bir, tiada kod. Sila sokong pengaturcara yang dahagakan!',
            'donate_button': 'Derma Wang Bir',
            'bank_label': 'Bank',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nama Akaun',
            'account_name': 'Encik Thammasorn Musikapan',
            'account_number_label': 'Nombor Akaun',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Berjaya',
            'error': 'Ralat',
            'settings_applied': 'Tetapan telah berjaya diterapkan!',
            'command_failed': 'Arahan gagal: {}',
            'need_sudo': 'Kebenaran pentadbir diperlukan',
            'no_ytdlp': 'yt-dlp tidak dijumpai. Sila pasang dahulu.',
            'app_manager': 'Pengurus Aplikasi',
            'app_manager_title': 'Urus Aplikasi Terpasang',
            'app_search_hint': '🔍  Cari nama aplikasi...',
            'app_col_name': 'Nama Aplikasi',
            'app_col_version': 'Versi',
            'app_col_desc': 'Penerangan',
            'app_uninstall': '🗑  Nyahpasang',
            'app_info': 'ℹ  Maklumat',
            'app_loading': '⏳  Memuatkan aplikasi...',
            'app_count': 'Aplikasi Terpasang',
            'app_reload': '🔄  Muat Semula',
            'app_confirm_uninstall': 'Sahkan Nyahpasang',
            'app_confirm_msg': 'Nyahpasang "{}" dari sistem?\n\nTindakan ini tidak boleh dibatalkan.',
            'app_uninstalling': 'Sedang nyahpasang {}...',
            'app_uninstall_ok': 'Berjaya nyahpasang {}',
            'app_uninstall_fail': 'Gagal nyahpasang:\n{}',
            'app_select_first': 'Sila pilih aplikasi terlebih dahulu',
            'app_info_title': 'Maklumat Aplikasi',
        }

        # hmn
        strings_hmn = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Tsev',
            'keyboard': 'Nplaum & Lus',
            'system_tools': 'Cov Cuab Yeej System',
            'network': 'Chaw Network',
            'entertainment': 'Ua Si Lom Zem',
            'theme': 'Tsis Siv Neeg',
            'backup': 'Thaub Qhia',
            'about': 'Hais Txog',
            'navigation': 'TUS TXAWV TXUJ CI',
            'welcome': 'Txais Tos Koj Los Rau Geng Settings Tools',
            'current_user': 'Tus neeg siv tam sim no',
            'hostname': 'Lub npe tshuab',
            'home_desc': 'Koj daim ntawv teeb tsa tag nrho hauv ib qho nyiaj rau Linux Mint Cinnamon 22.3.\nUa kom yooj yim kho keyboard shortcuts, tswj apps, huv si koj lub system, rub tawm media, thiab ntau ntxiv.\nXaiv ib pawg ntawm sab laj los pib — txhua yam nyob ib qho nias!',
            'keyboard_title': 'Nplaum & Lus Teeb',
            'grave_title': 'Hloov lus nrog Grave Accent (~)',
            'grave_desc': 'Siv Grave Accent yuam kom hloov hom ntawv nkag',
            'alt_shift_title': 'Hloov lus nrog Alt+Shift',
            'alt_shift_desc': 'Siv Alt + Shift cov yuam sij hloov hom ntawv nkag',
            'custom_key_title': 'Yuav tsum-programmed yuam sij',
            'custom_key_desc': 'Nias lub khawm hauv qab no los txiav txim siab qhov yuam sij sib xyaw uas xav tau',
            'capture_key': 'Tuav Yuam Sij',
            'apply_now': 'Siv Tam Sim No',
            'system_title': 'Cov Cuab Yeej Tswj System',
            'clean_system': 'Hloov Cov Ntaub Ntawv Pov Tseg',
            'clean_system_desc': 'Tshem tawm cov pob khoom uas tsis siv thiab ntxuav kev cache',
            'clear_ram': 'Ntxuav RAM/Cache',
            'clear_ram_desc': 'Ntxuav kev nco hauv system (sync && drop_caches)',
            'driver_manager': 'Tus Thawj Tswj Tsav Tsheb',
            'driver_manager_desc': 'Qhib Tus Thawj Tswj Tsav Tsheb mus txhim kho/tshem tsav tsheb',
            'flatpak': 'Tswj Flatpak',
            'flatpak_desc': 'Kho tshiab Flatpak thiab tswj cov ntawv thov',
            'apt_repair': 'APT Kho Dua',
            'apt_repair_desc': 'Kho cov pob khoom puas thiab hloov tshiab daim ntawv',
            'system_monitor': 'System Monitor',
            'system_monitor_desc': 'Qhib cuab yeej saib xyuas system',
            'network_title': 'Tswj Kev Network',
            'network_status': 'Xeev Network',
            'refresh': 'Refresh',
            'restart_network': 'Pib Dua Network',
            'flush_dns': 'Tshuav DNS',
            'renew_dhcp': 'Kho DHCP Tshiab',
            'interfaces': 'Chaw Network Interfaces',
            'connections': 'Connections',
            'entertainment_title': 'Ua Si Lom Zem',
            'install_steam': 'Txhim Kho Steam',
            'install_steam_desc': 'Txhim kho Steam rau kev ua si',
            'install_wine': 'Txhim Kho Wine',
            'install_wine_desc': 'Txhim kho Wine los khiav Windows cov program',
            'download_media': 'Rub Tawm Video/Audio',
            'url_label': 'URL',
            'format_label': 'Hom',
            'video': 'Video MP4',
            'audio': 'Suab M4A',
            'download': 'Rub Tawm',
            'install_ytdlp': 'Txhim Kho yt-dlp',
            'theme_title': 'Kev Kho Txawj Ntse',
            'dark_mode': 'Hom Dub',
            'light_mode': 'Hom Qhov Muag',
            'mint_y': 'Mint-Y (Qhov Muag)',
            'mint_y_dark': 'Mint-Y-Dub',
            'mint_y_dark_aqua': 'Mint-Y-Dub-Tsaus Ntsuab',
            'apply_theme': 'Siv Tsis Siv Neeg',
            'backup_title': 'Thaub Qhia Cov Ntaub Ntawv',
            'select_drive': 'Xaiv tsav tsheb qhov chaw khaws cia',
            'backup_now': 'Pib Thaub Qhia',
            'backup_progress': 'Tab tom thaub qab...',
            'backup_complete': 'Thaub Qhia Ua Tau Txhaum Cai',
            'backup_failed': 'Thaub Qhia Tsis Tau Zoo',
            'source': 'Pob',
            'destination': 'Qhov chaw',
            'exclude': 'Tshem tawm',
            'about_title': 'Hais Txog',
            'developer': 'Tus tsim qauv',
            'email': 'Email',
            'thanks': 'Cov cuab yeej no tau tsim los pab neeg siv Linux kom yooj yim dua.\nUa tsaug rau koj ua ib feem ntawm Open Source tsev neeg!',
            'donate_sentence': 'Tsis muaj cawv, tsis muaj code. Thov txhawb nqa tus kws sau ntawv uas haus cawv tshua!',
            'donate_button': 'Pub Cawv Nyiaj',
            'bank_label': 'Txhab nyiaj',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Lub npe nyiaj txiag',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Tus lej nyiaj txiag',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Ua Tau Zoo',
            'error': 'Yuav Tseem Muaj Kev Pab',
            'settings_applied': 'Teeb Npe Tau Siv Zoo!',
            'command_failed': 'Tsab Cai ua tsis tiav: {}',
            'need_sudo': 'Yuav tsum tau administrator txoj cai',
            'no_ytdlp': 'yt-dlp tsis pom. Thov nruab ua ntej.',
            'app_manager': 'Cov ntaub ntawv App Manager',
            'app_manager_title': 'Tswj Cov Apps Txhim Kho',
            'app_search_hint': '🔍  Nrhiav npe app...',
            'app_col_name': 'Npe App',
            'app_col_version': 'Version',
            'app_col_desc': 'Kev piav qhia',
            'app_uninstall': '🗑  Tshem tawm',
            'app_info': 'ℹ  Paub meej',
            'app_loading': '⏳  Tab tom thauj cov ntawv thov...',
            'app_count': 'Cov Apps Txhim Kho',
            'app_reload': '🔄  Rov Thaub Tsiaj',
            'app_confirm_uninstall': 'Pom zoo Tshem tawm',
            'app_confirm_msg': 'Tshem "{}" ntawm system?\n\nQhov no tsis tau rov qab.',
            'app_uninstalling': 'Tab tom tshem tawm {}...',
            'app_uninstall_ok': 'Ua tau zoo tshem tawm {}',
            'app_uninstall_fail': 'Tshem tawm tsis tau:\n{}',
            'app_select_first': 'Thov xaiv ib qho app ua ntej',
            'app_info_title': 'Paub Meej App',
        }

        # ca
        strings_ca = {
            'window_title': 'Geng Settings Tools v2.0.6',
            'home': 'Inici',
            'keyboard': 'Teclat i idioma',
            'system_tools': 'Eines del sistema',
            'network': 'Xarxa',
            'entertainment': 'Entreteniment',
            'theme': 'Tema',
            'backup': 'Còpia de seguretat',
            'about': 'Quant a',
            'navigation': 'NAVEGACIÓ',
            'welcome': 'Benvingut a Geng Settings Tools',
            'current_user': 'Usuari actual',
            'hostname': 'Nom de l\'amfitrió',
            'home_desc': 'La vostra eina tot en un per configurar Linux Mint Cinnamon 22.3.\nModifiqueu fàcilment les dreceres de teclat, gestioneu aplicacions, netegeu el sistema, descarregueu media i més.\nSeleccioneu una categoria de la barra lateral per començar — tot està a un clic!',
            'keyboard_title': 'Configuració de teclat i idioma',
            'grave_title': 'Canvia l\'idioma amb l\'accent greu (~)',
            'grave_desc': 'Utilitzeu la tecla d\'accent greu per canviar els mètodes d\'entrada',
            'alt_shift_title': 'Canvia l\'idioma amb Alt+Maj',
            'alt_shift_desc': 'Utilitzeu les tecles Alt + Maj per canviar els mètodes d\'entrada',
            'custom_key_title': 'Assignació de tecla personalitzada',
            'custom_key_desc': 'Premeu el botó següent per capturar la combinació de tecles desitjada',
            'capture_key': 'Capturar tecla',
            'apply_now': 'Aplica ara',
            'system_title': 'Eines de gestió del sistema',
            'clean_system': 'Neteja fitxers brossa',
            'clean_system_desc': 'Elimina paquets no usats i neteja la memòria cau',
            'clear_ram': 'Neteja la RAM/memòria cau',
            'clear_ram_desc': 'Neteja la memòria cau del sistema (sync && drop_caches)',
            'driver_manager': 'Gestor de controladors',
            'driver_manager_desc': 'Obre el gestor de controladors per instal·lar/eliminar controladors',
            'flatpak': 'Gestiona Flatpak',
            'flatpak_desc': 'Actualitza Flatpak i gestiona aplicacions',
            'apt_repair': 'Reparació APT',
            'apt_repair_desc': 'Repara paquets trencats i actualitza les llistes',
            'system_monitor': 'Monitor del sistema',
            'system_monitor_desc': 'Obre l\'eina de monitorització del sistema',
            'network_title': 'Gestió de xarxa',
            'network_status': 'Estat de la xarxa',
            'refresh': 'Refresca',
            'restart_network': 'Reinicia la xarxa',
            'flush_dns': 'Neteja DNS',
            'renew_dhcp': 'Renova DHCP',
            'interfaces': 'Interfícies de xarxa',
            'connections': 'Connexions',
            'entertainment_title': 'Entreteniment',
            'install_steam': 'Instal·la Steam',
            'install_steam_desc': 'Instal·la Steam per jugar',
            'install_wine': 'Instal·la Wine',
            'install_wine_desc': 'Instal·la Wine per executar programes de Windows',
            'download_media': 'Descarrega vídeo/àudio',
            'url_label': 'URL',
            'format_label': 'Format',
            'video': 'Vídeo MP4',
            'audio': 'Àudio M4A',
            'download': 'Descarrega',
            'install_ytdlp': 'Instal·la yt-dlp',
            'theme_title': 'Personalització de tema',
            'dark_mode': 'Mode fosc',
            'light_mode': 'Mode clar',
            'mint_y': 'Mint-Y (clar)',
            'mint_y_dark': 'Mint-Y-Fosc',
            'mint_y_dark_aqua': 'Mint-Y-Fosc-Aqua',
            'apply_theme': 'Aplica el tema',
            'backup_title': 'Còpia de seguretat de dades',
            'select_drive': 'Seleccioneu la unitat de destinació',
            'backup_now': 'Inicia la còpia de seguretat',
            'backup_progress': 'Fent còpia de seguretat...',
            'backup_complete': 'Còpia de seguretat completa',
            'backup_failed': 'La còpia de seguretat ha fallat',
            'source': 'Origen',
            'destination': 'Destí',
            'exclude': 'Exclou',
            'about_title': 'Quant a',
            'developer': 'Desenvolupador',
            'email': 'Correu electrònic',
            'thanks': 'Aquesta eina es va crear per ajudar a la gent a utilitzar Linux fàcilment.\nGràcies per formar part de la família de programari lliure!',
            'donate_sentence': 'Sense cervesa, no hi ha codi. Si us plau, doneu suport a un programador sedientos!',
            'donate_button': 'Dona diners per cervesa',
            'bank_label': 'Banc',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nom del compte',
            'account_name': 'Mr. Thammasorn Musikapan',
            'account_number_label': 'Número de compte',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Èxit',
            'error': 'Error',
            'settings_applied': 'Configuracions aplicades correctament!',
            'command_failed': 'Comanda fallida: {}',
            'need_sudo': 'Es requereixen privilegis d\'administrador',
            'no_ytdlp': 'No s\'ha trobat yt-dlp. Si us plau, instal·leu-lo primer.',
            'app_manager': 'Gestor d\'aplicacions',
            'app_manager_title': 'Gestiona les aplicacions instal·lades',
            'app_search_hint': '🔍  Busca el nom de l\'aplicació...',
            'app_col_name': 'Nom de l\'aplicació',
            'app_col_version': 'Versió',
            'app_col_desc': 'Descripció',
            'app_uninstall': '🗑  Desinstal·la',
            'app_info': 'ℹ  Informació',
            'app_loading': '⏳  Carregant aplicacions...',
            'app_count': 'Aplicacions instal·lades',
            'app_reload': '🔄  Recarrega',
            'app_confirm_uninstall': 'Confirma desinstal·lació',
            'app_confirm_msg': 'Desinstal·lar "{}" del sistema?\n\nAquesta acció és irreversible.',
            'app_uninstalling': 'Desinstal·lant {}...',
            'app_uninstall_ok': 'S\'ha desinstal·lat correctament {}',
            'app_uninstall_fail': 'Error en desinstal·lar:\n{}',
            'app_select_first': 'Si us plau, seleccioneu una aplicació primer',
            'app_info_title': 'Informació de l\'aplicació',
        }

        # ar-SD
        strings_ar_sd = {
            'window_title': 'أدوات إعدادات Geng الإصدار 2.0.6',
            'home': 'الرئيسية',
            'keyboard': 'لوحة المفاتيح & اللغة',
            'system_tools': 'أدوات النظام',
            'network': 'الشبكة',
            'entertainment': 'الترفيه',
            'theme': 'السمة',
            'backup': 'النسخ الاحتياطي',
            'about': 'حول',
            'navigation': 'التنقل',
            'welcome': 'مرحباً بك في أدوات إعدادات Geng',
            'current_user': 'المستخدم الحالي',
            'hostname': 'اسم الجهاز',
            'home_desc': 'صندوق أدوات التهيئة المتكامل لنظام Linux Mint Cinnamon 22.3.\nيمكنك بسهولة تعديل اختصارات لوحة المفاتيح، إدارة التطبيقات، تنظيف النظام، تنزيل الوسائط، وأكثر.\nاختر فئة من الشريط الجانبي للبدء — كل شيء على بعد نقرة واحدة!',
            'keyboard_title': 'إعدادات لوحة المفاتيح واللغة',
            'grave_title': 'تغيير اللغة بمفتاح الـ Grave Accent (~)',
            'grave_desc': 'استخدم مفتاح الـ Grave Accent لتبديل طرق الإدخال',
            'alt_shift_title': 'تغيير اللغة بمفتاح Alt+Shift',
            'alt_shift_desc': 'استخدم مفتاحي Alt + Shift لتبديل طرق الإدخال',
            'custom_key_title': 'اختصار مفتاح مخصص',
            'custom_key_desc': 'اضغط الزر أدناه لتسجيل تركيبة المفاتيح المطلوبة',
            'capture_key': 'التقاط المفتاح',
            'apply_now': 'تطبيق الآن',
            'system_title': 'أدوات إدارة النظام',
            'clean_system': 'تنظيف الملفات غير المرغوب فيها',
            'clean_system_desc': 'إزالة الحزم غير المستخدمة ومسح التخزين المؤقت',
            'clear_ram': 'تفريغ ذاكرة الوصول العشوائي/التخزين المؤقت',
            'clear_ram_desc': 'تفريغ ذاكرة النظام المؤقتة (sync && drop_caches)',
            'driver_manager': 'مدير التعريفات',
            'driver_manager_desc': 'افتح مدير التعريفات لتثبيت/إزالة التعريفات',
            'flatpak': 'إدارة Flatpak',
            'flatpak_desc': 'تحديث Flatpak وإدارة التطبيقات',
            'apt_repair': 'إصلاح APT',
            'apt_repair_desc': 'إصلاح الحزم المعطوبة وتحديث القوائم',
            'system_monitor': 'مراقب النظام',
            'system_monitor_desc': 'افتح أداة مراقبة النظام',
            'network_title': 'إدارة الشبكة',
            'network_status': 'حالة الشبكة',
            'refresh': 'تحديث',
            'restart_network': 'إعادة تشغيل الشبكة',
            'flush_dns': 'مسح DNS',
            'renew_dhcp': 'تجديد DHCP',
            'interfaces': 'واجهات الشبكة',
            'connections': 'الاتصالات',
            'entertainment_title': 'الترفيه',
            'install_steam': 'تثبيت Steam',
            'install_steam_desc': 'تثبيت Steam للألعاب',
            'install_wine': 'تثبيت Wine',
            'install_wine_desc': 'تثبيت Wine لتشغيل برامج ويندوز',
            'download_media': 'تنزيل فيديو/صوت',
            'url_label': 'الرابط',
            'format_label': 'الصيغة',
            'video': 'فيديو MP4',
            'audio': 'صوت M4A',
            'download': 'تحميل',
            'install_ytdlp': 'تثبيت yt-dlp',
            'theme_title': 'تخصيص السمة',
            'dark_mode': 'الوضع الليلي',
            'light_mode': 'الوضع النهاري',
            'mint_y': 'Mint-Y (فاقع)',
            'mint_y_dark': 'Mint-Y-داكن',
            'mint_y_dark_aqua': 'Mint-Y-داكن-أكوا',
            'apply_theme': 'تطبيق السمة',
            'backup_title': 'النسخ الاحتياطي للبيانات',
            'select_drive': 'اختر القرص الوجهة',
            'backup_now': 'بدء النسخ الاحتياطي',
            'backup_progress': 'يتم النسخ الاحتياطي...',
            'backup_complete': 'اكتمل النسخ الاحتياطي',
            'backup_failed': 'فشل النسخ الاحتياطي',
            'source': 'المصدر',
            'destination': 'الوجهة',
            'exclude': 'استبعاد',
            'about_title': 'حول',
            'developer': 'المطور',
            'email': 'البريد الإلكتروني',
            'thanks': 'تم إنشاء هذه الأداة لمساعدة الناس على استخدام لينكس بسهولة أكبر.\nشكراً لكونك جزءاً من عائلة المصدر المفتوح!',
            'donate_sentence': 'لا بيرة، لا كود. الرجاء دعم مبرمج عطشان!',
            'donate_button': 'تبرع بمصروف البيرة',
            'bank_label': 'البنك',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'اسم الحساب',
            'account_name': 'السيد ثماسورن موسيكابان',
            'account_number_label': 'رقم الحساب',
            'account_number': '1192455177',
            'paypal_label': 'باي بال',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'بيتكوين (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'نجاح',
            'error': 'خطأ',
            'settings_applied': 'تم تطبيق الإعدادات بنجاح!',
            'command_failed': 'فشل الأمر: {}',
            'need_sudo': 'تتطلب صلاحيات المسؤول',
            'no_ytdlp': 'لم يتم العثور على yt-dlp. الرجاء تثبيته أولاً.',
            'app_manager': 'مدير التطبيقات',
            'app_manager_title': 'إدارة التطبيقات المثبتة',
            'app_search_hint': '🔍  ابحث عن اسم التطبيق...',
            'app_col_name': 'اسم التطبيق',
            'app_col_version': 'الإصدار',
            'app_col_desc': 'الوصف',
            'app_uninstall': '🗑  إزالة التثبيت',
            'app_info': 'ℹ  معلومات',
            'app_loading': '⏳  جاري تحميل التطبيقات...',
            'app_count': 'التطبيقات المثبتة',
            'app_reload': '🔄  إعادة تحميل',
            'app_confirm_uninstall': 'تأكيد إلغاء التثبيت',
            'app_confirm_msg': 'هل تريد إزالة "{}" من النظام؟\n\nلا يمكن التراجع عن هذا الإجراء.',
            'app_uninstalling': 'جارٍ إزالة {}...',
            'app_uninstall_ok': 'تمت إزالة {} بنجاح',
            'app_uninstall_fail': 'فشل الإزالة:\n{}',
            'app_select_first': 'يرجى اختيار تطبيق أولاً',
            'app_info_title': 'معلومات التطبيق',
        }

        # es-CU
        strings_es_cu = {
            'window_title': 'Herramientas de Configuración Geng v2.0.6',
            'home': 'Inicio',
            'keyboard': 'Teclado y Lenguaje',
            'system_tools': 'Herramientas del Sistema',
            'network': 'Red',
            'entertainment': 'Entretenimiento',
            'theme': 'Tema',
            'backup': 'Respaldo',
            'about': 'Acerca de',
            'navigation': 'NAVEGACIÓN',
            'welcome': 'Bienvenido a Herramientas de Configuración Geng',
            'current_user': 'Usuario actual',
            'hostname': 'Nombre del equipo',
            'home_desc': 'Tu caja de herramientas todo en uno para la configuración de Linux Mint Cinnamon 22.3.\nAjusta fácilmente los atajos de teclado, administra aplicaciones, limpia tu sistema, descarga medios y más.\nSelecciona una categoría en la barra lateral para comenzar — ¡todo está a un clic de distancia!',
            'keyboard_title': 'Configuraciones de Teclado y Lenguaje',
            'grave_title': 'Cambiar idioma con Acento Grave (~)',
            'grave_desc': 'Usa la tecla de Acento Grave para cambiar métodos de entrada',
            'alt_shift_title': 'Cambiar idioma con Alt+Shift',
            'alt_shift_desc': 'Usa las teclas Alt + Shift para cambiar métodos de entrada',
            'custom_key_title': 'Combinación de teclas personalizada',
            'custom_key_desc': 'Presiona el botón abajo para capturar la combinación de teclas deseada',
            'capture_key': 'Capturar tecla',
            'apply_now': 'Aplicar ahora',
            'system_title': 'Herramientas de Gestión del Sistema',
            'clean_system': 'Limpiar Archivos Innecesarios',
            'clean_system_desc': 'Eliminar paquetes no usados y limpiar caché',
            'clear_ram': 'Limpiar RAM/Caché',
            'clear_ram_desc': 'Limpiar caché de memoria del sistema (sync && drop_caches)',
            'driver_manager': 'Administrador de Controladores',
            'driver_manager_desc': 'Abrir Administrador de Controladores para instalar/quitar controladores',
            'flatpak': 'Gestionar Flatpak',
            'flatpak_desc': 'Actualizar Flatpak y administrar aplicaciones',
            'apt_repair': 'Reparar APT',
            'apt_repair_desc': 'Reparar paquetes rotos y actualizar listas',
            'system_monitor': 'Monitor de Sistema',
            'system_monitor_desc': 'Abrir herramienta de monitoreo del sistema',
            'network_title': 'Gestión de Red',
            'network_status': 'Estado de la Red',
            'refresh': 'Actualizar',
            'restart_network': 'Reiniciar Red',
            'flush_dns': 'Vaciar DNS',
            'renew_dhcp': 'Renovar DHCP',
            'interfaces': 'Interfaces de Red',
            'connections': 'Conexiones',
            'entertainment_title': 'Entretenimiento',
            'install_steam': 'Instalar Steam',
            'install_steam_desc': 'Instalar Steam para juegos',
            'install_wine': 'Instalar Wine',
            'install_wine_desc': 'Instalar Wine para ejecutar programas de Windows',
            'download_media': 'Descargar Video/Audio',
            'url_label': 'URL',
            'format_label': 'Formato',
            'video': 'Video MP4',
            'audio': 'Audio M4A',
            'download': 'Descargar',
            'install_ytdlp': 'Instalar yt-dlp',
            'theme_title': 'Personalización de Tema',
            'dark_mode': 'Modo Oscuro',
            'light_mode': 'Modo Claro',
            'mint_y': 'Mint-Y (Claro)',
            'mint_y_dark': 'Mint-Y-Oscuro',
            'mint_y_dark_aqua': 'Mint-Y-Oscuro-Aqua',
            'apply_theme': 'Aplicar Tema',
            'backup_title': 'Respaldo de Datos',
            'select_drive': 'Seleccionar unidad de destino',
            'backup_now': 'Iniciar Respaldo',
            'backup_progress': 'Respaldando...',
            'backup_complete': 'Respaldo Completo',
            'backup_failed': 'Respaldo Fallido',
            'source': 'Origen',
            'destination': 'Destino',
            'exclude': 'Excluir',
            'about_title': 'Acerca de',
            'developer': 'Desarrollador',
            'email': 'Correo Electrónico',
            'thanks': 'Esta herramienta fue creada para ayudar a las personas a usar Linux más fácilmente.\n¡Gracias por ser parte de la familia de Código Abierto!',
            'donate_sentence': 'Sin cerveza, no hay código. ¡Por favor apoya a un programador sediento!',
            'donate_button': 'Donar Dinero para Cerveza',
            'bank_label': 'Banco',
            'bank_name': 'Kasikorn Thai',
            'account_name_label': 'Nombre de la Cuenta',
            'account_name': 'Sr. Thammasorn Musikapan',
            'account_number_label': 'Número de Cuenta',
            'account_number': '1192455177',
            'paypal_label': 'PayPal',
            'paypal': 'thammasorn2456@gmail.com',
            'bitcoin_label': 'Bitcoin (BTC)',
            'bitcoin': 'bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt',
            'success': 'Éxito',
            'error': 'Error',
            'settings_applied': '¡Configuraciones aplicadas con éxito!',
            'command_failed': 'Comando fallido: {}',
            'need_sudo': 'Se requieren privilegios de administrador',
            'no_ytdlp': 'No se encontró yt-dlp. Por favor instálalo primero.',
            'app_manager': 'Gestor de Aplicaciones',
            'app_manager_title': 'Administrar Aplicaciones Instaladas',
            'app_search_hint': '🔍  Buscar nombre de la aplicación...',
            'app_col_name': 'Nombre de la App',
            'app_col_version': 'Versión',
            'app_col_desc': 'Descripción',
            'app_uninstall': '🗑  Desinstalar',
            'app_info': 'ℹ  Información',
            'app_loading': '⏳  Cargando aplicaciones...',
            'app_count': 'Apps Instaladas',
            'app_reload': '🔄  Recargar',
            'app_confirm_uninstall': 'Confirmar Desinstalación',
            'app_confirm_msg': '¿Desinstalar "{}" del sistema?\n\nEsta acción no se puede deshacer.',
            'app_uninstalling': 'Desinstalando {}...',
            'app_uninstall_ok': 'Desinstalado correctamente {}',
            'app_uninstall_fail': 'Error al desinstalar:\n{}',
            'app_select_first': 'Por favor selecciona una aplicación primero',
            'app_info_title': 'Información de la App',
        }

        # For any other language, we return English as fallback.
        lang_map = {
            'en-US': strings_en,
            'th': strings_th,
            'lo': strings_lo,
            'de': strings_de,
            'fr': strings_fr,
            'ga': strings_ga,
            'nl': strings_nl,
            'sv': strings_sv,
            'da': strings_da,
            'nb': strings_nb,
            'cs': strings_cs,
            'pl': strings_pl,
            'de-AT': strings_de_at,
            'en-AU': strings_en_au,
            'en-GB': strings_en_gb,
            'es': strings_es,
            'de-CH': strings_de_ch,
            'en-CA': strings_en_ca,
            'fr-CA': strings_fr_ca,
            'it': strings_it,
            'hi': strings_hi,
            'id': strings_id,
            'pt': strings_pt,
            'pt-BR': strings_pt_br,
            'ja': strings_ja,
            'zh-CN': strings_zh_cn,
            'ru': strings_ru,
            'tr': strings_tr,
            'uk': strings_uk,
            'ar': strings_ar,
            'ko': strings_ko,
            'vi': strings_vi,
            'ms': strings_ms,
            'hmn': strings_hmn,
            'ca': strings_ca,
            'ar-SD': strings_ar_sd,
            'es-CU': strings_es_cu,
            'zh': strings_zh_cn,
            'hmn': strings_hmn,
        }
        return lang_map.get(lang, strings_en)

    def tr(self, key):
        return self.strings.get(key, key)

    def update_menu_titles(self):
        self.menu_list.clear()
        self.menu_list.addItem(self.tr('home'))
        self.menu_list.addItem(self.tr('keyboard'))
        self.menu_list.addItem(self.tr('system_tools'))
        self.menu_list.addItem(self.tr('app_manager'))
        self.menu_list.addItem(self.tr('network'))
        self.menu_list.addItem(self.tr('entertainment'))
        self.menu_list.addItem(self.tr('theme'))
        self.menu_list.addItem(self.tr('backup'))
        self.menu_list.addItem(self.tr('about'))

    def on_language_changed(self, index):
        lang = self.lang_combo.currentData()
        if lang != self.current_lang:
            # ── บันทึก row ปัจจุบันก่อนที่ update_menu_titles() จะ clear() รายการ ──
            saved_row = self.menu_list.currentRow()
            if saved_row < 0:
                saved_row = 0

            self.current_lang = lang
            self.strings = self.load_strings(lang)
            self.setWindowTitle(self.tr('window_title'))
            self.nav_label.setText(self.tr('navigation'))

            # Block signals เพื่อป้องกัน display_page(-1) ถูกเรียกระหว่าง clear()
            self.menu_list.blockSignals(True)
            self.update_menu_titles()
            self.menu_list.blockSignals(False)

            self.create_pages()

            # Restore selection และ page ที่ถูกต้อง
            self.menu_list.setCurrentRow(saved_row)
            self.pages.setCurrentIndex(saved_row)

    def make_page_title(self, text):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #E6EDF3; background: transparent;")
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #21262D; background-color: #21262D; border: none; max-height: 1px;")
        v.addWidget(lbl)
        v.addWidget(sep)
        return container

    def create_pages(self):
        while self.pages.count() > 0:
            self.pages.removeWidget(self.pages.widget(0))
        self.init_home_page()
        self.init_keyboard_page()
        self.init_system_tools_page()
        self.init_app_manager_page()
        self.init_network_page()
        self.init_entertainment_page()
        self.init_theme_page()
        self.init_backup_page()
        self.init_about_page()

    def create_card(self, title, description, btn_text, callback, btn_width=130):
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedHeight(80)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(14)

        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet("background-color: #1F6FEB; border-radius: 2px; border: none;")
        card_layout.addWidget(accent)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        t_label = QLabel(title)
        t_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #E6EDF3; background: transparent;")
        d_label = QLabel(description)
        d_label.setStyleSheet("font-size: 11px; color: #8B949E; background: transparent;")
        text_layout.addWidget(t_label)
        text_layout.addWidget(d_label)
        btn = QPushButton(btn_text)
        btn.setFixedWidth(btn_width)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB;
                color: #FFFFFF;
                border: none;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388BFD;
                border: none;
                color: white;
            }
            QPushButton:pressed {
                background-color: #1158C7;
                border: none;
            }
        """)
        btn.clicked.connect(callback)
        card_layout.addLayout(text_layout)
        card_layout.addStretch()
        card_layout.addWidget(btn)
        return card

    # -------------------- Home (updated text) --------------------
    def init_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hero = QWidget()
        hero.setStyleSheet("background-color: #161B22; border-bottom: 1px solid #21262D;")
        hero.setFixedHeight(120)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(32, 24, 32, 24)
        hero_layout.setSpacing(20)

        if os.path.exists(self.icon_path):
            logo_img = QLabel()
            logo_img.setPixmap(QPixmap(self.icon_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo_img.setStyleSheet("background: transparent; border: none;")
            hero_layout.addWidget(logo_img)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        welcome = QLabel(self.tr('welcome'))
        welcome.setStyleSheet("font-size: 20px; font-weight: 700; color: #E6EDF3; background: transparent;")
        pc_info = QLabel(f"  {os.getlogin()}  ·  {socket.gethostname()}")
        pc_info.setStyleSheet("color: #58A6FF; font-size: 12px; background: transparent;")
        text_col.addWidget(welcome)
        text_col.addWidget(pc_info)
        hero_layout.addLayout(text_col)
        hero_layout.addStretch()
        layout.addWidget(hero)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 24, 32, 24)
        body_layout.setSpacing(12)

        desc = QLabel(self.tr('home_desc'))
        desc.setStyleSheet("font-size: 13px; color: #8B949E; line-height: 1.6; background: transparent;")
        desc.setWordWrap(True)
        body_layout.addWidget(desc)

        # Add a little extra info
        tips = QLabel("✨ Quick tip: Use the sidebar to navigate. Most actions are one‑click!")
        tips.setStyleSheet("font-size: 12px; color: #58A6FF; background: transparent; margin-top: 10px;")
        body_layout.addWidget(tips)

        body_layout.addStretch()
        layout.addWidget(body)

        self.pages.addWidget(page)

    # -------------------- Keyboard --------------------
    def init_keyboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = self.make_page_title(self.tr('keyboard_title'))
        layout.addWidget(title)

        card1 = self.create_card(
            self.tr('grave_title'),
            self.tr('grave_desc'),
            self.tr('apply_now'),
            lambda: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" ; "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"[]\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"['grave']\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source-backward \"['<Shift>grave']\""
            )
        )
        layout.addWidget(card1)

        card2 = self.create_card(
            self.tr('alt_shift_title'),
            self.tr('alt_shift_desc'),
            self.tr('apply_now'),
            lambda: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"[]\" ; "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"['grp:alt_shift_toggle']\""
            )
        )
        layout.addWidget(card2)

        custom_group = QGroupBox(self.tr('custom_key_title'))
        custom_layout = QVBoxLayout(custom_group)
        capture_btn = QPushButton(self.tr('capture_key'))
        capture_btn.clicked.connect(self.capture_keybinding)
        custom_layout.addWidget(capture_btn)
        layout.addWidget(custom_group)

        layout.addStretch()
        self.pages.addWidget(page)

    def capture_keybinding(self):
        dlg = KeyGrabberDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            gsettings_str = dlg.get_gsettings_string()
            if not gsettings_str:
                QMessageBox.warning(self, self.tr('error'), "ไม่สามารถแปลงคีย์ที่กดได้")
                return
            cmd = f"gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" ; " \
                  f"gsettings set org.gnome.desktop.input-sources xkb-options \"[]\" ; " \
                  f"gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"['{gsettings_str}']\" ; "
            backward = f"gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source-backward \"['<Shift>{gsettings_str}']\""
            self.run_command(cmd + backward)

    # -------------------- System Tools --------------------
    def init_system_tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = self.make_page_title(self.tr('system_title'))
        layout.addWidget(title)

        card1 = self.create_card(self.tr('clean_system'), self.tr('clean_system_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("sudo apt autoremove -y && sudo apt autoclean"), 140)
        layout.addWidget(card1)
        card2 = self.create_card(self.tr('clear_ram'), self.tr('clear_ram_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches"), 140)
        layout.addWidget(card2)
        card3 = self.create_card(self.tr('driver_manager'), self.tr('driver_manager_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("pkexec mintdrivers", use_terminal=False), 140)
        layout.addWidget(card3)
        card4 = self.create_card(self.tr('flatpak'), self.tr('flatpak_desc'), self.tr('apply_now'),
                                 lambda: self.open_flatpak_dialog(), 140)
        layout.addWidget(card4)
        card5 = self.create_card(self.tr('apt_repair'), self.tr('apt_repair_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("sudo apt --fix-broken install && sudo dpkg --configure -a"), 140)
        layout.addWidget(card5)
        card6 = self.create_card(self.tr('system_monitor'), self.tr('system_monitor_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("gnome-system-monitor", use_terminal=False, wait=False), 140)
        layout.addWidget(card6)

        layout.addStretch()
        self.pages.addWidget(page)

    def open_flatpak_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Flatpak Manager")
        layout = QVBoxLayout(dlg)
        btn_update = QPushButton("อัปเดต Flatpak ทั้งหมด")
        btn_update.clicked.connect(lambda: self.run_command("flatpak update -y"))
        btn_install = QPushButton("ติดตั้งแอปพลิเคชัน (กรอก ID)")
        btn_install.clicked.connect(self.install_flatpak)
        btn_list = QPushButton("แสดงรายการ Flatpak")
        btn_list.clicked.connect(lambda: self.run_command("flatpak list", use_terminal=True))
        layout.addWidget(btn_update)
        layout.addWidget(btn_install)
        layout.addWidget(btn_list)
        dlg.exec()

    def install_flatpak(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("ติดตั้ง Flatpak")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("กรุณากรอก Flatpak ID (เช่น org.videolan.VLC):"))
        entry = QLineEdit()
        layout.addWidget(entry)
        btn_ok = QPushButton("ติดตั้ง")
        btn_ok.clicked.connect(lambda: self.run_command(f"flatpak install flathub {entry.text()} -y") or dlg.accept())
        layout.addWidget(btn_ok)
        dlg.exec()

    # -------------------- App Manager --------------------
    def init_app_manager_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(14)

        title = self.make_page_title(self.tr('app_manager_title'))
        layout.addWidget(title)

        toolbar = QWidget()
        toolbar.setStyleSheet("background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(10)

        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText(self.tr('app_search_hint'))
        self.app_search.setMinimumHeight(36)
        self.app_search.setStyleSheet("""
            QLineEdit {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #30363D;
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #58A6FF;
                background-color: #1C2128;
            }
        """)
        self.app_search.textChanged.connect(self._filter_app_table)
        toolbar_layout.addWidget(self.app_search, 1)

        reload_btn = QPushButton(self.tr('app_reload'))
        reload_btn.setMinimumHeight(36)
        reload_btn.setMinimumWidth(110)
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                padding: 6px 14px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
                color: #58A6FF;
            }
        """)
        reload_btn.clicked.connect(self._load_apps)
        toolbar_layout.addWidget(reload_btn)

        self.app_uninstall_btn = QPushButton(self.tr('app_uninstall'))
        self.app_uninstall_btn.setMinimumHeight(36)
        self.app_uninstall_btn.setMinimumWidth(150)
        self.app_uninstall_btn.setEnabled(False)
        self.app_uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #DA3633;
                color: #FFFFFF;
                border: none;
                padding: 6px 16px;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F85149;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #21262D;
                color: #484F58;
            }
        """)
        self.app_uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar_layout.addWidget(self.app_uninstall_btn)

        self.app_info_btn = QPushButton(self.tr('app_info'))
        self.app_info_btn.setMinimumHeight(36)
        self.app_info_btn.setMinimumWidth(100)
        self.app_info_btn.setEnabled(False)
        self.app_info_btn.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB;
                color: #FFFFFF;
                border: none;
                padding: 6px 14px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #388BFD;
            }
            QPushButton:disabled {
                background-color: #21262D;
                color: #484F58;
            }
        """)
        self.app_info_btn.clicked.connect(self._show_app_info)
        toolbar_layout.addWidget(self.app_info_btn)

        layout.addWidget(toolbar)

        self.app_status_lbl = QLabel(self.tr('app_loading'))
        self.app_status_lbl.setStyleSheet("color: #8B949E; font-size: 12px; background: transparent;")
        layout.addWidget(self.app_status_lbl)

        self.app_table = QTableWidget(0, 3)
        self.app_table.setHorizontalHeaderLabels([
            self.tr('app_col_name'),
            self.tr('app_col_version'),
            self.tr('app_col_desc'),
        ])
        self.app_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.app_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.app_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.app_table.setAlternatingRowColors(True)
        self.app_table.setSortingEnabled(True)
        self.app_table.verticalHeader().setVisible(False)
        self.app_table.setShowGrid(False)
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.app_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117;
                alternate-background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #21262D;
                border-radius: 8px;
                gridline-color: transparent;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #1F6FEB33;
                color: #58A6FF;
            }
            QHeaderView::section {
                background-color: #161B22;
                color: #8B949E;
                border: none;
                border-bottom: 1px solid #21262D;
                padding: 8px 10px;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.8px;
            }
            QScrollBar:vertical {
                background: #0D1117;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363D;
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        self.app_table.itemSelectionChanged.connect(self._on_app_selection_changed)
        layout.addWidget(self.app_table, 1)

        self.pages.addWidget(page)

        self._all_apps_data = []
        self._load_apps()

    def _load_apps(self):
        self.app_status_lbl.setText(self.tr('app_loading'))
        self.app_table.setRowCount(0)
        self.app_uninstall_btn.setEnabled(False)
        self.app_info_btn.setEnabled(False)
        self._app_loader = AppListLoader()
        self._app_loader.apps_loaded.connect(self._on_apps_loaded)
        self._app_loader.start()
        self.active_threads.append(self._app_loader)

    def _on_apps_loaded(self, apps):
        self._all_apps_data = apps
        if self._app_loader in self.active_threads:
            self.active_threads.remove(self._app_loader)
        self._populate_app_table(apps)
        count = len(apps)
        self.app_status_lbl.setText(f"{self.tr('app_count')}: {count:,}")

    def _populate_app_table(self, apps):
        self.app_table.setSortingEnabled(False)
        self.app_table.setRowCount(len(apps))
        for row, (name, version, desc) in enumerate(apps):
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor("#C9D1D9"))
            ver_item = QTableWidgetItem(version)
            ver_item.setForeground(QColor("#8B949E"))
            desc_item = QTableWidgetItem(desc)
            desc_item.setForeground(QColor("#6E7681"))
            self.app_table.setItem(row, 0, name_item)
            self.app_table.setItem(row, 1, ver_item)
            self.app_table.setItem(row, 2, desc_item)
        self.app_table.setSortingEnabled(True)

    def _filter_app_table(self, text):
        query = text.strip().lower()
        if not query:
            filtered = self._all_apps_data
        else:
            filtered = [
                (n, v, d) for n, v, d in self._all_apps_data
                if query in n.lower() or query in d.lower()
            ]
        self._populate_app_table(filtered)
        count_all = len(self._all_apps_data)
        count_filtered = len(filtered)
        if query:
            self.app_status_lbl.setText(f"พบ {count_filtered:,} รายการ (จาก {count_all:,})")
        else:
            self.app_status_lbl.setText(f"{self.tr('app_count')}: {count_all:,}")

    def _on_app_selection_changed(self):
        has_sel = bool(self.app_table.selectedItems())
        self.app_uninstall_btn.setEnabled(has_sel)
        self.app_info_btn.setEnabled(has_sel)

    def _get_selected_package(self):
        row = self.app_table.currentRow()
        if row < 0:
            return None
        item = self.app_table.item(row, 0)
        return item.text() if item else None

    def _uninstall_selected(self):
        pkg = self._get_selected_package()
        if not pkg:
            QMessageBox.warning(self, self.tr('error'), self.tr('app_select_first'))
            return
        msg = self.tr('app_confirm_msg').format(pkg)
        reply = QMessageBox.question(
            self,
            self.tr('app_confirm_uninstall'),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.app_status_lbl.setText(self.tr('app_uninstalling').format(pkg))
        self.app_uninstall_btn.setEnabled(False)
        self._uninstall_thread = UninstallThread(pkg)
        self._uninstall_thread.finished.connect(lambda code, out, err: self._on_uninstall_done(code, out, err, pkg))
        self._uninstall_thread.start()
        self.active_threads.append(self._uninstall_thread)

    def _on_uninstall_done(self, returncode, stdout, stderr, pkg):
        if self._uninstall_thread in self.active_threads:
            self.active_threads.remove(self._uninstall_thread)
        if returncode == 0:
            QMessageBox.information(self, self.tr('success'), self.tr('app_uninstall_ok').format(pkg))
            self._load_apps()
        else:
            err = stderr.strip() or f"Return code {returncode}"
            QMessageBox.critical(self, self.tr('error'), self.tr('app_uninstall_fail').format(err))
            self.app_status_lbl.setText(f"{self.tr('app_count')}: {len(self._all_apps_data):,}")
            self.app_uninstall_btn.setEnabled(True)

    def _show_app_info(self):
        pkg = self._get_selected_package()
        if not pkg:
            return
        try:
            result = subprocess.run(['apt-cache', 'show', pkg], capture_output=True, text=True)
            info_text = result.stdout.strip() or f"ไม่พบข้อมูลสำหรับ {pkg}"
        except Exception as e:
            info_text = str(e)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{self.tr('app_info_title')}: {pkg}")
        dlg.setMinimumSize(560, 420)
        dlg.setStyleSheet("QDialog { background-color: #161B22; } QLabel { color: #C9D1D9; }")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(20, 20, 20, 20)
        dlg_layout.setSpacing(12)

        pkg_title = QLabel(f"📦  {pkg}")
        pkg_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #58A6FF;")
        dlg_layout.addWidget(pkg_title)

        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setPlainText(info_text)
        text_box.setStyleSheet("""
            QTextEdit {
                background-color: #0D1117;
                color: #C9D1D9;
                border: 1px solid #21262D;
                border-radius: 6px;
                font-family: 'Monospace', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        dlg_layout.addWidget(text_box)

        close_btn = QPushButton("ปิด")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                padding: 7px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #30363D; }
        """)
        close_btn.clicked.connect(dlg.accept)
        dlg_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    # -------------------- Network --------------------
    def init_network_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = self.make_page_title(self.tr('network_title'))
        layout.addWidget(title)

        status_group = QGroupBox(self.tr('network_status'))
        status_layout = QVBoxLayout(status_group)
        self.network_info = QTextEdit()
        self.network_info.setReadOnly(True)
        self.network_info.setMaximumHeight(200)
        status_layout.addWidget(self.network_info)
        refresh_btn = QPushButton(self.tr('refresh'))
        refresh_btn.clicked.connect(self.update_network_info)
        status_layout.addWidget(refresh_btn)
        layout.addWidget(status_group)

        btn_layout = QGridLayout()
        btn_restart = QPushButton(self.tr('restart_network'))
        btn_restart.clicked.connect(lambda: self.run_command("sudo systemctl restart NetworkManager"))
        btn_flush = QPushButton(self.tr('flush_dns'))
        btn_flush.clicked.connect(lambda: self.run_command("sudo systemd-resolve --flush-caches"))
        btn_renew = QPushButton(self.tr('renew_dhcp'))
        btn_renew.clicked.connect(lambda: self.run_command("sudo dhclient -r && sudo dhclient"))
        btn_layout.addWidget(btn_restart, 0, 0)
        btn_layout.addWidget(btn_flush, 0, 1)
        btn_layout.addWidget(btn_renew, 1, 0)
        layout.addLayout(btn_layout)

        arp_group = QGroupBox(self.tr('connections'))
        arp_layout = QVBoxLayout(arp_group)
        self.arp_info = QTextEdit()
        self.arp_info.setReadOnly(True)
        self.arp_info.setMaximumHeight(150)
        arp_layout.addWidget(self.arp_info)
        layout.addWidget(arp_group)

        layout.addStretch()
        self.pages.addWidget(page)

        self.update_network_info()

    def update_network_info(self):
        self.network_loader = NetworkInfoLoader()
        self.network_loader.info_loaded.connect(self.on_network_info_loaded)
        self.network_loader.start()
        self.active_threads.append(self.network_loader)

    def on_network_info_loaded(self, ip_output, arp_output):
        self.network_info.setText(ip_output)
        self.arp_info.setText(arp_output)
        if self.network_loader in self.active_threads:
            self.active_threads.remove(self.network_loader)

    # -------------------- Entertainment --------------------
    def init_entertainment_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = self.make_page_title(self.tr('entertainment_title'))
        layout.addWidget(title)

        card1 = self.create_card(self.tr('install_steam'), self.tr('install_steam_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("sudo apt update && sudo apt install -y steam-installer", use_terminal=True), 140)
        layout.addWidget(card1)
        card2 = self.create_card(self.tr('install_wine'), self.tr('install_wine_desc'), self.tr('apply_now'),
                                 lambda: self.run_command("sudo apt update && sudo apt install -y wine64 winetricks && winetricks", use_terminal=True), 140)
        layout.addWidget(card2)

        media_group = QGroupBox(self.tr('download_media'))
        media_layout = QVBoxLayout(media_group)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel(self.tr('url_label') + ":"))
        self.url_entry = QLineEdit()
        url_layout.addWidget(self.url_entry)
        media_layout.addLayout(url_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel(self.tr('format_label') + ":"))
        self.format_combo = QComboBox()
        self.format_combo.addItem(self.tr('video'), 'video')
        self.format_combo.addItem(self.tr('audio'), 'audio')
        format_layout.addWidget(self.format_combo)
        media_layout.addLayout(format_layout)

        download_btn = QPushButton(self.tr('download'))
        download_btn.clicked.connect(self.download_media)
        media_layout.addWidget(download_btn)

        install_ytdlp_btn = QPushButton(self.tr('install_ytdlp'))
        install_ytdlp_btn.clicked.connect(lambda: self.run_command("sudo apt install -y yt-dlp", use_terminal=True))
        media_layout.addWidget(install_ytdlp_btn)

        layout.addWidget(media_group)
        layout.addStretch()
        self.pages.addWidget(page)

    def download_media(self):
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, self.tr('error'), "กรุณากรอก URL")
            return
        if subprocess.run(['which', 'yt-dlp'], capture_output=True).returncode != 0:
            QMessageBox.warning(self, self.tr('error'), self.tr('no_ytdlp'))
            return
        default_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(default_dir):
            default_dir = os.path.expanduser("~")
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "เลือกโฟลเดอร์สำหรับบันทึกไฟล์ / Select Download Folder",
            default_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if not save_dir:
            return
        fmt = self.format_combo.currentData()
        output_template = os.path.join(save_dir, '%(title)s.%(ext)s')
        if fmt == 'video':
            cmd = f"yt-dlp -f 'best[ext=mp4]/best' -o {shlex.quote(output_template)} {shlex.quote(url)}"
        else:
            cmd = f"yt-dlp -f 'bestaudio[ext=m4a]/bestaudio' -o {shlex.quote(output_template)} {shlex.quote(url)}"
        self.run_command(cmd, use_terminal=True)

    # -------------------- Theme Page --------------------
    def init_theme_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = self.make_page_title(self.tr('theme_title'))
        layout.addWidget(title)

        dark_btn = QPushButton(self.tr('dark_mode'))
        dark_btn.clicked.connect(lambda: self.apply_theme('Mint-Y-Dark-Aqua'))
        layout.addWidget(dark_btn)

        light_btn = QPushButton(self.tr('light_mode'))
        light_btn.clicked.connect(lambda: self.apply_theme('Mint-Y'))
        layout.addWidget(light_btn)

        themes = [
            ('Mint-Y-Dark', 'Mint-Y-Dark'),
            ('Mint-Y-Dark-Teal', 'Mint-Y-Dark-Teal'),
            ('Mint-Y-Dark-Grey', 'Mint-Y-Dark-Grey'),
            ('Mint-Y-Dark-Orange', 'Mint-Y-Dark-Orange'),
            ('Mint-Y-Dark-Purple', 'Mint-Y-Dark-Purple'),
            ('Mint-Y-Dark-Red', 'Mint-Y-Dark-Red'),
            ('Mint-Y-Dark-Brown', 'Mint-Y-Dark-Brown'),
            ('Mint-Y', 'Mint-Y (Light)'),
        ]
        for theme, label in themes:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, t=theme: self.apply_theme(t))
            layout.addWidget(btn)

        layout.addStretch()
        self.pages.addWidget(page)

    def apply_theme(self, theme_name):
        cmd = f"gsettings set org.cinnamon.desktop.interface gtk-theme '{theme_name}' && " \
              f"gsettings set org.cinnamon.theme name '{theme_name}'"
        self.run_command(cmd)

    # -------------------- Backup Page --------------------
    def init_backup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = self.make_page_title(self.tr('backup_title'))
        layout.addWidget(title)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel(self.tr('source') + ":"))
        self.source_entry = QLineEdit("/home")
        source_layout.addWidget(self.source_entry)
        source_btn = QPushButton("...")
        source_btn.clicked.connect(lambda: self.choose_dir(self.source_entry))
        source_layout.addWidget(source_btn)
        layout.addLayout(source_layout)

        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel(self.tr('destination') + ":"))
        self.dest_entry = QLineEdit()
        dest_layout.addWidget(self.dest_entry)
        dest_btn = QPushButton("...")
        dest_btn.clicked.connect(lambda: self.choose_dir(self.dest_entry))
        dest_layout.addWidget(dest_btn)
        layout.addLayout(dest_layout)

        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel(self.tr('exclude') + ":"))
        self.exclude_entry = QLineEdit("--exclude='.cache' --exclude='.thumbnails'")
        exclude_layout.addWidget(self.exclude_entry)
        layout.addLayout(exclude_layout)

        backup_btn = QPushButton(self.tr('backup_now'))
        backup_btn.clicked.connect(self.start_backup)
        layout.addWidget(backup_btn)

        layout.addStretch()
        self.pages.addWidget(page)

    def choose_dir(self, entry):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            entry.setText(dir_path)

    def start_backup(self):
        src = self.source_entry.text().strip()
        dest = self.dest_entry.text().strip()
        if not src or not dest:
            QMessageBox.warning(self, "Warning", "กรุณาเลือกแหล่งและปลายทาง")
            return
        exclude_opts = self.exclude_entry.text().strip()
        cmd = f"rsync -avh --progress {exclude_opts} {src}/ {dest}/backup_$(date +%Y%m%d_%H%M%S)/"
        self.run_command(cmd, use_terminal=True)

    # -------------------- About (updated with proper wrapping) --------------------
    def init_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        logo = QLabel()
        if os.path.exists(self.icon_path):
            logo.setPixmap(QPixmap(self.icon_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel("Geng Settings Tools")
        name.setStyleSheet("font-size: 20px; font-weight: 700; color: #58A6FF;")

        info = QLabel(
            f"<b>{self.tr('developer')}:</b> คุณธรรมสรณ์ มุสิกพันธ์ (Geng)<br>"
            f"<b>{self.tr('email')}:</b> gtzx26@gmail.com"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #E0E0E0; font-size: 13px;")

        # New donation sentence with word wrap and fixed width
        sentence = QLabel(self.tr('donate_sentence'))
        sentence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sentence.setStyleSheet("font-size: 16px; font-weight: 600; color: #F9ED69; margin: 10px 0;")
        sentence.setWordWrap(True)
        sentence.setFixedWidth(600)  # Ensures text fits within the box

        # Donate button
        donate_btn = QPushButton(self.tr('donate_button'))
        donate_btn.setStyleSheet("""
            QPushButton {
                background-color: #F9ED69;
                color: #0D1117;
                border: none;
                padding: 14px 28px;
                border-radius: 40px;
                font-weight: 800;
                font-size: 18px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #FFD966;
                border: 2px solid #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #E6B800;
            }
        """)
        donate_btn.clicked.connect(self.open_donate_link)

        # Donation details box
        donate_box = QFrame()
        donate_box.setFixedWidth(620)
        donate_box.setStyleSheet("background-color: #161B22; border: 1px solid #F9ED6944; border-radius: 10px; padding: 15px;")
        donate_layout = QHBoxLayout(donate_box)

        qr_label = QLabel()
        if os.path.exists(self.qr_path):
            qr_pixmap = QPixmap(self.qr_path).scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label.setPixmap(qr_pixmap)
            qr_label.setStyleSheet("border: 2px solid white; background-color: white;")
        qr_label.setFixedSize(150, 150)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        details_layout = QVBoxLayout()
        bank_info = QLabel(
            f"<b>{self.tr('bank_label')}:</b> {self.tr('bank_name')}<br>"
            f"<b>{self.tr('account_name_label')}:</b> {self.tr('account_name')}<br>"
            f"<b>{self.tr('account_number_label')}:</b> {self.tr('account_number')}<br><br>"
            f"<b>{self.tr('paypal_label')}:</b> {self.tr('paypal')}<br><br>"
            f"<b>{self.tr('bitcoin_label')}:</b>"
        )
        bank_info.setStyleSheet("color: white; border: none; font-size: 13px;")

        btc_address = QLabel(self.tr('bitcoin'))
        btc_address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        btc_address.setStyleSheet("color: #F7931A; font-family: Monospace; font-size: 12px; border: none; background: #2A2A2A; padding: 3px; border-radius: 3px;")
        btc_address.setToolTip("คุณสามารถลากคลุมดำและคัดลอกที่อยู่นี้ได้")

        details_layout.addWidget(bank_info)
        details_layout.addWidget(btc_address)

        donate_layout.addWidget(qr_label)
        donate_layout.addLayout(details_layout)

        # Assemble the page
        layout.addStretch()
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(sentence, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(donate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(donate_box, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.pages.addWidget(page)

    def open_donate_link(self):
        url = QUrl("https://buy.stripe.com/5kQfZ9bID6tyeXj2tf4ko01")
        QDesktopServices.openUrl(url)

    # -------------------- Async command execution --------------------
    def run_command(self, cmd, use_terminal=False, wait=False):
        if use_terminal:
            cmd_with_pause = f"{cmd}; echo; echo 'กด Enter เพื่อปิด...'; read"
            escaped_cmd = shlex.quote(cmd_with_pause)
            full_cmd = f"gnome-terminal -- bash -c {escaped_cmd}"
            subprocess.Popen(full_cmd, shell=True)
            return

        use_pkexec = "sudo" in cmd and not cmd.startswith("pkexec")
        thread = CommandThread(cmd, use_pkexec)
        thread.finished.connect(lambda code, out, err: self.on_command_finished(code, out, err))
        thread.start()
        self.active_threads.append(thread)
        thread.finished.connect(lambda: self.active_threads.remove(thread) if thread in self.active_threads else None)

    def on_command_finished(self, returncode, stdout, stderr):
        if returncode == 0:
            QMessageBox.information(self, self.tr('success'), self.tr('settings_applied'))
        else:
            error = stderr.strip() or f"Return code {returncode}"
            QMessageBox.critical(self, self.tr('error'), self.tr('command_failed').format(error))

    def display_page(self, index):
        self.pages.setCurrentIndex(index)


if __name__ == "__main__":
    if not os.environ.get('DISPLAY'):
        print("Error: No display found. Please run this program in a graphical environment.")
        sys.exit(1)

    log_dir = os.path.expanduser("~/.local/share/geng-tools")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "geng-tools.log")
    try:
        _log_file = open(log_path, "a")
        sys.stdout = _log_file
        sys.stderr = _log_file
    except Exception:
        pass

    app = QApplication(sys.argv)
    window = GengSettingsTools()
    window.show()
    sys.exit(app.exec())
