// Emergency Control Port

/*
 * ALPHA SOVEREIGN - EMERGENCY RAW TCP CONSOLE
 * =================================================================
 * Component Name: engine/src/transport/tcp_server.rs
 * Core Responsibility: واجهة تحكم نصية بدائية للطوارئ القصوى (Stability Pillar).
 * Design Pattern: Command Line Interface (CLI) over TCP
 * Forensic Impact: يسجل عنوان IP ووقت كل أمر "إداري" تم تنفيذه يدوياً.
 * =================================================================
 */

use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tracing::{info, warn, error};
use std::env;
use crate::error::AlphaResult;
use crate::risk::{trigger_emergency_stop, is_emergency_state};

pub struct TcpAdminServer {
    port: u16,
    auth_token: String,
}

impl TcpAdminServer {
    pub fn new(port: u16) -> Self {
        // يجب تعيين رمز سري في متغيرات البيئة، وإلا نستخدم قيمة افتراضية عشوائية للأمان
        let auth_token = env::var("ADMIN_SECRET_TOKEN")
            .unwrap_or_else(|_| "ALPHA_EMERGENCY_KEY_CHANGE_ME".to_string());
            
        Self { port, auth_token }
    }

    /// بدء الخادم
    pub async fn start(&self) -> AlphaResult<()> {
        // نربط الخادم بـ localhost فقط لأسباب أمنية
        // لا يجب أبداً تعريض هذا المنفذ للإنترنت العام
        let addr = format!("127.0.0.1:{}", self.port);
        let listener = TcpListener::bind(&addr).await
            .map_err(|e| crate::error::AlphaError::BootstrapError(format!("TCP Bind Error: {}", e)))?;

        info!("ADMIN_CONSOLE: Listening on {} (Raw TCP)", addr);

        let token = self.auth_token.clone();

        // حلقة قبول الاتصالات
        tokio::spawn(async move {
            loop {
                match listener.accept().await {
                    Ok((socket, addr)) => {
                        info!("ADMIN_CONSOLE: New connection from {}", addr);
                        let token_clone = token.clone();
                        
                        // معالجة كل اتصال في خيط منفصل
                        tokio::spawn(async move {
                            if let Err(e) = handle_connection(socket, token_clone).await {
                                warn!("ADMIN_CONSOLE: Connection error: {}", e);
                            }
                        });
                    }
                    Err(e) => {
                        error!("ADMIN_CONSOLE: Accept error: {}", e);
                    }
                }
            }
        });

        Ok(())
    }
}

/// معالجة جلسة الاتصال الواحدة
async fn handle_connection(mut socket: TcpStream, valid_token: String) -> std::io::Result<()> {
    let (reader, mut writer) = socket.split();
    let mut reader = BufReader::new(reader);
    let mut line = String::new();

    // 1. الترحيب وطلب التوثيق
    writer.write_all(b"ALPHA SOVEREIGN EMERGENCY CONSOLE\n").await?;
    writer.write_all(b"AUTH REQUIRED: ").await?;

    // قراءة التوكن
    line.clear();
    if reader.read_line(&mut line).await? == 0 { return Ok(()); } // EOF
    
    if line.trim() != valid_token {
        writer.write_all(b"AUTH FAILED. DISCONNECTING.\n").await?;
        warn!("ADMIN_CONSOLE: Auth failed attempt.");
        return Ok(()); // إغلاق الاتصال
    }

    writer.write_all(b"ACCESS GRANTED. Type 'HELP' for commands.\nalpha> ").await?;

    // 2. حلقة الأوامر (REPL Loop)
    loop {
        line.clear();
        let bytes_read = reader.read_line(&mut line).await?;
        if bytes_read == 0 { break; } // EOF (Client disconnected)

        let command = line.trim();
        let response = process_command(command);

        writer.write_all(response.as_bytes()).await?;
        writer.write_all(b"\nalpha> ").await?;
    }

    info!("ADMIN_CONSOLE: Session closed.");
    Ok(())
}

/// تنفيذ الأوامر
fn process_command(cmd: &str) -> String {
    let parts: Vec<&str> = cmd.split_whitespace().collect();
    if parts.is_empty() { return "".to_string(); }

    match parts[0].to_uppercase().as_str() {
        "HELP" => {
            "AVAILABLE COMMANDS:
             STATUS  - Check system health
             PANIC   - TRIGGER GLOBAL KILL SWITCH (HALT TRADING)
             PING    - Test latency
             EXIT    - Close connection".to_string()
        },
        
        "PING" => "PONG".to_string(),
        
        "STATUS" => {
            let emergency = is_emergency_state();
            format!("SYSTEM STATUS: Running\nEMERGENCY MODE: {}", emergency)
        },
        
        "PANIC" | "STOP" => {
            trigger_emergency_stop();
            warn!("ADMIN_CONSOLE: MANUAL KILL SWITCH TRIGGERED VIA TCP!");
            "!!! EMERGENCY STOP TRIGGERED !!! ALL TRADING HALTED.".to_string()
        },
        
        "EXIT" | "QUIT" => {
            "Goodbye.".to_string()
        },
        
        _ => format!("Unknown command: '{}'", cmd),
    }
}