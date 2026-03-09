#!/usr/bin/env python3
import gi
import os
import subprocess
import socket
import getpass
import shlex
import sys
import json
import datetime
import shutil
from pathlib import Path

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib


class I18n:
    """Internationalization support"""
    
    TRANSLATIONS = {
        'th': {
            # Window titles
            'window_title': 'Geng Settings Tools v2.0.6',
            
            # Sidebar
            'home': 'หน้าแรก',
            'keyboard': 'คีย์บอร์ด & ภาษา',
            'system': 'เครื่องมือระบบ',
            'gaming': 'เล่นเกม',
            'ui': 'ปรับแต่ง UI',
            'about': 'เกี่ยวกับ',
            'backup': 'สำรองข้อมูล',
            
            # Home page
            'welcome': 'ยินดีต้อนรับสู่ <b>Geng Settings Tools</b>',
            'current_user': 'ผู้ใช้ปัจจุบัน: <b>{}</b>',
            'hostname': 'เครื่องคอมพิวเตอร์: <b>{}</b>',
            'description': 'เครื่องมือช่วยตั้งค่าพื้นฐานสำหรับ Linux Mint Cinnamon 22.3\nออกแบบมาเพื่อให้การใช้งาน Linux เป็นเรื่องง่ายสำหรับทุกคน',
            
            # Keyboard page
            'keyboard_title': 'คีย์บอร์ด & ภาษา',
            'grave_accent_title': 'สลับภาษาด้วยปุ่ม Grave Accent (~)',
            'grave_accent_desc': 'ตั้งค่าให้ใช้ปุ่มตัวหนอน (Grave Accent) ในการสลับภาษา (มาตรฐานคนไทย)',
            'alt_shift_title': 'สลับภาษาด้วยปุ่ม Alt+Shift',
            'alt_shift_desc': 'ตั้งค่าให้ใช้ปุ่ม Alt + Shift ในการสลับภาษา',
            'apply_now': 'ตั้งค่าทันที',
            
            # System tools page
            'system_title': 'เครื่องมือระบบ',
            'optimize_title': 'เพิ่มประสิทธิภาพระบบ',
            'optimize_desc': 'ล้างแคช, ลบแพ็กเกจที่ไม่ได้ใช้งาน และทำความสะอาดระบบ',
            'codecs_title': 'ติดตั้ง Multimedia Codecs',
            'codecs_desc': 'ติดตั้งตัวแปลงสัญญาณเพื่อให้ดูหนังฟังเพลงได้ทุกรูปแบบ',
            'start': 'เริ่มทำงาน',
            'install_now': 'ติดตั้งทันที',
            
            # Gaming page
            'gaming_title': 'พร้อมสำหรับการเล่นเกม',
            'steam_title': 'ติดตั้ง Steam & Wine',
            'steam_desc': 'เตรียมเครื่องให้พร้อมสำหรับการเล่นเกมบน Linux',
            
            # UI Tweaks page
            'ui_title': 'ปรับแต่งหน้าตา (UI)',
            'dark_mode_title': 'สลับเป็น Dark Mode',
            'dark_mode_desc': 'เปลี่ยนธีมของระบบให้เป็นโหมดมืดเพื่อถนอมสายตา',
            'light_mode_title': 'สลับเป็น Light Mode',
            'light_mode_desc': 'เปลี่ยนธีมของระบบให้เป็นโหมดสว่าง',
            'dark_mode': 'เปิดโหมดมืด',
            'light_mode': 'เปิดโหมดสว่าง',
            
            # Backup page
            'backup_title': 'สำรองและกู้คืนข้อมูล',
            'backup_settings_title': 'สำรองการตั้งค่าปัจจุบัน',
            'backup_settings_desc': 'บันทึกการตั้งค่าทั้งหมด (คีย์บอร์ด, ธีม, ฯลฯ) ลงในไฟล์',
            'restore_settings_title': 'กู้คืนการตั้งค่าจากไฟล์',
            'restore_settings_desc': 'นำเข้าการตั้งค่าที่เคยสำรองไว้',
            'export_settings_title': 'ส่งออกการตั้งค่า',
            'export_settings_desc': 'ส่งออกการตั้งค่าเพื่อแชร์ระหว่างเครื่อง',
            'import_settings_title': 'นำเข้าการตั้งค่า',
            'import_settings_desc': 'นำเข้าการตั้งค่าจากเครื่องอื่น',
            'backup_now': 'สำรองข้อมูล',
            'restore_now': 'กู้คืนข้อมูล',
            'export_now': 'ส่งออก',
            'import_now': 'นำเข้า',
            
            # About page
            'about_title': 'เกี่ยวกับ',
            'developer': 'ผู้พัฒนา:',
            'email': 'Email:',
            'thanks': 'เครื่องมือนี้สร้างขึ้นเพื่อช่วยให้คนไทยใช้งาน Linux ได้ง่ายขึ้น\nขอขอบคุณที่ร่วมเป็นส่วนหนึ่งของครอบครัว Open Source',
            'donate': '☕ สนับสนุนค่ากาแฟผู้พัฒนา',
            'qr_placeholder': '(สามารถสแกน QR Code เพื่อสนับสนุนผู้พัฒนาได้)',
            'bank_kbank': 'กสิกรไทย (K-Bank):',
            'account_name': 'ชื่อบัญชี:',
            'paypal': 'PayPal:',
            'bitcoin': 'Bitcoin (BTC):',
            
            # Messages
            'success': 'สำเร็จ',
            'error': 'ข้อผิดพลาด',
            'warning': 'คำเตือน',
            'info': 'แจ้งเตือน',
            'settings_applied': 'ดำเนินการตั้งค่าเรียบร้อยแล้ว!',
            'command_failed': 'ไม่สามารถดำเนินการได้: {}',
            'backup_success': 'สำรองข้อมูลเรียบร้อยแล้วที่:\n{}',
            'backup_failed': 'ไม่สามารถสำรองข้อมูลได้: {}',
            'restore_success': 'กู้คืนข้อมูลเรียบร้อยแล้ว!\nกรุณารีสตาร์ทแอปพลิเคชันเพื่อให้การเปลี่ยนแปลงมีผล',
            'restore_failed': 'ไม่สามารถกู้คืนข้อมูลได้: {}',
            'import_success': 'นำเข้าการตั้งค่าเรียบร้อยแล้ว!\nกรุณารีสตาร์ทแอปพลิเคชัน',
            'import_failed': 'ไม่สามารถนำเข้าการตั้งค่าได้: {}',
            'export_success': 'ส่งออกการตั้งค่าเรียบร้อยแล้วที่:\n{}',
            'export_failed': 'ไม่สามารถส่งออกการตั้งค่าได้: {}',
            'no_terminal': 'ไม่พบ gnome-terminal ในระบบ\nกรุณาติดตั้ง gnome-terminal',
            'root_warning': 'ต้องการสิทธิ์ผู้ดูแลระบบ\nบางคำสั่งต้องการสิทธิ์ root ในการทำงาน\nหากคำสั่งล้มเหลว กรุณารันโปรแกรมด้วย sudo',
            'invalid_backup': 'ไฟล์สำรองข้อมูลไม่ถูกต้อง',
            'confirm_restore': 'ยืนยันการกู้คืนข้อมูล',
            'confirm_restore_msg': 'การกู้คืนข้อมูลจะเขียนทับการตั้งค่าปัจจุบัน\nคุณต้องการดำเนินการต่อหรือไม่?',
            
            # Buttons
            'yes': 'ใช่',
            'no': 'ไม่',
            'ok': 'ตกลง',
            'cancel': 'ยกเลิก',
            
            # Language
            'language': 'ภาษา',
            'thai': 'ไทย',
            'english': 'อังกฤษ',
        },
        'en': {
            # Window titles
            'window_title': 'Geng Settings Tools v2.0.6',
            
            # Sidebar
            'home': 'Home',
            'keyboard': 'Keyboard & Language',
            'system': 'System Tools',
            'gaming': 'Gaming',
            'ui': 'UI Tweaks',
            'about': 'About',
            'backup': 'Backup',
            
            # Home page
            'welcome': 'Welcome to <b>Geng Settings Tools</b>',
            'current_user': 'Current user: <b>{}</b>',
            'hostname': 'Hostname: <b>{}</b>',
            'description': 'Basic settings tool for Linux Mint Cinnamon 22.3\nDesigned to make Linux easy for everyone',
            
            # Keyboard page
            'keyboard_title': 'Keyboard & Language',
            'grave_accent_title': 'Switch language with Grave Accent (~)',
            'grave_accent_desc': 'Use Grave Accent key to switch input methods (Thai standard)',
            'alt_shift_title': 'Switch language with Alt+Shift',
            'alt_shift_desc': 'Use Alt + Shift keys to switch input methods',
            'apply_now': 'Apply Now',
            
            # System tools page
            'system_title': 'System Tools',
            'optimize_title': 'Optimize System',
            'optimize_desc': 'Clean cache, remove unused packages, and clean up system',
            'codecs_title': 'Install Multimedia Codecs',
            'codecs_desc': 'Install codecs to play all media formats',
            'start': 'Start',
            'install_now': 'Install Now',
            
            # Gaming page
            'gaming_title': 'Gaming Ready',
            'steam_title': 'Install Steam & Wine',
            'steam_desc': 'Prepare your system for gaming on Linux',
            
            # UI Tweaks page
            'ui_title': 'UI Tweaks',
            'dark_mode_title': 'Switch to Dark Mode',
            'dark_mode_desc': 'Change system theme to dark mode',
            'light_mode_title': 'Switch to Light Mode',
            'light_mode_desc': 'Change system theme to light mode',
            'dark_mode': 'Enable Dark Mode',
            'light_mode': 'Enable Light Mode',
            
            # Backup page
            'backup_title': 'Backup & Restore',
            'backup_settings_title': 'Backup Current Settings',
            'backup_settings_desc': 'Save all settings (keyboard, theme, etc.) to a file',
            'restore_settings_title': 'Restore Settings from File',
            'restore_settings_desc': 'Import previously backed up settings',
            'export_settings_title': 'Export Settings',
            'export_settings_desc': 'Export settings to share between computers',
            'import_settings_title': 'Import Settings',
            'import_settings_desc': 'Import settings from another computer',
            'backup_now': 'Backup Now',
            'restore_now': 'Restore Now',
            'export_now': 'Export',
            'import_now': 'Import',
            
            # About page
            'about_title': 'About',
            'developer': 'Developer:',
            'email': 'Email:',
            'thanks': 'This tool is created to help Thai people use Linux easily\nThank you for being part of the Open Source family',
            'donate': '☕ Buy me a coffee',
            'qr_placeholder': '(Scan QR Code to support the developer)',
            'bank_kbank': 'K-Bank:',
            'account_name': 'Account name:',
            'paypal': 'PayPal:',
            'bitcoin': 'Bitcoin (BTC):',
            
            # Messages
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'settings_applied': 'Settings applied successfully!',
            'command_failed': 'Command failed: {}',
            'backup_success': 'Backup saved successfully at:\n{}',
            'backup_failed': 'Backup failed: {}',
            'restore_success': 'Settings restored successfully!\nPlease restart the application for changes to take effect',
            'restore_failed': 'Restore failed: {}',
            'import_success': 'Settings imported successfully!\nPlease restart the application',
            'import_failed': 'Import failed: {}',
            'export_success': 'Settings exported successfully at:\n{}',
            'export_failed': 'Export failed: {}',
            'no_terminal': 'gnome-terminal not found\nPlease install gnome-terminal',
            'root_warning': 'Root privileges required\nSome commands need root access\nIf commands fail, please run with sudo',
            'invalid_backup': 'Invalid backup file',
            'confirm_restore': 'Confirm Restore',
            'confirm_restore_msg': 'Restoring will overwrite current settings\nDo you want to continue?',
            
            # Buttons
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'cancel': 'Cancel',
            
            # Language
            'language': 'Language',
            'thai': 'Thai',
            'english': 'English',
        }
    }
    
    def __init__(self, lang='th'):
        self.lang = lang if lang in self.TRANSLATIONS else 'th'
    
    def set_language(self, lang):
        if lang in self.TRANSLATIONS:
            self.lang = lang
    
    def get(self, key, *args):
        """Get translated string with optional formatting"""
        if key in self.TRANSLATIONS[self.lang]:
            text = self.TRANSLATIONS[self.lang][key]
            if args:
                return text.format(*args)
            return text
        return key


