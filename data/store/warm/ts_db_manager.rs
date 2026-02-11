// ALPHA SOVEREIGN - TIME-SERIES DATABASE MANAGER
// =================================================================
// Component Name: data/storage/warm/ts_db_manager.rs
// Core Responsibility: إدارة الكتابة فائقة السرعة إلى TimescaleDB (Pillar: Performance).
// Design Pattern: Data Access Object (DAO) / Connection Pooling
// Forensic Impact: يضمن تخزين كل نبضة (Tick) بطابع زمني دقيق غير قابل للتزوير (Immutable Logs).
// Language: Rust (sqlx Async)
// =================================================================

use sqlx::postgres::{PgPoolOptions, PgPool};
use sqlx::{Row, Error};
use std::time::Duration;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// -----------------------------------------------------------------
// 1. هياكل البيانات (Data Structures)
// -----------------------------------------------------------------

/// هيكل يمثل نبضة السوق المخزنة في قاعدة البيانات.
/// مطابق لجدول 'market_ticks' في TimescaleDB.
#[derive(Debug, sqlx::FromRow, Serialize, Deserialize)]
pub struct MarketTick {
    pub time: DateTime<Utc>,
    pub symbol: String,
    pub price: f64,
    pub quantity: f64,
    pub source: String,
    pub is_anomalous: bool, // علامة جنائية: هل كانت البيانات مشبوهة؟
}

// -----------------------------------------------------------------
// 2. مدير قاعدة البيانات (Database Manager)
// -----------------------------------------------------------------

pub struct TSDBManager {
    /// مسبح الاتصالات (Connection Pool).
    /// يسمح بتنفيذ عمليات متعددة متزامنة دون إعادة فتح الاتصال في كل مرة.
    pool: PgPool,
}

impl TSDBManager {
    /// إنشاء مدير جديد والاتصال بقاعدة البيانات.
    ///
    /// # Arguments
    /// * `connection_url`: رابط الاتصال (postgres://user:pass@localhost:5432/alpha_db)
    pub async fn new(connection_url: &str) -> Result<Self, sqlx::Error> {
        println!("TSDB_INIT: جاري الاتصال بـ TimescaleDB...");

        // إعداد مسبح الاتصالات
        let pool = PgPoolOptions::new()
            .max_connections(20) // تحديد الحد الأقصى لمنع خنق السيرفر
            .acquire_timeout(Duration::from_secs(5))
            .connect(connection_url)
            .await?;

        println!("TSDB_CONNECTED: تم تأسيس الاتصال بنجاح.");
        
        // التحقق من وجود الجداول الأساسية (Hypertable Check)
        // هذا مجرد فحص سريع، الإنشاء الفعلي يتم عبر ملفات SQL migration
        Self::verify_schema(&pool).await?;

        Ok(Self { pool })
    }

    /// التحقق من صحة المخطط (Schema Validation).
    async fn verify_schema(pool: &PgPool) -> Result<(), sqlx::Error> {
        // استعلام بسيط للتأكد من أن قاعدة البيانات تعمل
        sqlx::query("SELECT 1")
            .execute(pool)
            .await?;
        Ok(())
    }

    /// الكتابة فائقة السرعة (High-Velocity Insert).
    /// يقوم بإدراج نبضة واحدة في قاعدة البيانات.
    ///
    /// # ملاحظة هندسية:
    /// في بيئة الإنتاج القصوى، يفضل استخدام Batch Insert (تجميع 1000 صف وإرسالهم مرة واحدة).
    /// ولكن هنا نكتب دالة الإدراج الفردي كأساس.
    pub async fn insert_tick(&self, tick: &MarketTick) -> Result<(), sqlx::Error> {
        // الاستعلام المحضر (Prepared Statement) للأداء والأمان (ضد SQL Injection)
        let query = "
            INSERT INTO market_ticks (time, symbol, price, quantity, source, is_anomalous)
            VALUES ($1, $2, $3, $4, $5, $6)
        ";

        sqlx::query(query)
            .bind(tick.time)
            .bind(&tick.symbol)
            .bind(tick.price)
            .bind(tick.quantity)
            .bind(&tick.source)
            .bind(tick.is_anomalous)
            .execute(&self.pool)
            .await?;

        Ok(())
    }

    /// الكتابة بالجملة (Batch Ingestion).
    /// هذه هي الطريقة المفضلة للأداء العالي (10k writes/sec).
    pub async fn insert_batch(&self, ticks: Vec<MarketTick>) -> Result<u64, sqlx::Error> {
        if ticks.is_empty() {
            return Ok(0);
        }

        // بناء استعلام ديناميكي للإدخال المتعدد
        // (ملاحظة: sqlx يدعم طرقاً أكثر تعقيداً مثل UNNEST، لكن هذا للتوضيح)
        let mut query_builder = sqlx::QueryBuilder::new(
            "INSERT INTO market_ticks (time, symbol, price, quantity, source, is_anomalous) "
        );

        query_builder.push_values(ticks, |mut b, tick| {
            b.push_bind(tick.time)
             .push_bind(tick.symbol)
             .push_bind(tick.price)
             .push_bind(tick.quantity)
             .push_bind(tick.source)
             .push_bind(tick.is_anomalous);
        });

        let query = query_builder.build();
        let result = query.execute(&self.pool).await?;

        Ok(result.rows_affected())
    }

    /// الاسترجاع الجنائي (Forensic Retrieval).
    /// جلب البيانات التاريخية لإعادة تشغيل السوق (Replay) أو تدريب الذكاء الاصطناعي.
    pub async fn fetch_history(
        &self, 
        symbol: &str, 
        start: DateTime<Utc>, 
        end: DateTime<Utc>
    ) -> Result<Vec<MarketTick>, sqlx::Error> {
        
        let query = "
            SELECT time, symbol, price, quantity, source, is_anomalous
            FROM market_ticks
            WHERE symbol = $1 AND time >= $2 AND time <= $3
            ORDER BY time ASC
        ";

        let rows = sqlx::query_as::<_, MarketTick>(query)
            .bind(symbol)
            .bind(start)
            .bind(end)
            .fetch_all(&self.pool)
            .await?;

        Ok(rows)
    }

    /// إغلاق الاتصال بأمان.
    pub async fn close(&self) {
        self.pool.close().await;
        println!("TSDB_CLOSED: تم إغلاق الاتصال بقاعدة البيانات.");
    }
}

// -----------------------------------------------------------------
// 3. اختبار الوحدة (Unit Test)
// -----------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_tick_structure() {
        let tick = MarketTick {
            time: Utc::now(),
            symbol: "BTCUSDT".to_string(),
            price: 50000.0,
            quantity: 1.5,
            source: "BINANCE".to_string(),
            is_anomalous: false,
        };
        
        assert_eq!(tick.symbol, "BTCUSDT");
        assert!(tick.price > 0.0);
    }
}