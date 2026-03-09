#!/bin/bash

# Geng Settings Tools Build Script
# สร้างไฟล์ .deb สำหรับติดตั้งใน Linux Mint / Ubuntu

VERSION="2.0.6"
PKG_NAME="geng-settings-tools"
BUILD_DIR="build_pkg"

echo "🚀 เริ่มต้นการ build $PKG_NAME v$VERSION..."

# 1. ล้างโฟลเดอร์ build เก่า
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR/DEBIAN
mkdir -p $BUILD_DIR/usr/bin
mkdir -p $BUILD_DIR/usr/share/gst-assets
mkdir -p $BUILD_DIR/usr/share/applications
mkdir -p $BUILD_DIR/usr/share/icons/hicolor/scalable/apps

# 2. คัดลอกไฟล์ control
cp debian/control $BUILD_DIR/DEBIAN/

# 3. คัดลอกสคริปต์หลักและตั้งค่าสิทธิ์การรัน
cp src/geng-settings-tools.py $BUILD_DIR/usr/bin/geng-settings-tools
chmod +x $BUILD_DIR/usr/bin/geng-settings-tools

# 4. คัดลอก Assets (รูปภาพต่างๆ)
cp assets/qrcode.png $BUILD_DIR/usr/share/gst-assets/
mkdir -p $BUILD_DIR/usr/share/icons/hicolor/256x256/apps
cp assets/icon.png $BUILD_DIR/usr/share/icons/hicolor/256x256/apps/geng-settings-tools.png
cp assets/icon.png $BUILD_DIR/usr/share/icons/hicolor/scalable/apps/geng-settings-tools.png

# 5. คัดลอกไฟล์ Desktop
cp packaging/geng-settings-tools.desktop $BUILD_DIR/usr/share/applications/

# 6. Build ไฟล์ .deb
echo "📦 กำลังสร้างไฟล์ .deb..."
dpkg-deb --build $BUILD_DIR "${PKG_NAME}_${VERSION}_all.deb"

# 7. ทำความสะอาด
rm -rf $BUILD_DIR

echo "✅ Build สำเร็จแล้ว! พี่เก่งจะได้ไฟล์ ${PKG_NAME}_${VERSION}_all.deb มาใช้งานนะคะ"
echo "💡 สามารถติดตั้งได้ด้วยคำสั่ง: sudo apt install ./${PKG_NAME}_${VERSION}_all.deb"
