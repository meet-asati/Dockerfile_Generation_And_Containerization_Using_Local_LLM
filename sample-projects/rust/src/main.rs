use std::env;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};

fn main() -> std::io::Result<()> {
    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let address = format!("0.0.0.0:{port}");
    let listener = TcpListener::bind(&address)?;

    println!("Rust service listening on {address}");

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => handle_request(stream)?,
            Err(error) => eprintln!("Connection failed: {error}"),
        }
    }

    Ok(())
}

fn handle_request(mut stream: TcpStream) -> std::io::Result<()> {
    let mut buffer = [0; 1024];
    let bytes_read = stream.read(&mut buffer)?;
    let request = String::from_utf8_lossy(&buffer[..bytes_read]);
    let path = request.split_whitespace().nth(1).unwrap_or("/");

    let (status, body) = match path {
        "/health" => ("200 OK", r#"{"status":"ok"}"#),
        "/" => (
            "200 OK",
            r#"{"message":"Hello from the multi-stage Rust sample project"}"#,
        ),
        _ => ("404 Not Found", r#"{"error":"not found"}"#),
    };

    let response = format!(
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    stream.write_all(response.as_bytes())?;
    stream.flush()
}