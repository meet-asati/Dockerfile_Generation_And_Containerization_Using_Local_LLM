# Sample PHP project

This small PHP service is intentionally structured for a multi-stage Dockerfile:

- The builder stage installs Composer dependencies and generates an optimized autoloader.
- The runtime stage can copy only `public/`, `src/`, and production `vendor/` files.
- The service listens on `0.0.0.0:8080` and exposes `/health` for container checks.

## Run locally

Install Composer dependencies, then start the PHP development server:

```powershell
composer install
composer run start
```

Open `http://localhost:8080/health` or `http://localhost:8080/`.

A typical multi-stage Dockerfile can use `composer:2` as a dependency builder and `php:8.3-cli` as the runtime image. The runtime command is:

```text
php -S 0.0.0.0:8080 -t public
```
