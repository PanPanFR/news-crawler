## Arsitektur & Alur Kerja yang Dioptimalkan
Berikut adalah alur kerja baru yang memisahkan setiap tugas secara bersih, membuatnya lebih tahan banting (resilient), efisien, dan scalable.

Alur Visual:
[Crawler] -> [Database Supabase] -> [Skrip Prioritas] -> [Antrian Prioritas REDIS] -> [Worker Summarizer] -> [Database Supabase (Update)]

### Tahap 1: Ingesti - Crawler/Scraper 🏃‍♂️
Tugas Tunggal: Tugas crawler kamu setiap 15-30 menit hanyalah mengambil 300-an data berita (judul, url, konten mentah, source, dll).

Simpan ke Database: Setelah data didapat, langsung INSERT ke tabel public.news di Supabase. Kolom summary biarkan NULL.

Selesai: Proses crawler selesai di sini. Dia tidak perlu tahu-menahu soal summarizing. Ini membuat proses scraping sangat cepat dan terisolasi.

### Tahap 2: Prioritas & Antrian - Otak Sistem dengan Redis 🧠
Ini adalah bagian paling cerdas dari sistem baru. Kita tidak akan meringkas semua berita, hanya yang penting.

Skrip Prioritas: Buat sebuah skrip terpisah (misalnya prioritizer.py) yang berjalan setelah crawler selesai.

Ambil Berita Baru: Skrip ini melakukan query ke Supabase: SELECT id, title, source, publish_date FROM public.news WHERE summary IS NULL;.

Beri Skor (Scoring): Untuk setiap berita, berikan skor prioritas. Contoh sederhana:

Skor dari Sumber: Jika source adalah media besar (misal, Kompas, Detik, CNN Indonesia), beri +20 poin.

Skor dari Judul: Jika title mengandung kata kunci trending (misal, "pemerintah", "saham", "teknologi", "pemilu"), beri +10 poin per kata kunci.

Skor dari Waktu: Berita yang lebih baru bisa diberi sedikit bonus.

Masukkan ke Antrian Prioritas Redis: Daripada langsung meringkas, skrip ini memasukkan ID berita ke Redis Sorted Set.

Command: ZADD news_summarization_queue <SKOR_PRIORITAS> <ID_BERITA>

Contoh: ZADD news_summarization_queue 30 "uuid-berita-A" (Berita A punya skor 30)

ZADD news_summarization_queue 10 "uuid-berita-B" (Berita B punya skor 10)

### Tahap 3: Eksekusi - Worker Summarizer 🤖
Ini adalah skrip yang berjalan terus-menerus di background. Tugasnya adalah mengeksekusi ringkasan berdasarkan antrian di Redis.

Ambil Tugas dari Antrian: Worker akan mengambil berita dengan skor tertinggi dari Redis.

Command: ZPOPMAX news_summarization_queue (Ambil dan hapus 1 member dengan skor tertinggi).

Ambil Konten Lengkap: Dengan ID_BERITA dari Redis, worker melakukan query ke Supabase untuk mengambil konten lengkap artikel.

Panggil API LLM: Worker memanggil API LLM untuk meringkas konten. Logika time.sleep() untuk rate limiting tetap ada di sini. Worker ini adalah satu-satunya bagian yang "berbicara" dengan API LLM.

Update Database: Setelah ringkasan didapat, worker melakukan UPDATE pada baris berita di Supabase, mengisi kolom summary.

Manajemen Gagal (Retry): Jika API gagal, worker bisa memasukkan kembali ID_BERITA ke antrian Redis, mungkin dengan skor yang sedikit lebih rendah atau memasukkannya ke antrian khusus "gagal" untuk dicoba lagi nanti.

Ulangi: Worker kembali ke langkah 1 untuk mengambil tugas berikutnya.

### Tahap 4: Manajemen - Cache & Pembersihan 🧹
Caching: Database Supabase kamu sudah bertindak sebagai cache. Karena worker hanya mengambil berita dengan summary IS NULL, berita yang sudah diringkas tidak akan pernah diproses ulang. Ini memenuhi syarat nomor 3.

Pembersihan: Buat sebuah cron job yang berjalan mingguan atau bulanan untuk membersihkan ringkasan lama jika diperlukan.

Contoh SQL: UPDATE public.news SET summary = NULL WHERE publish_date < NOW() - INTERVAL '6 months';

Ini akan mengosongkan kolom summary untuk berita yang lebih lama dari 6 bulan, menghemat ruang, dan memungkinkan berita tersebut diringkas ulang di masa depan jika ada model LLM yang lebih baru.

## Kenapa Redis Sangat Berguna di Sini?
Menangani Beban Puncak (Burst Handling): Crawler-mu "melempar" 300 berita sekaligus. Redis dengan mudah menelan semuanya ke dalam antrian, sementara worker tetap bekerja dengan tenang dan stabil sesuai rate limit API.

Antrian Prioritas (Priority Queue): Dengan Sorted Set, kamu memastikan bahwa worker akan selalu mengerjakan berita yang paling penting terlebih dahulu. Berita "biasa" akan diringkas hanya jika tidak ada berita penting lainnya yang mengantri.

Memisahkan Proses (Decoupling): Crawler, prioritizer, dan worker adalah tiga proses yang berjalan sendiri-sendiri. Jika worker mati, antrian di Redis tetap aman dan crawler bisa tetap berjalan. Sistem jadi jauh lebih stabil.