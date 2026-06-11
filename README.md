# Sistem Case-Based Reasoning (CBR) untuk Analisis Putusan Pengadilan
### Pidana Umum — Penganiayaan | Pengadilan Negeri Malang

---

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?logo=jupyter)
![Scikit-learn](https://img.shields.io/badge/scikit--learn-1.2+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Mata Kuliah:** Penalaran Komputer | Semester Genap 2025/2026  
**Program Studi:** Informatika — Fakultas Teknik, Universitas Muhammadiyah Malang  
**Sumber Data:** [Direktori Putusan Mahkamah Agung RI](https://putusan3.mahkamahagung.go.id)

</div>

---

## 📋 Deskripsi Proyek

Proyek ini mengimplementasikan sistem **Case-Based Reasoning (CBR)** berbasis Python untuk mendukung analisis putusan pengadilan pada domain **Pidana Umum — Penganiayaan** (Pasal 351–356 KUHP). Sistem bekerja dengan siklus CBR penuh:

```
Retrieve → Reuse → Revise → Retain
```

Diberikan deskripsi kasus baru, sistem akan:
1. Mencari putusan lama yang paling mirip dari case base (≥ 30 putusan PN Malang)
2. Menggunakan putusan-putusan termirip sebagai dasar prediksi vonis
3. Memvalidasi dan menyimpan kasus baru yang terbukti benar ke case base

---

## 👥 Tim

| Nama | NIM |Github |
|------|-----|-----
| Mohammad Ravlindo Saputra | 202310370311115 | ravlindoMs |
| Mukhamad Sofyan | 202310370311135 | mukhamadsofyan |

---

## 🗂️ Struktur Repository

```
projek-cbr-hukum/
│
├── data/
│   ├── raw/                    # File .txt bersih per kasus (case_001.txt, ...)
│   ├── processed/
│   │   ├── cases.csv           # Metadata + fitur semua kasus
│   │   └── cases.json          # Versi JSON lengkap (termasuk text_full)
│   ├── eval/
│   │   ├── queries.json        # Query uji (manual + dari test set)
│   │   ├── train_idx.csv       # Indeks data training
│   │   ├── test_idx.csv        # Indeks data testing
│   │   ├── retrieval_metrics.csv
│   │   ├── prediction_metrics.csv
│   │   ├── error_analysis.csv
│   │   ├── model_comparison.png
│   │   └── confusion_matrices.png
│   └── results/
│       ├── predictions.csv     # Hasil prediksi semua query
│       └── retain_log.csv      # Log kasus yang berhasil di-retain
│
├── notebooks/
│   ├── 01_preprocessing.ipynb  # Tahap 1: Bangun Case Base
│   ├── 02_representation.ipynb # Tahap 2: Case Representation
│   ├── 03_retrieval.ipynb      # Tahap 3: Case Retrieval
│   ├── 04_reuse.ipynb          # Tahap 4: Reuse + Revisi & Retain
│   └── 05_evaluation.ipynb     # Tahap 5: Evaluasi Model
│
├── models/                     # Model tersimpan — tidak di-commit (lihat .gitignore)
│   ├── tfidf_vectorizer.pkl
│   ├── svm_model.pkl
│   ├── nb_model.pkl
│   ├── label_encoder.pkl
│   └── bert_embeddings.npy
│
├── logs/
│   └── cleaning.log            # Log proses preprocessing tiap file
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalasi

### Prasyarat
- Python 3.9 atau lebih baru
- pip
- (Opsional) GPU untuk mempercepat BERT embedding

### Langkah Instalasi

```bash
# 1. Clone repository ini
git clone https://github.com/<username>/projek-cbr-hukum.git
cd projek-cbr-hukum

# 2. Buat virtual environment (sangat disarankan)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# 3. Install semua dependensi
pip install -r requirements.txt
```

### Dependensi Utama

| Library | Versi | Kegunaan |
|---------|-------|----------|
| `pandas` | ≥ 1.5.0 | Manipulasi data tabular |
| `scikit-learn` | ≥ 1.2.0 | TF-IDF, SVM, Naive Bayes, metrik |
| `sentence-transformers` | ≥ 2.2.0 | Sentence-BERT embedding |
| `pdfminer.six` | ≥ 20221105 | Ekstraksi teks dari PDF |
| `Sastrawi` | ≥ 1.0.1 | Stemming Bahasa Indonesia |
| `matplotlib` | ≥ 3.6.0 | Visualisasi metrik & grafik |
| `tqdm` | ≥ 4.64.0 | Progress bar |

---

## 🚀 Cara Menjalankan Pipeline

> Buka VSCode → buka folder `projek-cbr-hukum` → jalankan tiap notebook **secara berurutan**.

---

### 📥 Langkah 0 — Siapkan Data

1. Buka [https://putusan3.mahkamahagung.go.id](https://putusan3.mahkamahagung.go.id)
2. Filter pencarian:
   - **Klasifikasi:** Pidana Umum
   - **Sub-klasifikasi:** Penganiayaan
   - **Pengadilan:** Pengadilan Negeri Malang
3. Download minimal **34 file PDF** putusan
4. Letakkan semua PDF di folder `data/raw/`

---

### Tahap 1 — Membangun Case Base
**File:** `notebooks/01_preprocessing.ipynb`

**Yang dilakukan:**
- Membaca semua PDF dari `data/raw` menggunakan `pdfminer.six`
- Menghapus header/footer khas Direktori MA RI
- Normalisasi unicode, spasi, dan karakter kontrol
- Validasi kualitas teks (cek keberadaan elemen kunci: kata "putusan", nomor perkara, kata "penganiayaan/kekerasan/luka")
- Menyimpan teks bersih ke `data/raw/cleaned/case_001.txt`, `case_002.txt`, dst.
- Mencatat semua proses ke `logs/cleaning.log`

**Output:**
```
data/raw/case_001.txt
data/raw/case_002.txt
...
data/raw/case_034.txt
logs/cleaning.log
```

---

### Tahap 2 — Case Representation
**File:** `notebooks/02_representation.ipynb`

**Yang dilakukan:**
- Ekstraksi metadata otomatis via regex:
  - Nomor perkara (format `XXX/Pid/YYYY/PN.Mlg`)
  - Tanggal putusan (konversi ke format `YYYY-MM-DD`)
  - Jenis perkara (Penganiayaan / KDRT / Pembunuhan)
  - Pasal yang digunakan (Pasal 351–356 KUHP)
  - Nama terdakwa & penuntut umum
  - Vonis & amar putusan
  - Ringkasan fakta & barang bukti
- Feature engineering: `word_count`, `text_combined`, `label_vonis`
- Labeling otomatis: `ringan` / `sedang` / `berat` / `bebas`

**Output:**
```
data/processed/cases.csv    # Metadata + fitur (tanpa text_full)
data/processed/cases.json   # Lengkap termasuk text_full
```

**Contoh kolom `cases.csv`:**

| case_id | no_perkara | tanggal | jenis_perkara | pasal | vonis | label_vonis |
|---------|-----------|---------|--------------|-------|-------|------------|
| case_001 | 123/Pid/2023/PN.Mlg | 2023-05-12 | Pidana Umum - Penganiayaan | Pasal 351 KUHP | pidana penjara 2 tahun | ringan |

---

### Tahap 3 — Case Retrieval
**File:** `notebooks/03_retrieval.ipynb`

**Yang dilakukan:**
- Preprocessing teks (lowercase, hapus angka & tanda baca, stopword domain hukum)
- **Pendekatan A — TF-IDF:**
  - `TfidfVectorizer` (unigram+bigram, max 5.000 fitur, `sublinear_tf=True`)
  - Split data 80:20 dengan stratify per label
  - Training **LinearSVC** dan **Naive Bayes**
- **Pendekatan B — Sentence-BERT:**
  - Model: `paraphrase-multilingual-MiniLM-L12-v2`
  - Embedding dinormalisasi (L2), cosine similarity via dot product
- Fungsi `retrieve(query, k=5, method='bert')` → List `(case_id, similarity_score)`
- Query evaluasi: 5 query manual + 10 query dari test set nyata

**Output:**
```
models/tfidf_vectorizer.pkl
models/svm_model.pkl
models/nb_model.pkl
models/label_encoder.pkl
models/bert_embeddings.npy
data/eval/queries.json
data/eval/train_idx.csv
data/eval/test_idx.csv
```

**Contoh penggunaan fungsi retrieve:**
```python
hasil = retrieve(
    query = "terdakwa memukul korban dengan benda tumpul mengakibatkan luka berat",
    k     = 5,
    method = 'bert'   # atau 'tfidf'
)
# Output: [('case_012', 0.8821), ('case_007', 0.8543), ...]
```

---

### Tahap 4 — Case Reuse + Revisi & Retain
**File:** `notebooks/04_reuse.ipynb`

**Yang dilakukan:**

*Reuse:*
- Mengambil amar putusan & vonis dari top-k kasus termirip sebagai "solusi"
- Algoritma **Majority Vote** dan **Weighted Similarity Vote**
- Fungsi `predict_outcome(query, k=5, method='bert', voting='weighted')`
- Demo prediksi 5 kasus baru

*Revisi & Retain (opsional):*
- `revise()` — validasi sebelum retain, kasus ditolak jika:
  - Confidence < 60%
  - Max similarity < 0.25
  - Prediksi ≠ label yang dikonfirmasi
- `retain()` — tambah kasus baru ke case base:
  - Simpan teks ke `data/raw/`
  - Update `cases.csv` dan `cases.json`
  - Update matrix TF-IDF dan BERT embedding in-memory
  - Catat ke `retain_log.csv`

**Output:**
```
data/results/predictions.csv
data/results/retain_log.csv
```

**Contoh penggunaan:**
```python
hasil = predict_outcome(
    query  = "terdakwa memukul korban dengan kayu hingga luka sobek di kepala",
    k      = 5,
    method = 'bert',
    voting = 'weighted'
)
# Output: {'predicted_label': 'sedang', 'confidence': 0.73, 'top_k_case_ids': [...]}
```

---

### Tahap 5 — Evaluasi Model
**File:** `notebooks/05_evaluation.ipynb`

**Yang dilakukan:**
- Menghitung metrik untuk 4 model: CBR TF-IDF, CBR BERT, SVM, Naive Bayes
- Metrik: **Accuracy, Precision, Recall, F1-Score** (weighted average)
- Retrieval metrics: **Hit@1, Hit@3, Hit@5, MRR**
- Visualisasi: bar chart perbandingan + confusion matrix (2 model)
- Error analysis: pola kesalahan & rekomendasi perbaikan

**Output:**
```
data/eval/retrieval_metrics.csv
data/eval/prediction_metrics.csv
data/eval/error_analysis.csv
data/eval/model_comparison.png
data/eval/confusion_matrices.png
```

---

## Arsitektur Sistem CBR

```
Input Kasus Baru
      │
      ▼
┌─────────────┐
│  RETRIEVE   │  TF-IDF / Sentence-BERT + Cosine Similarity
│             │  → Top-5 kasus termirip
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REUSE     │  Weighted Vote dari amar putusan top-5
│             │  → Prediksi label vonis + teks solusi
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REVISE    │  Validasi: confidence ≥ 60%, similarity ≥ 0.25,
│             │  prediksi cocok dengan konfirmasi pakar
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   RETAIN    │  Simpan ke case base → update model in-memory
└─────────────┘
```

---

## Label Vonis

| Label | Kriteria | Pasal Acuan |
|-------|---------|------------|
| `ringan` | Penjara ≤ 4 tahun | Pasal 351 ayat (1) & (2) KUHP |
| `sedang` | Penjara 5–10 tahun | Pasal 351 ayat (3), Pasal 353 KUHP |
| `berat` | Penjara > 10 tahun | Pasal 354, 355 KUHP (luka berat / meninggal) |
| `bebas` | Bebas / tidak terbukti | — |

---

## Catatan Teknis

| Hal | Keterangan |
|-----|-----------|
| BERT RAM | Set `BERT_ENABLED = False` di notebook 03 jika RAM < 4 GB |
| Retain | `dry_run = True` = simulasi tanpa tulis file; ubah ke `False` untuk menyimpan |
| Model | Folder `models/` tidak di-commit ke GitHub (`.gitignore`) |
| Split | Rasio 80:20 dengan stratify agar tiap label terwakili |
| Stopwords | Disesuaikan dengan domain hukum penganiayaan |

---

## Referensi


- Direktori Putusan MA RI: [https://putusan3.mahkamahagung.go.id](https://putusan3.mahkamahagung.go.id)
- Scikit-learn Documentation: [https://scikit-learn.org](https://scikit-learn.org)
- Sentence-Transformers: [https://www.sbert.net](https://www.sbert.net)
- KUHP Pasal 351–356 tentang Penganiayaan
