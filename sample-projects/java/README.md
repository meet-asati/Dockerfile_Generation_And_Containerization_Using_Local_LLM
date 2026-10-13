# Sample Java project

This small Java HTTP service is intentionally structured for a multi-stage Docker build:

- The builder stage can use `maven:3.9-eclipse-temurin-17` to run `mvn package`.
- The runtime stage only needs a Java 17 JRE and the JAR from `target/`.
- Maven adds `com.example.Application` as the JAR entry point.
- The service listens on `0.0.0.0` and exposes `/health`.

## Run locally

```powershell
mvn test package
java -jar target/sample-java-multistage-1.0.0.jar
```

Then open `http://localhost:8080/health`.

Set a different port with the `PORT` environment variable:

```powershell
$env:PORT = "9090"
java -jar target/sample-java-multistage-1.0.0.jar
```
