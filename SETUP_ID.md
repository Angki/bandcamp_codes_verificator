# Instruksi Setup Credentials

## Cara Mudah: Menggunakan File .env

1. **Copy file contoh**
   ```bash
   copy .env.example .env
   ```

2. **Edit file `.env`** dengan editor favorit Anda (Notepad++, VSCode, dll)

3. **Isi credentials Anda:**
   - Buka browser dan login ke Bandcamp
   - Kunjungi https://bandcamp.com/yum
   - Buka Developer Tools (F12)
   - Buka tab Network
   - Coba verify kode download
   - Cari request ke `/verify`
   - Copy nilai:
     - **BANDCAMP_CRUMB**: dari payload request
     - **BANDCAMP_CLIENT_ID**: dari cookies
     - **BANDCAMP_SESSION**: dari cookies

4. **Paste ke file `.env`:**
   ```
   BANDCAMP_CRUMB=|api/codes/1/verify|1759468523|HTNmuiFhDBD3w/Ylg7GlDUjCmi8=
   BANDCAMP_CLIENT_ID=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772
   BANDCAMP_SESSION=1%09r%3A%5B%22...%22%5D%09t%3A...
   ```

5. **Save file dan restart server**
   ```bash
   python run_web.py
   ```

6. **Buka browser** ke `http://127.0.0.1:5000` - Form credentials tidak akan muncul lagi!

## Keuntungan Menggunakan .env:

✅ **Praktis** - Setup sekali saja
✅ **Aman** - File .env tidak akan masuk ke Git
✅ **Cepat** - Tinggal paste codes dan verify
✅ **Fleksibel** - Bisa update credentials kapan saja

## Catatan:

- Jika credentials expired, tinggal update file `.env`
- Untuk testing dengan credentials berbeda, bisa input manual di form (jika credentials di .env tidak diisi)
- File `.env` sudah ada di `.gitignore`, jadi aman untuk privacy Anda
