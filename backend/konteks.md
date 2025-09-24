# Detail Design Backend Aplikasi Agregator Berita

## Bahasa dan Framework
- Bahasa: Python (karena ekosistem crawling kuat dan mudah integrasi)
- Framework Web/API: FastAPI (ringan, cepat, modern, dan mendukung asynchronous programming)
- Library Crawling: Scrapy untuk crawling besar atau BeautifulSoup + requests untuk crawling sederhana
- Scheduler: Render Scheduler untuk menjalankan crawling secara berkala dan stabil
- Database Client: Supabase Python client atau asyncpg untuk koneksi PostgreSQL

---

## Daftar Situs Web Berita Sumber Crawling
Berikut adalah contoh daftar situs berita populer yang bisa dijadikan sumber crawling untuk aplikasi agregator berita:

- kompas.com
- detik.com
- tempo.co
- antaranews.com
- bbc.com
- cnbcindonesia.com
- republika.co.id
- katadata.co.id
- theguardian.com
- nytimes.com

Daftar ini bersifat manual dan bisa dikembangkan atau disesuaikan dengan kebutuhan dan target pengguna.

---

## Struktur Folder Backend

- `app/main.py`: Entry point FastAPI, inisiasi API server backend.
- `app/api/routes.py`: Endpoint API seperti `/news`, `/categories` untuk frontend.
- `app/crawler/spider.py`: Script atau Scrapy spider yang melakukan crawling berita dari sumber.
- `app/crawler/utils.py`: Fungsi helper parsing HTML dan scraping data.
- `app/db/models.py`: Definisi model ORM untuk representasi tabel pada database.
- `app/db/crud.py`: Fungsi CRUD untuk berinteraksi dengan database (insert, update, delete).
- `app/scheduler.py`: Fungsi yang dipanggil oleh Render Scheduler untuk menjalankan proses crawling secara berkala.
- `requirements.txt`: Daftar dependensi Python yang digunakan (fastapi, uvicorn, scrapy, psycopg2, supabase-py, dll).

---

## Alur Backend

1. **Scheduler**: Render Scheduler memicu fungsi crawling di `scheduler.py` setiap 15-30 menit sesuai jadwal.
2. **Crawler**: Fungsi crawling menjalankan spider Scrapy atau requests + BeautifulSoup untuk mengambil data berita terbaru dari situs yang sudah ditentukan.
3. **Pengecekan Database**: Per setiap berita di-crawl, sistem memeriksa apakah berita tersebut sudah ada di database dengan membandingkan `content_hash` untuk mendeteksi duplikat atau update.
4. **Penyimpanan**: Berita baru atau yang mengalami update disimpan atau diupdate di database Supabase.
5. **API Backend**: FastAPI menyajikan data berita melalui RESTful endpoint dengan support pencarian dan filter seperti kategori, tanggal, dan query kata kunci.
6. **Manajemen Data Lama**: Data berita yang sudah berumur lebih dari 30 hari dihapus otomatis untuk menjaga ukuran database agar tidak membengkak.

---

## Pengelolaan Crawling

- Crawling dilakukan secara **paralel dengan concurrency dibatasi** (misalnya 3-5 situs berbarengan) untuk mempercepat proses tanpa membebani server backend.
- Kontrol concurrency ini penting untuk menghindari limit resource pada hosting (Render free tier) dan penghindaran pemblokiran oleh situs target.
- Crawling difokuskan hanya mengambil data inti seperti judul, url, ringkasan, tanggal publish, sumber, dan kategori saja untuk menghemat resource dan storage.

---

## Pengelolaan Database

- Menggunakan Supabase (PostgreSQL) sebagai database penyimpanan.
- Struktur tabel menyimpan data berita inti dengan kolom seperti `title`, `url`, `summary`, `source`, `category`, `publish_date`, `crawl_date`, dan `content_hash`.
- Tabel didesain agar mendukung query pencarian cepat dan filter berdasar kategori atau tanggal.
- Data lama secara rutin dibersihkan menggunakan job terjadwal supaya ruang penyimpanan tidak cepat penuh.

---

## Deployment dan Infrastruktur

- Backend langsung di-deploy ke platform Render tanpa containerize Docker.
- Render Scheduler digunakan untuk menjadwalkan job crawling secara terpisah, menjadikan penjadwalan lebih stabil dan bebas dari gangguan seperti backend idle atau restart.
- Backend melayani API yang diakses frontend dengan performa dan latency yang baik.

---

## Manfaat Setup Ini

- Otomatisasi crawling secara berkala dengan jadwal terkontrol dan concurrency terbatas mengoptimalkan pemakaian resource.
- Penyimpanan data yang terstruktur dan dibersihkan secara rutin menjaga performa dan biaya operasional tetap rendah.
- Backend API modern dengan FastAPI menjamin kemudahan pengembangan dan integrasi dengan frontend Next.js.
- Infrastruktur deployment gratis (Render dan Supabase free tier) cocok untuk Proof of Concept sampai MVP tahap awal.

---

Jika diperlukan, detail pengembangan seperti panduan pembuatan API, contoh cron job di Render, atau teknik crawling paralel bisa diberikan lebih lanjut.

pokoknya untuk urusan konfigurasi, anda buatkan file terpisah misal konfigurasi.md dan juga untuk skema databasenya anda buatkan juga query sqlnya di file terpisah yaitu skema.md