بصفتي **مهندس برمجيات النظم الموزعة (Distributed Systems Engineer)**، سأقوم بصياغة وثيقة `docs/blueprints/ipc_communication_flow.md`.

هذا الملف هو **"خريطة الأعصاب"**.
في الأنظمة الموزعة، الفوضى هي الأصل. إذا لم نحدد بدقة من يتحدث مع من، وبأي لغة، وكيف نحل الخلاف، سينتهي بنا المطاف بـ "Deadlocks" (تجمد النظام) أو "Race Conditions" (تضارب البيانات).
هذه الوثيقة تشرح بروتوكول **ZMQ** وكيفية تدفق البيانات بين (Rust) و (Python) بسرعة الصوت.

إليك الوثيقة الكاملة بصيغة Markdown:

### الملف: `docs/blueprints/ipc_communication_flow.md`

```markdown
# ALPHA SOVEREIGN - IPC COMMUNICATION PROTOCOLS
================================================================================
**Classification:** TOP SECRET // ENGINEERING DEPT
**Component:** Inter-Process Communication (IPC)
**Protocol:** ZMQ (ZeroMQ) over TCP/IPC
**Author:** Chief System Architect
================================================================================

## 1. Introduction (المقدمة)

يعتمد نظام Alpha Sovereign على معمارية **"الأطراف غير المتزامنة" (Asynchronous Actors)**.
- **Engine (Rust):** هو المنتج (Producer) للبيانات والمنفذ للأوامر.
- **Brain (Python):** هو المستهلك (Consumer) للبيانات وصانع القرار.
- **UI (Dart):** هو المراقب (Observer).

يتم الربط بينهم باستخدام **ZeroMQ**، وهو مكتبة شبكات عالية الأداء تعمل بدون وسيط (Brokerless)، مما يقلل زمن الانتقال إلى الحد الأدنى (Microseconds).

---

## 2. Topology & Ports (الطوبولوجيا والمنافذ)



النظام يستخدم المنافذ التالية (داخل شبكة Docker الداخلية `alpha_net`):

| Port | Pattern | Role | Direction | Data Type |
| :--- | :--- | :--- | :--- | :--- |
| **5555** | `PUB/SUB` | **Market Data Stream** | Engine -> Brain/UI | `Flatbuffers` (Ticks) |
| **5556** | `REQ/REP` | **Execution Command** | Brain -> Engine | `Protobuf` (Orders) |
| **5557** | `PUSH/PULL`| **Telemetry Pipeline** | All -> Ops | `JSON` (Logs/Metrics) |
| **5558** | `PUB/SUB` | **System Events** | Ops -> All | `Protobuf` (Signals) |

---

## 3. Data Flow Pathways (مسارات تدفق البيانات)

### A. The Hot Path: Tick-to-Trade (مسار البيانات السريع)
هذا المسار هو الأهم، حيث كل نانو ثانية لها ثمن.

1.  **Ingestion:** المحرك (Rust) يستقبل `WebSocket Packet` من البورصة.
2.  **Normalization:** يتم تحويل البيانات فوراً إلى هيكل `MarketTick` باستخدام **Flatbuffers**.
    * *لماذا Flatbuffers؟* لأنها تسمح بقراءة البيانات دون فك تشفيرها (Zero-Copy Serialization)، مما يوفر وقتاً هائلاً للبايثون.
3.  **Broadcast (ZMQ PUB):** المحرك يبث البيانات على المنفذ `5555`.
4.  **Reaction:** العقل (Python) المشترك في هذا المنفذ يستيقظ، يقرأ السعر، ويحدث الذاكرة.

### B. The Critical Path: Order Execution (مسار الأوامر)
هذا المسار يتطلب الموثوقية (Reliability) أكثر من السرعة المطلقة.

1.  **Decision:** العقل يقرر الشراء. ينشئ رسالة `OrderRequest` باستخدام **Protobuf**.
2.  **Request (ZMQ REQ):** العقل يرسل الطلب للمحرك على المنفذ `5556` وينتظر الرد (Blocking Call) أو يستخدم `Asyncio Future`.
3.  **Risk Check:** المحرك يستلم الطلب. **قبل التنفيذ**، يمرره عبر "فلاتر المخاطر" (Risk Filters).
4.  **Execution:** إذا اجتاز الفحص، يرسله للبورصة.
5.  **Reply (ZMQ REP):** المحرك يرسل `OrderAck` (تم القبول) أو `OrderReject` (تم الرفض مع السبب) للعقل.

---

## 4. Conflict Resolution (حل النزاعات)

ماذا يحدث عندما تختلف المكونات؟ من له الكلمة العليا؟

### Scenario 1: The Greedy Brain (العقل الطماع)
* **الموقف:** العقل يحاول إرسال أمر شراء بـ 100% من المحفظة، لكن المحرك مضبوط على مخاطرة قصوى 10% للصفقة.
* **البروتوكول:**
    1.  المحرك يملك "حق النقض" (Veto Power).
    2.  يتم رفض الطلب فوراً داخل المحرك (دون إرساله للبورصة).
    3.  يتم إرجاع رسالة خطأ `RISK_VIOLATION` للعقل.
    4.  العقل يجب أن يعيد حساباته (أو يتم معاقبته بخفض صلاحياته).

### Scenario 2: The Stale Data (البيانات القديمة)
* **الموقف:** الشبكة بطيئة، والعقل اتخذ قراراً بناءً على سعر وصل قبل 500 مللي ثانية.
* **البروتوكول:**
    1.  كل رسالة `Tick` و `Order` تحتوي على طابع زمن دقيق (`timestamp_ns`).
    2.  عندما يستلم المحرك الأمر، يقارن وقته بوقت السعر الحالي.
    3.  إذا كان الفارق (TTL) أكبر من المسموح (مثلاً 100ms)، يتم رفض الأمر (`TTL_EXPIRED`).

---

## 5. Serialization Strategy (استراتيجية السريلة)

نحن نستخدم لغات مختلفة لأغراض مختلفة:

### Flatbuffers (`.fbs`)
* **الاستخدام:** بيانات السوق المتدفقة (High Frequency).
* **الميزة:** `Access without parsing`. بايثون يمكنها قراءة حقل `price` فقط دون قراءة باقي الرسالة، مما يقلل استهلاك المعالج.

### Protobuf (`.proto`)
* **الاستخدام:** الأوامر، الإعدادات، والحالة (State).
* **الميزة:** `Schema Evolution`. يمكن إضافة حقول جديدة للأوامر دون كسر التوافق مع النسخ القديمة من المحرك.

---

## 6. Emergency Protocols (بروتوكولات الطوارئ)

كيف يتم قطع الاتصال في الحالات الحرجة؟

1.  **The Kill Switch (Ops -> Engine):**
    * رسالة خاصة على منفذ `5558` بنوع `SYSTEM_HALT`.
    * المحرك يوقف فوراً استقبال أي رسائل من العقل (يغلق منفذ 5556).
    * ينتقل المحرك لوضع `Cancel-Only` (إلغاء الأوامر المفتوحة فقط).

2.  **Brain Death (Heartbeat Monitor):**
    * المحرك يتوقع "نبضة قلب" (Heartbeat) من العقل كل 1 ثانية.
    * إذا غاب العقل لأكثر من 3 ثوانٍ، يعتبره المحرك "ميتاً".
    * يقوم المحرك تلقائياً بتسييل المراكز الخطرة (حسب الإعدادات).

---

> **Forensic Note:** All IPC messages, specifically commands and their acknowledgments, are logged asynchronously to the `blackbox` recorder. This allows reconstructing the exact sequence of events leading to any trade decision.

```

### التحليل الهندسي:

1. **فلسفة "حق النقض" (Veto Power):**
* تم توضيح أن `Engine` هو الحاكم الفعلي. `Brain` يقترح، و `Engine` يوافق أو يرفض.
* هذا التصميم يحمي المحفظة من أخطاء الذكاء الاصطناعي (Hallucinations) أو الأخطاء البرمجية في بايثون.


2. **السرعة مقابل الموثوقية:**
* التمييز بين `Flatbuffers` للسرعة (Market Data) و `Protobuf` للموثوقية (Orders) هو قرار هندسي ناضج يعكس فهم طبيعة كل نوع من البيانات.


3. **مراقبة القلب (Heartbeat):**
* النظام لا يفترض أن العقل يعمل دائماً. إذا تجمدت بايثون (بسبب Garbage Collection طويل مثلاً)، المحرك سيعرف ويتصرف لحماية الأموال.



**الخلاصة:**
هذه الوثيقة هي الدستور الذي يحكم العلاقة بين مكونات النظام.

