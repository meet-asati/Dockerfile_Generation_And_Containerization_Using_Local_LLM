# Sample Python API

This is a small FastAPI service designed to provide enough structure for generating and testing a multi-stage Dockerfile.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn sample_api.main:app --host 0.0.0.0 --port 8000
```

The service exposes `GET /health` and `GET /`. Interactive API documentation is available at `/docs`.

## Test

```powershell
pytest
```

## Multi-stage build signals

- `pyproject.toml` describes the installable application package.
- `requirements.txt` contains production dependencies only.
- `requirements-dev.txt` contains build and test tooling.
- The `src/` layout keeps application code separate from project metadata and tests.

A generated Dockerfile can use a builder stage to build a wheel or install dependencies, then copy only the application and runtime dependencies into a smaller Python runtime stage.
