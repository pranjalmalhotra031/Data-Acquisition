"""
Data Acquisition
----------------------------------------------------------------------------
1. Scrapes and downloads PDFs from a given URL
2. Extracts metadata using pikepdf
3. Extracts text using PyMuPDF
4. Runs OCR (Tesseract) automatically if text extraction fails
5. Saves all outputs into a JSONL dataset and produces readable CSV/pretty JSON and separate full-text files
"""

import os
import re
import json
import argparse
import logging
import requests
import fitz
import pikepdf
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import csv

# Try optional OCR libraries
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# ================== CONFIG DEFAULTS ==================
DEFAULT_URL = "https://dyysg.org.uk/docs.php"  # default target URL
DEFAULT_DIR = "Scraped_PDFs"
DEFAULT_DPI = 150
DATASET_FILE = "dataset.jsonl"
# =====================================================

def setup_logging(output_dir):
    """Configure log file inside output folder and console handler."""
    log_path = os.path.join(output_dir, "data_acquisition.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    # add simple console output as well
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)
    return logging.getLogger(__name__)

def get_desktop_path():
    one_drive = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    local = os.path.join(os.path.expanduser("~"), "Desktop")
    return one_drive if os.path.exists(one_drive) else local

# =====================================================
# SCRAPE AND DOWNLOAD PDFs
# =====================================================
def scrape_and_download_pdfs(base_url, output_dir, logger):
    logger.info(f"🌐 Fetching page: {base_url}")
    try:
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"❌ Failed to access {base_url}: {e}")
        return 0

    soup = BeautifulSoup(response.text, "lxml")
    links = soup.find_all("a", href=True)
    pdf_count = 0

    for link in links:
        href = link["href"]
        if ".pdf" not in href.lower():
            continue

        pdf_url = urljoin(base_url, href)
        logger.info(f"📥 Downloading: {pdf_url}")

        try:
            pdf_response = requests.get(pdf_url, timeout=20)
            pdf_response.raise_for_status()

            filename = unquote(os.path.basename(pdf_response.url)).replace(" ", "_")
            save_path = os.path.join(output_dir, filename)

            if os.path.exists(save_path):
                logger.info(f"⏭️ Skipping existing file: {filename}")
                continue

            with open(save_path, "wb") as f:
                f.write(pdf_response.content)
            pdf_count += 1
            logger.info(f"✅ Saved: {save_path}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to download {pdf_url}: {e}")

    logger.info(f"✅ Download complete! {pdf_count} new PDF(s) saved.")
    return pdf_count

# =====================================================
# METADATA EXTRACTION
# =====================================================
def extract_metadata(pdf_path, logger):
    try:
        pdf = pikepdf.Pdf.open(pdf_path)
        metadata = pdf.docinfo
        meta_dict = {str(k).strip("/"): str(v).strip() for k, v in metadata.items()}

        title = meta_dict.get("Title", "").strip() or "Unknown Title"
        author = meta_dict.get("Author", "").strip() or "Unknown Author"
        producer = meta_dict.get("Producer", "").strip() or "Unknown Producer"

        year = "Unknown Year"
        for field in ["ModDate", "CreationDate", "Producer", "Creator"]:
            val = meta_dict.get(field, "")
            match = re.search(r"(19|20)\d{2}", val)
            if match:
                year = match.group()
                break

        pdf.close()
        return {"title": title, "author": author, "producer": producer, "year": year}

    except Exception as e:
        logger.warning(f"⚠️ Metadata extraction failed for {pdf_path}: {e}")
        return {"title": "Error Reading File", "author": "", "producer": "", "year": ""}

# =====================================================
# TEXT EXTRACTION + AUTO OCR FALLBACK
# =====================================================
def extract_text_auto_ocr(pdf_path, logger, dpi=150):
    """Try PyMuPDF first; fallback to OCR if text extraction fails."""
    try:
        doc = fitz.open(pdf_path)
        all_text = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if text:
                all_text.append(text)
        doc.close()

        extracted_text = "\n".join(all_text).strip()
        if extracted_text:
            return extracted_text, False  # normal text extraction

        # --- Fallback to OCR if text empty ---
        if OCR_AVAILABLE:
            logger.info(f"🧠 OCR fallback for scanned PDF: {os.path.basename(pdf_path)}")
            pages = convert_from_path(pdf_path, dpi=dpi)
            ocr_text = []
            for img in pages:
                t = pytesseract.image_to_string(img)
                if t.strip():
                    ocr_text.append(t.strip())
            return "\n".join(ocr_text).strip(), True
        else:
            logger.warning(f"⚠️ OCR not available for {pdf_path}")
            return "", False

    except Exception as e:
        logger.error(f"⚠️ Text extraction failed for {pdf_path}: {e}")
        return "", False

# =====================================================
# READABLE OUTPUTS: write text files, CSV summary, and pretty JSON
# =====================================================
def safe_filename(name: str) -> str:
    base = os.path.splitext(name)[0]
    return re.sub(r'[\\/:"*?<>|]+', '_', base)

