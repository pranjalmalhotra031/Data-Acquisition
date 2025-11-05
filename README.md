# Data-Acquisition
It involves fetching PDFs using web scraping, extraction of text from those PDFs, cleaning the metadata and then storing structured text and metadata.

# 🧠 Data Acquisition Pipeline with OCR and Readable Outputs
This project automates the **data acquisition and preprocessing** of PDF documents from web sources. It handles scraping, downloading, metadata extraction, text extraction, and OCR fallback for scanned PDFs. The output is both machine-readable (JSONL) and human-friendly (CSV, pretty JSON, and separate text files).

---

## 🚀 Features
✅ **Automated PDF Scraping** – Fetches and downloads all PDF files from a target webpage.  
✅ **Metadata Extraction** – Extracts title, author, producer, and year using 'pikepdf'.  
✅ **Text Extraction** – Reads embedded text from PDFs using 'PyMuPDF'.  
✅ **OCR Fallback** – Uses 'Tesseract' via 'pytesseract' for scanned or image-only PDFs.  
✅ **Readable Output Files** – Generates:
  - 'dataset.jsonl' → raw machine-readable records
  - 'dataset_readable.csv' → clean summary for humans
  - 'dataset_pretty.json' → formatted JSON array
  - 'full_texts/' → cleaned text for each document  
✅ **Logging** – Saves progress and warnings to 'data_acquisition.log'.  
✅ **Command-Line Interface** – Customizable URL, output directory, and OCR DPI.

---

## 🗂️ Output Structure
Scraped_PDFs/
├── file1.pdf
├── file2.pdf
├── dataset.jsonl
├── dataset_readable.csv
├── dataset_pretty.json
├── full_texts/
│   ├── file1.txt
│   ├── file2.txt
└── data_acquisition.log

---

## ⚙️ Installation

### 1️⃣ Install Dependencies
#### Minimal (without OCR):
bash
pip install requests beautifulsoup4 lxml pymupdf pikepdf
#### With OCR Support (recommended):
bash
pip install pdf2image pytesseract pillow

### 2️⃣ Install Tesseract OCR Engine
#### 🪟 Windows
Download from [UB Mannheim Builds] (https://github.com/UB-Mannheim/tesseract/wiki)
Install to:
C:\Program Files\Tesseract-OCR
Make sure to check **“Add to system PATH”**.

#### 🍏 macOS
bash
brew install tesseract

#### 🐧 Linux (Ubuntu/Debian)
bash
sudo apt update && sudo apt install tesseract-ocr

Verify installation:
bash
tesseract --version

---

## 🧠 How It Works
1. **Scrape & Download PDFs** – Collects and saves all linked PDF files from a webpage.  
2. **Extract Metadata** – Reads basic document info using 'pikepdf'.  
3. **Extract Text** – Pulls text from each page using 'PyMuPDF'.  
4. **OCR Fallback** – Automatically runs OCR on scanned PDFs if text extraction fails.  
5. **Create Outputs** – Writes data into 'dataset.jsonl', then formats for readability (CSV, JSON, and text files).  

---

## 📈 Example Use Cases
- Building datasets of research papers or reports.  
- Archiving scanned documents with OCR.  
- Creating corpora for NLP and text mining.  
- Metadata cataloging for digital libraries.

---

## 🧾 Example Command
bash
python main_data_acquisition.py --url https://dyysg.org.uk/docs.php --out "C:/Users/YourName/Desktop/Scraped_PDFs" --dpi 150

---

## 🧩 Credits
Developed as part of the **Data Acquisition Module** in a data processing project.  
Built with:
- **Python** 3.9+
- 'requests', 'beautifulsoup4', 'pikepdf', 'PyMuPDF', 'pytesseract', 'pdf2image'

---

✨ *This pipeline forms the foundation of a full data processing system — from acquisition to cleaning, clustering, and visualization.*
