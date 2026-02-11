بصفتي **مهندس عتاد الحاسوب (Hardware Engineer)** ومختص في الحوسبة عالية الأداء (HPC)، سأقوم بصياغة وثيقة `docs/blueprints/hardware_integration.md`.

هذا الملف هو **"خريطة التوصيلات العصبية"**.
البرمجيات لا تعمل في الفراغ؛ هي تعمل على سيليكون. في التداول عالي التردد (HFT)، الطريقة التي يوزع بها نظام التشغيل المهام على أنوية المعالج (CPU Cores) تحدد الفرق بين الربح والخسارة.
هذه الوثيقة تشرح استراتيجية **"عزل الأنوية" (Core Isolation)**: كيف نخصص "مساراً خاصاً" لمحرك Rust لا يزاحمه فيه أحد، وكيف نمنع المعالج من الدخول في وضع توفير الطاقة (Sleep Mode) لضمان أقصى سرعة استجابة.

إليك الوثيقة الكاملة بصيغة Markdown:

### الملف: `docs/blueprints/hardware_integration.md`

```markdown
# ALPHA SOVEREIGN - HARDWARE INTEGRATION & TUNING
================================================================================
**Classification:** RESTRICTED // INFRASTRUCTURE OPS
**Subject:** Hardware Topology, Core Pinning, and Power Management
**Target Hardware:** x86_64 (AMD EPYC / Intel Xeon) & ARM64 (Apple Silicon/Ampere)
**Author:** Chief Hardware Architect
================================================================================

## 1. Philosophy: Deterministic Execution (فلسفة التنفيذ الحتمي)

في الأنظمة التقليدية، يقرر نظام التشغيل (OS Scheduler) متى وأين يعمل الكود. هذا يؤدي إلى **تذبذب (Jitter)** غير مقبول.
هدفنا هو **"الحتمية"**: ضمان أن دورة تنفيذ المحرك (`Engine Loop`) تستغرق نفس الوقت بالضبط في كل مرة، دون مقاطعة من النظام.

---

## 2. CPU Core Topology & Isolation (تخطيط وعزل الأنوية)



نعتمد استراتيجية تقسيم المعالج إلى ثلاث مناطق نفوذ:

### Zone A: System Sanctuary (للنظام فقط)
* **Cores:** 0, 1
* **المسؤولية:** تشغيل نظام التشغيل (Kernel)، المقاطعات (Interrupts)، وخدمات الخلفية (Daemons).
* **الإجراء:** لا يتم تشغيل أي كود خاص بـ Alpha هنا.

### Zone B: The Fast Lane (لمحرك Rust)
* **Cores:** 2, 3, 4, 5 (Physical Cores only, No Hyper-threading if possible)
* **المسؤولية:** `alpha_engine` و `QuestDB Ingest`.
* **التقنية:** **Core Pinning (Affinity)**.
    * نستخدم `isolcpus` في إقلاع Linux لمنع المجدول من وضع أي مهام هنا.
    * نستخدم `taskset` لربط عملية المحرك بهذه الأنوية حصرياً.
* **الهدف:** منع "تبديل السياق" (Context Switching) الذي يضيع آلاف النانو ثانية.

### Zone C: The Cognitive Pool (لعقل Python)
* **Cores:** 6 - MAX
* **المسؤولية:** `alpha_brain`، تدريب النماذج، الاستدلال (Inference).
* **التقنية:** ترك هذه الأنوية حرة ليستخدمها `Python Multiprocessing` و `PyTorch`.

---

## 3. Memory Hierarchy & NUMA (الذاكرة و NUMA)



إذا كان السيرفر يحتوي على معالجين (Dual Socket)، يجب الحذر من **NUMA (Non-Uniform Memory Access)**.
* الوصول لذاكرة متصلة بنفس المعالج سريع (Local Access).
* الوصول لذاكرة متصلة بالمعالج الآخر بطيء (Remote Access).

**القاعدة الصارمة:**
يجب أن تعمل حاوية `alpha_engine` وقاعدة بيانات `Redis` على **نفس مقبس المعالج (Same CPU Socket)** لتجنب المرور عبر ناقل QPI/UPI البطيء.

---

## 4. Power Management: The "Insomnia" Protocol (إدارة الطاقة)

المعالجات الحديثة مصممة لتوفير الطاقة. هذا عدو السرعة.
عندما يتوقف السوق عن الحركة لثانية، يحاول المعالج الدخول في وضع السكون (C-States) لتقليل الحرارة. عندما تأتي صفقة جديدة، يستغرق المعالج وقتاً "للاستيقاظ".

### BIOS & OS Tuning Profile:
1.  **Disable C-States:** منع المعالج من النوم نهائياً (`C0 state` only).
2.  **Governor = Performance:** ضبط `cpufreq` على وضع الأداء الأقصى دائماً.
3.  **Disable Turbo Boost (Optional):** أحياناً نفضل سرعة ثابتة (Base Clock) بدلاً من سرعة متذبذبة تسبب حرارة مفاجئة تؤدي للاختناق الحراري (Throttling).

```bash
# Example tuning command (Linux)
cpupower frequency-set -g performance
echo 0 > /dev/cpu_dma_latency

