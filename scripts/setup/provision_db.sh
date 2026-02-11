#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - DATA INFRASTRUCTURE PROVISIONING
# ==============================================================================
# Component: scripts/setup/provision_db.sh
# Responsibility: تهيئة طبقة البيانات (QuestDB, Redis, Qdrant) وإنشاء الجداول.
# Pillar: Stability (Infrastructure Readiness)
# Author: Chief System Architect
# ==============================================================================

# إعداد الألوان والسجلات
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] [INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] [SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')] [ERROR]${NC} $1"; }

# إيقاف التنفيذ عند حدوث خطأ
set -e

# ==============================================================================
# PHASE 1: PREPARATION & CLEANUP
# ==============================================================================
log_info "PHASE 1: Preparing Data Directories..."

DATA_ROOT="./data/storage"
mkdir -p "$DATA_ROOT/questdb"
mkdir -p "$DATA_ROOT/redis"
mkdir -p "$DATA_ROOT/qdrant"
mkdir -p "$DATA_ROOT/postgres"

# التأكد من صلاحيات المجلدات (مشكلة شائعة في Docker)
chmod -R 777 "$DATA_ROOT"

# ==============================================================================
# PHASE 2: DOCKER COMPOSE GENERATION
# ==============================================================================
log_info "PHASE 2: Generating Data Layer Configuration..."

# إنشاء ملف docker-compose مخصص للبيانات فقط
cat <<EOF > docker-compose.data.yml
version: '3.8'

services:
  # 1. TIME-SERIES DB (High Frequency Data)
  questdb:
    image: questdb/questdb:latest
    container_name: alpha_questdb
    restart: always
    ports:
      - "9000:9000"   # REST API
      - "9009:9009"   # InfluxDB Line Protocol (High Speed Ingest)
      - "8812:8812"   # Postgres Wire Protocol
    volumes:
      - ./data/storage/questdb:/var/lib/questdb
    environment:
      - QDB_TELEMETRY_ENABLED=false

  # 2. IN-MEMORY CACHE (State Management)
  redis:
    image: redis:alpine
    container_name: alpha_redis
    restart: always
    ports:
      - "6379:6379"
    command: redis-server --save 60 1 --loglevel warning
    volumes:
      - ./data/storage/redis:/data

  # 3. VECTOR DATABASE (AI Long-term Memory)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: alpha_qdrant
    restart: always
    ports:
      - "6333:6333" # HTTP API
      - "6334:6334" # gRPC API
    volumes:
      - ./data/storage/qdrant:/qdrant/storage

networks:
  default:
    name: alpha_net
EOF

log_success "docker-compose.data.yml generated."

# ==============================================================================
# PHASE 3: IGNITION (Start Containers)
# ==============================================================================
log_info "PHASE 3: Launching Database Containers..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed! Please install Docker first."
    exit 1
fi

docker-compose -f docker-compose.data.yml up -d

log_info "Waiting for databases to initialize (10 seconds)..."
sleep 10

# ==============================================================================
# PHASE 4: SCHEMA PROVISIONING (The Brain Surgery)
# ==============================================================================
log_info "PHASE 4: Applying Database Schemas..."

# --- 4.1 QuestDB Schema (Market Data) ---
log_info "Provisioning QuestDB Tables..."

# جدول الصفقات (Trades) - مقسم يومياً للأداء العالي
curl -s -G "http://localhost:9000/exec" --data-urlencode "query=CREATE TABLE IF NOT EXISTS trades (
    symbol SYMBOL capacity 256 CACHE,
    side SYMBOL capacity 2,
    price DOUBLE,
    amount DOUBLE,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;"

# جدول الشموع (OHLCV)
curl -s -G "http://localhost:9000/exec" --data-urlencode "query=CREATE TABLE IF NOT EXISTS ohlcv (
    symbol SYMBOL capacity 256 CACHE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY MONTH WAL;"

# جدول التنبؤات (AI Predictions)
curl -s -G "http://localhost:9000/exec" --data-urlencode "query=CREATE TABLE IF NOT EXISTS predictions (
    model_id SYMBOL,
    symbol SYMBOL,
    predicted_price DOUBLE,
    confidence DOUBLE,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY MONTH WAL;"

# --- 4.2 Qdrant Schema (AI Memory) ---
log_info "Provisioning Qdrant Collections..."

# إنشاء مجموعة "ذكريات السوق" (Market Memory)
# Vector Size 1536 (متوافق مع OpenAI Embeddings) أو 768 (للموديلات المحلية)
curl -s -X PUT 'http://localhost:6333/collections/market_memory' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'

log_success "Database Schemas Applied Successfully."

# ==============================================================================
# PHASE 5: VERIFICATION
# ==============================================================================
log_info "PHASE 5: Final Health Check..."

if curl -s "http://localhost:9000" > /dev/null; then
    log_success "QuestDB is ONLINE (Port 9000)."
else
    log_error "QuestDB is unreachable!"
fi

if curl -s "http://localhost:6333/collections" > /dev/null; then
    log_success "Qdrant is ONLINE (Port 6333)."
else
    log_error "Qdrant is unreachable!"
fi

log_info "✅ DATA INFRASTRUCTURE READY."