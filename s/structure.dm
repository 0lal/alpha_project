Goal: توثيق الهيكلة الشجرية الكاملة لمجلد s مع شرح معماري وتشغيلي.
Dependencies: كل مكونات Bio-Schema تحت s/ + أدوات registry/toolkit.

# Bio-Schema Directory Map (.dm)

هذا الملف هو خريطة ملاحة شاملة لمجلد `s/`، ويشرح دور كل طبقة
وكيف تتفاعل المكونات مع بعضها داخل نظام البيانات الحيوية.

## 1) الفلسفة العامة
- `definitions/`: تعريفات العقود والبُنى (Transport/Storage/ML/Config/Reports).
- `governance/`: سياسات الحوكمة والحدود والامتثال والأمن.
- `intelligence/`: طبقة الذكاء الفعلي (Validators/Mutators/Adapters/Memory/Optimizer).
- `registry/`: برج التحكم (manifest/catalog/history/hooks/migrations).
- `toolkit/`: المصنع التشغيلي (compilers/linters/generators/fuzzers/viewers/benchmarker/tests).

## 2) الشجرة الكاملة
```
s/
├── definitions
│   ├── common
│   │   ├── currency_codes.json
│   │   └── error_codes.json
│   ├── config
│   │   ├── strategy_params.json
│   │   └── system_config.json
│   ├── hardware
│   │   ├── fpga_registers.yaml
│   │   └── network_stack.yaml
│   ├── ml
│   │   ├── feature_store.fbs
│   │   └── model_metadata.json
│   ├── reports
│   │   ├── backtest_results.json
│   │   └── regulatory_report.json
│   ├── storage
│   │   ├── cold
│   │   │   ├── audit_trail.sql
│   │   │   ├── ledger_entries.sql
│   │   │   ├── strategy_perf.sql
│   │   │   ├── trade_history.sql
│   │   │   └── user_profiles.sql
│   │   └── hot
│   │       ├── indicators.fbs
│   │       ├── market_tick.fbs
│   │       ├── order_book.fbs
│   │       └── risk_state.fbs
│   └── transport
│       ├── events
│       │   ├── market_events.proto
│       │   ├── strategy_events.proto
│       │   └── system_events.proto
│       ├── rest
│       │   ├── admin_panel.json
│       │   ├── client_response.json
│       │   └── public_api.json
│       └── rpc
│           ├── auth_gateway.proto
│           ├── brain_service.proto
│           ├── execution_link.proto
│           ├── risk_control.proto
│           ├── service_discovery.proto
│           └── telemetry.proto
├── governance
│   ├── compliance
│   │   ├── anti_manipulation.yaml
│   │   └── audit_policy.yaml
│   ├── lifecycle
│   │   ├── gdpr_rules.yaml
│   │   └── retention.yaml
│   ├── security
│   │   ├── access_control.yaml
│   │   └── encryption_policy.yaml
│   └── thresholds
│       ├── risk_limits.yaml
│       └── volatility.yaml
├── intelligence
│   ├── adapters
│   │   ├── __init__.py
│   │   ├── binance_mapper.py
│   │   └── fix_to_proto.py
│   ├── memory
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py
│   │   └── state_fetcher.py
│   ├── mutators
│   │   ├── __init__.py
│   │   ├── enricher.py
│   │   └── sanitizer.py
│   ├── optimizer
│   │   ├── __init__.py
│   │   └── schema_pruner.py
│   ├── validators
│   │   ├── __init__.py
│   │   ├── atomic.py
│   │   ├── contextual.py
│   │   ├── pipeline.py
│   │   └── semantic.py
│   └── __init__.py
├── registry
│   ├── history
│   │   ├── schema_v1_backup
│   │   └── market_tick.meta
│   ├── hooks
│   │   └── pre_commit_check.sh
│   ├── migrations
│   │   └── v1_to_v2.md
│   ├── __init__.py
│   ├── catalog.py
│   ├── compiled_catalog.json
│   └── manifest.json
├── toolkit
│   ├── benchmarker
│   │   └── speed_test.rs
│   ├── compilers
│   │   ├── __init__.py
│   │   └── schema_builder.py
│   ├── fuzzers
│   │   ├── __init__.py
│   │   └── chaos_injector.py
│   ├── generators
│   │   ├── __init__.py
│   │   ├── replay_tool.py
│   │   └── smart_mock.py
│   ├── linters
│   │   ├── __init__.py
│   │   ├── compatibility.py
│   │   └── style_check.py
│   ├── tests
│   │   └── test_smart_validation.py
│   ├── viewers
│   │   ├── __init__.py
│   │   └── schema_graph.py
│   └── __init__.py
└── __init__.py
```

## 3) شرح تفصيلي للطبقات

### A) definitions/
تمثل الـ DNA للبيانات. تحتوي:
- `transport/`: عقود RPC و Events و REST.
- `storage/hot`: نماذج FlatBuffers للبيانات اللحظية.
- `storage/cold`: جداول SQL للتخزين التحليلي والتدقيقي.
- `ml/`: توصيف feature vectors و metadata النماذج.
- `common/config/reports/hardware`: معايير مشتركة وإعدادات وتقارير وتهيئة عتاد.

### B) governance/
القوانين العليا للنظام:
- `thresholds/`: حدود التقلب والمخاطر التي يقرأها ContextualValidator وقت التشغيل.
- `security/`: صلاحيات الوصول والتشفير.
- `compliance/`: سياسات الرقابة ومنع التلاعب.
- `lifecycle/`: الاحتفاظ، الأرشفة، وخصوصية GDPR.

### C) intelligence/
العقل التشغيلي:
- `validators/`: فحص ذري + دلالي + سياقي + pipeline موحّد.
- `mutators/`: تنظيف وإثراء غير مدمر مع قابلية تتبع.
- `adapters/`: تحويل البيانات من مصادر/بروتوكولات خارجية إلى نموذج موحد.
- `memory/`: استرجاع الحالة والتعرف على الانحرافات.
- `optimizer/`: اقتراحات تحسين schema واكتشاف الحقول غير المستخدمة.

### D) registry/
مصدر الحقيقة:
- `manifest.json`: التعريف الرسمي للإصدار والسياسات.
- `catalog.py`: اكتشاف ملفات schema وحساب بصماتها.
- `compiled_catalog.json`: ناتج البناء الآلي للكتالوج.
- `history/`: تتبع تغييرات وmeta.
- `hooks/`: فحوص ما قبل الالتزام.
- `migrations/`: خطط تطور الإصدارات.

### E) toolkit/
أدوات الإنتاج والجودة:
- `compilers/`: بناء كتالوج وتوليد مخرجات تشغيلية.
- `linters/`: ضبط نمط التوثيق والتوافق.
- `generators/`: بيانات تجريبية وإعادة بث.
- `fuzzers/`: اختبارات فوضى ومناعة.
- `viewers/`: رسم العلاقات.
- `benchmarker/`: قياس الأداء.
- `tests/`: اختبارات التكامل والسلوك.

## 4) مسار التشغيل المقترح
1. تعديل schema/سياسة.
2. تشغيل `style_check` + `schema_builder`.
3. تشغيل اختبارات `test_smart_validation`.
4. اعتماد التغيير ثم تحديث migration notes عند الحاجة.

## 5) ملاحظات حوكمة
- أي ملف `.proto` أو `.json` يجب أن يحوي Goal/Dependencies.
- أي تغيير breaking في proto يجب أن يمر عبر compatibility checks.
- أي تعديل على thresholds يؤثر مباشرة على القرار بسبب hot-reload.
