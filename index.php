<?php
/**
 * Bandcamp Code Verificator (PHP Rewrite)
 * Features: Auto-Crumb Extraction, Native cURL WAF Bypass, AJAX Processing
 */

session_start();

// Constants
const VERIFY_URL = 'https://bandcamp.com/api/codes/1/verify';
const YUM_URL = 'https://bandcamp.com/yum';
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0';

// Helpers
function send_json_response($status, $data)
{
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

// 1. Auto-Crumb extraction endpoint
if (isset($_GET['api']) && $_GET['api'] === 'get_crumb') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST')
        send_json_response(405, ['error' => 'Method not allowed']);

    $input = json_decode(file_get_contents('php://input'), true);
    $client_id = trim($input['client_id'] ?? '');
    $session = trim($input['session'] ?? '');
    $identity = trim($input['identity'] ?? '');

    if (!$client_id || !$session || !$identity) {
        send_json_response(400, ['error' => 'client_id, session, and identity are required for auto-extraction']);
    }

    $cookieHeader = "client_id={$client_id}; session={$session}; identity={$identity}; js_logged_in=1";

    $ch = curl_init(YUM_URL);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'User-Agent: ' . USER_AGENT,
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language: en-US,en;q=0.9',
            'Cookie: ' . $cookieHeader
        ],
        CURLOPT_TIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => true
    ]);

    $html = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($status !== 200 || !$html) {
        send_json_response(500, ['error' => "Failed to fetch bandcamp.com/yum. Status: {$status}"]);
    }

    // Parse crumb from data-blob or script tag
    // Looking for &quot;crumb&quot;:&quot;([^&]+)&quot;
    if (preg_match('/&quot;crumb&quot;:&quot;([^&"\']+)&quot;/', $html, $matches)) {
        send_json_response(200, ['crumb' => $matches[1]]);
    }

    if (preg_match('/[\'"]crumb[\'"]\s*:\s*[\'"]([^"\']+)[\'"]/', $html, $matches)) {
        send_json_response(200, ['crumb' => $matches[1]]);
    }

    send_json_response(500, ['error' => 'Crumb not found in page. Ensure cookies are correct and not expired.']);
}

