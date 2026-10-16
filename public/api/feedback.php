<?php
declare(strict_types=1);

date_default_timezone_set('Asia/Shanghai');

const MAX_NOTES = 2000;
const MAX_TEXT = 2000;
const MAX_NAME = 40;

$root = dirname(__DIR__);
$dataFile = $root . '/data/feedback.json';
$jsFile = $root . '/data/feedback.js';
$lockFile = $root . '/data/.feedback.lock';

function end_json(int $code, array $payload): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function clean_text($value, int $limit, bool $keepLines): ?string
{
    if (!is_string($value)) {
        $value = '';
    }
    $value = str_replace(["\r\n", "\r"], "\n", $value);
    $chars = preg_split('//u', $value, -1, PREG_SPLIT_NO_EMPTY);
    if ($chars === false) {
        return null;
    }
    $out = '';
    foreach ($chars as $ch) {
        if ($ch === "\n") {
            $out .= $keepLines ? "\n" : ' ';
            continue;
        }
        if ($ch === "\t") {
            $out .= ' ';
            continue;
        }
        $ord = mb_ord($ch, 'UTF-8');
        if ($ord < 32 || $ord === 127) {
            continue;
        }
        $out .= $ch;
    }
    if ($keepLines) {
        $text = trim($out);
    } else {
        $text = trim(preg_replace('/\s+/u', ' ', $out) ?? '');
    }
    if (mb_strlen($text, 'UTF-8') > $limit) {
        return null;
    }
    return $text;
}

function client_ip(): string
{
    $raw = (string) ($_SERVER['REMOTE_ADDR'] ?? '');
    if (str_starts_with($raw, '::ffff:')) {
        $raw = substr($raw, 7);
    }
    $raw = trim($raw);
    if (strlen($raw) > 64) {
        $raw = substr($raw, 0, 64);
    }
    return $raw;
}

function load_notes(string $dataFile): ?array
{
    if (!is_file($dataFile)) {
        return [];
    }
    $raw = file_get_contents($dataFile);
    if ($raw === false) {
        return null;
    }
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        return null;
    }
    return $data;
}

function save_notes(string $dataFile, string $jsFile, array $notes): bool
{
    $flags = JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT;
    $payload = json_encode(array_values($notes), $flags);
    $js = json_encode(array_values($notes), $flags);
    if ($payload === false || $js === false) {
        return false;
    }
    $payload .= "\n";
    $jsBody = "window.ZHISHI_FEEDBACK = " . $js . ";\n";
    $tmp = $dataFile . '.tmp';
    $tmpJs = $jsFile . '.tmp';
    if (file_put_contents($tmp, $payload, LOCK_EX) === false) {
        return false;
    }
    if (!rename($tmp, $dataFile)) {
        @unlink($tmp);
        return false;
    }
    if (file_put_contents($tmpJs, $jsBody, LOCK_EX) === false) {
        return false;
    }
    if (!rename($tmpJs, $jsFile)) {
        @unlink($tmpJs);
        return false;
    }
    return true;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method === 'OPTIONS') {
    http_response_code(204);
    header('Allow: GET, POST, OPTIONS');
    exit;
}

$lock = fopen($lockFile, 'c');
if ($lock === false) {
    end_json(500, ['error' => '白板读不出来。']);
}
flock($lock, LOCK_EX);

if ($method === 'GET') {
    $notes = load_notes($dataFile);
    if ($notes === null) {
        flock($lock, LOCK_UN);
        fclose($lock);
        end_json(500, ['error' => '白板读不出来。']);
    }
    $ip = client_ip();
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(200, ['notes' => $notes, 'ip' => $ip]);
}

if ($method !== 'POST') {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(404, ['error' => '没有这个地址。']);
}

$length = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($length <= 0 || $length > 8192) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '内容没送成。']);
}
$raw = file_get_contents('php://input');
if ($raw === false) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '内容没送成。']);
}
$payload = json_decode($raw, true);
if (!is_array($payload)) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '内容没送成。']);
}

$name = clean_text($payload['name'] ?? '', MAX_NAME, false);
$text = clean_text($payload['text'] ?? '', MAX_TEXT, true);
if ($name === null) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '称呼太长。']);
}
if ($text === null) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '内容太长。']);
}
if ($text === '') {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(400, ['error' => '写点内容再送。']);
}

$note = [
    'id' => date('YmdHis') . '-' . bin2hex(random_bytes(3)),
    'name' => $name,
    'text' => $text,
    'ip' => client_ip(),
    'at' => date('c'),
];
$notes = load_notes($dataFile);
if ($notes === null) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(500, ['error' => '白板读不出来。']);
}
$notes[] = $note;
if (count($notes) > MAX_NOTES) {
    $notes = array_slice($notes, -MAX_NOTES);
}
if (!save_notes($dataFile, $jsFile, $notes)) {
    flock($lock, LOCK_UN);
    fclose($lock);
    end_json(500, ['error' => '白板没有写成。']);
}
$ip = client_ip();
flock($lock, LOCK_UN);
fclose($lock);
end_json(200, ['notes' => $notes, 'ip' => $ip]);
