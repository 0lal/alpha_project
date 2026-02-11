# INCIDENT REPORT: INC-001 Unexpected Latency Spike

| Field | Detail |
| :--- | :--- |
| **Date** | 2026-02-01 |
| **Severity** | SEV-2 (Major) |
| **Status** | RESOLVED |
| **Impact** | High execution latency (500ms instead of 5ms), 3 missed trades. |
| **Owner** | Chief System Architect |

---

## 1. Executive Summary
في تمام الساعة 14:00 بتوقيت السيرفر، رصد نظام المراقبة ارتفاعاً مفاجئاً في زمن الاستجابة (Latency) داخل `alpha_engine`. أدى هذا التأخير إلى رفض البورصة لثلاثة أوامر تداول بسبب انتهاء صلاحية الـ TTL (Time-To-Live).

## 2. Impact Assessment
* **Financial Loss:** ~$150 (Opportunity Cost - missed profit).
* **Data Loss:** None.
* **Downtime:** System remained online but degraded for 45 seconds.

## 3. Timeline
* **14:00:05** `benchmark_all.sh` (Running in background) flagged CPU spike.
* **14:00:07** `alpha_engine` reported `WARN: Order processing took 450ms`.
* **14:00:10** 3 Orders rejected by Exchange (Reason: `Timestamp too old`).
* **14:00:15** `HealthRecoveryNode` detected CPU starvation on Core 2.
* **14:00:45** Latency returned to normal (5ms).

## 4. Root Cause Analysis
* **Direct Cause:** CPU Core 2 (assigned to Engine) reached 100% usage.
* **Root Cause:** A heavy `docker image prune` operation was triggered manually by an admin on the host machine without using `nice` levels, causing resource contention.
* **Trigger:** Admin ran maintenance script during trading hours.

## 5. Resolution & Recovery
* **Immediate Fix:** The maintenance process finished naturally.
* **Permanent Fix:**
    1. Update `hardware_integration.md` to strictly enforce `isolcpus` (Kernel Isolation) so host processes CANNOT use Core 2.
    2. Update `data_purger.sh` to prevent running during market hours (Add time check).

## 6. Lessons Learned
* **Good:** The `TTL` mechanism successfully prevented executing "stale" orders, saving us from buying at the wrong price.
* **Bad:** Core isolation was configured in software (Docker CPUSet) but not at the Kernel level (Grub), allowing leaks.
* **Action Item:** Apply `isolcpus=2,3` to `/etc/default/grub`.

---
**Tags:** #cpu #latency #ops #human_error