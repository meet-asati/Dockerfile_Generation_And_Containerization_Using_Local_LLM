import express from 'express';

const app = express();
const port = Number(process.env.PORT ?? 3000);

app.get('/health', (_request, response) => {
  response.json({ status: 'ok' });
});

app.get('/', (_request, response) => {
  response.json({
    message: 'Hello from the multi-stage Node.js sample project',
    environment: process.env.NODE_ENV ?? 'development'
  });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server listening on port ${port}`);
});