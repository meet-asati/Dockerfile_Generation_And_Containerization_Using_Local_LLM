# Sample Node.js project

This TypeScript service is intentionally structured for a multi-stage Dockerfile:

- The build stage installs all dependencies and compiles `src/` into `dist/`.
- The runtime stage can install only production dependencies and copy `dist/`.
- The service listens on `0.0.0.0` and exposes a `/health` endpoint.

## Run locally

```powershell
npm install
npm run build
npm start
```

Then open `http://localhost:3000/health`.

For development with the TypeScript runner:

```powershell
npm install
npm run dev
```
