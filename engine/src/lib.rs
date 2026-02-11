// ALPHA SOVEREIGN - ROOT LIBRARY
// Status: CLEAN REWRITE

// 1. تعريف الوحدات (Modules)
pub mod error;
pub mod utils;
pub mod models;
pub mod matching;
pub mod risk;
pub mod hardware;
pub mod transport;
pub mod adapters;
pub mod api;

// 2. التصدير العام (Re-exports)
pub use error::{AlphaError, AlphaResult};
pub use models::order::{Order, OrderSide, OrderType, OrderStatus};
pub use utils::logger::{LogEntry, init_logger};

// 3. البروتوكولات (Protos)
pub mod interfaces {
    pub mod control { tonic::include_proto!("alpha.core.v1"); }
    pub mod auth { tonic::include_proto!("alpha.auth.v1"); }
    pub mod brain { tonic::include_proto!("alpha.brain.v1"); }
    pub mod shield { tonic::include_proto!("alpha.shield.v1"); }
    pub mod swarm { tonic::include_proto!("alpha.swarm.v1"); }
    pub mod telemetry { tonic::include_proto!("alpha.telemetry.v1"); }
    pub mod evolution { tonic::include_proto!("alpha.evolution"); }
}

pub mod prelude {
    pub use crate::AlphaError;
    pub use crate::Order;
    pub use crate::LogEntry;
}
