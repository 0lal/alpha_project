#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - TOOLCHAIN PROVISIONING SCRIPT
# ==============================================================================
# Component: scripts/setup/install_toolchains.sh
# Responsibility: تجهيز بيئة التطوير والتشغيل بأدوات موحدة (Rust, Python, Flutter).
# Pillar: Stability (Environment Consistency)
# Author: Chief System Architect
# ==============================================================================

# إعداد الألوان للمخرجات
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# دالة للطباعة الجنائية (مع الوقت)
log_info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] [INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] [WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] [ERROR]${NC} $1"
}

# التأكد من تشغيل السكريبت بصلاحيات كافية (لكن ليس كـ root للملفات الشخصية)
if [ "$EUID" -eq 0 ]; then
  log_warn "Running as root. Be careful not to mess up user permissions for Flutter/Rust."
fi

# ==============================================================================
# PHASE 1: SYSTEM DEPENDENCIES (The Foundation)
# ==============================================================================
log_info "PHASE 1: Installing System Dependencies (Ubuntu/Debian)..."

# تحديث القوائم
sudo apt-get update -y

# تنصيب الأساسيات الضرورية للبناء
# curl/git: للجلب
# build-essential: لمترجمات C++ (ضرورية لربط Rust مع Python)
# libclang-dev: ضروري لمكتبة flutter_rust_bridge لتوليد الأكواد
# libgtk-3-dev: ضروري لتشغيل Flutter على Linux
DEPENDENCIES=(
    "curl" "git" "wget" "unzip" "xz-utils" "zip" "libglu1-mesa"
    "build-essential" "cmake" "pkg-config" "libssl-dev"
    "libclang-dev" "libgtk-3-dev" "ninja-build"
)

for dep in "${DEPENDENCIES[@]}"; do
    if dpkg -l | grep -q "^ii  $dep "; then
        log_info "$dep is already installed."
    else
        log_info "Installing $dep..."
        sudo apt-get install -y "$dep"
    fi
done

# ==============================================================================
# PHASE 2: RUST TOOLCHAIN (The Muscle)
# ==============================================================================
log_info "PHASE 2: Installing Rust Toolchain (Nightly)..."

if ! command -v rustc &> /dev/null; then
    log_info "Rust not found. Installing via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    log_info "Rust is already installed."
fi

# التبديل إلى النسخة Nightly (ضروري للأداء العالي جداً في HFT)
log_info "Switching to Rust Nightly channel..."
rustup toolchain install nightly
rustup default nightly

# إضافة أهداف التجميع (Targets)
# للموبايل (Android) ولينكس
rustup target add aarch64-linux-android
rustup target add x86_64-unknown-linux-gnu

# تنصيب أدوات الربط مع Flutter
if ! command -v flutter_rust_bridge_codegen &> /dev/null; then
    log_info "Installing flutter_rust_bridge_codegen..."
    cargo install flutter_rust_bridge_codegen
fi

# ==============================================================================
# PHASE 3: PYTHON TOOLCHAIN (The Brain)
# ==============================================================================
log_info "PHASE 3: Installing Python 3.12+ Toolchain..."

# إضافة PPA للحصول على أحدث نسخ بايثون إذا لم تكن موجودة
if ! command -v python3.12 &> /dev/null; then
    log_info "Python 3.12 not found. Adding deadsnakes PPA..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update -y
    sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
else
    log_info "Python 3.12 is already available."
fi

# التأكد من وجود pip
if ! command -v pip3 &> /dev/null; then
    sudo apt-get install -y python3-pip
fi

# ==============================================================================
# PHASE 4: FLUTTER SDK (The Senses)
# ==============================================================================
log_info "PHASE 4: Installing Flutter SDK..."

FLUTTER_ROOT="$HOME/development/flutter"

if [ ! -d "$FLUTTER_ROOT" ]; then
    log_info "Flutter SDK not found. Downloading stable release..."
    mkdir -p "$HOME/development"
    cd "$HOME/development"
    
    # تنزيل النسخة المستقرة
    git clone https://github.com/flutter/flutter.git -b stable
    
    # إضافة Flutter للمسار (PATH) في ملفات التكوين
    SHELL_CONFIG="$HOME/.bashrc"
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_CONFIG="$HOME/.zshrc"
    fi
    
    if ! grep -q "flutter/bin" "$SHELL_CONFIG"; then
        echo "export PATH=\"\$PATH:$FLUTTER_ROOT/bin\"" >> "$SHELL_CONFIG"
        log_info "Added Flutter to PATH in $SHELL_CONFIG"
        export PATH="$PATH:$FLUTTER_ROOT/bin"
    fi
else
    log_info "Flutter SDK already exists at $FLUTTER_ROOT"
fi

# تشخيص حالة Flutter
log_info "Running Flutter Doctor..."
$FLUTTER_ROOT/bin/flutter doctor

# ==============================================================================
# PHASE 5: VERIFICATION
# ==============================================================================
log_info "PHASE 5: Final Verification..."

echo "---------------------------------------------------"
echo -e "${GREEN}SYSTEM TOOLCHAIN REPORT:${NC}"
echo "Rust Version:   $(rustc --version)"
echo "Cargo Version:  $(cargo --version)"
echo "Python Version: $(python3.12 --version)"
echo "Flutter Version: $($FLUTTER_ROOT/bin/flutter --version | head -n 1)"
echo "---------------------------------------------------"

log_info "✅ SETUP COMPLETE. PLEASE RESTART YOUR TERMINAL."