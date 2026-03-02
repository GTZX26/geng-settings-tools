#!/usr/bin/env python3
import gi
import os
import subprocess
import socket
import getpass

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('Handy', '1')
    from gi.repository import Gtk, Gdk, Gio, GLib, Handy
    HAS_HANDY = True
except (ImportError, ValueError):
    from gi.repository import Gtk, Gdk, Gio, GLib
    HAS_HANDY = False

class GengSettingsTools(Gtk.Window):
    def __init__(self):
        super().__init__(title="Geng Settings Tools v2.0")
        self.set_default_size(900, 650)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Paths
        self.icon_path = "/usr/share/gst-assets/icon.png"
        if not os.path.exists(self.icon_path):
            self.icon_path = os.path.expanduser("~/gst_work/GST/usr/share/gst-assets/icon.png")
            
        if os.path.exists(self.icon_path):
            self.set_icon_from_file(self.icon_path)

        if HAS_HANDY:
            Handy.init()
            self.main_box = Handy.Leaflet()
        else:
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            
        self.add(self.main_box)

        # Sidebar
        self.stack_sidebar = Gtk.StackSidebar()
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)
        
        self.stack_sidebar.set_stack(self.stack)
        self.stack_sidebar.set_width_request(220)
        
        self.main_box.add(self.stack_sidebar)
        self.main_box.add(self.stack)

        self.init_home_page()
        self.init_keyboard_page()
        self.init_system_tools_page()
        self.init_gaming_page()
        self.init_ui_tweaks_page()
        self.init_about_page()
        
        self.show_all()

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

    def create_action_card(self, title, description, button_label, callback):
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
        
        text_box.pack_start(t_label, False, False, 0)
        text_box.pack_start(d_label, False, False, 0)
        
        button = Gtk.Button(label=button_label)
        button.set_valign(Gtk.Align.CENTER)
        button.get_style_context().add_class("suggested-action")
        button.connect("clicked", callback)
        
        box.pack_start(text_box, True, True, 0)
        box.pack_end(button, False, False, 0)
        
        frame.add(box)
        return frame

    def init_home_page(self):
        page = self.create_page_box("หน้าแรก")
        
        if os.path.exists(self.icon_path):
            image = Gtk.Image.new_from_file(self.icon_path)
            # Resize image if needed
            page.pack_start(image, False, False, 10)

        welcome = Gtk.Label()
        welcome.set_markup("<span size='x-large'>ยินดีต้อนรับสู่ <b>Geng Settings Tools</b></span>")
        page.pack_start(welcome, False, False, 10)
        
        info_text = f"ผู้ใช้ปัจจุบัน: <b>{getpass.getuser()}</b>\nเครื่องคอมพิวเตอร์: <b>{socket.gethostname()}</b>"
        info_label = Gtk.Label()
        info_label.set_markup(info_text)
        page.pack_start(info_label, False, False, 5)
        
        desc = Gtk.Label(label="เครื่องมือช่วยตั้งค่าพื้นฐานสำหรับ Linux Mint Cinnamon 22.3\nออกแบบมาเพื่อให้การใช้งาน Linux เป็นเรื่องง่ายสำหรับทุกคน")
        desc.set_justify(Gtk.Justification.CENTER)
        page.pack_start(desc, False, False, 20)
        
        self.stack.add_titled(page, "home", "หน้าแรก")

    def init_keyboard_page(self):
        page = self.create_page_box("คีย์บอร์ด & ภาษา")
        
        card1 = self.create_action_card(
            "สลับภาษาด้วยปุ่ม Grave Accent (~)",
            "ตั้งค่าให้ใช้ปุ่มตัวหนอน (Grave Accent) ในการสลับภาษา (มาตรฐานคนไทย)",
            "ตั้งค่าทันที",
            lambda b: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" && "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"[]\" && "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"['grave']\" && "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source-backward \"['<Shift>grave']\""
            )
        )
        
        card2 = self.create_action_card(
            "สลับภาษาด้วยปุ่ม Alt+Shift",
            "ตั้งค่าให้ใช้ปุ่ม Alt + Shift ในการสลับภาษา",
            "ตั้งค่าทันที",
            lambda b: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" && "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"[]\" && "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"['grp:alt_shift_toggle']\""
            )
        )
        
        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        self.stack.add_titled(page, "keyboard", "คีย์บอร์ด & ภาษา")

    def init_system_tools_page(self):
        page = self.create_page_box("เครื่องมือระบบ")
        
        card1 = self.create_action_card(
            "เพิ่มประสิทธิภาพระบบ",
            "ล้างแคช, ลบแพ็กเกจที่ไม่ได้ใช้งาน และทำความสะอาดระบบ",
            "เริ่มทำงาน",
            lambda b: self.run_terminal_command("sudo apt update && sudo apt autoremove -y && sudo apt autoclean && sync && echo 3 | sudo tee /proc/sys/vm/drop_caches")
        )
        
        card2 = self.create_action_card(
            "ติดตั้ง Multimedia Codecs",
            "ติดตั้งตัวแปลงสัญญาณเพื่อให้ดูหนังฟังเพลงได้ทุกรูปแบบ",
            "ติดตั้งทันที",
            lambda b: self.run_terminal_command("sudo apt install -y ubuntu-restricted-extras mint-meta-codecs")
        )
        
        page.pack_start(card1, False, False, 0)
        page.pack_start(card2, False, False, 0)
        self.stack.add_titled(page, "system", "เครื่องมือระบบ")

    def init_gaming_page(self):
        page = self.create_page_box("พร้อมสำหรับการเล่นเกม")
        
        card1 = self.create_action_card(
            "ติดตั้ง Steam & Wine",
            "เตรียมเครื่องให้พร้อมสำหรับการเล่นเกมบน Linux",
            "ติดตั้งทันที",
            lambda b: self.run_terminal_command("sudo apt update && sudo apt install -y steam-installer wine64 winetricks")
        )
        
        page.pack_start(card1, False, False, 0)
        self.stack.add_titled(page, "gaming", "เล่นเกม")

    def init_ui_tweaks_page(self):
        page = self.create_page_box("ปรับแต่งหน้าตา (UI)")
        
        card1 = self.create_action_card(
            "สลับเป็น Dark Mode",
            "เปลี่ยนธีมของระบบให้เป็นโหมดมืดเพื่อถนอมสายตา",
            "เปิดโหมดมืด",
            lambda b: self.run_command("gsettings set org.cinnamon.desktop.interface gtk-theme 'Mint-Y-Dark-Aqua' && gsettings set org.cinnamon.theme name 'Mint-Y-Dark-Aqua'")
        )
        
        page.pack_start(card1, False, False, 0)
        self.stack.add_titled(page, "ui", "ปรับแต่ง UI")

    def init_about_page(self):
        page = self.create_page_box("เกี่ยวกับ")
        page.set_halign(Gtk.Align.CENTER)
        
        label = Gtk.Label()
        label.set_markup(
            "<span size='xx-large' weight='bold' foreground='#00ADB5'>Geng Settings Tools</span>\n"
            "<span>เวอร์ชัน 2.0 (GTK Edition)</span>\n\n"
            "<b>ผู้พัฒนา:</b> คุณธรรมสรณ์ มุสิกพันธ์ (Geng)\n"
            "<b>Email:</b> gtzx26@gmail.com\n\n"
            "เครื่องมือนี้สร้างขึ้นเพื่อช่วยให้คนไทยใช้งาน Linux ได้ง่ายขึ้น\n"
            "ขอขอบคุณที่ร่วมเป็นส่วนหนึ่งของครอบครัว Open Source"
        )
        label.set_justify(Gtk.Justification.CENTER)
        page.pack_start(label, False, False, 0)
        
        self.stack.add_titled(page, "about", "เกี่ยวกับ")

    def run_command(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True)
            self.show_message("สำเร็จ", "ดำเนินการตั้งค่าเรียบร้อยแล้ว!")
        except Exception as e:
            self.show_message("ข้อผิดพลาด", f"ไม่สามารถดำเนินการได้: {str(e)}", Gtk.MessageType.ERROR)

    def run_terminal_command(self, cmd):
        # ใช้ pkexec สำหรับคำสั่งที่ต้องการสิทธิ์ root
        if "sudo" in cmd:
            cmd = cmd.replace("sudo ", "")
            full_cmd = f"gnome-terminal -- bash -c 'pkexec bash -c \"{cmd}\"; echo; echo กด Enter เพื่อปิด...; read'"
        else:
            full_cmd = f"gnome-terminal -- bash -c \"{cmd}; echo; echo กด Enter เพื่อปิด...; read\""
        
        subprocess.Popen(full_cmd, shell=True)

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
    win = GengSettingsTools()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
