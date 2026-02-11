بصفتي **مهندس الواجهة الأمامية (Frontend Architect)** ومسؤول تجربة المستخدم، سأقوم بصياغة `docs/api_ref/ui_communication_api.md`.

هذا الملف هو **"العصب البصري"**.
الواجهة (UI) في نظام Alpha Sovereign ليست مجرد لوحة تحكم ثابتة (Dashboard) تعرض تقارير قديمة. إنها **"قمرة قيادة حية" (Live Cockpit)**.
البيانات تتدفق إليها بسرعة تصل إلى 60 إطاراً في الثانية (60fps). نحن لا نستخدم REST API (لأنه بطيء: "طلب واستجابة"). نحن نستخدم **Streams** (تدفقات) عبر جسر الذاكرة المباشر (FFI) لضمان أن السعر الذي تراه عينك هو السعر الحقيقي الآن، وليس قبل ثانية.

إليك الوثيقة الكاملة بصيغة Markdown:

### الملف: `docs/api_ref/ui_communication_api.md`

```markdown
# ALPHA SOVEREIGN - UI COMMUNICATION LAYER REFERENCE
================================================================================
**Component:** User Interface (Flutter/Dart)
**Mechanism:** FFI Streams (via flutter_rust_bridge) & ZMQ Bridging
**Latency Goal:** < 16ms (60 FPS updates)
**Last Updated:** 2026-02-03
================================================================================

## 1. Philosophy: Reactive Streams (فلسفة التدفق التفاعلي)

The UI does not "poll" the backend ("Are we there yet?").
Instead, the UI **reacts** to events pushed by the backend.
* **Architecture:** Stream-based State Management (using `BLoC` or `Riverpod`).
* **Transport:** Direct memory mapping via Rust FFI (No HTTP overhead).



---

## 2. Real-Time Data Streams (تدفقات البيانات)

These streams are exposed by the `RustImpl` class in Dart.

### `streamPriceUpdates()`
* **Purpose:** Live market ticker updates.
* **Dart Type:** `Stream<MarketTick>`
* **Frequency:** High (up to 100 updates/sec).
* **Payload:**
    ```dart
    class MarketTick {
      final String symbol;
      final double price;
      final double volume;
      final int timestampNs; // Nanosecond precision
    }
    ```
* **UI Usage:** Should be throttled in the UI layer (e.g., update widget every 100ms) to avoid freezing the main thread, while the backend processes everything.

### `streamTradeEvents()`
* **Purpose:** Updates on order status (Filled, Partial, Canceled).
* **Dart Type:** `Stream<TradeEvent>`
* **Frequency:** Event-driven.
* **Payload:**
    ```dart
    class TradeEvent {
      final String orderId;
      final String status; // "FILLED", "REJECTED"
      final double fillPrice;
      final String? rejectionReason;
    }
    ```
* **UI Usage:** Triggers "Toast" notifications and updates the "Open Orders" table.

### `streamSystemHealth()`
* **Purpose:** Vital signs of the infrastructure.
* **Dart Type:** `Stream<HealthStatus>`
* **Frequency:** 1 update per second (Heartbeat).
* **Payload:**
    ```dart
    class HealthStatus {
      final double cpuUsage;
      final double ramUsage;
      final bool isRedisAlive;
      final bool isBrainConnected;
    }
    ```
* **UI Usage:** Updates the status bar icons (Green/Red dots).

### `streamLogOutput()`
* **Purpose:** The "Matrix" view (Real-time terminal logs).
* **Dart Type:** `Stream<LogEntry>`
* **Frequency:** Variable.
* **Payload:**
    ```dart
    class LogEntry {
      final String level; // "INFO", "WARN", "ERROR"
      final String component; // "Engine", "Brain"
      final String message;
      final String timestamp;
    }
    ```

---

## 3. Command Methods (طرق الإرسال)

How the UI sends user intentions to the backend.

### `sinkManualOrder(OrderRequest)`
* **Description:** Used by the "Trade Ticket" widget.
* **Behavior:** Asynchronous. Returns a `Future<String>` (OrderID) immediately after validation, but execution result comes later via `streamTradeEvents`.

### `sinkSystemControl(ControlCommand)`
* **Description:** Used by the "Panic Button" or "Shutdown" menu.
* **Commands:**
    * `HALT_TRADING`: Cancel all open orders, stop engine.
    * `REBOOT_BRAIN`: Restart the Python subsystem.
    * `FLUSH_LOGS`: Clear UI log buffer.

---

## 4. State Rehydration (إعادة ترطيب الحالة)

When the app launches, streams are empty. We need initial data.

### `fetchInitialState()`
* **Type:** `Future<AppState>`
* **Description:** Called on app startup (`main.dart`).
* **Returns:**
    * `activeOrders`: List of currently open orders.
    * `portfolioBalance`: Current wallet snapshot.
    * `chartHistory`: Last 100 candles for the default timeframe.

---

## 5. Error Handling & Connection State

The UI must handle backend crashes gracefully.

| State | Visual Indicator | Action |
| :--- | :--- | :--- |
| **Connected** | 🟢 Green Dot | Normal operation. |
| **Lagging** | 🟡 Yellow Dot | Data received > 500ms ago. Show warning. |
| **Disconnected** | 🔴 Red Dot | Backend process died. Show "Reconnecting..." overlay. |

**Dart Implementation Note:**
Use a global `ConnectionBloc` to listen to the FFI bridge status. If the bridge breaks (Rust panic), trigger a UI alert to run `alpha_reboot.sh`.

---

> **Engineering Impact:** By using FFI Streams instead of WebSockets for local communication, we save serialization/deserialization overhead, keeping the UI snappy even during high-load stress tests.

```

### ⚠️ إعلان انتهاء مرحلة التوثيق بالكامل (Docs Layer Complete)

لقد أتممنا الآن **الـ 38 ملفاً** التمهيدياً:

* **الأدوات (Scripts):** 14 ملف.
* **العمليات (Ops):** 15 ملف.
* **الوثائق (Docs):** 9 ملفات.

النظام الآن:

1. **مؤسس:** (Infrastructure ready).
2. **محمي:** (Security hardened).
3. **موثق:** (Blueprints clear).
4. **قانوني:** (Compliance set).

**الآن.. حان وقت "الانفجار العظيم" (The Big Bang).**
سننتقل من التنظير إلى الخلق.

المجلد: **`shield/core`**.
الملف الأول: **`shield/core/brain_router.py`**.

هل أنت مستعد لبدء كتابة "العقل"؟