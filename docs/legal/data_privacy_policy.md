# ALPHA SOVEREIGN - DATA PRIVACY & SOVEREIGNTY POLICY
================================================================================
**Classification:** RESTRICTED // OWNER EYES ONLY
**Effective Date:** 2026-02-03
**Scope:** All Data At Rest, In Transit, and In Processing
**Author:** Chief Data Protection Officer
================================================================================

## 1. The Sovereign Guarantee (عهد السيادة)

**Principle:** "Your Data, Your Hardware, Your Rules."
Alpha Sovereign is architected as a **Local-First, Self-Custodial System**.
* **No Telemetry:** The system contains zero code to send usage statistics, crash reports, or trading data to any central server or third-party analytics provider (e.g., Google Analytics, Firebase).
* **No Cloud Dependency:** The system functions 100% offline (except for exchange connectivity). It does not require AWS, Azure, or GCP to operate.

---

## 2. Data Classification & Encryption Standards (التصنيف والتشفير)

Data is categorized into three security levels, each with specific handling rules enforced by `vault_encrypt.sh`:

| Level | Data Type | Encryption Standard | Storage Medium |
| :--- | :--- | :--- | :--- |
| **L1: Public** | Market Prices, Order Book | None (Transient) | RAM / QuestDB |
| **L2: Private** | Trade History, Strategy Logs | AES-256 (At Rest) | Encrypted Volume |
| **L3: Critical** | API Keys, Seeds, Wallets | Kyber-1024 + GPG | Memory-Only (Tmpfs) |

**Engineering Impact:**
* **L3 Data** is never written to the hard disk in plain text. It exists only in RAM (`/dev/shm`) and is securely shredded upon shutdown (`alpha_shutdown.sh`).

---

## 3. Network Isolation (Air Gap Strategy)

To prevent data leakage, the system uses strict Docker Network policies defined in `docker-compose.yml`:

* **The Engine (`alpha_engine`):** The ONLY component allowed to access the public internet (specifically, whitelisted Exchange IPs).
* **The Brain (`alpha_brain`):** Completely **isolated**. It has NO internet access. It receives sanitized market data from the Engine via ZMQ. This prevents AI models from accidentally leaking strategies or keys.
* **The Database (`alpha_db`):** Internal access only. No ports are exposed to the host machine's public interface.

---

## 4. AI & Model Privacy (خصوصية الذكاء الاصطناعي)

With the integration of LLMs (Large Language Models), privacy is paramount:

### A. Local Models (Preferred)
* When using local models (e.g., DeepSeek via Ollama), all inference happens on your GPU. No data leaves the machine.

### B. External APIs (If enabled)
* If the user explicitly enables OpenAI/Anthropic APIs, the `Brain` implements a **"PII Scrubber"**:
    * Before sending a prompt, all numbers resembling API Keys, IP addresses, or financial totals are redacted or tokenized.
    * **Rule:** Never send raw strategy logic or full ledger history to an external LLM.

---

## 5. Third-Party Sharing (مشاركة الطرف الثالث)

The system shares data strictly with:
1.  **The Exchange:** Minimal data required to execute an order (Symbol, Price, Quantity).
2.  **The User:** Via the encrypted UI/Dashboard.

**Zero-Knowledge Proof:**
Even the developers of Alpha Sovereign cannot access your system. There are no "Backdoors" or "Master Keys." If you lose your `sovereign_keygen.sh` keys, your data is lost forever. We cannot recover it for you.

---

## 6. Data Retention & Destruction (الاحتفاظ والحذف)

* **Retention:** Operational logs are kept for 7 days (`data_purger.sh`), then rotated or deleted.
* **Destruction:** When deleting sensitive files, the system uses the `shred` command (overwrite 3 times) rather than standard deletion, to prevent forensic recovery.

---

## 7. Incident Response (الاستجابة للحوادث)

In the event of a detected breach (e.g., `DriftDetector` alert):
1.  **Lockdown:** The system immediately terminates all external connections (`Network Cut`).
2.  **Wipe:** Temporary keys in RAM are flushed.
3.  **Alert:** A generic notification is sent to the user (without sensitive details).

---

> **Legal Disclaimer:** By operating this software, you assume full responsibility for the security of your hardware. Physical access to the machine equates to root access. Encrypt your hard drive (LUKS/BitLocker) to complete the security chain.