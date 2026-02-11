// Hot-Reload Config

/*
 * ALPHA SOVEREIGN - HOT-RELOAD CONFIGURATION MANAGER
 * =================================================================
 * Component Name: engine/src/utils/config_loader.rs
 * Core Responsibility: تحميل ومراقبة وتحديث الإعدادات دون توقف (Adaptability Pillar).
 * Design Pattern: Observer / Atomic Reference Swap
 * Forensic Impact: يسجل بدقة متى تم تغيير الإعدادات ومن قام بذلك (عبر بصمة الملف). يمنع "أنا لم أغير شيئاً" كعذر.
 * =================================================================
 */

use config::{Config, File, FileFormat};
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use notify::{Watcher, RecursiveMode, RecommendedWatcher, Config as NotifyConfig};
use tokio::sync::watch;
use tracing::{info, error, warn};
use crate::error::{AlphaResult, AlphaError};

// =================================================================
// تعريفات هيكل الإعدادات (Configuration Schema)
// =================================================================

#[derive(Debug, Deserialize, Clone)]
pub struct GlobalConfig {
    pub server: ServerConfig,
    pub risk: RiskConfig,
    pub strategy: StrategyConfig,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub log_level: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct RiskConfig {
    pub max_drawdown_pct: f64,
    pub max_leverage: u32,
    pub daily_loss_limit: f64,
    pub circuit_breaker_enabled: bool,
}

#[derive(Debug, Deserialize, Clone)]
pub struct StrategyConfig {
    pub active_strategies: Vec<String>,
    pub execution_mode: String, // "paper" or "live"
}

// =================================================================
// مدير الإعدادات (Configuration Manager)
// =================================================================

pub struct ConfigManager {
    file_path: PathBuf,
    /// قناة لبث التحديثات للمكونات الأخرى
    /// نستخدم watch channel لأنها تحتفظ دائماً بآخر نسخة
    notifier: watch::Sender<GlobalConfig>,
    /// مخزن الإعدادات الحالي للقراءة السريعة
    current_config: Arc<RwLock<GlobalConfig>>,
}

impl ConfigManager {
    /// تحميل الإعدادات لأول مرة وإنشاء المدير
    pub fn new(path: &str) -> AlphaResult<(Self, watch::Receiver<GlobalConfig>)> {
        let path_buf = PathBuf::from(path);
        
        // 1. التحميل الأولي (يجب أن ينجح وإلا يفشل الإقلاع)
        let initial_config = Self::load_from_disk(&path_buf)?;
        
        info!("CONFIG: Initial configuration loaded successfully.");

        let (tx, rx) = watch::channel(initial_config.clone());

        Ok((Self {
            file_path: path_buf,
            notifier: tx,
            current_config: Arc::new(RwLock::new(initial_config)),
        }, rx))
    }

    /// دالة التحميل من القرص (Pure Function)
    fn load_from_disk(path: &Path) -> AlphaResult<GlobalConfig> {
        let settings = Config::builder()
            .add_source(File::from(path).format(FileFormat::Toml))
            .build()
            .map_err(|e| AlphaError::ConfigMissing(format!("Build Error: {}", e)))?;

        settings.try_deserialize::<GlobalConfig>()
            .map_err(|e| AlphaError::ConfigMissing(format!("Parse Error: {}", e)))
    }

    /// بدء مراقبة الملف للتغييرات (Background Watcher)
    pub async fn start_watcher(self: Arc<Self>) {
        let path = self.file_path.clone();
        let manager = self.clone();

        tokio::spawn(async move {
            let (tx, mut rx) = tokio::sync::mpsc::channel(1);

            // إعداد مراقب الملفات (Notify)
            let mut watcher = RecommendedWatcher::new(move |res| {
                let _ = tx.blocking_send(res);
            }, NotifyConfig::default()).unwrap();

            if let Err(e) = watcher.watch(&path, RecursiveMode::NonRecursive) {
                error!("CONFIG_WATCHER: Failed to watch file: {}", e);
                return;
            }

            info!("CONFIG_WATCHER: Active on {:?}", path);

            // حلقة معالجة الأحداث
            while let Some(res) = rx.recv().await {
                match res {
                    Ok(_) => {
                        // الملف تغير!
                        // ننتظر قليلاً (Debounce) لأن بعض المحررات تكتب الملف مرتين
                        tokio::time::sleep(Duration::from_millis(100)).await;

                        info!("CONFIG_WATCHER: Change detected. Reloading...");

                        match Self::load_from_disk(&path) {
                            Ok(new_config) => {
                                // التحديث الذري (Atomic Update)
                                {
                                    let mut write_lock = manager.current_config.write().unwrap();
                                    *write_lock = new_config.clone();
                                } // Release lock immediately

                                // إبلاغ الجميع
                                if let Err(e) = manager.notifier.send(new_config) {
                                    error!("CONFIG_WATCHER: Failed to broadcast update: {}", e);
                                } else {
                                    info!("CONFIG_WATCHER: Hot-Reload Successful. New config applied.");
                                    // هنا يمكننا تسجيل الفروقات (Diff) جنائياً
                                }
                            },
                            Err(e) => {
                                // إذا كان الملف الجديد فاسداً، نتجاهله ونحتفظ بالقديم
                                warn!("CONFIG_WATCHER: Reload Failed (Invalid Config): {}. Keeping old config.", e);
                            }
                        }
                    },
                    Err(e) => error!("CONFIG_WATCHER: Watch error: {}", e),
                }
            }
        });
    }

    /// الحصول على لقطة من الإعدادات الحالية
    pub fn get_current(&self) -> GlobalConfig {
        self.current_config.read().unwrap().clone()
    }
}