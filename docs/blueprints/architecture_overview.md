بصفتي **كبير مهندسي الأنظمة (Chief System Architect)**، سأقوم بصياغة المخطط الهندسي العام `docs/blueprints/architecture_overview.md`.

هذا الملف هو **"الخريطة الكبرى"**.
قبل أن نغوص في كود "العقل" (`shield/core`)، يجب أن نرى كيف تتصل الأجزاء ببعضها. هذا المستند يشرح كيف يتعاون **Rust** (العضلات) مع **Python** (العقل) عبر **ZMQ** (الأعصاب)، وكيف يحميهم **Bash/Docker** (الدرع).

إليك الوثيقة الكاملة بصيغة Markdown:

### الملف: `docs/blueprints/architecture_overview.md`

```markdown
# ALPHA SOVEREIGN - SYSTEM ARCHITECTURE BLUEPRINT
================================================================================
**Classification:** TOP SECRET // SOVEREIGN EYES ONLY
**Version:** 1.0.0 (Phoenix)
**Date:** 2026-02-03
**Author:** Chief System Architect
================================================================================

## 1. Executive Summary (الرؤية العامة)

نظام **Alpha Sovereign** ليس مجرد بوت تداول، بل هو **"كائن سيبراني هجين" (Hybrid Cyber-Organism)**.
يعتمد التصميم على مبدأ **"فصل المسؤوليات القائم على السرعة" (Latency-Based Separation of Concerns)**:
1.  العمليات التي تتطلب سرعة الضوء (Nanoseconds) تُكتب بـ **Rust**.
2.  العمليات التي تتطلب الذكاء والمرونة (Cognitive) تُكتب بـ **Python**.
3.  البنية التحتية والحماية تُدار بواسطة **Shell/Docker**.

النظام مصمم ليكون **مستقلاً (Sovereign)**، لا يعتمد على خدمات سحابية خارجية، ويمتلك ذاكرته وقراره بنسبة 100%.

---

## 2. The Four Pillars (الأركان الأربعة)



[Image of System Architecture Diagram Layered]


يتكون النظام من أربع طبقات متكاملة تعمل بتناغم تام:

### I. The Muscle (العضلات) - `engine/`
* **اللغة:** Rust (Nightly).
* **المسؤولية:** السرعة الخام، التنفيذ، الاتصال بالبورصة، وإدارة المخاطر اللحظية.
* **المميزات:**
    * **Zero-GC:** لا يوجد جامع قمامة يوقف النظام.
    * **Memory Safety:** أمان الذاكرة مضمون في وقت التجميع.
    * **Concurrency:** استخدام `Tokio` لمعالجة آلاف الإشارات في الثانية.

### II. The Brain (العقل) - `shield/`
* **اللغة:** Python 3.12 (Asyncio).
* **المسؤولية:** التحليل الاستراتيجي، الذكاء الاصطناعي، اتخاذ القرارات المعقدة.
* **المميزات:**
    * **AI Integration:** دمج نماذج LLM (مثل DeepSeek) و Vector DB.
    * **Flexibility:** سهولة تعديل الاستراتيجيات دون إعادة بناء النظام بالكامل.

### III. The Shield (الدرع) - `ops/` & `scripts/`
* **اللغة:** Bash, Docker, Python (Ops).
* **المسؤولية:** المناعة، التعافي الذاتي، الأمن السيبراني، والبنية التحتية.
* **المميزات:**
    * **Self-Healing:** إعادة تشغيل المكونات التالفة تلقائياً.
    * **Encryption:** تشفير البيانات والأسرار (GPG/Kyber).
    * **Isolation:** عزل العمليات داخل حاويات Docker.

### IV. The Cockpit (القمرة) - `ui/`
* **اللغة:** Dart (Flutter).
* **المسؤولية:** المراقبة، التحكم اليدوي، والتصور البياني (Visualization).
* **المميزات:**
    * **Cross-Platform:** يعمل على Web, Desktop, Mobile.
    * **Real-Time:** تحديثات حية عبر gRPC/WebSockets.

---

## 3. The Nervous System (الجهاز العصبي)

كيف تتحدث العضلات مع العقل؟ عبر **ZeroMQ (ZMQ)**.



* **نمط الاتصال:** `PUB/SUB` (للبث العام) و `REQ/REP` (للأوامر المباشرة).
* **لغة التفاهم:** `Protobuf` و `Flatbuffers`.
    * نستخدم **Flatbuffers** للبيانات السريعة جداً (Market Ticks).
    * نستخدم **Protobuf** للرسائل الإدارية والتقارير.
* **السرعة:** زمن الانتقال (Latency) أقل من 20 ميكرو ثانية داخل المضيف المحلي (`localhost`).

---

## 4. Data Flow (تدفق البيانات)

دورة حياة "النبضة" (Tick) داخل النظام:

1.  **Sensation (الإحساس):**
    * `Engine (Rust)` يستقبل السعر من البورصة (WebSocket).
    * يتم تطبيع البيانات (Normalization) وتحويلها لـ Flatbuffer.

2.  **Perception (الإدراك):**
    * يتم إرسال البيانات فوراً إلى `Brain (Python)` عبر ZMQ.
    * يقوم `Brain` بتحديث المؤشرات الفنية والذاكرة المتجهية (Qdrant).

3.  **Decision (القرار):**
    * يقوم وكلاء الذكاء الاصطناعي (`Agents`) بتقييم الفرصة.
    * يتم إصدار أمر (شراء/بيع) إذا تطابقت الشروط.

4.  **Action (الفعل):**
    * يتم إرسال الأمر مرة أخرى إلى `Engine`.
    * يقوم `Engine` بفحص المخاطر (Pre-Trade Risk Check) في نانو ثانية.
    * إذا كان آمناً، يُرسل الأمر للبورصة.

5.  **Memory (الذاكرة):**
    * يتم تخزين الصفقة في `QuestDB` (للتاريخ) و `Redis` (للحالة اللحظية).

---

## 5. Deployment Topology (طوبولوجيا النشر)

النظام مصمم ليعمل في بيئة معزولة (Containerized):

| Container Name | Role | Ports | Storage |
| :--- | :--- | :--- | :--- |
| `alpha_engine` | Execution Core | Internal ZMQ | Ephemeral |
| `alpha_brain` | AI Logic | Internal ZMQ | Models Volume |
| `alpha_redis` | Hot Cache | 6379 | Dump Persistence |
| `alpha_questdb`| Time-Series DB | 9000, 8812 | WAL Journaling |
| `alpha_qdrant` | Vector DB | 6333 | Vector Storage |
| `alpha_ui` | Frontend | 8080 (Web) | N/A |

---

## 6. Security & Sovereignty (السيادة والأمن)

1.  **الهوية:** النظام يمتلك مفاتيح PGP خاصة به (`sovereign_keygen.sh`).
2.  **الأسرار:** لا توجد كلمات مرور في الكود. يتم حقنها كمتغيرات بيئة مشفرة.
3.  **الشبكة:** جميع الاتصالات الخارجية (ما عدا البورصة) محظورة افتراضياً.
4.  **النسخ الاحتياطي:** تشفير كمي (Quantum-Resistant) للبيانات قبل التخزين.

---

> **Forensic Note:** This document serves as the "Constitution" of the system. Any deviation in code implementation from this blueprint must be flagged as a potential anomaly or drift.

```

### التحليل الهندسي للوثيقة:

1. **الوضوح (Explainability):**
* تم استخدام استعارة "الكائن الحي" (عقل، عضلات، درع) لتبسيط الفهم.
* هذا المستند يمكن تقديمه لمستثمر، مدقق مالي، أو مبرمج جديد، وسيفهم الجميع دور كل جزء.


2. **الواقعية (Reality Check):**
* التصميم يعترف بحدود بايثون (البطء) ويعالجها باستخدام Rust للعضلات.
* يعترف بحدود الذاكرة البشرية ويعالجها باستخدام التوثيق التلقائي.


3. **التحضير للمرحلة القادمة:**
* الآن وقد وضعنا الخريطة، أصبح من المنطقي جداً أن نبدأ بـ `shield/core`. نحن نعلم الآن أن دوره هو "التفكير" واستقبال البيانات من ZMQ، وليس الاتصال المباشر بالبورصة.