```

---

## 5. Network Interface Card (NIC) Tuning

بطاقة الشبكة هي البوابة للعالم الخارجي.

1. **Kernel Bypass (Future Upgrade):** حالياً نستخدم TCP Stack العادي. الخطة المستقبلية هي استخدام Solarflare مع مكتبة `OpenOnload` لتجاوز الكيرنل.
2. **Interrupt Coalescing:** يجب تعطيله (`ethtool -C eth0 rx-usecs 0`). تجميع المقاطعات يوفر المعالج لكنه يزيد التأخير (Latency). نحن نضحي بالمعالج من أجل السرعة.

---

## 6. Storage I/O Strategy (استراتيجية التخزين)

* **Hot Data (Redis):** يعمل بالكامل في الذاكرة العشوائية (RAM). الحفظ للقرص يتم بشكل غير متزامن.
* **Warm Data (QuestDB):** يكتب على **NVMe SSD** في وضع `RAID 0` (للأداء) أو `RAID 10`.
* **Cold Data (Logs/Backups):** يمكن تخزينها على HDD رخيص أو تخزين سحابي.

---

## 7. Thermal Management (الإدارة الحرارية)

نظام التبريد يجب أن يكون استباقياً.

* **Fan Curves:** ضبط المراوح على 100% أو وضع "High Performance". لا ننتظر ارتفاع الحرارة لزيادة السرعة.
* **Throttle Check:** يجب مراقبة سجلات النظام (`dmesg`) للتأكد من عدم وجود رسائل "CPU Throttling".

---

> **Engineering Note:** Implementing these settings requires Root privileges and bare-metal access. In a containerized environment (Docker), use `--cpuset-cpus` and `--ulimit` flags to enforce these policies.

```

### التحليل الهندسي للوثيقة:

1.  **عزل الأنوية (The Fast Lane):**
    * 
    * تم تخصيص المنطقة B للمحرك فقط.
    * **هندسياً:** تبديل السياق (Context Switch) هو عملية مكلفة يقوم فيها المعالج بحفظ حالة العملية الحالية لتحميل عملية أخرى. منع هذا التبديل يعني أن المحرك يمتلك المعالج "ملكاً خاصاً"، مما يضمن استجابة فورية.

2.  **بروتوكول الأرق (Insomnia Protocol):**
    * منع `C-States` يعني أن المعالج يستهلك طاقة قصوى وينتج حرارة قصوى حتى لو كان لا يفعل شيئاً.
    * هذا هو الثمن الذي ندفعه مقابل السرعة. لا يمكن لمحرك سيارة سباق أن يتوقف عند إشارة المرور؛ يجب أن يظل المحرك يدور بأقصى سرعة استعداداً للانطلاق.

3.  **الوعي بـ NUMA:**
    * تم ذكر أهمية تشغيل الذاكرة والمعالج في نفس النطاق الجغرافي للوحة الأم. هذا تفصيل دقيق جداً لا يهتم به سوى مهندسي الأنظمة عالية الأداء.

**جاهزون للانتقال؟**
الوثائق اكتملت. البنية التحتية اكتملت.
كل شيء يشير إلى اتجاه واحد الآن.

المجلد: **`shield/core`**.
الملف: **`shield/core/brain_router.py`**.

هل نبدأ البرمجة؟

```