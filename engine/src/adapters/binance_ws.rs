// Exchange Connector

/*
 * ALPHA SOVEREIGN - BINANCE WEBSOCKET ADAPTER
 * =================================================================
 * Component Name: engine/src/adapters/binance_ws.rs
 * Core Responsibility: إدارة تدفق بيانات Binance اللحظي وضمان استمرارية الاتصال (Integration Pillar).
 * Design Pattern: Async Event Loop / Auto-Reconnect / Heartbeat
 * Forensic Impact: يسجل لحظة الانقطاع ولحظة العودة بدقة. أي فجوة زمنية هنا تعني "فجوة في البيانات" (Data Gap) في التحقيق.
 * =================================================================
 */

use std::time::Duration;
use futures::{StreamExt, SinkExt};
use tokio::net::TcpStream;
use tokio::time::sleep;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message, MaybeTlsStream, WebSocketStream};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::{info, warn, error, debug};
use url::Url;

use crate::transport::{EventTx, IngressEvent};
use crate::error::AlphaResult;

// الثوابت
const BINANCE_FUTURES_WS: &str = "wss://fstream.binance.com/ws";
const RECONNECT_DELAY_MS: u64 = 1000;
const MAX_RECONNECT_DELAY_MS: u64 = 30000;

/// هيكل البيانات القادمة من Binance (Book Ticker)
#[derive(Debug, Deserialize)]
struct BinanceBookTicker {
    s: String, // Symbol
    b: String, // Best Bid Price
    B: String, // Best Bid Qty
    a: String, // Best Ask Price
    A: String, // Best Ask Qty
    T: u64,    // Transaction Time
    E: u64,    // Event Time
}

pub struct BinanceWsManager {
    event_bus: EventTx,
    running: bool,
}

impl BinanceWsManager {
    pub fn new(event_bus: EventTx) -> Self {
        Self {
            event_bus,
            running: true,
        }
    }

    /// تشغيل الاستماع للبيانات العامة (Market Data)
    /// يقوم بإنشاء خيط خلفي يدير الاتصال ويعيد المحاولة للأبد.
    pub async fn start_market_stream(&self, symbols: Vec<String>) {
        let bus = self.event_bus.clone();
        
        // تحويل الرموز لصيغة URL (btcusdt@bookTicker)
        let streams: Vec<String> = symbols.iter()
            .map(|s| format!("{}@bookTicker", s.to_lowercase()))
            .collect();
        
        let url_str = format!("{}/{}", BINANCE_FUTURES_WS, streams.join("/"));

        tokio::spawn(async move {
            let mut retry_delay = RECONNECT_DELAY_MS;

            loop {
                info!("BINANCE_WS: Connecting to Market Stream...");
                
                match connect_async(Url::parse(&url_str).unwrap()).await {
                    Ok((ws_stream, _)) => {
                        info!("BINANCE_WS: Connected successfully.");
                        retry_delay = RECONNECT_DELAY_MS; // إعادة ضبط التأخير عند النجاح
                        
                        // بدء معالجة الرسائل
                        Self::handle_connection(ws_stream, bus.clone()).await;
                        
                        warn!("BINANCE_WS: Connection lost via handle return.");
                    },
                    Err(e) => {
                        error!("BINANCE_WS: Connection Failed: {}. Retrying in {}ms", e, retry_delay);
                    }
                }

                // استراتيجية الانتظار قبل إعادة المحاولة (Exponential Backoff)
                sleep(Duration::from_millis(retry_delay)).await;
                retry_delay = std::cmp::min(retry_delay * 2, MAX_RECONNECT_DELAY_MS);
            }
        });
    }

    /// المعالج الداخلي للاتصال (The Inner Loop)
    async fn handle_connection(
        mut ws_stream: WebSocketStream<MaybeTlsStream<TcpStream>>,
        event_bus: EventTx
    ) {
        // حلقة القراءة
        while let Some(msg) = ws_stream.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    // محاولة فك التشفير السريع (Fast Path)
                    // نستخدم serde_json::from_str داخل كتلة منطقية
                    
                    // هنا نفترض أن الرسالة هي BookTicker
                    // في التطبيق الكامل، يجب التمييز بين أنواع الرسائل
                    match serde_json::from_str::<BinanceBookTicker>(&text) {
                        Ok(ticker) => {
                            // تحويل السعر من String إلى Decimal (مكلف قليلاً لكن ضروري)
                            if let (Ok(price), Ok(_qty)) = (
                                rust_decimal::Decimal::from_str_radix(&ticker.b, 10), // Bid Price as ref
                                rust_decimal::Decimal::from_str_radix(&ticker.B, 10)
                            ) {
                                // إرسال الحدث للمحرك
                                let event = IngressEvent::MarketData {
                                    symbol: ticker.s,
                                    price: price, // نستخدم Bid كسعر حالي للتبسيط
                                    timestamp: ticker.T,
                                };
                                
                                if let Err(e) = event_bus.try_send(event) {
                                    // إذا امتلأت القناة، فهذا يعني أن المحرك يختنق!
                                    // لا نوقف WS، بل نسقط الحزمة ونسجل الخطأ
                                    error!("BINANCE_WS: Engine Backpressure! Dropping tick. {}", e);
                                }
                            }
                        },
                        Err(e) => {
                            // قد تكون رسالة ping أو heartbeat من البورصة
                            if !text.contains("ping") {
                                debug!("BINANCE_WS: Parse Error or Unknown Msg: {} | Payload: {:.50}...", e, text);
                            }
                        }
                    }
                },
                Ok(Message::Ping(payload)) => {
                    // الرد بـ Pong إلزامي للحفاظ على الاتصال
                    let _ = ws_stream.send(Message::Pong(payload)).await;
                },
                Ok(Message::Close(_)) => {
                    warn!("BINANCE_WS: Server sent CLOSE frame.");
                    break;
                },
                Err(e) => {
                    error!("BINANCE_WS: Stream Error: {}", e);
                    break;
                },
                _ => {} // Binary/Pong ignored
            }
        }
    }

    /// (اختياري) تجديد ListenKey للبيانات الخاصة
    /// يتطلب REST Client (سنفترض وجوده)
    pub async fn keepalive_user_stream(listen_key: String) {
        // حلقة لا نهائية ترسل طلب PUT كل 30 دقيقة
        // لمنع انتهاء صلاحية جلسة المستخدم
        tokio::spawn(async move {
            loop {
                sleep(Duration::from_secs(1800)).await; // 30 دقيقة
                info!("BINANCE_WS: Renewing ListenKey...");
                // adapter.rest_client.put_listen_key(&listen_key).await;
            }
        });
    }
}