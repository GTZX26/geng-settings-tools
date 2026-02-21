#!/usr/bin/env python3
"""Geng Setting Tools (GST) main application."""

import getpass
import os
import shlex
import socket
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class GengSettingsTools(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geng Setting Tools")
        self.setFixedSize(850, 600)

        self.icon_path = "/usr/share/geng-setting-tools/icon.png"
        self.qr_path = "/usr/share/geng-setting-tools/qrcode.png"

        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.setStyleSheet(
            """
            QMainWindow { background-color: #121212; }
            QWidget#Sidebar { background-color: #1E1E1E; border-right: 1px solid #333; }
            QListWidget { background-color: #1E1E1E; border: none; color: #E0E0E0; font-size: 14px; outline: none; }
            QListWidget::item { padding: 15px; border-bottom: 1px solid #2A2A2A; }
            QListWidget::item:selected { background-color: #333; color: #00ADB5; border-left: 3px solid #00ADB5; }
            QWidget#ContentArea { background-color: #121212; }
            QLabel { color: #E0E0E0; }
            QPushButton { background-color: #00ADB5; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #008C92; }
            QFrame#Card { background-color: #1E1E1E; border: 1px solid #333; border-radius: 8px; }
            """
        )

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)

        self.menu_list = QListWidget()
        self.menu_list.addItem("หน้าแรก")
        self.menu_list.addItem("คีย์บอร์ด & ภาษา")
        self.menu_list.addItem("เครื่องมือระบบ")
        self.menu_list.addItem("เกี่ยวกับ")
        self.menu_list.currentRowChanged.connect(self.display_page)

        sidebar_layout.addWidget(self.menu_list)
        layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("ContentArea")

        self.init_home_page()
        self.init_keyboard_page()
        self.init_tools_page()
        self.init_about_page()

        layout.addWidget(self.pages)
        self.menu_list.setCurrentRow(0)

    def create_card(self, title, description, btn_text, callback):
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedHeight(100)
        card_layout = QHBoxLayout(card)

        text_layout = QVBoxLayout()
        t_label = QLabel(title)
        t_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ADB5;")
        d_label = QLabel(description)
        d_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")

        text_layout.addWidget(t_label)
        text_layout.addWidget(d_label)

        btn = QPushButton(btn_text)
        btn.setFixedWidth(120)
        btn.clicked.connect(callback)

        card_layout.addLayout(text_layout)
        card_layout.addStretch()
        card_layout.addWidget(btn)
        return card

    def init_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        if os.path.exists(self.icon_path):
            logo_img = QLabel()
            logo_img.setPixmap(
                QPixmap(self.icon_path).scaled(
                    100,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            layout.addWidget(logo_img, alignment=Qt.AlignmentFlag.AlignLeft)

        welcome = QLabel("ยินดีต้อนรับสู่ Geng Setting Tools")
        welcome.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 10px;")

        username = getpass.getuser()
        pc_info = QLabel(
            f"ผู้ใช้ปัจจุบัน: {username} | เครื่องคอมพิวเตอร์: {socket.gethostname()}"
        )
        pc_info.setStyleSheet("color: #00ADB5; font-size: 13px; font-style: italic;")

        desc = QLabel(
            "เครื่องมือช่วยตั้งค่าพื้นฐานสำหรับ Linux Mint Cinnamon 22.3\n"
            "เลือกเมนูทางด้านซ้ายเพื่อเริ่มการตั้งค่า"
        )
        desc.setStyleSheet("font-size: 14px; color: #AAAAAA; margin-top: 10px;")

        layout.addWidget(welcome)
        layout.addWidget(pc_info)
        layout.addWidget(desc)
        layout.addStretch()
        self.pages.addWidget(page)

    def init_keyboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("การตั้งค่าคีย์บอร์ด & ภาษา")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        card1 = self.create_card(
            "สลับภาษาด้วยปุ่ม Grave Accent (~)",
            "ตั้งค่าให้ใช้ปุ่มตัวหนอน (Grave Accent) ในการสลับภาษา",
            "ตั้งค่าทันที",
            lambda: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" ; "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"[]\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"['grave']\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source-backward \"['<Shift>grave']\""
            ),
        )

        card2 = self.create_card(
            "สลับภาษาด้วยปุ่ม Alt+Shift",
            "ตั้งค่าให้ใช้ปุ่ม Alt + Shift ในการสลับภาษา",
            "ตั้งค่าทันที",
            lambda: self.run_command(
                "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'th')]\" ; "
                "gsettings set org.cinnamon.desktop.keybindings.wm switch-input-source \"[]\" ; "
                "gsettings set org.gnome.desktop.input-sources xkb-options \"['grp:alt_shift_toggle']\""
            ),
        )

        layout.addWidget(card1)
        layout.addWidget(card2)
        layout.addStretch()
        self.pages.addWidget(page)

    def init_tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("เครื่องมือระบบ")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        card1 = self.create_card(
            "อัปเดตระบบ",
            "ตรวจสอบและติดตั้งการอัปเดตล่าสุด",
            "เริ่มอัปเดต",
            lambda: self.run_terminal_command("sudo apt update && sudo apt upgrade -y"),
        )
        card2 = self.create_card(
            "ล้างไฟล์ขยะ",
            "ลบแพ็กเกจที่ไม่ได้ใช้งาน",
            "เริ่มทำความสะอาด",
            lambda: self.run_terminal_command("sudo apt autoremove -y && sudo apt autoclean"),
        )

        layout.addWidget(card1)
        layout.addWidget(card2)
        layout.addStretch()
        self.pages.addWidget(page)

    def init_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        logo = QLabel()
        if os.path.exists(self.icon_path):
            logo.setPixmap(
                QPixmap(self.icon_path).scaled(
                    80,
                    80,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel("Geng Setting Tools")
        name.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ADB5;")

        info = QLabel(
            "<b>ผู้พัฒนา:</b> คุณธรรมสรณ์ มุสิกพันธ์ (Geng)<br>"
            "<b>Email:</b> gtzx26@gmail.com | <b>PayPal:</b> thammasorn2456@gmail.com"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #E0E0E0; font-size: 13px;")

        donate_box = QFrame()
        donate_box.setFixedWidth(620)
        donate_box.setStyleSheet(
            "background-color: #1E1E1E; border: 1px dashed #F9ED69; border-radius: 10px; padding: 15px;"
        )
        donate_layout = QHBoxLayout(donate_box)

        qr_label = QLabel()
        if os.path.exists(self.qr_path):
            qr_pixmap = QPixmap(self.qr_path).scaled(
                150,
                150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            qr_label.setPixmap(qr_pixmap)
            qr_label.setStyleSheet("border: 2px solid white; background-color: white;")

        qr_label.setFixedSize(150, 150)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        details_layout = QVBoxLayout()
        d_title = QLabel("☕ สนับสนุนค่ากาแฟผู้พัฒนา")
        d_title.setStyleSheet(
            "font-weight: bold; color: #F9ED69; border: none; font-size: 16px;"
        )

        bank_info = QLabel(
            "<b>กสิกรไทย (K-Bank):</b> 119-2-45517-7<br>"
            "<b>ชื่อบัญชี:</b> นาย ธรรมสรณ์ มุสิกพันธ์<br><br>"
            "<b>Bitcoin (BTC):</b>"
        )
        bank_info.setStyleSheet("color: white; border: none; font-size: 13px;")

        btc_address = QLabel("bc1q9vyeatst52eef7mv6fp2dpalxc6qwt9aug5rlt")
        btc_address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        btc_address.setStyleSheet(
            "color: #F7931A; font-family: Monospace; font-size: 12px; border: none;"
            "background: #2A2A2A; padding: 3px; border-radius: 3px;"
        )
        btc_address.setToolTip("คุณสามารถลากคลุมดำและคัดลอกที่อยู่นี้ได้")

        details_layout.addWidget(d_title)
        details_layout.addWidget(bank_info)
        details_layout.addWidget(btc_address)

        donate_layout.addWidget(qr_label)
        donate_layout.addLayout(details_layout)

        layout.addStretch()
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(donate_box, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.pages.addWidget(page)

    def display_page(self, index):
        self.pages.setCurrentIndex(index)

    def run_command(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True)
            QMessageBox.information(self, "สำเร็จ", "ตั้งค่าปุ่มสลับภาษาเรียบร้อยแล้ว!")
        except subprocess.CalledProcessError as exc:
            QMessageBox.critical(self, "ข้อผิดพลาด", f"ไม่สามารถตั้งค่าได้: {exc}")

    def run_terminal_command(self, cmd):
        full_cmd = (
            "gnome-terminal -- bash -c "
            + shlex.quote(f"{cmd}; echo; echo กด Enter เพื่อปิด...; read")
        )
        subprocess.Popen(full_cmd, shell=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GengSettingsTools()
    window.show()
    sys.exit(app.exec())
