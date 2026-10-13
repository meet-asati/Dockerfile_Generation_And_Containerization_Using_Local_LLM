<?php

declare(strict_types=1);

require dirname(__DIR__) . '/vendor/autoload.php';

use App\App;

$app = new App();
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$statusCode = $app->statusCode($path);

http_response_code($statusCode);
header('Content-Type: application/json');
echo json_encode($app->respond($path), JSON_THROW_ON_ERROR) . PHP_EOL;