// 2. Code Verification endpoint
if (isset($_GET['api']) && $_GET['api'] === 'verify') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST')
        send_json_response(405, ['error' => 'Method not allowed']);

    $input = json_decode(file_get_contents('php://input'), true);
    $code = trim($input['code'] ?? '');
    $crumb = trim($input['crumb'] ?? '');
    $client_id = trim($input['client_id'] ?? '');
    $session = trim($input['session'] ?? '');
    $identity = trim($input['identity'] ?? '');

    if (!$code || !$crumb || !$client_id || !$session || !$identity) {
        send_json_response(400, ['ok' => false, 'error' => 'Missing required parameters']);
    }

    $cookieHeader = "client_id={$client_id}; session={$session}; identity={$identity}; js_logged_in=1";

    $payload = [
        'is_corp' => true,
        'band_id' => null,
        'platform_closed' => false,
        'hard_to_download' => false,
        'fan_logged_in' => true,
        'band_url' => null,
        'was_logged_out' => null,
        'is_https' => true,
        'ref_url' => null,
        'code' => $code,
        'crumb' => $crumb,
    ];

    $ch = curl_init(VERIFY_URL);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Accept: */*',
            'Origin: https://bandcamp.com',
            'Referer: https://bandcamp.com/yum',
            'X-Requested-With: XMLHttpRequest',
            'User-Agent: ' . USER_AGENT,
            'Cookie: ' . $cookieHeader
        ],
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_TIMEOUT => 25,
        CURLOPT_SSL_VERIFYPEER => true
    ]);

    // Attempt to force HTTP/2 if available (which was the secret sauce)
    if (defined('CURL_HTTP_VERSION_2TLS')) {
        curl_setopt($ch, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2TLS);
    }

    $t0 = microtime(true);
    $raw = curl_exec($ch);
    $t1 = microtime(true);

    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);

    if ($raw === false) {
        send_json_response(500, ['ok' => false, 'error' => "cURL error: {$err}"]);
    }

    $json = json_decode($raw, true);

    send_json_response(200, [
        'ok' => ($status >= 200 && $status < 300),
        'status' => $status,
        'delay_sec' => 0,
        'elapsed_ms' => round(($t1 - $t0) * 1000),
        'body' => $json ?: $raw
    ]);
}
?>
<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bandcamp Code Verificator (PHP Rewrite)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: #f3f4f6;
        }

        .table-cell {
            word-break: break-all;
        }

        .glass-panel {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
        }
    </style>
</head>

<body class="text-gray-800 min-h-screen pb-16">
    <div class="container mx-auto p-4 md:p-8 max-w-5xl">

        <div class="bg-blue-600 text-white rounded-t-xl p-6 shadow-md">
            <h1 class="text-3xl font-bold">Bandcamp Code Verificator</h1>
            <p class="mt-2 opacity-80">Auto-extrak crumb & verifikasi kode berkecepatan tinggi tanpa hambatan 403 WAF.
            </p>
        </div>

        <div class="glass-panel p-6 rounded-b-xl shadow-md border-x border-b border-gray-200">
            <form id="appForm" onsubmit="return false;" class="space-y-6">
                <!-- Credentials Section -->
                <div>
                    <h2 class="text-lg font-bold text-gray-700 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z">
                            </path>
                        </svg>
                        Bandcamp Session Cookies
                    </h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-1">client_id</label>
                            <input type="text" id="client_id"
                                class="w-full px-3 py-2 border rounded shadow-sm focus:ring focus:ring-blue-200 focus:border-blue-500"
                                placeholder="2F468B..." required autocomplete="off">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-1">session</label>
                            <input type="text" id="session"
                                class="w-full px-3 py-2 border rounded shadow-sm focus:ring focus:ring-blue-200 focus:border-blue-500"
                                placeholder="1%09r%3A..." required autocomplete="off">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-1">identity</label>
                            <input type="text" id="identity"
                                class="w-full px-3 py-2 border rounded shadow-sm focus:ring focus:ring-blue-200 focus:border-blue-500"
                                placeholder="7%09ORa7..." required autocomplete="off">
                        </div>
                    </div>
                </div>

                <!-- Crumb Output -->
                <div class="bg-gray-50 p-4 border border-gray-200 rounded-lg flex items-center gap-4">
                    <div class="flex-1">
                        <label class="block text-sm font-semibold text-gray-700 mb-1">Crumb Data</label>
                        <input type="text" id="crumb" readonly
                            class="w-full md:w-2/3 px-3 py-2 border rounded bg-gray-100 text-gray-500 select-all"
                            placeholder="Crumb akan diekstrak otomatis sebelum verifikasi...">
                    </div>
                    <div class="pt-6">
                        <button type="button" id="btnExtractCrumb"
                            class="bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-semibold py-2 px-4 border border-indigo-300 rounded shadow-sm transition">
                            Ekstrak Crumb Manual
                        </button>
                    </div>
                </div>

                <!-- Codes List -->
                <div>
                    <h2 class="text-lg font-bold text-gray-700 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2">
                            </path>
                        </svg>
                        Daftar Kode
                    </h2>
                    <textarea id="codes" rows="8"
                        class="w-full px-3 py-2 border rounded shadow-sm font-mono text-sm focus:ring focus:ring-blue-200 focus:border-blue-500"
                        placeholder="Paste kode Anda di sini (satu kode per baris)&#10;xxxx-yyyy&#10;zzzz-aaaa&#10;bbbb-cccc"
                        required></textarea>
                </div>

                <!-- Actions & Progress -->
                <div class="border-t pt-4">
                    <div class="flex items-center gap-3 mb-4">
                        <button id="btnStart" type="button"
                            class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-6 rounded shadow-md transition">Mulai
                            Verifikasi</button>
                        <button id="btnStop" type="button"
                            class="bg-red-500 hover:bg-red-600 text-white font-bold py-2.5 px-6 rounded shadow-md transition hidden">Batalkan</button>
                        <button id="btnExport" type="button"
                            class="bg-green-600 hover:bg-green-700 text-white font-bold py-2.5 px-6 rounded shadow-md transition hidden">Export
                            CSV</button>
                    </div>

                    <div id="progressContainer" class="hidden">
                        <div class="flex justify-between text-sm font-semibold text-gray-600 mb-1">
                            <span id="statusText">Memproses...</span>
                            <span id="progressPercentage">0%</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2.5">
                            <div id="progressBar" class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                                style="width: 0%"></div>
                        </div>
                    </div>

                </div>
            </form>
        </div>

        <!-- Results Table -->
        <div id="resultsContainer" class="glass-panel mt-6 p-0 rounded-xl shadow-md overflow-hidden hidden">
            <div class="bg-gray-100 px-6 py-4 border-b font-bold text-gray-700">Hasil Verifikasi</div>
            <div class="overflow-x-auto">
                <table class="min-w-full text-sm text-left whitespace-nowrap">
                    <thead class="text-xs text-gray-700 uppercase bg-gray-50 border-b">
                        <tr>
                            <th scope="col" class="px-6 py-3 w-16">No</th>
                            <th scope="col" class="px-6 py-3 w-32">Kode</th>
                            <th scope="col" class="px-6 py-3 w-24">HTTP</th>
                            <th scope="col" class="px-6 py-3 w-32">Elapse (MS)</th>
                            <th scope="col" class="px-6 py-3">Respons Server</th>
                        </tr>
                    </thead>
                    <tbody id="resultsTbody" class="divide-y divide-gray-200">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // State variables
        let stopFlag = false;
        let resultsExport = [];

        // Local Storage Hydration
        document.addEventListener("DOMContentLoaded", () => {
            const fields = ['client_id', 'session', 'identity'];
            fields.forEach(f => {
                if (localStorage.getItem('bc_' + f)) document.getElementById(f).value = localStorage.getItem('bc_' + f);
                document.getElementById(f).addEventListener('change', (e) => localStorage.setItem('bc_' + f, e.target.value.trim()));
            });
        });

        const DOM = {
            codes: document.getElementById('codes'),
            crumb: document.getElementById('crumb'),
            clientId: document.getElementById('client_id'),
            session: document.getElementById('session'),
            identity: document.getElementById('identity'),
            btnStart: document.getElementById('btnStart'),
            btnStop: document.getElementById('btnStop'),
            btnExport: document.getElementById('btnExport'),
            btnExtractCrumb: document.getElementById('btnExtractCrumb'),
            progCont: document.getElementById('progressContainer'),
            progBar: document.getElementById('progressBar'),
            progPct: document.getElementById('progressPercentage'),
            statusTxt: document.getElementById('statusText'),
            resCont: document.getElementById('resultsContainer'),
            tbody: document.getElementById('resultsTbody')
        };

        const updateProgress = (current, total, text) => {
            DOM.progCont.classList.remove('hidden');
            const pct = Math.round((current / total) * 100);
            DOM.progBar.style.width = pct + '%';
            DOM.progPct.textContent = pct + '%';
            DOM.statusTxt.textContent = text || `Memproses ${current} dari ${total}...`;
        };

        const delay = ms => new Promise(res => setTimeout(res, ms));

        const getCrumb = async () => {
            const req = {
                client_id: DOM.clientId.value.trim(),
                session: DOM.session.value.trim(),
                identity: DOM.identity.value.trim()
            };
            if (!req.client_id || !req.session || !req.identity) throw new Error("Semua cookie (client_id, session, identity) wajib diisi!");

            DOM.btnExtractCrumb.textContent = "Loading...";
            DOM.btnExtractCrumb.disabled = true;

            try {
                const res = await fetch("?api=get_crumb", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(req)
                });
                const data = await res.json();

                if (res.status === 200 && data.crumb) {
                    DOM.crumb.value = data.crumb;
                    DOM.btnExtractCrumb.textContent = "Crumb Didapat ✓";
                    return data.crumb;
                } else {
                    throw new Error(data.error || "Gagal mendapatkan crumb");
                }
            } finally {
                DOM.btnExtractCrumb.disabled = false;
            }
        };

        DOM.btnExtractCrumb.addEventListener('click', () => {
            getCrumb().catch(err => alert("Error: " + err.message));
        });

        const verifyCode = async (code, crumb) => {
            const payload = {
                code: code,
                crumb: crumb,
                client_id: DOM.clientId.value.trim(),
                session: DOM.session.value.trim(),
                identity: DOM.identity.value.trim()
            };

            const res = await fetch("?api=verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok && res.status !== 403) { // 403 usually returns JSON error from API, that's fine to pass through
                const text = await res.text();
                try { return JSON.parse(text); } catch (e) { return { status: res.status, ok: false, body: text }; }
            }
            return await res.json();
        };

        DOM.btnStart.addEventListener('click', async () => {
            const codesStr = DOM.codes.value.trim();
            if (!codesStr) return alert("Masukkan minimal satu kode!");

            const codeArray = codesStr.split(/\r?\n/).map(c => c.trim()).filter(Boolean);

            // Setup UI
            stopFlag = false;
            resultsExport = [];
            DOM.btnStart.classList.add('hidden');
            DOM.btnStop.classList.remove('hidden');
            DOM.btnExport.classList.add('hidden');
            DOM.tbody.innerHTML = '';
            DOM.resCont.classList.remove('hidden');

            try {
                // Auto-fetch crumb if missing
                let crumb = DOM.crumb.value.trim();
                if (!crumb) {
                    updateProgress(0, codeArray.length, "Menarik Crumb Otomatis...");
                    crumb = await getCrumb();
                }

                for (let i = 0; i < codeArray.length; i++) {
                    if (stopFlag) {
                        updateProgress(i, codeArray.length, "Dibatalkan oleh Pengguna");
                        break;
                    }

                    updateProgress(i, codeArray.length, `Memverifikasi ${codeArray[i]}...`);

                    try {
                        const result = await verifyCode(codeArray[i], crumb);

                        // Add delay randomly to avoid rate limits (2 to 4 seconds)
                        if (i < codeArray.length - 1) {
                            const sleepTime = Math.floor(Math.random() * 2000) + 2000;
                            await delay(sleepTime);
                        }

                        // Render to table
                        const tr = document.createElement('tr');
                        tr.className = "hover:bg-gray-50 border-b";

                        let bgStatus = result.ok ? "text-green-600 bg-green-100" : "text-red-600 bg-red-100";
                        if (result.status === 200) bgStatus = "text-green-600 bg-green-100";
                        else if (result.status === 403) bgStatus = "text-yellow-600 bg-yellow-100";

                        tr.innerHTML = `
                        <td class="px-6 py-4">${i + 1}</td>
                        <td class="px-6 py-4 font-mono font-bold">${codeArray[i]}</td>
                        <td class="px-6 py-4"><span class="px-2 py-1 rounded text-xs font-semibold ${bgStatus}">${result.status || 'ERR'}</span></td>
                        <td class="px-6 py-4 text-gray-500">${result.elapsed_ms || 0}</td>
                        <td class="px-6 py-4 table-cell font-mono text-xs text-gray-600">
                            <pre class="whitespace-pre-wrap">${typeof result.body === 'object' ? JSON.stringify(result.body, null, 2) : String(result.body)}</pre>
                        </td>
                    `;
                        DOM.tbody.appendChild(tr);

                        resultsExport.push({
                            no: i + 1, code: codeArray[i], http: result.status,
                            elapsed_ms: result.elapsed_ms,
                            response: typeof result.body === 'object' ? JSON.stringify(result.body) : result.body
                        });

                    } catch (e) {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `<td colspan="5" class="px-6 py-4 text-red-500">Error: ${e.message}</td>`;
                        DOM.tbody.appendChild(tr);
                    }

                    updateProgress(i + 1, codeArray.length, `Selesai ${i + 1}`);
                }

                if (!stopFlag) updateProgress(codeArray.length, codeArray.length, "Semua kode selesai dicek");

            } catch (err) {
                updateProgress(0, codeArray.length, "Gagal: " + err.message);
                alert("Error: " + err.message);
            } finally {
                DOM.btnStart.classList.remove('hidden');
                DOM.btnStop.classList.add('hidden');
                if (resultsExport.length > 0) DOM.btnExport.classList.remove('hidden');
            }
        });

        DOM.btnStop.addEventListener('click', () => {
            stopFlag = true;
            DOM.btnStop.disabled = true;
            DOM.btnStop.textContent = "Membatalkan...";
        });

        DOM.btnExport.addEventListener('click', () => {
            if (resultsExport.length === 0) return;
            const header = ["No", "Kode", "HTTP", "Elapse MS", "Response"];
            const csvRows = [header.join(",")];

            for (const row of resultsExport) {
                const rowValues = [
                    row.no,
                    row.code,
                    row.http,
                    row.elapsed_ms,
                    `"${String(row.response).replace(/"/g, '""')}"`
                ];
                csvRows.push(rowValues.join(","));
            }

            const blob = new Blob([csvRows.join("\n")], { type: 'text/csv' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `Bandcamp_Verify_${new Date().getTime()}.csv`;
            a.click();
        });

    </script>
</body>

</html>