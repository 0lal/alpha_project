#!/bin/bash
# =================================================================
# ALPHA SOVEREIGN - PANIC PROTOCOL: SECURE WIPE
# =================================================================
# Component: shield/panic/wipe_secrets.sh
# Core Responsibility: المسح الجنائي للمفاتيح والأسرار (Irreversible Data Destruction).
# usage: sudo ./wipe_secrets.sh
# =================================================================

# التأكد من التشغيل بصلاحيات Root لضمان الوصول للذاكرة والملفات المحمية
if [ "$EUID" -ne 0 ]; then
  echo "PANIC_ERR: This protocol requires ROOT privileges."
  exit 1
fi

echo "[!!!] INITIATING PANIC PROTOCOL - SECURE WIPE SEQUENCE STARTED [!!!]"
echo "[!!!] TIMESTAMP: $(date -u)"

# =================================================================
# 1. إيقاف النزيف (Stop Processes)
# =================================================================
echo "[1/6] Killing all Alpha processes..."

# إيقاف جميع حاويات Docker فوراً (SIGKILL)
if command -v docker &> /dev/null; then
    docker kill $(docker ps -q --filter "name=alpha") 2>/dev/null
    docker rm -f $(docker ps -aq --filter "name=alpha") 2>/dev/null
    echo "      > Containers terminated."
else
    echo "      > Docker not found, skipping."
fi

# قتل أي عمليات محلية (Python/Rust)
pkill -9 -f "alpha_core" 2>/dev/null
pkill -9 -f "python3.*shield" 2>/dev/null
echo "      > Processes terminated."

# =================================================================
# 2. تدمير المفاتيح (Shredding Keys)
# =================================================================
echo "[2/6] Shredding cryptographic material..."

# دالة للمسح الآمن
secure_wipe() {
    local target="$1"
    if [ -e "$target" ]; then
        # -u: remove after overwriting
        # -z: add a final overwrite with zeros to hide shredding
        # -n 7: overwrite 7 times (NIST standard is usually 3, we do 7 for paranoia)
        find "$target" -type f -exec shred -v -u -z -n 7 {} \; 2>/dev/null
        rm -rf "$target"
        echo "      > WIPED: $target"
    fi
}

# مسح المجلدات الحساسة
secure_wipe "./shield/crypto"
secure_wipe "./config"
secure_wipe "./logs/forensics" # نمسح تقارير الحوادث لأنها قد تحتوي على لقطات ذاكرة
secure_wipe "dms_state.json"

# =================================================================
# 3. تنظيف الذاكرة المشتركة (Shared Memory Wipe)
# =================================================================
echo "[3/6] Cleaning Shared Memory (/dev/shm)..."
# المحرك يستخدم الذاكرة المشتركة للسرعة، يجب مسحها
rm -rf /dev/shm/alpha_*
rm -rf /dev/shm/sem.alpha_*

# =================================================================
# 4. تنظيف الذاكرة العشوائية والتبادل (RAM & Swap Flush)
# =================================================================
echo "[4/6] Flushing RAM and Swap..."

# تفريغ الكاش من الرام
echo 3 > /proc/sys/vm/drop_caches

# إيقاف وتشغيل Swap لمسح أي بيانات تم ترحيلها للقرص
if [ -f /proc/swaps ]; then
    swapoff -a
    # لا نعيد تشغيله لزيادة الأمان، أو نعيده فارغاً
    # swapon -a 
    echo "      > Swap flushed and disabled."
fi

# =================================================================
# 5. تنظيف آثار الشبكة والدخول (Network & Auth Logs)
# =================================================================
echo "[5/6] Clearing history..."
history -c
cat /dev/null > ~/.bash_history

# =================================================================
# 6. التدمير الذاتي للسكريبت (Suicide)
# =================================================================
echo "[6/6] Self-destructing script..."
# السكريبت يمسح نفسه في النهاية لمنع تحليل الكود ومعرفة ماذا تم حذفه
shred -u -z -n 7 "$0"

# (لن يتم تنفيذ أي شيء بعد هذا السطر لأن الملف لم يعد موجوداً)
echo "[!!!] PANIC PROTOCOL COMPLETE. SYSTEM IS CLEAN."