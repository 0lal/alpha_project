# ==============================================================================
# ALPHA SOVEREIGN - MASTER COMMAND CENTER
# ==============================================================================
# This Makefile abstracts complex shell scripts into simple commands.
# Usage: make [command]
# ==============================================================================

# الألوان لتحسين القراءة في الطرفية
YELLOW := \033[1;33m
GREEN := \033[1;32m
RED := \033[1;31m
NC := \033[0m # No Color

.PHONY: help setup build up down restart test logs clean shell-brain shell-engine

# ==============================================================================
# 1. MAIN COMMANDS (الأوامر الرئيسية)
# ==============================================================================

## help: عرض قائمة الأوامر المتاحة
help:
	@echo "${YELLOW}Alpha Sovereign - Command Menu:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}'

## setup: تثبيت الأدوات والمكتبات وتهيئة البيئة (مرة واحدة)
setup:
	@echo "${YELLOW}[MAKE] Setting up environment...${NC}"
	@bash ./scripts/setup/install_toolchains.sh
	@bash ./scripts/setup/generate_env_keys.sh
	@bash ./scripts/setup/provision_databases.sh

## build: تجميع كود Rust وبناء حاويات Docker
build:
	@echo "${YELLOW}[MAKE] Building System Artifacts...${NC}"
	@bash ./scripts/development/compile_all.sh
	@docker-compose build

## up: تشغيل النظام بالكامل في وضع الخلفية
up:
	@echo "${YELLOW}[MAKE] Launching Alpha Sovereign...${NC}"
	@docker-compose up -d
	@echo "${GREEN}[DONE] System is running. Check 'make logs' for status.${NC}"

## down: إيقاف آمن للنظام (تسييل + حفظ الذاكرة)
down:
	@echo "${RED}[MAKE] Initiating Secure Shutdown...${NC}"
	@bash ./scripts/lifecycle/alpha_shutdown.sh

## restart: إعادة تشغيل آمنة ومتسلسلة
restart:
	@echo "${YELLOW}[MAKE] Rebooting...${NC}"
	@bash ./scripts/lifecycle/alpha_reboot.sh

# ==============================================================================
# 2. TESTING & QUALITY (الاختبار والجودة)
# ==============================================================================

## test: تشغيل كافة اختبارات الوحدة (Unit Tests)
test:
	@echo "${YELLOW}[MAKE] Running Test Suite...${NC}"
	@cd engine && cargo test
	@cd shield && pytest

## stress: تشغيل اختبارات التحمل (Stress Test)
stress:
	@echo "${RED}[MAKE] WARNING: STARTING STRESS TEST${NC}"
	@bash ./scripts/testing/stress_test_system.sh

## audit: فحص أمني للمكتبات
audit:
	@bash ./scripts/development/dependency_audit.sh

# ==============================================================================
# 3. MAINTENANCE (الصيانة)
# ==============================================================================

## logs: مراقبة السجلات الحية لكافة الخدمات
logs:
	@docker-compose logs -f --tail=100

## clean: تنظيف الملفات المؤقتة والبيانات القديمة
clean:
	@echo "${YELLOW}[MAKE] Cleaning up...${NC}"
	@bash ./scripts/maintenance/data_purger.sh
	@cargo clean --manifest-path engine/Cargo.toml
	@rm -rf shield/__pycache__

## backup: إنشاء نسخة احتياطية مشفرة فوراً
backup:
	@bash ./scripts/maintenance/backup_sovereign.sh

# ==============================================================================
# 4. DEBUGGING (التصحيح)
# ==============================================================================

## shell-brain: الدخول إلى حاوية العقل (SSH)
shell-brain:
	@docker-compose exec brain /bin/bash

## shell-engine: الدخول إلى حاوية المحرك
shell-engine:
	@docker-compose exec engine /bin/bash