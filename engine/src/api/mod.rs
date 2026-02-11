/*
 * ALPHA SOVEREIGN - gRPC API GATEWAY (FIXED)
 * =================================================================
 * Forensic Fix: Type Mismatch Resolution (String <-> u64)
 * =================================================================
 */

use tonic::{Request, Response, Status, Code};
use std::sync::Arc;
use parking_lot::RwLock;
use std::str::FromStr;
use rust_decimal::Decimal;

use crate::interfaces::control::engine_control_server::EngineControl;
use crate::interfaces::control::{ExecuteOrderRequest, ExecuteOrderResponse};
use crate::matching::engine::MatchingEngine;
use crate::models::order::{Order, OrderSide, OrderType};

pub struct AlphaServiceImpl {
    matching_engine: Arc<RwLock<MatchingEngine>>,
}

impl AlphaServiceImpl {
    pub fn new(matching_engine: Arc<RwLock<MatchingEngine>>) -> Self {
        Self { matching_engine }
    }
}

#[tonic::async_trait]
impl EngineControl for AlphaServiceImpl {
    async fn execute_order(
        &self,
        request: Request<ExecuteOrderRequest>,
    ) -> Result<Response<ExecuteOrderResponse>, Status> {
        
        let req = request.into_inner();
        tracing::info!("API: Received Order Request ID: {}", req.order_id);

        // 1. معالجة التحويلات (Fixing Type Mismatches)
        
        // FIX 1: تحويل معرف الطلب من String إلى u64
        // إذا كان النص غير رقمي، نرفض الطلب
        let internal_id = req.order_id.parse::<u64>()
            .map_err(|_| Status::new(Code::InvalidArgument, "Order ID must be a numeric value (u64)"))?;

        let side = match req.side {
            0 => OrderSide::Buy,
            1 => OrderSide::Sell,
            _ => return Err(Status::new(Code::InvalidArgument, "Invalid Side")),
        };

        let order_type = match req.order_type {
            0 => OrderType::Market,
            1 => OrderType::Limit,
            _ => return Err(Status::new(Code::InvalidArgument, "Invalid Order Type")),
        };

        let qty = Decimal::from_str(&req.quantity)
            .map_err(|_| Status::new(Code::InvalidArgument, "Invalid Quantity Format"))?;

        let price = if req.price.is_empty() || req.price == "0" {
            None 
        } else {
            Some(Decimal::from_str(&req.price)
                .map_err(|_| Status::new(Code::InvalidArgument, "Invalid Price Format"))?)
        };

        // 2. بناء الأمر (الآن الأنواع متطابقة)
        let order = Order::new(
            internal_id,           // تم الإصلاح: نمرر u64
            req.strategy_id,
            req.symbol.clone(),
            req.exchange,
            side,
            order_type,
            qty,
            price,
        );

        // 3. التنفيذ
        let mut engine = self.matching_engine.write();
        
        match engine.process_order(order) {
            Ok(result) => {
                Ok(Response::new(ExecuteOrderResponse {
                    // FIX 2: تحويل الرد من u64 إلى String ليتوافق مع البروتو
                    order_id: result.order.id.to_string(), 
                    status: format!("{:?}", result.order.status),
                    filled_qty: result.order.executed_qty.to_string(),
                    message: "Order Accepted".to_string(),
                }))
            },
            Err(e) => {
                Err(Status::internal(format!("Engine Error: {:?}", e)))
            }
        }
    }
}