from fastapi import FastAPI

app = FastAPI(title="Sample Python API", version="0.1.0")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", tags=["system"])
def welcome() -> dict[str, str]:
    return {"service": "sample-python-api"}
