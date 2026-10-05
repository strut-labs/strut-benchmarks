use axum::{routing::get, Json, Router};
use serde_json::{json, Value};

async fn plaintext() -> &'static str {
    "Hello, World!"
}

async fn json_route() -> Json<Value> {
    Json(json!({"message": "Hello, World!"}))
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/plaintext", get(plaintext))
        .route("/json", get(json_route));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080")
        .await
        .expect("bind 0.0.0.0:8080");
    axum::serve(listener, app).await.expect("serve");
}
