<?php
// bandcamp_checker.php
// Production-ready single file with HTML UI, AJAX API, config, logging, and robust error handling.

// ==============================
// CONFIG
// ==============================
const APP_NAME          = 'Bandcamp Code Checker';
const LOG_FILE          = __DIR__ . '/bandcamp_checker.log';
const MIN_DELAY_SEC     = 1;
const MAX_DELAY_SEC     = 5;
const CURL_TIMEOUT      = 25;
const CURL_HTTP2        = true;
const VERIFY_URL        = 'https://bandcamp.com/api/codes/1/verify';
const ENABLE_CSRF       = true;
const MAX_CODES         = 2000;
const MAX_CODE_LEN      = 256;
const MAX_CRUMB_LEN     = 512;
const MAX_CLIENT_ID_LEN = 128;
const MAX_SESSION_LEN   = 4096;
const JSON_DEPTH        = 512;

// ==============================
// Session, JSON helpers, logging
// ==============================
function start_secure_session(): void {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_set_cookie_params([
            'lifetime' => 0,
            'path'     => '/',
            'httponly' => true,
            'samesite' => 'Lax',
            'secure'   => (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on'),
        ]);
        session_start();
    }
}

function json_response(int $code, array $data): never {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_SLASHES);
    exit;
}

function now_ms(): int {
    return (int) floor(microtime(true) * 1000);
}

function log_line(array $fields): void {
    try {
        $fields['ts'] = date('c');
        $line = json_encode($fields, JSON_UNESCAPED_SLASHES);
        if ($line !== false) {
            error_log($line . PHP_EOL, 3, LOG_FILE);
        }
    } catch (Throwable $e) { /* ignore logging errors */ }
}

function make_csrf(): string {
    start_secure_session();
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf'];
}

function check_csrf(string $token): void {
    if (!ENABLE_CSRF) return;
    start_secure_session();
    if (empty($_SESSION['csrf']) || !hash_equals($_SESSION['csrf'], $token)) {
        json_response(419, ['ok' => false, 'error' => 'CSRF token invalid']);
    }
}

// ==============================
// Sanitizers
// ==============================
function sanitize_codes(string $raw): array {
    $raw = preg_replace("/\r\n|\r/", "\n", $raw);
    $lines = explode("\n", $raw);
    $out = [];
    foreach ($lines as $ln) {
        $c = trim($ln);
        if ($c === '') continue;
        if (mb_strlen($c) > MAX_CODE_LEN) $c = mb_substr($c, 0, MAX_CODE_LEN);
        $out[] = $c;
    }
    return $out;
}

// Remove CR/LF and semicolons to prevent header injection in Cookie
function sanitize_cookie_value(string $v, int $maxLen): string {
    $v = trim($v);
    $v = str_replace(["\r", "\n"], '', $v);
    $v = str_replace(';', '', $v);
    if (mb_strlen($v) > $maxLen) $v = mb_substr($v, 0, $maxLen);
    return $v;
}

// ==============================
// Core HTTP call
// ==============================
function call_bandcamp_verify(string $code, string $crumb, string $cookieHeader): array {
    $payload = [
        'is_corp'           => true,
        'band_id'           => null,
        'platform_closed'   => false,
        'hard_to_download'  => false,
        'fan_logged_in'     => true,
        'band_url'          => null,
        'was_logged_out'    => null,
        'is_https'          => true,
        'ref_url'           => null,
        'code'              => $code,
        'crumb'             => $crumb,
    ];

    $headers = [
        'Accept: */*',
        'Content-Type: application/json',
        'Origin: https://bandcamp.com',
        'Referer: https://bandcamp.com/yum',
        'X-Requested-With: XMLHttpRequest',
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
    ];

    $ch = curl_init(VERIFY_URL);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_POSTFIELDS     => json_encode($payload, JSON_UNESCAPED_SLASHES),
        CURLOPT_HEADER         => true,
        CURLOPT_TIMEOUT        => CURL_TIMEOUT,
        CURLOPT_ENCODING       => '',
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    if (CURL_HTTP2) {
        curl_setopt($ch, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2TLS);
    }
    if ($cookieHeader !== '') {
        curl_setopt($ch, CURLOPT_COOKIE, $cookieHeader);
    }

    $raw = curl_exec($ch);
    $errno = curl_errno($ch);
    $err   = curl_error($ch);
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    curl_close($ch);

    if ($raw === false) {
        return ['ok' => false, 'status' => 0, 'headers' => '', 'body' => null, 'error' => "cURL error {$errno}: {$err}"];
    }

    $respHeaders = substr($raw, 0, $headerSize);
    $respBody    = substr($raw, $headerSize);

    $json = json_decode($respBody, true, JSON_DEPTH);
    $jsonErr = json_last_error();

    return [
        'ok'      => $status >= 200 && $status < 300,
        'status'  => $status,
        'headers' => $respHeaders,
        'body'    => $jsonErr === JSON_ERROR_NONE ? $json : $respBody,
        'error'   => $jsonErr === JSON_ERROR_NONE ? null : 'Non JSON response',
    ];
}

