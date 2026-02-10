<?php
// Function to send a POST request using cURL
function send_post_request($url, $data, $headers)
{
    $ch = curl_init($url);

    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_ENCODING, 'gzip, deflate, br, zstd'); // Handle compressed responses
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0');
    // It's good practice to set a timeout
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);

    $response = curl_exec($ch);
    
    // Check for cURL errors
    if (curl_errno($ch)) {
        $error_msg = curl_error($ch);
        curl_close($ch);
        return json_encode(['error' => 'cURL Error: ' . $error_msg]);
    }
    
    curl_close($ch);
    return $response;
}

$results = [];

// Check if the form has been submitted
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['codes'])) {
    $codes_input = trim($_POST['codes']);
    // Split the textarea content by new lines
    $codes_array = preg_split('/\r\n|\r|\n/', $codes_input);
    // Filter out any empty lines
    $codes_array = array_filter($codes_array, 'trim');

    $url = 'https://bandcamp.com/api/codes/1/verify';

    // Static headers from your request
    $headers = [
        'Content-Type: application/json',
        'Accept: */*',
        'X-Requested-With: XMLHttpRequest',
        'Origin: https://bandcamp.com',
        'Referer: https://bandcamp.com/yum',
        'Cookie: client_id=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772; cart_client_id=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772; __stripe_mid=f1211081-028b-4282-a904-60c8f307891d830cae; identity=7%09ORa7wa4GGV7uB64FjeNZia7wpV%2Bdp7NHJ6ddST7CU0g%3D%09%7B%22id%22%3A945599202%2C%22ex%22%3A0%7D; js_logged_in=1; playlimit_client_id=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772; _ga_R8D5ZS679J=GS2.1.s1752667751$o7$g0$t1752667751$j60$l0$h0; _ga=GA1.1.1320110872.1750821239; download_encoding=102; fan_visits=4383170z897682z9122604; cookie_preferences=%7B%22allow%22%3A%5B%22analytics%22%2C%22advertising%22%5D%2C%22version%22%3A1%7D; BACKENDID3=c2flexocentral-sscq-1; __stripe_sid=0199e172-c5e0-4d06-a90e-9515c66582420d8fc0; session=1%09r%3A%5B%2210394G0a4138079492x1759466180%22%2C%2210394G0i818798756x1759465993%22%2C%2210394G0a2616970060x1759465893%22%5D%09t%3A1759465890%09bp%3A1%09c%3A1; _rdt_uuid=1758901563471.3f624835-88f1-40b2-b3c8-6c4e78e2ebf5; _ga_MN4RN3JYWL=GS2.1.s1759465897$o170$g1$t1759466733$j60$l0$h0'
    ];

    foreach ($codes_array as $index => $code) {
        // Dynamic payload based on your structure
        $data = [
            "is_corp" => true,
            "band_id" => null,
            "platform_closed" => false,
            "hard_to_download" => false,
            "fan_logged_in" => true,
            "band_url" => null,
            "was_logged_out" => null,
            "is_https" => true,
            "ref_url" => null,
            "code" => trim($code), // The current code from the loop
            "crumb" => "|api/codes/1/verify|1759468523|HTNmuiFhDBD3w/Ylg7GlDUjCmi8="
        ];
        
        $response = send_post_request($url, $data, $headers);
        
        $results[] = [
            'number' => $index + 1,
            'code' => htmlspecialchars(trim($code)),
            'response' => htmlspecialchars($response)
        ];
    }
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bandcamp Code Verifier</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        .table-cell {
            word-break: break-all;
        }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">

    <div class="container mx-auto p-4 md:p-8 max-w-4xl">
        <div class="bg-white rounded-lg shadow-md p-6">
            <h1 class="text-2xl font-bold mb-4 text-center">Form Permintaan Verifikasi Kode</h1>
            
            <form action="" method="POST">
                <div class="mb-4">
                    <label for="codes" class="block text-gray-700 text-sm font-bold mb-2">Masukkan Kode (satu per baris):</label>
                    <textarea 
                        name="codes" 
                        id="codes" 
                        rows="10" 
                        class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                        placeholder="Contoh:&#10;xxxx-yyyy&#10;zzzz-aaaa&#10;bbbb-cccc"
                    ><?= isset($_POST['codes']) ? htmlspecialchars($_POST['codes']) : '' ?></textarea>
                </div>
                
                <div class="flex items-center justify-center">
                    <button 
                        type="submit"
                        class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                    >
                        Submit
                    </button>
                </div>
            </form>
        </div>

        <?php if (!empty($results)): ?>
        <div class="bg-white rounded-lg shadow-md p-6 mt-8">
            <h2 class="text-xl font-bold mb-4 text-center">Hasil</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full bg-white">
                    <thead class="bg-gray-200">
                        <tr>
                            <th class="w-1/12 py-2 px-4 text-left">No.</th>
                            <th class="w-3/12 py-2 px-4 text-left">Kode</th>
                            <th class="w-8/12 py-2 px-4 text-left">Respon</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($results as $result): ?>
                        <tr class="border-b hover:bg-gray-50">
                            <td class="py-2 px-4 table-cell"><?= $result['number'] ?></td>
                            <td class="py-2 px-4 table-cell"><?= $result['code'] ?></td>
                            <td class="py-2 px-4 table-cell text-sm"><pre class="whitespace-pre-wrap"><?= $result['response'] ?></pre></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endif; ?>

    </div>

</body>
</html>