class SettingsManager:
    """Manage backup, restore, import, export of settings"""
    
    SETTINGS_KEYS = [
        # Keyboard settings
        ('org.gnome.desktop.input-sources', 'sources'),
        ('org.gnome.desktop.input-sources', 'xkb-options'),
        ('org.cinnamon.desktop.keybindings.wm', 'switch-input-source'),
        ('org.cinnamon.desktop.keybindings.wm', 'switch-input-source-backward'),
        
        # UI settings
        ('org.cinnamon.desktop.interface', 'gtk-theme'),
        ('org.cinnamon.theme', 'name'),
        ('org.cinnamon.desktop.interface', 'icon-theme'),
        ('org.cinnamon.desktop.interface', 'cursor-theme'),
        ('org.cinnamon.desktop.interface', 'font-name'),
    ]
    
    @staticmethod
    def get_current_settings():
        """Get all current settings"""
        settings = {
            'timestamp': datetime.datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'user': getpass.getuser(),
            'settings': {}
        }
        
        for schema, key in SettingsManager.SETTINGS_KEYS:
            try:
                result = subprocess.run(
                    ['gsettings', 'get', schema, key],
                    capture_output=True,
                    text=True,
                    check=True
                )
                settings['settings'][f'{schema}:{key}'] = result.stdout.strip()
            except:
                settings['settings'][f'{schema}:{key}'] = None
        
        return settings
    
    @staticmethod
    def apply_settings(settings_data):
        """Apply settings from backup data"""
        if 'settings' not in settings_data:
            return False, "Invalid backup format"
        
        success_count = 0
        fail_count = 0
        
        for key, value in settings_data['settings'].items():
            if value is None or value == 'null':
                continue
                
            try:
                schema, setting = key.split(':', 1)
                subprocess.run(
                    ['gsettings', 'set', schema, setting, value],
                    check=True,
                    capture_output=True
                )
                success_count += 1
            except:
                fail_count += 1
        
        return True, f"Applied {success_count} settings, {fail_count} failed"
    
    @staticmethod
    def backup_to_file(filepath):
        """Backup settings to file"""
        try:
            settings = SettingsManager.get_current_settings()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True, filepath
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def restore_from_file(filepath):
        """Restore settings from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            return SettingsManager.apply_settings(settings)
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_backup_dir():
        """Get backup directory path"""
        backup_dir = os.path.expanduser("~/.config/geng-settings-tools/backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    @staticmethod
    def get_default_backup_filename():
        """Generate default backup filename"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"geng_settings_backup_{timestamp}.json"


