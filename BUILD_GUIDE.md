# 📦 Geng Settings Tools - Build Guide

## ปัญหาที่พบและวิธีแก้ไข

### 🔴 ปัญหาหลัก
เวลา build แล้วโปรแกรมมีปัญหา แม้ว่าโค้ดรันได้ปกติ ปัญหาเกิดจากการจัดการไฟล์และพาธ (Path) ที่ไม่ถูกต้อง

### ✅ วิธีแก้ไขที่ทำให้แล้ว

#### 1. **ปัญหาเรื่องการหาไฟล์ Assets (รูปภาพ)**
   - **ปัญหา:** โค้ดมองหาไฟล์ QR Code จากเพียงไม่กี่ที่ ถ้า build ไปวางในที่อื่นจะหาไฟล์ไม่เจอ
   - **วิธีแก้:** เพิ่มพาธเพิ่มเติมในโค้ด และจัดเรียงลำดับความสำคัญให้ถูกต้อง
   ```python
   qr_paths = [
       "/usr/share/gst-assets/qrcode.png",              # ตำแหน่งหลักหลัง install
       os.path.expanduser("~/.local/share/gst-assets/qrcode.png"),  # User directory
       os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "qrcode.png"),  # ข้างๆ ไฟล์ .py
       os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "qrcode.png"),  # ข้างๆ src folder
       "./assets/qrcode.png"  # Current directory
   ]
   ```

#### 2. **ปัญหาเรื่อง Shebang (#!/usr/bin/env python3)**
   - **ปัญหา:** ไฟล์ Python ต้องมี shebang เพื่อให้ระบบรู้ว่าใช้ interpreter ตัวไหน
   - **วิธีแก้:** เพิ่ม `#!/usr/bin/env python3` ที่บรรทัดแรกของไฟล์

#### 3. **ปัญหาเรื่อง Desktop Entry**
   - **ปัญหา:** ไฟล์ `.desktop` ระบุให้รันที่ `/usr/local/bin/geng-settings-tools` แต่ build script ไม่ได้สร้างไฟล์นั้น
   - **วิธีแก้:** เปลี่ยน `Exec=python3 /usr/local/bin/geng-settings-tools` เป็น `Exec=geng-settings-tools` เพื่อให้ระบบหาไฟล์เองจาก PATH

#### 4. **ปัญหาเรื่อง Dependencies**
   - **ปัญหา:** ไฟล์ control ไม่ได้ระบุ dependencies ที่จำเป็นทั้งหมด
   - **วิธีแก้:** เพิ่ม dependencies ที่ขาด:
   ```
   Depends: python3, python3-gi, gir1.2-gtk-3.0, policykit-1, gnome-terminal, 
            gir1.2-gdkpixbuf-2.0, gir1.2-pango-1.0, gir1.2-glib-2.0
   ```

#### 5. **ปัญหาเรื่องไอคอน (Icon)**
   - **ปัญหา:** ไอคอนต้องติดตั้งในตำแหน่งมาตรฐานของ Linux
   - **วิธีแก้:** ติดตั้งไอคอนใน `/usr/share/icons/hicolor/` ตามมาตรฐาน XDG

## 🚀 วิธี Build ที่ถูกต้อง

### ขั้นตอนที่ 1: ใช้ Build Script
```bash
cd /path/to/geng-settings-tools
chmod +x build.sh
./build.sh
```

สคริปต์นี้จะ:
1. สร้างโครงสร้างโฟลเดอร์ที่ถูกต้อง
2. คัดลอกไฟล์ทั้งหมดไปยังตำแหน่งที่ถูกต้อง
3. ตั้งค่าสิทธิ์การรัน (executable permission)
4. สร้างไฟล์ `.deb` ที่พร้อมติดตั้ง

### ขั้นตอนที่ 2: ติดตั้งแพ็กเกจ
```bash
sudo apt install ./geng-settings-tools_2.0.6_all.deb
```

### ขั้นตอนที่ 3: รันโปรแกรม
```bash
geng-settings-tools
```

หรือค้นหา "Geng Settings Tools" ในเมนู Applications

## 📋 ไฟล์ที่ได้รับการแก้ไข

| ไฟล์ | การแก้ไข |
|------|---------|
| `src/geng-settings-tools.py` | เพิ่ม shebang และปรับปรุงการหาไฟล์ assets |
| `packaging/geng-settings-tools.desktop` | เปลี่ยน Exec path ให้ถูกต้อง |
| `debian/control` | เพิ่ม dependencies ที่ขาด |
| `build.sh` (ไฟล์ใหม่) | สคริปต์สำหรับ build ที่ถูกต้อง |

## 🔍 การตรวจสอบ

หลังจาก build เสร็จ สามารถตรวจสอบเนื้อหาของแพ็กเกจได้:
```bash
dpkg -c geng-settings-tools_2.0.6_all.deb
```

ควรจะเห็นไฟล์ต่อไปนี้:
- `/usr/bin/geng-settings-tools` - ไฟล์โปรแกรมหลัก
- `/usr/share/gst-assets/qrcode.png` - ไฟล์ QR Code
- `/usr/share/icons/hicolor/*/apps/geng-settings-tools.png` - ไอคอน
- `/usr/share/applications/geng-settings-tools.desktop` - Desktop Entry

## 💡 เคล็ดลับเพิ่มเติม

### ถ้าต้องการ uninstall
```bash
sudo apt remove geng-settings-tools
```

### ถ้าต้องการ rebuild
```bash
cd /path/to/geng-settings-tools
rm -f geng-settings-tools_*.deb
./build.sh
```

### ถ้าต้องการแก้ไขโค้ด
1. แก้ไขไฟล์ใน `src/geng-settings-tools.py`
2. รัน `./build.sh` อีกครั้ง
3. ติดตั้งแพ็กเกจใหม่

## 📞 ติดต่อ

หากมีปัญหาเพิ่มเติม สามารถติดต่อผู้พัฒนาได้ที่:
- **Email:** gtzx26@gmail.com
- **GitHub:** https://github.com/GTZX26/geng-settings-tools

---

**ขอบคุณที่ใช้ Geng Settings Tools! 🎉**
