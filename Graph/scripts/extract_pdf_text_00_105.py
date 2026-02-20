
import os
import pypdfium2 as pdfium

# Ensure output directory exists for safety, though extraction is in-place
# 获取脚本所在目录的父目录作为项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
source_dir = os.path.join(BASE_DIR, "source", "insurance")

print(f"Scanning directory: {source_dir}")

# Range from 011 to 105
target_prefixes = [f"{i:03d}" for i in range(1, 106)]

pdf_files = []

# List all files and filter manually to handle potential encoding/glob issues better
try:
    all_files = os.listdir(source_dir)
    for f in all_files:
        if f.lower().endswith(".pdf"):
            for prefix in target_prefixes:
                if f.startswith(prefix):
                    pdf_files.append(os.path.join(source_dir, f))
                    break
except Exception as e:
    print(f"Error listing directory: {e}")

print(f"Found {len(pdf_files)} PDF files to process.")

for pdf_path in pdf_files:
    try:
        txt_path = pdf_path + ".txt"
        
        # Check if text file already exists to avoid re-processing if needed (optional, but good for speed)
        # For now, we will overwrite as per user request to "convert all"
        
        print(f"Processing: {pdf_path}")
        pdf = pdfium.PdfDocument(pdf_path)
        text = ""
        for i, page in enumerate(pdf):
            text_page = page.get_textpage()
            text += text_page.get_text_range() + "\n"
        
        # Save text file next to PDF for easy access
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved text to: {txt_path}")
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
