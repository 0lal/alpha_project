use thiserror::Error;
use tonic::Status;

#[derive(Error, Debug)]
pub enum AlphaError {
    #[error("Configuration Error: {0}")]
    ConfigMissing(String),
    #[error("Initialization Failed: {0}")]
    BootstrapError(String),
    #[error("Connection Lost: {0}")]
    NetworkError(String),
    #[error("Exchange Rejection: {0}")]
    ExchangeRejection(String),
    
    // FIX: Use named arguments for named fields
    #[error("Risk Violation: {rule} | Limit: {limit} | Actual: {actual}")]
    RiskViolation { rule: String, actual: String, limit: String },
    
    #[error("Execution Failed: {0}")]
    ExecutionFailed(String),
    #[error("Validation Failed: {0}")]
    ValidationFailed(String),
    #[error("Internal Error: {0}")]
    InternalError(String),
    #[error("Fatal Error: {0}")]
    Fatal(String),
}

impl From<AlphaError> for Status {
    fn from(err: AlphaError) -> Self {
        Status::internal(format!("{:?}", err))
    }
}

pub type AlphaResult<T> = Result<T, AlphaError>;
