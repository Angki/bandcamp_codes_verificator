# 🤖 Smart Auto-Extraction Feature

## Fitur Baru: Auto-Extract Credentials dari Browser!

Sistem sekarang bisa **otomatis mengambil credentials dari browser** Anda yang sedang login ke Bandcamp!

### 🚀 Cara Pakai:

1. **Login ke Bandcamp** di browser favorit Anda (Chrome/Firefox/Edge)
2. **Kunjungi** https://bandcamp.com/yum
3. **Buka aplikasi** ini: `python run_web.py`
4. **Klik tombol** `🤖 Auto-Extract from Browser`
5. **✨ Magic!** - Form otomatis terisi!

### 🎯 Apa yang Terjadi?

Sistem secara cerdas:
- ✅ **Membaca cookies** dari browser Anda (Chrome/Firefox/Edge)
- ✅ **Mengambil client_id** dan **session** dari cookies Bandcamp
- ✅ **Scraping crumb** langsung dari halaman Bandcamp
- ✅ **Mengisi form** secara otomatis!

### 📋 Requirements

Install dependencies tambahan:
```bash
pip install browser-cookie3 beautifulsoup4
```

Atau update semua:
```bash
pip install -r requirements.txt
```

### ⚡ Keuntungan

**Tanpa File .env:**
- Tidak perlu simpan credentials di file
- Tidak perlu copy-paste manual
- Credentials selalu fresh dari browser

**1-Klik Setup:**
- Klik button auto-extract
- Tunggu 2 detik
- Form terisi otomatis!
- Langsung bisa verify codes!

### 🔒 Keamanan

- Credentials **TIDAK disimpan** di server
- Hanya dibaca dari browser lokal Anda
- Hanya dipakai untuk session saat ini

### 📝 Troubleshooting

**Jika auto-extract gagal:**
1. Pastikan sudah install `browser-cookie3`
2. Pastikan sudah login di Bandcamp 
3. Pastikan sudah pernah buka bandcamp.com/yum
4. Coba browser lain (Chrome/Firefox/Edge)
5. Jika masih gagal, input manual masih bisa dipakai

---

**🎉 Enjoy the smart automation!**
