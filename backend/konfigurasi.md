# Konfigurasi & Panduan Deploy Backend News Crawler

Dokumen ini menjelaskan cara menjalankan proyek secara lokal, mengonfigurasi environment, serta men-deploy ke Render dan menghubungkan ke database Supabase menggunakan Supabase client.

## 1) Prasyarat

- Python 3.11+ (disarankan)
- Akses ke project Supabase
- Git (opsional, jika ingin deploy dari repo)

## 2) Instalasi Dependensi

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Konfigurasi Environment

Aplikasi menggunakan Supabase client dengan dua variabel environment:

- `SUPABASE_URL` - Project URL dari dashboard Supabase
- `SUPABASE_KEY` - Anon key dari dashboard Supabase

Contoh file `.env` (opsional untuk local dev):

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key-here
```

Catatan:
- Modul akan otomatis memuat `.env` (via python-dotenv) sehingga selama `.env` ada di root proyek, aplikasi akan menemukannya.
- Pastikan tabel `news` sudah dibuat di Supabase sesuai skema di `skema.md`

## 4) Menjalankan API Secara Lokal

Setelah mengisi `.env` dengan URL dan key Supabase:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoint dasar:
- `GET /` → ringkasan service
- `GET /health` → health check
- `GET /api/news` → daftar berita dengan filter opsional
- `GET /api/news/{id}` → detail 1 berita
- `POST /api/news/crawl` → trigger proses crawling manual
  - Query:
    - `concurrency` (default 3, min 1, max 10)
    - `domains` (opsional, comma-separated: `kompas.com,detik.com`)
- `POST /api/news/cleanup` → hapus data lama manual
  - Query:
    - `days` (default 30)
    - `by_publish` (boolean; jika true pakai kolom publish_date, selainnya pakai crawl_date)

Contoh:
```bash
# Crawl default sources dengan concurrency 3
curl -X POST "http://localhost:8000/api/news/crawl?concurrency=3"

# Crawl domain spesifik
curl -X POST "http://localhost:8000/api/news/crawl?domains=kompas.com,detik.com&concurrency=2"

# Cleanup data lebih dari 30 hari (berdasar crawl_date)
curl -X POST "http://localhost:8000/api/news/cleanup?days=30"
```

## 5) Menjalankan Scheduler (CLI)

Selain endpoint HTTP, tersedia entrypoint CLI untuk dijalankan oleh Render Scheduler atau cron:

```bash
# Crawl semua sumber bawaan
python -m app.scheduler crawl --concurrency 3

# Crawl domain tertentu
python -m app.scheduler crawl --domains kompas.com,detik.com --concurrency 2

# Hapus data > 30 hari (berdasar publish_date)
python -m app.scheduler cleanup --days 30 --by-publish
```

## 6) Skema Database

Pastikan tabel `news` sudah dibuat di Supabase sesuai skema di `skema.md`. 
Ringkasnya:
- Tabel `news` berisi `id`, `title`, `url` (unik), `summary`, `source`, `category`, `publish_date`, `crawl_date`, `content_hash`
- Pastikan kolom `url` memiliki constraint unik

Lihat `skema.md` untuk perintah lengkap.

## 7) Deployment ke Render (Web Service)

- Service type: Web Service
- Runtime: Python
- Build command:
  ```
  pip install -r requirements.txt
  ```
- Start command:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Environment Variables:
  - `SUPABASE_URL` diisi project URL Supabase
  - `SUPABASE_KEY` diisi anon key Supabase
- Region: pilih yang terdekat
- Auto deploy: optional

Pastikan tabel `news` sudah dibuat di Supabase sesuai `skema.md`.

## 8) Render Scheduler (Job Crawling & Cleanup)

Buat dua job scheduler:

1) Crawl job
- Name: crawl-news
- Schedule: Every 15 minutes (atau sesuai kebutuhan)
- Command:
  ```
  python -m app.scheduler crawl --concurrency 3
  ```
- Environment: sama seperti Web Service (butuh `SUPABASE_URL` dan `SUPABASE_KEY`)

2) Cleanup job
- Name: cleanup-news
- Schedule: Daily (misal pukul 01:00)
- Command:
  ```
  python -m app.scheduler cleanup --days 30
  ```
- Environment: sama seperti Web Service

Catatan:
- Sesuaikan nilai `--concurrency` (3–5 disarankan agar hemat resource).
- Atur jadwal agar tidak overlap terlalu sering jika resource terbatas.

## 9) Mengambil SUPABASE_URL dan SUPABASE_KEY

Di Supabase:
- Buka Project → Settings → API
- Project URL: Salin dari bagian "Project URL"
- Anon key: Salin dari bagian "Project API keys" → `anon` key
- Salin ke `SUPABASE_URL` dan `SUPABASE_KEY` di Render dan/atau `.env` lokal.

## 10) Catatan Kinerja dan Etika Crawling

- Proses memakai RSS jika tersedia; fallback scraping HTML seminimal mungkin.
- Concurrency dibatasi agar tidak membebani situs sumber.
- Pertimbangkan robots.txt dan terms of service situs tujuan.
- Simpan hanya field esensial untuk hemat storage.
- Bersihkan data lama secara berkala (default 30 hari).

## 11) Troubleshooting

- Error: `SUPABASE_URL and SUPABASE_KEY must be configured`
  - Pastikan `.env` berisi `SUPABASE_URL` dan `SUPABASE_KEY` (lokal), atau Render Environment Variables terisi.
- Tidak ada data masuk setelah crawl:
  - Cek logs job crawler di Render.
  - Pastikan tabel `news` sudah dibuat di Supabase.
  - Coba jalankan crawl domain spesifik via CLI atau endpoint.
- Lambat saat query:
  - Pastikan index telah dibuat di tabel Supabase.
  - Untuk pencarian teks, pertimbangkan menggunakan fitur full-text search Supabase.
