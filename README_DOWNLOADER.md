# CSV-Driven PDF Downloader

Automated exam PDF downloader that prioritizes unpublished exams by view count.

## How It Works

### **Workflow**

```
1. Read CSV catalog (comcbt_data_published.csv)
   ↓
2. Filter out published exams (Published = "Y")
   ↓
3. Select exam with HIGHEST view count
   ↓
4. Download up to 15 PDFs from that exam's board
   ↓
5. Mark exam as Published = "Y" in CSV
   ↓
6. Repeat for next highest exam
```

---

## Files Created

### **Core Modules**
```
src/exam_pipeline/pdf_downloader/
├── csv_manager.py     # CSV catalog management
├── downloader.py      # PDF download with Selenium
├── workflow.py        # Automated workflow
└── __init__.py        # Module exports
```

### **CSV Format**
```csv
title,view_count,url,Published
산업안전기사...,97268,https://www.comcbt.com/xe/bw,Y
건설안전산업기사...,77086,https://www.comcbt.com/xe/bj,
전자기사...,20570,https://www.comcbt.com/xe/bf,
```

- **title**: Exam name
- **view_count**: Number of views (for prioritization)
- **url**: Board URL to scrape
- **Published**: "Y" = already done, empty = not done yet

---

## Usage

### **Option 1: Quick Test (View Catalog)**

```python
from pathlib import Path
from src.exam_pipeline.pdf_downloader import ExamCatalog

# Load catalog
catalog = ExamCatalog(Path("src/exam_pipeline/comcbt_data_published.csv"))

# Show statistics
catalog.print_statistics()

# List top 10 unpublished exams
catalog.list_top_unpublished(limit=10)
```

**Output:**
```
📊 Exam Catalog Statistics
==================================================
Total exams:     1,247
Published:       892
Unpublished:     355
Completion:      71.5%
==================================================

🔝 Top 10 Unpublished Exams (by views):
--------------------------------------------------------------------------------
 1.   77,086 views | 건설안전산업기사 필기 기출문제 및 CBT...
 2.   20,570 views | 전자기사 필기 기출문제 및 CBT...
 3.   14,799 views | 화공기사 필기 기출문제 및 CBT...
...
```

---

### **Option 2: Automatic Download (Single Exam)**

```python
from pathlib import Path
from src.exam_pipeline.pdf_downloader import run_auto_download

# Download top exam (up to 15 PDFs)
success, count = run_auto_download(
    csv_path=Path("src/exam_pipeline/comcbt_data_published.csv"),
    download_dir=Path("~/Desktop/downloads"),
    max_pdfs_per_exam=15,
    log_callback=print  # Print progress
)

print(f"Downloaded {count} files")
```

**What happens:**
1. Selects: 건설안전산업기사 (77,086 views) ← Highest unpublished
2. Downloads: Up to 15 PDFs from `https://www.comcbt.com/xe/bj`
3. Saves to: `~/Desktop/downloads/건설안전산업기사/`
4. Marks: Row updated with `Published = "Y"`

---

### **Option 3: Batch Download (Multiple Exams)**

```python
from pathlib import Path
from src.exam_pipeline.pdf_downloader import DownloadWorkflow

workflow = DownloadWorkflow(
    csv_path=Path("src/exam_pipeline/comcbt_data_published.csv"),
    download_dir=Path("~/Desktop/downloads"),
    max_pdfs_per_exam=15
)

# Download 5 exams
exams_done, total_files = workflow.run_batch_downloads(
    batch_size=5,
    log_callback=print
)

print(f"Completed {exams_done} exams, {total_files} files total")
```

**What happens:**
- Run 1: 건설안전산업기사 (77,086 views) → 15 PDFs → Mark Y
- Run 2: 전자기사 (20,570 views) → 12 PDFs → Mark Y
- Run 3: 화공기사 (14,799 views) → 15 PDFs → Mark Y
- Run 4: Next highest...
- Run 5: Next highest...

---

## Configuration

### **Download Limits**

```python
downloader = PDFDownloader(
    download_dir=Path("~/downloads"),
    max_pdfs_per_category=15,  # Max PDFs per exam (default: 15)
    request_timeout=20,         # HTTP timeout (seconds)
    implicit_wait=3             # Selenium wait (seconds)
)
```

### **Custom CSV Path**

```python
catalog = ExamCatalog(Path("/custom/path/to/catalog.csv"))
```

---

## Example Run

```bash
$ python test_downloader.py
```

**Output:**
```
📊 Exam Catalog Statistics
==================================================
Total exams:     1,247
Published:       892
Unpublished:     355
Completion:      71.5%
==================================================

🔝 Top 10 Unpublished Exams (by views):
--------------------------------------------------------------------------------
 1.   77,086 views | 건설안전산업기사 필기 기출문제 및 CBT...
 2.   20,570 views | 전자기사 필기 기출문제 및 CBT...
...

======================================================================
🎯 Selected Exam (Rank #1 by views)
======================================================================
Title:  건설안전산업기사 필기 기출문제 및 CBT 2020년 08월 22일(3회)
Views:  77,086
URL:    https://www.comcbt.com/xe/bj
Target: Download up to 15 PDFs
======================================================================

Visiting: 건설안전산업기사...
Found 23 posts, checking for PDFs...
[1/15] 2024년 4회 기출문제...
  ✓ Downloaded (1/15)
[2/15] 2024년 3회 기출문제...
  ✓ Downloaded (2/15)
...
[15/15] 2022년 1회 기출문제...
  ✓ Downloaded (15/15)

✓ Downloaded 15 PDF files
✓ Marked as published in CSV
✓ Download complete: 15 files
```

---

## Features

✅ **Automatic Prioritization** - Always downloads most popular unpublished exam
✅ **Progress Tracking** - CSV marks completed exams
✅ **Duplicate Prevention** - Skips already published exams
✅ **Limit Control** - Download up to 15 PDFs per exam
✅ **Error Handling** - Continues on failures
✅ **Batch Processing** - Process multiple exams in one run
✅ **Live Logging** - Real-time progress updates

---

## Dependencies

```bash
# Required packages
pip install selenium requests

# ChromeDriver (auto-detected by Selenium)
# Make sure Chrome browser is installed
```

---

## CSV Updates

The CSV is automatically updated after each successful download:

**Before:**
```csv
건설안전산업기사...,77086,https://www.comcbt.com/xe/bj,
```

**After:**
```csv
건설안전산업기사...,77086,https://www.comcbt.com/xe/bj,Y
```

This prevents re-downloading the same exam in future runs.

---

## Next Steps

After downloading PDFs, use the PDF extraction module to:
1. Extract questions from PDFs
2. Generate AI explanations
3. Create Flutter app
4. Deploy to App Store

See main README for full pipeline documentation.
