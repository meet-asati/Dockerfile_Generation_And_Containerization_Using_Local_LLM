<?php

declare(strict_types=1);

namespace App;

use Monolog\Handler\StreamHandler;
use Monolog\Logger;

final class App
{
    private Logger $logger;

    public function __construct()
    {
        $this->logger = new Logger('sample-php-service');
        $this->logger->pushHandler(new StreamHandler('php://stderr', Logger::INFO));
    }

    /**
     * @return array<string, mixed>
     */
    public function respond(string $path): array
    {
        $this->logger->info('Handling request', ['path' => $path]);

        return match ($path) {
            '/health' => [
                'status' => 'ok',
                'service' => 'sample-php-service',
            ],
            '/' => [
                'message' => 'Hello from the multi-stage PHP sample project',
                'environment' => getenv('APP_ENV') ?: 'development',
            ],
            default => [
                'error' => 'Not found',
            ],
        };
    }

    public function statusCode(string $path): int
    {
        return $path === '/' || $path === '/health' ? 200 : 404;
    }
}
