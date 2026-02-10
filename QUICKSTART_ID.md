# Quick Start - Bandcamp Code Verificator

## 🚀 Langkah Cepat

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Credentials (Optional tapi Recommended!)

**Copy file contoh:**
```bash
copy .env.example .env
```

**Edit `.env` dengan Notepad atau editor favorit, isi:**
```env
BANDCAMP_CRUMB=|api/codes/1/verify|1759468523|HTNmuiFhDBD3w/Ylg7GlDUjCmi8=
BANDCAMP_CLIENT_ID=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772
BANDCAMP_SESSION=1%09r%3A%5B%22...%22%5D%09t%3A...
```

📌 **Cara dapat credentials:** Lihat [SETUP_ID.md](SETUP_ID.md)

### 3. Jalankan Web Server
```bash
python run_web.py
```

### 4. Buka Browser
```
http://127.0.0.1:5000
```

## ✨ Fitur Baru!

**Jika sudah setup `.env`:**
- ✅ Form credentials **HILANG OTOMATIS**
- ✅ Tinggal **PASTE CODES** dan klik verify!
- ✅ **SUPER CEPAT** dan praktis!

**Jika belum setup `.env`:**
- Form credentials masih muncul
- Bisa input manual setiap kali

## 📝 Alternatif: Pakai CLI Mode
```bash
python cli.py verify --input codes.txt --output results.csv
```

---

**Made with ❤️ for Bandcamp users**
