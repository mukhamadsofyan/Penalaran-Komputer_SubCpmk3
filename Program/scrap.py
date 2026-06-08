"""
Scraper Putusan Mahkamah Agung Indonesia
Mendukung: keyword, URL langsung, filter tahun, download PDF, simpan ke CSV/Excel
"""

import argparse
import io
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ─── Konfigurasi ─────────────────────────────────────────────────────────────

BASE_URL = "https://putusan3.mahkamahagung.go.id"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
    "Referer": BASE_URL,
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─── Argumen CLI ──────────────────────────────────────────────────────────────

def get_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Scraper Putusan Mahkamah Agung Indonesia",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-k", "--keyword", dest="keyword",
                        help="Kata kunci pencarian, contoh: penganiayaan")
    parser.add_argument("-u", "--url", dest="url",
                        help=(
                            "URL lengkap halaman pencarian, contoh:\n"
                            "https://putusan3.mahkamahagung.go.id/search.html"
                            "?q=penganiayaan&cat=4210395c07581866de499a7b125ea4bc"
                            "&jenis_doc=putusan&t_put=2024"
                        ))
    parser.add_argument("-tp", "--tahun-putusan", dest="tahun_putusan",
                        help="Filter tahun putusan, contoh: 2024")
    parser.add_argument("-sd", "--sort-date", dest="sort_date",
                        action="store_true", default=False,
                        help="Urutkan dari putusan terbaru")
    parser.add_argument("-dp", "--download-pdf", dest="download_pdf",
                        action="store_true", default=False,
                        help="Download file PDF setiap putusan")
    parser.add_argument("-o", "--output", dest="output_dir",
                        default="output_putusan",
                        help="Folder output (default: output_putusan)")
    parser.add_argument("-w", "--workers", dest="workers",
                        type=int, default=4,
                        help="Jumlah thread paralel (default: 4)")
    parser.add_argument("--max-pages", dest="max_pages",
                        type=int, default=None,
                        help="Batasi jumlah halaman yang di-scrape")
    return parser.parse_args(argv)


# ─── Helper ───────────────────────────────────────────────────────────────────

def fetch_soup(url: str, retries: int = 3, delay: float = 3.0):
    """Ambil BeautifulSoup dari URL, retry jika gagal."""
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            print(f"  [WARN] Gagal fetch ({attempt+1}/{retries}): {url} — {exc}")
            time.sleep(delay * (attempt + 1))
    return None


def get_cell(table, label: str) -> str:
    """Ambil nilai sel dari tabel detail berdasarkan label."""
    try:
        td = table.find(lambda tag: tag.name == "td" and label in tag.get_text())
        return td.find_next_sibling("td").get_text(strip=True) if td else ""
    except Exception:
        return ""


def extract_pdf_text(url: str) -> tuple[str, str]:
    """Unduh PDF dan ekstrak teksnya. Kembalikan (teks, nama_file)."""
    try:
        from pdfminer import high_level  # opsional
        with urllib.request.urlopen(url) as f:
            filename = (f.info().get_filename() or "putusan.pdf").replace("/", "_")
            data = f.read()
        text = high_level.extract_text(io.BytesIO(data))
        return text.strip(), filename
    except ImportError:
        return "[pdfminer tidak terinstall — jalankan: pip install pdfminer.six]", ""
    except Exception as exc:
        return f"[Gagal ekstrak PDF: {exc}]", ""


def build_search_url(keyword: str, page: int, tahun: str = "", sort_date: bool = False) -> str:
    url = f"{BASE_URL}/search.html?q={urllib.parse.quote(keyword)}&page={page}"
    if tahun:
        url += f"&t_put={tahun}"
    if sort_date:
        url += "&obf=TANGGAL_PUTUS&obm=desc"
    return url


# ─── Ekstraksi Data Satu Putusan ──────────────────────────────────────────────

def extract_putusan(link: str, download_pdf: bool, pdf_dir: str) -> dict | None:
    """Ambil semua field dari halaman detail satu putusan."""
    soup = fetch_soup(link)
    if not soup:
        return None

    try:
        table = soup.find("table", {"class": "table"})
        if not table:
            return None

        judul_tag = table.find("h2")
        judul = judul_tag.get_text(strip=True) if judul_tag else ""
        if judul_tag:
            judul_tag.decompose()

        fields = [
            "Nomor", "Tingkat Proses", "Klasifikasi", "Kata Kunci",
            "Tahun", "Tanggal Register", "Lembaga Peradilan",
            "Jenis Lembaga Peradilan", "Hakim Ketua", "Hakim Anggota",
            "Panitera", "Amar", "Amar Lainnya", "Catatan Amar",
            "Tanggal Musyawarah", "Tanggal Dibacakan", "Kaidah", "Abstrak",
        ]
        row = {"judul": judul, "link": link}
        for f in fields:
            row[f.lower().replace(" ", "_")] = get_cell(table, f)

        # PDF
        pdf_tag = soup.find("a", href=re.compile(r"/pdf/"))
        row["link_pdf"] = pdf_tag["href"] if pdf_tag else ""
        row["nama_file_pdf"] = ""
        row["teks_pdf"] = ""

        if pdf_tag and download_pdf:
            pdf_url = pdf_tag["href"]
            teks, nama = extract_pdf_text(pdf_url)
            row["teks_pdf"] = teks
            row["nama_file_pdf"] = nama
            if nama:
                pdf_path = os.path.join(pdf_dir, nama)
                try:
                    urllib.request.urlretrieve(pdf_url, pdf_path)
                except Exception:
                    pass

        return row

    except Exception as exc:
        print(f"  [ERROR] Gagal parse: {link} — {exc}")
        return None