// ==============================
// Router: AJAX endpoint
// ==============================
if (isset($_GET['api']) && $_GET['api'] === 'verify' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $t0 = now_ms();

    $ct = $_SERVER['CONTENT_TYPE'] ?? '';
    if (stripos($ct, 'application/json') === false) {
        json_response(415, ['ok' => false, 'error' => 'Unsupported content type']);
    }

    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true, JSON_DEPTH);
    if (!is_array($data)) {
        json_response(400, ['ok' => false, 'error' => 'Invalid JSON']);
    }

    $csrf       = (string)($data['csrf'] ?? '');
    $code       = (string)($data['code'] ?? '');
    $crumb      = (string)($data['crumb'] ?? '');
    $client_id  = (string)($data['client_id'] ?? '');
    $sessionVal = (string)($data['session'] ?? '');
    $idx        = (int)($data['index'] ?? -1);
    $total      = (int)($data['total'] ?? -1);

    check_csrf($csrf);

    if ($code === '') {
        json_response(400, ['ok' => false, 'error' => 'Missing code']);
    }
    if ($crumb === '' || mb_strlen($crumb) > MAX_CRUMB_LEN) {
        json_response(400, ['ok' => false, 'error' => 'Invalid crumb']);
    }
    if ($client_id === '' || mb_strlen($client_id) > MAX_CLIENT_ID_LEN) {
        json_response(400, ['ok' => false, 'error' => 'Invalid client_id']);
    }
    if ($sessionVal === '' || mb_strlen($sessionVal) > MAX_SESSION_LEN) {
        json_response(400, ['ok' => false, 'error' => 'Invalid session']);
    }

    $client_id  = sanitize_cookie_value($client_id, MAX_CLIENT_ID_LEN);
    $sessionVal = sanitize_cookie_value($sessionVal, MAX_SESSION_LEN);
    // Susun header Cookie minimum sesuai permintaan kamu
    $cookieHeader = "client_id={$client_id}; session={$sessionVal}";

    $delay = random_int(MIN_DELAY_SEC, MAX_DELAY_SEC);
    sleep($delay);

    $res = call_bandcamp_verify($code, $crumb, $cookieHeader);

    $t1 = now_ms();
    log_line([
        'event'      => 'verify',
        'ip'         => $_SERVER['REMOTE_ADDR'] ?? 'unknown',
        'ua'         => substr($_SERVER['HTTP_USER_AGENT'] ?? 'unknown', 0, 200),
        'status'     => $res['status'],
        'index'      => $idx,
        'total'      => $total,
        'code'       => $code,
        'elapsed_ms' => $t1 - $t0,
        'delay_sec'  => $delay,
        'ok'         => $res['ok'],
        'err'        => $res['error'],
        // Jangan log nilai cookie mentah
    ]);

    $bodyOut = is_array($res['body']) ? $res['body'] : (string)$res['body'];

    json_response(200, [
        'ok'         => $res['ok'],
        'status'     => $res['status'],
        'delay_sec'  => $delay,
        'elapsed_ms' => $t1 - $t0,
        'body'       => $bodyOut,
    ]);
}

