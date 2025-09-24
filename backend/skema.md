# Skema Database News Crawler (PostgreSQL / Supabase)

Dokumen ini berisi perintah SQL untuk membuat tabel, constraint, dan index yang dibutuhkan oleh backend.

Catatan:
- Untuk Supabase, ekstensi biasanya terpasang di schema `extensions`. Jika `CREATE EXTENSION` standar gagal, gunakan varian dengan `WITH SCHEMA extensions`.
- UUID default memakai `gen_random_uuid()` dari ekstensi `pgcrypto`.

## 1) Enable Extensions

-- Opsi A (umum Postgres)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Opsi B (Supabase; bila A gagal, coba gunakan schema extensions)
-- CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
-- CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions;

-- Opsional: jika ingin memakai uuid_generate_v4()
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


## 2) Tabel Utama

CREATE TABLE IF NOT EXISTS public.news (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  summary TEXT NULL,
  source TEXT NOT NULL,
  category TEXT NULL,
  publish_date TIMESTAMPTZ NULL,
  crawl_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  content_hash TEXT NULL
);

-- URL harus unik untuk mencegah duplikasi
ALTER TABLE public.news
  ADD CONSTRAINT news_url_unique UNIQUE (url);


## 3) Indexes untuk Kinerja Query

-- Filter dan sort berdasarkan publish_date
CREATE INDEX IF NOT EXISTS idx_news_publish_date ON public.news (publish_date);

-- Filter dan sort berdasarkan crawl_date
CREATE INDEX IF NOT EXISTS idx_news_crawl_date ON public.news (crawl_date);

-- Filter by domain/source (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_news_source_lower ON public.news ((LOWER(source)));

-- Filter by category (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_news_category_lower ON public.news ((LOWER(category)));

-- Pencarian ILIKE judul/summary (butuh pg_trgm)
CREATE INDEX IF NOT EXISTS idx_news_title_trgm
  ON public.news USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_news_summary_trgm
  ON public.news USING GIN (summary gin_trgm_ops);


## 4) Contoh Query Umum

-- 4.1. Ambil daftar berita terbaru (prioritaskan publish_date, lalu crawl_date)
SELECT id, title, url, summary, source, category, publish_date, crawl_date, content_hash
FROM public.news
ORDER BY publish_date DESC NULLS LAST, crawl_date DESC
LIMIT 20 OFFSET 0;

-- 4.2. Filter berdasarkan source dan category
SELECT id, title, url, summary, source, category, publish_date, crawl_date, content_hash
FROM public.news
WHERE LOWER(source) = LOWER('kompas.com')
  AND LOWER(category) = LOWER('ekonomi')
ORDER BY publish_date DESC NULLS LAST, crawl_date DESC
LIMIT 20 OFFSET 0;

-- 4.3. Pencarian teks pada title/summary (ILIKE)
SELECT id, title, url, summary, source, category, publish_date, crawl_date, content_hash
FROM public.news
WHERE title ILIKE '%ekonomi%'
   OR summary ILIKE '%ekonomi%'
ORDER BY publish_date DESC NULLS LAST, crawl_date DESC
LIMIT 20 OFFSET 0;

-- 4.4. Filter rentang tanggal publish
SELECT id, title, url, summary, source, category, publish_date, crawl_date, content_hash
FROM public.news
WHERE (publish_date::date) BETWEEN DATE '2025-09-01' AND DATE '2025-09-30'
ORDER BY publish_date DESC NULLS LAST, crawl_date DESC;


## 5) Pembersihan Data Lama (Opsional via SQL Langsung)

-- Hapus berdasarkan crawl_date > N hari
-- (Backend sudah menyediakan job cleanup; perintah ini untuk referensi manual)
-- Ganti N sesuai kebutuhan, misal 30
WITH deleted AS (
  DELETE FROM public.news
  WHERE crawl_date < (NOW() - (30 || ' days')::INTERVAL)
  RETURNING 1
)
SELECT COUNT(*) AS deleted_count FROM deleted;

-- Alternatif: berdasarkan publish_date > N hari (jika publish_date tersedia)
WITH deleted AS (
  DELETE FROM public.news
  WHERE publish_date IS NOT NULL
    AND publish_date < (NOW() - (30 || ' days')::INTERVAL)
  RETURNING 1
)
SELECT COUNT(*) AS deleted_count FROM deleted;


## 6) Validasi dan Observasi

-- Hitung total baris sebagai sanity check
SELECT COUNT(*) FROM public.news;

-- Cek distribusi source
SELECT LOWER(source) AS source, COUNT(*)
FROM public.news
GROUP BY LOWER(source)
ORDER BY COUNT(*) DESC;

-- Cek rentang waktu publish
SELECT MIN(publish_date) AS oldest_publish, MAX(publish_date) AS newest_publish
FROM public.news;

-- Cek duplikasi URL (seharusnya 0 karena unique constraint)
SELECT url, COUNT(*)
FROM public.news
GROUP BY url
HAVING COUNT(*) > 1;


## 7) Catatan

- Pastikan koneksi memakai `sslmode=require` pada Supabase.
- Unik pada kolom `url` memudahkan upsert (ON CONFLICT url DO UPDATE).
- Tambahkan index tambahan sesuai pattern query real di produksi.