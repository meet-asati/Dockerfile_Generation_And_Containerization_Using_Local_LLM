# Sample Go service

This is a small HTTP service designed to be used as input for Dockerfile generation.
It has no third-party dependencies, so a Docker builder stage can compile a static binary
and a separate runtime stage can contain only that binary and the required certificates.

## Run locally

From this directory:

```text
go run ./cmd/server
```

The service listens on port `8080` by default. Set `PORT` to use another port.

```text
curl http://localhost:8080/
curl http://localhost:8080/healthz
```

## Build and test

```text
go test ./...
go build -trimpath -ldflags="-s -w" -o bin/server ./cmd/server
```

The expected container command is `./server`, and the container should expose port `8080`.