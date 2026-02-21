# Geng Setting Tools

แอปเดสก์ท็อป (PyQt6) สำหรับ Linux Mint 22.3 Cinnamon เพื่อช่วยตั้งค่าคีย์บอร์ด/ภาษา และเครื่องมือดูแลระบบแบบคลิกเดียว

## โครงสร้างโปรเจกต์

- `src/geng_settings_tools.py` — โค้ดแอปหลัก
- `debian/` — ไฟล์แพ็กเกจ Debian สำหรับสร้าง `GST.deb`
- `packaging/geng-setting-tools.desktop` — เมนูแอป
- `packaging/io.github.gengx26.geng-setting-tools.metainfo.xml` — AppStream metadata (ให้ Software Manager แสดงข้อมูล)
- `assets/README.md` — วิธีใส่ `icon.png`/`qrcode.png` เองโดยไม่ commit binary

## วิธี build เป็นไฟล์ .deb

บน Linux Mint/Ubuntu:

```bash
sudo apt update
sudo apt install -y build-essential devscripts debhelper dh-python

dpkg-buildpackage -us -uc -b
```

ไฟล์ `.deb` จะถูกสร้างไว้ที่โฟลเดอร์ชั้นบนของโปรเจกต์ เช่น:

- `../geng-setting-tools_1.1.0-2_all.deb`

ติดตั้งด้วย:

```bash
sudo apt install ../geng-setting-tools_1.1.0-2_all.deb
```

## จะให้ขึ้นใน Software Manager ต้องทำอย่างไร

Software Manager จะดึงแอปจาก “repository” (APT repo / PPA / distro repo) ไม่ได้ดึงตรงจาก GitHub โดยตรง

### ตัวเลือกที่แนะนำสำหรับมือใหม่

1. **เริ่มจากแจกไฟล์ `.deb` ใน GitHub Releases**
   - คนทั่วไปดาวน์โหลดง่าย
   - ยังไม่ขึ้นใน Software Manager อัตโนมัติ
2. **ทำ APT repository เอง** (เช่นใช้ `reprepro` + GitHub Pages/Cloudflare R2)
   - ผู้ใช้เพิ่ม repo ครั้งเดียว แล้วได้อัปเดตผ่าน APT
3. **ส่งเข้า repo ของ Linux Mint/Ubuntu (ยากที่สุด)**
   - ถ้าผ่าน review จะขึ้น Software Manager โดยตรงแบบ native

## ระบบอัปเดตจากคุณไปหาผู้ใช้

ถ้าต้องการ “แจ้งอัปเดตอัตโนมัติ” แนะนำใช้ **APT repo ของคุณเอง**:

- เมื่อออกเวอร์ชันใหม่ (`1.1.1`, `1.2.0`)
- อัปโหลดแพ็กเกจใหม่เข้า repo
- ผู้ใช้จะเห็นอัปเดตผ่าน Update Manager / Software Manager

## ข้อแนะนำสำคัญ

- วางโลโก้จริงเป็น `/usr/share/geng-setting-tools/icon.png` และ QR เป็น `/usr/share/geng-setting-tools/qrcode.png` ตอนติดตั้งจริง
- เพิ่ม LICENSE (MIT) และหน้า Releases ให้ชัดเจน
- สร้าง Issue template / changelog เพื่อให้ผู้ใช้แจ้งปัญหาได้ง่าย
- ถ้าจะโตระยะยาว ให้พิจารณาทำ Flatpak ด้วย (Linux Mint รองรับดี)


## หมายเหตุเรื่อง binary

ถ้าระบบรีวิวแจ้งว่า **ไม่รองรับไบนารี** ให้เก็บรูปไว้ใน release asset หรือ package artifact แทนการ commit เข้า git โดยตรง
