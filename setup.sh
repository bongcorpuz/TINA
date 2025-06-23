#!/bin/bash

set -e

# OS Check
echo "🔍 Checking operating system..."
if grep -qi debian /etc/os-release || grep -qi ubuntu /etc/os-release; then
  echo "✅ Debian/Ubuntu system detected. Proceeding with installation."
  echo "🔄 Running apt-get update..."
  sudo apt-get update

  echo "📦 Installing Tesseract OCR, Poppler, LibreOffice with version locking..."
  sudo apt-get install -y \
    tesseract-ocr=4.1.1 \
    poppler-utils \
    libreoffice

elif grep -qi alpine /etc/os-release; then
  echo "🔧 Alpine Linux detected. Installing dependencies..."
  sudo apk update
  sudo apk add tesseract poppler libreoffice

elif grep -qi redhat /etc/os-release || grep -qi centos /etc/os-release || grep -qi fedora /etc/os-release; then
  echo "🔧 RedHat-based system detected. Installing dependencies..."
  sudo yum install -y \
    tesseract \
    poppler-utils \
    libreoffice

else
  echo "❌ Unsupported OS. This script supports Debian, Ubuntu, Alpine, and RedHat-based systems."
  exit 1
fi

# Delete apt.txt if present (redundant)
if [ -f "apt.txt" ]; then
  echo "🧹 Removing redundant apt.txt..."
  rm apt.txt
fi

echo "✔ All system dependencies installed successfully!"
