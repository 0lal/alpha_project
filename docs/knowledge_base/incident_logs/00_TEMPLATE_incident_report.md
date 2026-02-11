# INCIDENT REPORT: [INC-XXXX] [Short Title]

| Field | Detail |
| :--- | :--- |
| **Date** | YYYY-MM-DD |
| **Severity** | SEV-1 (Critical) / SEV-2 (Major) / SEV-3 (Minor) |
| **Status** | OPEN / INVESTIGATING / RESOLVED / ARCHIVED |
| **Impact** | [High Level Impact, e.g., $500 Loss, 10 min Downtime] |
| **Owner** | [Name/Role] |

---

## 1. Executive Summary (ملخص تنفيذي)
*شرح مختصر للمشكلة بلغة بسيطة. ماذا حدث؟ ومن تأثر؟*
> Example: The Engine stopped executing buy orders for 5 minutes due to a Redis connection timeout.

## 2. Impact Assessment (تقدير الأضرار)
* **Financial Loss:** $0.00
* **Data Loss:** [e.g., 500 Ticks missed]
* **Downtime:** [Duration]
* **Reputation:** [Internal/External]

## 3. Timeline (الجدول الزمني - الدقيقة بالدقيقة)
* **[HH:MM:SS]** Incident started (Alert triggered).
* **[HH:MM:SS]** System detected anomaly via `DriftDetector`.
* **[HH:MM:SS]** `HealthRecoveryNode` attempted auto-restart.
* **[HH:MM:SS]** Manual intervention initiated.
* **[HH:MM:SS]** Service restored.

## 4. Root Cause Analysis (تحليل السبب الجذري - The 5 Whys)
* **Direct Cause:** [What technically failed?]
* **Root Cause:** [Why did it fail? e.g., Configuration drift, Memory leak, Logic bug]
* **Trigger:** [What specific event triggered the failure?]

## 5. Resolution & Recovery (الحل والتعافي)
* **Immediate Fix:** [What was done to stop the bleeding?]
* **Permanent Fix:** [What code/config changes are needed to prevent recurrence?]

## 6. Lessons Learned (الدروس المستفادة)
* [What went well?]
* [What went wrong?]
* [Action Items]

---
**Tags:** #database #redis #timeout #sev1