# ─── Scraping Per Halaman ────────────────────────────────────────────────────

def scrape_page(page_url: str, download_pdf: bool, pdf_dir: str, workers: int) -> list[dict]:
    """Scrape satu halaman daftar putusan, kembalikan list dict."""
    soup = fetch_soup(page_url)
    if not soup:
        return []

    links = [
        a["href"] for a in soup.find_all("a", href=re.compile(r"/direktori/putusan/"))
        if a.get("href")
    ]
    links = list(dict.fromkeys(links))  # deduplicate

    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(extract_putusan, lnk, download_pdf, pdf_dir): lnk for lnk in links}
        for fut in as_completed(futures):
            data = fut.result()
            if data:
                results.append(data)
                print(f"    ✓ {data.get('judul', '')[:70]}")
    return results


def get_last_page(soup) -> int:
    """Ambil nomor halaman terakhir dari pagination."""
    try:
        pages = soup.find_all("a", {"class": "page-link"})
        nums = [
            int(a["data-ci-pagination-page"])
            for a in pages
            if a.get("data-ci-pagination-page", "").isdigit()
        ]
        return max(nums) if nums else 1
    except Exception:
        return 1


# ─── Main ─────────────────────────────────────────────────────────────────────

import urllib.parse


def main():
    args = get_args()

    if not args.keyword and not args.url:
        print("❌ Harap berikan --keyword atau --url")
        return

    # Buat folder output
    os.makedirs(args.output_dir, exist_ok=True)
    pdf_dir = os.path.join(args.output_dir, "pdf")
    if args.download_pdf:
        os.makedirs(pdf_dir, exist_ok=True)

    # Tentukan URL awal
    if args.url:
        # Pastikan page=1 ada di URL
        base_url = re.sub(r"[&?]page=\d+", "", args.url)
        sep = "&" if "?" in base_url else "?"
        first_url = f"{base_url}{sep}page=1"
        label = "url-custom"
    else:
        first_url = build_search_url(
            args.keyword, 1, args.tahun_putusan or "", args.sort_date
        )
        label = args.keyword.replace(" ", "_")
        if args.tahun_putusan:
            label += f"_{args.tahun_putusan}"

    print(f"\n🔍 Membuka halaman pertama: {first_url}")
    soup_first = fetch_soup(first_url)
    if not soup_first:
        print("❌ Tidak bisa membuka halaman. Coba lagi nanti.")
        return

    last_page = get_last_page(soup_first)
    if args.max_pages:
        last_page = min(last_page, args.max_pages)

    est = last_page * 20
    print(f"📄 Total halaman: {last_page} (~{est} putusan)\n")

    # Kumpulkan semua data
    all_data: list[dict] = []
    today = date.today().strftime("%Y-%m-%d")
    csv_path = os.path.join(args.output_dir, f"putusan_{label}_{today}.csv")
    xlsx_path = os.path.join(args.output_dir, f"putusan_{label}_{today}.xlsx")

    for page in range(1, last_page + 1):
        if args.url:
            base_url = re.sub(r"[&?]page=\d+", "", args.url)
            sep = "&" if "?" in base_url else "?"
            page_url = f"{base_url}{sep}page={page}"
        else:
            page_url = build_search_url(
                args.keyword, page, args.tahun_putusan or "", args.sort_date
            )

        print(f"📃 Halaman {page}/{last_page}: {page_url}")
        rows = scrape_page(page_url, args.download_pdf, pdf_dir, args.workers)
        all_data.extend(rows)

        # Simpan incremental per halaman
        if rows:
            df_inc = pd.DataFrame(rows)
            df_inc.to_csv(
                csv_path,
                mode="a",
                header=not os.path.exists(csv_path) or page == 1,
                index=False,
                encoding="utf-8-sig",
            )

        time.sleep(1.5)  # jeda antar halaman

    if not all_data:
        print("\n⚠️  Tidak ada data yang berhasil di-scrape.")
        return

    # Simpan Excel final
    df_final = pd.DataFrame(all_data)
    df_final.to_excel(xlsx_path, index=False)

    print(f"\n✅ Selesai! {len(all_data)} putusan berhasil di-scrape.")
    print(f"   📄 CSV  : {csv_path}")
    print(f"   📊 Excel: {xlsx_path}")
    if args.download_pdf:
        print(f"   📁 PDF  : {pdf_dir}/")


if __name__ == "__main__":
    main()