#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - FULL STACK LATENCY BENCHMARK
# ==============================================================================
# Component: scripts/testing/benchmark_all.sh
# Responsibility: قياس زمن التأخير (Latency) في كافة طبقات النظام (Disk, Net, DB, Logic).
# Pillar: Performance (Microsecond Precision Analysis)
# Author: Chief Performance Engineer
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[BENCH]${NC} $1"; }
log_res()  { echo -e "${GREEN}[RESULT]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC}  $1"; }

TEMP_FILE="./benchmark_temp.dat"

echo "============================================================"
echo "ALPHA SOVEREIGN - SYSTEM LATENCY REPORT"
echo "Date: $(date)"
echo "CPU: $(lscpu | grep 'Model name' | awk -F: '{print $2}' | xargs)"
echo "============================================================"

# ==============================================================================
# PHASE 1: DISK I/O LATENCY (WAL Performance)
# ==============================================================================
# لماذا هذا مهم؟ قواعد البيانات تكتب في (Write Ahead Log) قبل الذاكرة.
# إذا كان القرص بطيئاً، ستتوقف قاعدة البيانات عن قبول صفقات جديدة.
log_info "Phase 1: Measuring Disk Sync Latency (WAL Simulation)..."

# نكتب 1000 كتلة صغيرة (4KB) مع إجبار المزامنة (fdatasync) لمحاكاة كتابة الصفقات
# conv=fdatasync: يجبر النظام على الكتابة الفيزيائية للقرص (تجاوز الكاش)
dd if=/dev/zero of=$TEMP_FILE bs=4k count=1000 conv=fdatasync 2>&1 | tail -n 1 | awk '{print "Write Speed: " $10 " " $11}' > disk_result.txt

DISK_RES=$(cat disk_result.txt)
log_res "Disk I/O: $DISK_RES"

# تنظيف
rm $TEMP_FILE disk_result.txt

# ==============================================================================
# PHASE 2: NETWORK LOOPBACK LATENCY (IPC Speed)
# ==============================================================================
# لماذا هذا مهم؟ الاتصال بين Rust Engine و Python Brain يتم عبر الشبكة المحلية.
log_info "Phase 2: Measuring Localhost Network Jitter..."

# نستخدم بايثون لقياس رحلة الذهاب والإياب (Round Trip Time) بدقة الميكرو ثانية
python3 -c "
import time, socket, threading

def server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 9999))
    s.listen(1)
    conn, _ = s.accept()
    while True:
        data = conn.recv(1024)
        if not data: break
        conn.send(data) # Echo back
    conn.close()

t = threading.Thread(target=server, daemon=True)
t.start()
time.sleep(0.5)

# Client Benchmark
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 9999))

latencies = []
for _ in range(1000):
    start = time.perf_counter()
    sock.send(b'x')
    sock.recv(1)
    end = time.perf_counter()
    latencies.append((end - start) * 1_000_000) # Convert to microseconds

avg = sum(latencies) / len(latencies)
print(f'Average RTT: {avg:.2f} µs')
print(f'Max Jitter:  {max(latencies):.2f} µs')
sock.close()
" > net_bench_output.txt

cat net_bench_output.txt | while read line; do log_res "$line"; done
rm net_bench_output.txt

# ==============================================================================
# PHASE 3: DATABASE INGESTION SPEED (QuestDB)
# ==============================================================================
log_info "Phase 3: Benchmarking QuestDB Ingestion..."

if curl -s "http://localhost:9000" > /dev/null; then
    # قياس وقت إدخال صفقة واحدة عبر HTTP
    # %{time_total}: يعطي الوقت الإجمالي بالثواني
    
    QDB_LATENCY=$(curl -w "%{time_total}\n" -o /dev/null -s -G "http://localhost:9000/exec" --data-urlencode "query=SELECT 1;")
    
    # تحويل من ثواني إلى مللي ثانية
    QDB_MS=$(echo "$QDB_LATENCY * 1000" | bc)
    log_res "QuestDB Query Latency: ${QDB_MS} ms"
else
    log_err "QuestDB not running. Skipping."
fi

# ==============================================================================
# PHASE 4: SERIALIZATION COST (Python vs Binary)
# ==============================================================================
# لماذا هذا مهم؟ تحليل JSON هو أكبر مبدد للوقت في بايثون.
# هذا الاختبار يثبت لماذا يجب استخدام Protobuf/Flatbuffers.
log_info "Phase 4: Serialization Cost Analysis (JSON vs Struct)..."

python3 -c "
import json, struct, timeit

data_dict = {'symbol': 'BTCUSDT', 'price': 50000.12, 'qty': 1.5, 'side': 'BUY'}
# محاكاة بنية C++ (4 chars, double, double, 4 chars)
data_struct = struct.pack('4sd d 4s', b'BTCU', 50000.12, 1.5, b'BUY ')

# 1. JSON Benchmark
t_json = timeit.timeit(lambda: json.loads(json.dumps(data_dict)), number=10000)

# 2. Binary Struct Benchmark
t_struct = timeit.timeit(lambda: struct.unpack('4sd d 4s', data_struct), number=10000)

print(f'JSON (10k ops):   {t_json:.4f} s')
print(f'Binary (10k ops): {t_struct:.4f} s')
print(f'Speedup Factor:   {t_json / t_struct:.1f}x FASTER')
" > serial_bench.txt

cat serial_bench.txt | while read line; do log_res "$line"; done
rm serial_bench.txt

# ==============================================================================
# SUMMARY
# ==============================================================================
echo "============================================================"
echo "BENCHMARK COMPLETE"
echo "If Network RTT > 50µs -> Check Loopback optimization."
echo "If Disk Write < 200 MB/s -> Upgrade to NVMe SSD."
echo "If JSON Speedup < 10x -> Re-check Python version."
echo "============================================================"