// ==============================
// HTML UI
// ==============================
$csrf = make_csrf();
?>
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title><?php echo htmlspecialchars(APP_NAME); ?></title>
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { padding: 24px; }
    textarea, code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    .table-wrap { max-height: 55vh; overflow: auto; }
    .resp-cell { max-width: 720px; white-space: pre-wrap; word-break: break-word; }
    .fixed-footer { position: sticky; bottom: 0; background: #fff; padding-top: 12px; }
  </style>
</head>
<body>
<div class="container">
  <h1 class="mb-3"><?php echo htmlspecialchars(APP_NAME); ?></h1>

  <div class="alert alert-warning">
    Pakai cookie dari sesi login yang sama. Masukkan <strong>client_id</strong> dan <strong>session</strong>. Simpan file ini di host yang kamu kontrol.
  </div>

  <form id="cfgForm" class="mb-4" onsubmit="return false;">
    <div class="row g-3">
      <div class="col-12">
        <label for="codes" class="form-label">Daftar Kode</label>
        <textarea id="codes" class="form-control" rows="8" placeholder="Satu kode per baris"></textarea>
        <div class="form-text">Maksimal <?php echo MAX_CODES; ?> baris.</div>
      </div>

      <div class="col-md-6">
        <label for="crumb" class="form-label">Crumb</label>
        <input id="crumb" type="text" class="form-control" maxlength="<?php echo MAX_CRUMB_LEN; ?>"
               placeholder="|api/codes/1/verify|1759468523|HTNmuiFhDBD3w/Ylg7GlDUjCmi8=">
      </div>

      <div class="col-md-3">
        <label for="client_id" class="form-label">client_id</label>
        <input id="client_id" type="text" class="form-control" maxlength="<?php echo MAX_CLIENT_ID_LEN; ?>"
               placeholder="2F468B34...">
      </div>

      <div class="col-md-3">
        <label for="session" class="form-label">session</label>
        <input id="session" type="text" class="form-control" maxlength="<?php echo MAX_SESSION_LEN; ?>"
               placeholder='1%09r%3A%5B%22...%22%5D%09t%3A...'>
      </div>
    </div>

    <div class="mt-3 d-flex gap-2">
      <button id="btnStart" class="btn btn-primary">Mulai Proses</button>
      <button id="btnStop"  class="btn btn-outline-danger" disabled>Hentikan</button>
      <button id="btnExport" class="btn btn-outline-secondary" type="button" disabled>Export CSV</button>
    </div>
  </form>

  <div class="mb-2">
    <div class="progress" role="progressbar" aria-label="Progress" aria-valuemin="0" aria-valuemax="100">
      <div id="progBar" class="progress-bar" style="width: 0%">0%</div>
    </div>
    <div id="statusLine" class="form-text mt-1">Siap.</div>
  </div>

  <div class="table-wrap">
    <table class="table table-striped table-bordered align-middle" id="resultTable">
      <thead class="table-light">
      <tr>
        <th style="width:80px;">No</th>
        <th style="width:240px;">Kode</th>
        <th style="width:120px;">HTTP</th>
        <th style="width:120px;">Delay</th>
        <th style="width:140px;">Elapsed</th>
        <th>Respon</th>
      </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="fixed-footer">
    <hr>
    <small class="text-muted">
      Log ke <code><?php echo htmlspecialchars(LOG_FILE); ?></code>. Delay acak <?php echo MIN_DELAY_SEC; ?> sampai <?php echo MAX_DELAY_SEC; ?> detik di server.
    </small>
  </div>
</div>

<script>
(function(){
  const csrf = <?php echo json_encode($csrf, JSON_UNESCAPED_SLASHES); ?>;

  const elCodes    = document.getElementById('codes');
  const elCrumb    = document.getElementById('crumb');
  const elClientId = document.getElementById('client_id');
  const elSession  = document.getElementById('session');
  const btnStart   = document.getElementById('btnStart');
  const btnStop    = document.getElementById('btnStop');
  const btnExport  = document.getElementById('btnExport');
  const progBar    = document.getElementById('progBar');
  const statusLine = document.getElementById('statusLine');
  const tbody      = document.querySelector('#resultTable tbody');

  let stopFlag = false;
  let results  = [];

  function parseCodes(raw) {
    return raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  }

  function setProgress(done, total) {
    const pct = total > 0 ? Math.round(done * 100 / total) : 0;
    progBar.style.width = pct + '%';
    progBar.textContent = pct + '%';
    progBar.setAttribute('aria-valuenow', String(pct));
  }

  function setStatus(txt) { statusLine.textContent = txt; }

  function appendRow(index, code, http, delaySec, elapsedMs, body) {
    const tr = document.createElement('tr');
    const c1 = document.createElement('td'); c1.textContent = String(index+1);
    const c2 = document.createElement('td'); c2.innerHTML  = '<code></code>'; c2.querySelector('code').textContent = code;
    const c3 = document.createElement('td'); c3.textContent = String(http);
    const c4 = document.createElement('td'); c4.textContent = delaySec + ' s';
    const c5 = document.createElement('td'); c5.textContent = elapsedMs + ' ms';
    const c6 = document.createElement('td'); c6.className = 'resp-cell'; c6.innerHTML = '<small></small>';
    const s = c6.querySelector('small');
    try {
      if (typeof body === 'object') s.textContent = JSON.stringify(body);
      else s.textContent = String(body ?? '');
    } catch { s.textContent = String(body ?? ''); }
    tr.append(c1,c2,c3,c4,c5,c6);
    tbody.appendChild(tr);
  }

  async function verifyOne(index, total, code, crumb, client_id, sessionVal) {
    const resp = await fetch('?api=verify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ csrf, index, total, code, crumb, client_id, session: sessionVal })
    });
    const http = resp.status;
    let json = null;
    try { json = await resp.json(); }
    catch { return { http, ok: false, delay_sec: 0, elapsed_ms: 0, body: 'Invalid JSON from server' }; }
    return { http, ...json };
  }

  function sanitizeCsvField(v) {
    if (v == null) return '';
    let s = typeof v === 'object' ? JSON.stringify(v) : String(v);
    if (s.includes('"') || s.includes(',') || s.includes('\n')) {
      s = '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function exportCsv(rows) {
    const header = ['no','code','http','delay_sec','elapsed_ms','response'];
    const lines = [header.join(',')];
    rows.forEach((r, i) => {
      const line = [
        String(i+1),
        sanitizeCsvField(r.code),
        String(r.http ?? ''),
        String(r.delay_sec ?? ''),
        String(r.elapsed_ms ?? ''),
        sanitizeCsvField(r.body),
      ].join(',');
      lines.push(line);
    });
    const blob = new Blob([lines.join('\n')], {type: 'text/csv;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'bandcamp_results.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  btnStart.addEventListener('click', async () => {
    const codes     = parseCodes(elCodes.value);
    const crumb     = elCrumb.value.trim();
    const client_id = elClientId.value.trim();
    const session   = elSession.value.trim();

    if (codes.length === 0) { setStatus('Tidak ada kode'); return; }
    if (codes.length > <?php echo MAX_CODES; ?>) { setStatus('Terlalu banyak kode'); return; }
    if (!crumb) { setStatus('Crumb kosong'); return; }
    if (!client_id) { setStatus('client_id kosong'); return; }
    if (!session) { setStatus('session kosong'); return; }

    stopFlag = false;
    results = [];
    tbody.innerHTML = '';
    setProgress(0, codes.length);
    setStatus('Memulai...');

    btnStart.disabled = true;
    btnStop.disabled  = false;
    btnExport.disabled= true;

    for (let i = 0; i < codes.length; i++) {
      if (stopFlag) { setStatus('Dihentikan oleh pengguna'); break; }

      setStatus(`Memproses ${i+1}/${codes.length}...`);
      try {
        const res = await verifyOne(i, codes.length, codes[i], crumb, client_id, session);
        appendRow(i, codes[i], res.status ?? res.http ?? 0, res.delay_sec ?? 0, res.elapsed_ms ?? 0, res.body);
        results.push({ code: codes[i], http: res.status ?? res.http ?? 0, delay_sec: res.delay_sec ?? 0, elapsed_ms: res.elapsed_ms ?? 0, body: res.body });
      } catch {
        appendRow(i, codes[i], 0, 0, 0, 'Request error');
        results.push({ code: codes[i], http: 0, delay_sec: 0, elapsed_ms: 0, body: 'Request error' });
      }
      setProgress(i+1, codes.length);
    }

    btnStart.disabled = false;
    btnStop.disabled  = true;
    btnExport.disabled= results.length > 0 ? false : true;
    setStatus('Selesai.');
  });

  btnStop.addEventListener('click', () => {
    stopFlag = true;
    btnStop.disabled = true;
  });

  btnExport.addEventListener('click', () => {
    if (results.length === 0) return;
    exportCsv(results);
  });
})();
</script>
</body>
</html>