def clean_text_for_storage(s: str) -> str:
    if not s:
        return ""
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = s.strip()
    return s

def write_readable_outputs(records, output_dir, logger):
    """Given list of record dicts (as created below), write:
       - dataset.jsonl (already created in main - optional overwrite)
       - full_texts/<file>.txt cleaned
       - dataset_readable.csv summary
       - dataset_pretty.json pretty array referencing txt files
    """
    full_text_dir = os.path.join(output_dir, "full_texts")
    os.makedirs(full_text_dir, exist_ok=True)

    summary_rows = []
    pretty_list = []

    for rec in records:
        filename = rec.get('filename', '')
        cleaned = clean_text_for_storage(rec.get('full_text', '') or '')
        txt_name = safe_filename(filename) + '.txt' if filename else f'doc_{len(summary_rows)+1}.txt'
        txt_path = os.path.join(full_text_dir, txt_name)

        # write full text file
        with open(txt_path, 'w', encoding='utf-8') as tf:
            tf.write(cleaned)

        text_length = len(cleaned)
        word_count = len(cleaned.split()) if cleaned else 0
        excerpt = cleaned[:800] + ('...' if len(cleaned) > 800 else '')

        row = {
            'filename': filename,
            'title': rec.get('title', ''),
            'author': rec.get('author', ''),
            'year': rec.get('year', ''),
            'producer': rec.get('producer', ''),
            'ocr_used': bool(rec.get('ocr_used', False)),
            'text_length_chars': text_length,
            'word_count': word_count,
            'excerpt': excerpt,
            'full_text_path': os.path.relpath(txt_path, output_dir)
        }
        summary_rows.append(row)

        pretty_rec = {k: row[k] for k in row if k != 'excerpt'}  # omit long excerpt in pretty json
        pretty_list.append(pretty_rec)

    # write CSV
    csv_path = os.path.join(output_dir, 'dataset_readable.csv')
    fields = ['filename','title','author','year','producer','ocr_used','text_length_chars','word_count','excerpt','full_text_path']
    with open(csv_path, 'w', encoding='utf-8', newline='') as cf:
        writer = csv.DictWriter(cf, fieldnames=fields)
        writer.writeheader()
        for r in summary_rows:
            writer.writerow(r)

    # write pretty json
    json_path = os.path.join(output_dir, 'dataset_pretty.json')
    with open(json_path, 'w', encoding='utf-8') as jf:
        json.dump(pretty_list, jf, indent=2, ensure_ascii=False)

    logger.info(f"💾 Readable outputs saved: {csv_path}, {json_path}, full texts in {full_text_dir}")
    return csv_path, json_path, full_text_dir

# =====================================================
# MAIN PIPELINE
# =====================================================
def run_pipeline(url, output_dir, dpi):
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)

    logger.info("🚀 Starting Data Acquisition Pipeline...")
    logger.info(f"Target URL: {url}")
    logger.info(f"Output Directory: {output_dir}")

    scrape_and_download_pdfs(url, output_dir, logger)

    dataset_path = os.path.join(output_dir, DATASET_FILE)
    total = 0
    records = []

    # open dataset.jsonl for writing incrementally
    with open(dataset_path, 'w', encoding='utf-8') as out_f:
        for filename in sorted(os.listdir(output_dir)):
            if not filename.lower().endswith('.pdf'):
                continue

            total += 1
            pdf_path = os.path.join(output_dir, filename)
            logger.info(f"\n📄 Processing: {filename}")

            metadata = extract_metadata(pdf_path, logger)
            text, used_ocr = extract_text_auto_ocr(pdf_path, logger, dpi)

            record = {
                "filename": filename,
                "title": metadata.get('title',''),
                "author": metadata.get('author',''),
                "year": metadata.get('year',''),
                "producer": metadata.get('producer',''),
                "ocr_used": used_ocr,
                "full_text": text
            }

            # write to jsonl
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            records.append(record)

    logger.info(f"\n✅ Data acquisition complete! Total PDFs processed: {len(records)}")
    logger.info(f"📁 Output dataset: {dataset_path}")

    # produce human-readable outputs
    write_readable_outputs(records, output_dir, logger)

# =====================================================
# CLI ENTRY POINT
# =====================================================
def main():
    parser = argparse.ArgumentParser(description="Data Acquisition Pipeline for PDF documents.")
    parser.add_argument("--url", type=str, default=DEFAULT_URL,
                        help="Target website URL containing PDF links.")
    parser.add_argument("--out", type=str, default=os.path.join(get_desktop_path(), DEFAULT_DIR),
                        help="Output directory for downloaded and processed PDFs.")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                        help="DPI used for OCR image conversion.")
    args = parser.parse_args()

    run_pipeline(args.url, args.out, args.dpi)

if __name__ == "__main__":
    main()