class GengSettingsTools(Gtk.Window):
    def __init__(self):
        self.i18n = I18n('th')  # Default to Thai
        super().__init__(title=self.i18n.get('window_title'))
        self.set_default_size(950, 700)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Apply custom CSS
        self.apply_css()

        # Set application icon with fallback
        icon_theme = Gtk.IconTheme.get_default()
        if icon_theme.has_icon("geng-settings-tools"):
            self.set_icon_name("geng-settings-tools")
        else:
            self.set_icon_name("applications-system")

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self.main_box)

        # Left panel with language selector
        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left_panel.set_size_request(220, -1)
        
        # Language selector at top of sidebar
        self.create_language_selector(left_panel)
        
        # Sidebar
        self.stack_sidebar = Gtk.StackSidebar()
        left_panel.pack_start(self.stack_sidebar, True, True, 0)
        
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)

        self.stack_sidebar.set_stack(self.stack)

        self.main_box.pack_start(left_panel, False, False, 0)
        self.main_box.pack_start(self.stack, True, True, 0)

        # Initialize pages
        self.init_home_page()
        self.init_keyboard_page()
        self.init_system_tools_page()
        self.init_gaming_page()
        self.init_ui_tweaks_page()
        self.init_backup_page()  # New backup page
        self.init_about_page()

        self.show_all()

    def create_language_selector(self, parent_box):
        """Create language selector dropdown"""
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        lang_box.set_margin_start(10)
        lang_box.set_margin_end(10)
        lang_box.set_margin_top(10)
        lang_box.set_margin_bottom(5)
        
        lang_label = Gtk.Label(label="🌐")
        lang_box.pack_start(lang_label, False, False, 0)
        
        lang_combo = Gtk.ComboBoxText()
        lang_combo.append("th", "ไทย")
        lang_combo.append("en", "English")
        lang_combo.set_active(1)  # Default to English (ถ้า 0 => Thai)
        lang_combo.connect("changed", self.on_language_changed)
        lang_box.pack_start(lang_combo, True, True, 0)
        
        parent_box.pack_start(lang_box, False, False, 0)

    def on_language_changed(self, combo):
        """Handle language change"""
        lang = combo.get_active_id()
        self.i18n.set_language(lang)
        self.refresh_ui()

    def refresh_ui(self):
        """Refresh all UI text when language changes"""
        # Update window title
        self.set_title(self.i18n.get('window_title'))
        
        # Clear and recreate all pages
        for child in self.stack.get_children():
            self.stack.remove(child)
        
        self.init_home_page()
        self.init_keyboard_page()
        self.init_system_tools_page()
        self.init_gaming_page()
        self.init_ui_tweaks_page()
        self.init_backup_page()
        self.init_about_page()
        
        self.show_all()

    def apply_css(self):
        """Apply custom CSS styling to the application"""
        css_provider = Gtk.CssProvider()
        css = b"""
        .suggested-action {
            background: #00ADB5;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        .suggested-action:hover {
            background: #008C94;
        }
        .suggested-action:active {
            background: #006B73;
        }
        .destructive-action {
            background: #F05454;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        .destructive-action:hover {
            background: #D34545;
        }
        frame {
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        frame:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .language-selector {
            background: #f0f0f0;
            border-radius: 4px;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def create_page_box(self, title_text):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(30)
        box.set_margin_end(30)
        box.set_margin_top(30)
        box.set_margin_bottom(30)

        title = Gtk.Label()
        title.set_markup(f"<span size='xx-large' weight='bold'>{title_text}</span>")
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)

        return box

    def create_action_card(self, title, description, button_label, callback, button_style="suggested-action"):
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        t_label = Gtk.Label()
        t_label.set_markup(f"<span size='large' weight='bold' foreground='#00ADB5'>{title}</span>")
        t_label.set_halign(Gtk.Align.START)

        d_label = Gtk.Label(label=description)
        d_label.set_line_wrap(True)
        d_label.set_halign(Gtk.Align.START)
        d_label.set_max_width_chars(50)

        text_box.pack_start(t_label, False, False, 0)
        text_box.pack_start(d_label, False, False, 0)

        button = Gtk.Button(label=button_label)
        button.set_valign(Gtk.Align.CENTER)
        button.get_style_context().add_class(button_style)
        button.connect("clicked", callback)

        box.pack_start(text_box, True, True, 0)
        box.pack_end(button, False, False, 0)

        frame.add(box)
        return frame

    def init_home_page(self):
        page = self.create_page_box(self.i18n.get('home'))

        # Load icon from theme with fallback
        try:
            icon_image = Gtk.Image.new_from_icon_name("geng-settings-tools", Gtk.IconSize.DIALOG)
        except:
            icon_image = Gtk.Image.new_from_icon_name("applications-system", Gtk.IconSize.DIALOG)
        
        page.pack_start(icon_image, False, False, 10)

        welcome = Gtk.Label()
        welcome.set_markup(f"<span size='x-large'>{self.i18n.get('welcome')}</span>")
        page.pack_start(welcome, False, False, 10)

        info_text = f"{self.i18n.get('current_user', getpass.getuser())}\n{self.i18n.get('hostname', socket.gethostname())}"
        info_label = Gtk.Label()
        info_label.set_markup(info_text)
        page.pack_start(info_label, False, False, 5)

        desc = Gtk.Label(label=self.i18n.get('description'))
        desc.set_justify(Gtk.Justification.CENTER)
        page.pack_start(desc, False, False, 20)

        self.stack.add_titled(page, "home", self.i18n.get('home'))

    def init_keyboard_page(self):
        page = self.create_page_box(self.i18n.get('keyboard_title'))

        card1 = self.create_action_card(
            self.i18n.get('grave_accent_title'),
            self.i18n.get('grave_accent_desc'),
            self.i18n.get('apply_now'),
            lambda b: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" && "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"[]\" && "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"['grave']\" && "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source-backward \"['<Shift>grave']\""
            ),
        )

        card2 = self.create_action_card(
            self.i18n.get('alt_shift_title'),
            self.i18n.get('alt_shift_desc'),
            self.i18n.get('apply_now'),
            lambda b: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" && "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"['grp:alt_shift_toggle']\""
            ),
        )

        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        self.stack.add_titled(page, "keyboard", self.i18n.get('keyboard'))

    def init_system_tools_page(self):
        page = self.create_page_box(self.i18n.get('system_title'))

        card1 = self.create_action_card(
            self.i18n.get('optimize_title'),
            self.i18n.get('optimize_desc'),
            self.i18n.get('start'),
            lambda b: self.run_terminal_command("sudo apt update && sudo apt autoremove -y && sudo apt autoclean && sync && echo 3 | sudo tee /proc/sys/vm/drop_caches")
        )

        card2 = self.create_action_card(
            self.i18n.get('codecs_title'),
            self.i18n.get('codecs_desc'),
            self.i18n.get('install_now'),
            lambda b: self.run_terminal_command("sudo apt install -y ubuntu-restricted-extras mint-meta-codecs")
        )

        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        self.stack.add_titled(page, "system", self.i18n.get('system'))

    def init_gaming_page(self):
        page = self.create_page_box(self.i18n.get('gaming_title'))

        card1 = self.create_action_card(
            self.i18n.get('steam_title'),
            self.i18n.get('steam_desc'),
            self.i18n.get('install_now'),
            lambda b: self.run_terminal_command("sudo apt update && sudo apt install -y steam-installer wine64 winetricks")
        )

        page.pack_start(card1, False, False, 0)
        self.stack.add_titled(page, "gaming", self.i18n.get('gaming'))

    def init_ui_tweaks_page(self):
        page = self.create_page_box(self.i18n.get('ui_title'))

        card1 = self.create_action_card(
            self.i18n.get('dark_mode_title'),
            self.i18n.get('dark_mode_desc'),
            self.i18n.get('dark_mode'),
            lambda b: self.run_command("gsettings set org.cinnamon.desktop.interface gtk-theme 'Mint-Y-Dark-Aqua' && gsettings set org.cinnamon.theme name 'Mint-Y-Dark-Aqua'")
        )
        
        card2 = self.create_action_card(
            self.i18n.get('light_mode_title'),
            self.i18n.get('light_mode_desc'),
            self.i18n.get('light_mode'),
            lambda b: self.run_command("gsettings set org.cinnamon.desktop.interface gtk-theme 'Mint-Y' && gsettings set org.cinnamon.theme name 'Mint-Y'")
        )

        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        self.stack.add_titled(page, "ui", self.i18n.get('ui'))

    def init_backup_page(self):
        """Initialize backup and restore page"""
        page = self.create_page_box(self.i18n.get('backup_title'))

        # Backup card
        card1 = self.create_action_card(
            self.i18n.get('backup_settings_title'),
            self.i18n.get('backup_settings_desc'),
            self.i18n.get('backup_now'),
            lambda b: self.backup_settings()
        )

        # Restore card
        card2 = self.create_action_card(
            self.i18n.get('restore_settings_title'),
            self.i18n.get('restore_settings_desc'),
            self.i18n.get('restore_now'),
            lambda b: self.restore_settings(),
            "destructive-action"
        )

        # Export card
        card3 = self.create_action_card(
            self.i18n.get('export_settings_title'),
            self.i18n.get('export_settings_desc'),
            self.i18n.get('export_now'),
            lambda b: self.export_settings()
        )

        # Import card
        card4 = self.create_action_card(
            self.i18n.get('import_settings_title'),
            self.i18n.get('import_settings_desc'),
            self.i18n.get('import_now'),
            lambda b: self.import_settings()
        )

        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        page.pack_start(card3, False, False, 0)
        page.pack_start(card4, False, False, 0)

        self.stack.add_titled(page, "backup", self.i18n.get('backup'))

    def init_about_page(self):
        # Create a scrolled window for the about page content
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        page_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page_content_box.set_margin_start(30)
        page_content_box.set_margin_end(30)
        page_content_box.set_margin_top(30)
        page_content_box.set_margin_bottom(30)
        page_content_box.set_halign(Gtk.Align.CENTER)
        
        title = Gtk.Label()
        title.set_markup(f"<span size='xx-large' weight='bold'>{self.i18n.get('about_title')}</span>")
        title.set_halign(Gtk.Align.START)
        page_content_box.pack_start(title, False, False, 0)

        label = Gtk.Label()
        label.set_markup(
            "<span size='x-large' weight='bold' foreground='#00ADB5'>Geng Settings Tools</span>\n"
            "<span>เวอร์ชัน 2.0.6 (GTK Edition)</span>\n\n"
            f"<b>{self.i18n.get('developer')}</b> คุณธรรมสรณ์ มุสิกพันธ์ (เก่ง)\n"
            f"<b>{self.i18n.get('email')}</b> gtzx26@gmail.com\n\n"
            f"{self.i18n.get('thanks')}"
        )
        label.set_justify(Gtk.Justification.CENTER)
        page_content_box.pack_start(label, False, False, 0)

        # Donate Section
        donate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        donate_box.set_margin_top(20)
        donate_box.set_halign(Gtk.Align.CENTER)
        donate_box.set_valign(Gtk.Align.CENTER)

        donate_title = Gtk.Label()
        donate_title.set_markup(f"<span size='large' weight='bold' foreground='#F9ED69'>{self.i18n.get('donate')}</span>")
        donate_box.pack_start(donate_title, False, False, 0)

        # Try multiple paths for QR code
        qr_paths = [
            "/usr/share/gst-assets/qrcode.png",
            os.path.expanduser("~/.local/share/gst-assets/qrcode.png"),
            "./assets/qrcode.png",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "qrcode.png")
        ]

        qr_found = False
        for path in qr_paths:
            if os.path.exists(path):
                try:
                    qr_image = Gtk.Image.new_from_file(path)
                    qr_image.set_pixel_size(200)
                    donate_box.pack_start(qr_image, False, False, 0)
                    qr_found = True
                    break
                except GLib.Error:
                    continue

        if not qr_found:
            # Show text placeholder instead of QR code
            no_qr_label = Gtk.Label(label=self.i18n.get('qr_placeholder'))
            no_qr_label.set_sensitive(False)
            no_qr_label.set_margin_top(10)
            no_qr_label.set_margin_bottom(10)
            donate_box.pack_start(no_qr_label, False, False, 0)

        bank_info = Gtk.Label()
        bank_info.set_markup(
            f"<b>{self.i18n.get('bank_kbank')}</b> 119-2-45517-7<br>"
            f"<b>{self.i18n.get('account_name')}</b> นาย ธรรมสรณ์ มุสิกพันธ์<br><br>"
            f"<b>{self.i18n.get('paypal')}</b> thammasorn2456@gmail.com<br><br>"
            f"<b>{self.i18n.get('bitcoin')}</b> <span selectable='true'>bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt</span>"
        )
        bank_info.set_justify(Gtk.Justification.CENTER)
        bank_info.set_line_wrap(True)
        donate_box.pack_start(bank_info, False, False, 0)

        page_content_box.pack_start(donate_box, False, False, 0)
        
        scrolled_window.add(page_content_box)
        self.stack.add_titled(scrolled_window, "about", self.i18n.get('about'))

    # Backup and Restore Functions
    def backup_settings(self):
        """Backup current settings to file"""
        dialog = Gtk.FileChooserDialog(
            title=self.i18n.get('backup_settings_title'),
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            self.i18n.get('cancel'), Gtk.ResponseType.CANCEL,
            self.i18n.get('ok'), Gtk.ResponseType.OK
        )
        
        # Set default filename
        backup_dir = SettingsManager.get_backup_dir()
        dialog.set_current_folder(backup_dir)
        dialog.set_current_name(SettingsManager.get_default_backup_filename())
        
        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files (*.json)")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if not filepath.endswith('.json'):
                filepath += '.json'
            
            success, result = SettingsManager.backup_to_file(filepath)
            if success:
                self.show_message(
                    self.i18n.get('success'),
                    self.i18n.get('backup_success', result)
                )
            else:
                self.show_message(
                    self.i18n.get('error'),
                    self.i18n.get('backup_failed', result),
                    Gtk.MessageType.ERROR
                )
        
        dialog.destroy()

    def restore_settings(self):
        """Restore settings from backup file"""
        # Show confirmation dialog
        confirm = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=self.i18n.get('confirm_restore')
        )
        confirm.format_secondary_text(self.i18n.get('confirm_restore_msg'))
        
        if confirm.run() != Gtk.ResponseType.YES:
            confirm.destroy()
            return
        confirm.destroy()
        
        # File chooser
        dialog = Gtk.FileChooserDialog(
            title=self.i18n.get('restore_settings_title'),
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            self.i18n.get('cancel'), Gtk.ResponseType.CANCEL,
            self.i18n.get('ok'), Gtk.ResponseType.OK
        )
        
        # Set to backup directory
        dialog.set_current_folder(SettingsManager.get_backup_dir())
        
        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files (*.json)")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            success, result = SettingsManager.restore_from_file(filepath)
            if success:
                self.show_message(
                    self.i18n.get('success'),
                    self.i18n.get('restore_success')
                )
            else:
                self.show_message(
                    self.i18n.get('error'),
                    self.i18n.get('restore_failed', result),
                    Gtk.MessageType.ERROR
                )
        
        dialog.destroy()

    def export_settings(self):
        """Export settings for sharing"""
        dialog = Gtk.FileChooserDialog(
            title=self.i18n.get('export_settings_title'),
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            self.i18n.get('cancel'), Gtk.ResponseType.CANCEL,
            self.i18n.get('ok'), Gtk.ResponseType.OK
        )
        
        # Set default filename without sensitive info
        default_name = f"geng_settings_export_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_current_name(default_name)
        
        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files (*.json)")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if not filepath.endswith('.json'):
                filepath += '.json'
            
            # Get settings and remove user-specific info
            settings = SettingsManager.get_current_settings()
            settings.pop('user', None)
            settings.pop('hostname', None)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                self.show_message(
                    self.i18n.get('success'),
                    self.i18n.get('export_success', filepath)
                )
            except Exception as e:
                self.show_message(
                    self.i18n.get('error'),
                    self.i18n.get('export_failed', str(e)),
                    Gtk.MessageType.ERROR
                )
        
        dialog.destroy()

    def import_settings(self):
        """Import settings from exported file"""
        dialog = Gtk.FileChooserDialog(
            title=self.i18n.get('import_settings_title'),
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            self.i18n.get('cancel'), Gtk.ResponseType.CANCEL,
            self.i18n.get('ok'), Gtk.ResponseType.OK
        )
        
        dialog.set_current_folder(os.path.expanduser("~"))
        
        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files (*.json)")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Apply settings
                success, result = SettingsManager.apply_settings(settings)
                if success:
                    self.show_message(
                        self.i18n.get('success'),
                        self.i18n.get('import_success')
                    )
                else:
                    self.show_message(
                        self.i18n.get('error'),
                        self.i18n.get('import_failed', result),
                        Gtk.MessageType.ERROR
                    )
            except Exception as e:
                self.show_message(
                    self.i18n.get('error'),
                    self.i18n.get('import_failed', str(e)),
                    Gtk.MessageType.ERROR
                )
        
        dialog.destroy()

    def check_root_permission(self, show_warning=True):
        """Check if running with root privileges"""
        if os.geteuid() != 0 and show_warning:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=self.i18n.get('warning')
            )
            dialog.format_secondary_text(self.i18n.get('root_warning'))
            dialog.run()
            dialog.destroy()
            return False
        return os.geteuid() == 0

    def run_command(self, cmd):
        """Run a command without opening a terminal window"""
        try:
            result = subprocess.run(cmd, shell=True, check=True, 
                                   capture_output=True, text=True)
            self.show_message(self.i18n.get('success'), self.i18n.get('settings_applied'))
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            self.show_message(
                self.i18n.get('error'),
                self.i18n.get('command_failed', error_msg),
                Gtk.MessageType.ERROR
            )
        except Exception as e:
            self.show_message(
                self.i18n.get('error'),
                self.i18n.get('command_failed', str(e)),
                Gtk.MessageType.ERROR
            )

    def run_terminal_command(self, cmd):
        """Run a command in a new terminal window"""
        try:
            # Check if gnome-terminal is available
            gnome_terminal_check = subprocess.run(
                ["which", "gnome-terminal"], 
                capture_output=True, 
                text=True
            )
            
            if gnome_terminal_check.returncode != 0:
                self.show_message(
                    self.i18n.get('error'),
                    self.i18n.get('no_terminal'),
                    Gtk.MessageType.ERROR
                )
                return

            if "sudo" in cmd:
                # Remove 'sudo' from the command as we'll use pkexec
                actual_cmd = cmd.replace("sudo ", "")
                
                # Escape single quotes in the command
                actual_cmd = actual_cmd.replace("'", "'\\''")
                
                # Create terminal command with pkexec
                terminal_cmd = [
                    "gnome-terminal",
                    "--title=Geng Settings Tools - รันคำสั่ง",
                    "--",
                    "bash", "-c",
                    f"pkexec bash -c '{actual_cmd}'; echo ''; echo '✅ เสร็จสิ้น - กด Enter เพื่อปิดหน้าต่างนี้...'; read"
                ]
            else:
                # Escape single quotes in the command
                cmd = cmd.replace("'", "'\\''")
                
                terminal_cmd = [
                    "gnome-terminal",
                    "--title=Geng Settings Tools - รันคำสั่ง",
                    "--",
                    "bash", "-c",
                    f"{cmd}; echo ''; echo '✅ เสร็จสิ้น - กด Enter เพื่อปิดหน้าต่างนี้...'; read"
                ]
            
            # Run the terminal command
            subprocess.Popen(terminal_cmd)
            
        except FileNotFoundError as e:
            self.show_message(
                self.i18n.get('error'),
                self.i18n.get('command_failed', str(e)),
                Gtk.MessageType.ERROR
            )
        except Exception as e:
            self.show_message(
                self.i18n.get('error'),
                self.i18n.get('command_failed', str(e)),
                Gtk.MessageType.ERROR
            )

    def show_message(self, title, message, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    # Check if running with proper display
    if not os.environ.get('DISPLAY'):
        print("Error: No display found. Please run this program in a graphical environment.")
        sys.exit(1)
    
    try:
        win = GengSettingsTools()
        win.connect("destroy", Gtk.main_quit)
        Gtk.main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
