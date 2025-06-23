#!/bin/bash

set -e

echo "🔍 Detecting operating system..."
if grep -qi debian /etc/os-release || grep -qi ubuntu /etc/os-release; then
  echo "✅ Debian/Ubuntu detected. Installing dependencies..."
  sudo apt-get update
  sudo apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libreoffice \
    python3 \
    python3-pip \
    build-essential \
    libgl1

elif grep -qi alpine /etc/os-release; then
  echo "✅ Alpine Linux detected. Installing dependencies..."
  sudo apk update
  sudo apk add \
    tesseract \
    poppler \
    libreoffice \
    python3 \
    py3-pip \
    build-base \
    ttf-freefont

elif grep -qi redhat /etc/os-release || grep -qi centos /etc/os-release || grep -qi fedora /etc/os-release; then
  echo "✅ RedHat-based system detected. Installing dependencies..."
  sudo yum install -y \
    tesseract \
    poppler-utils \
    libreoffice \
    python3 \
    python3-pip \
    gcc \
    gcc-c++ \
    make

else
  echo "❌ Unsupported OS. Only Debian, Ubuntu, Alpine, and RedHat-based systems are supported."
  exit 1
fi

echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "🧹 Cleaning up old apt.txt (if exists)..."
[ -f "apt.txt" ] && rm apt.txt

echo "✅ Setup complete. Environment is ready!"