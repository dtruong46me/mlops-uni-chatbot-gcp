import os
import sys

from markitdown import MarkItDown
from openai import OpenAI
from dotenv import load_dotenv

__root__ = os.getcwd()
sys.path.append(__root__)

load_dotenv()

PDF_FILENAMES = [
    "qd-phe-duyet-thong-tin-tuyen-sinh-nam-2025-10.06.2025_2.pdf",
    "qd-dhbk_xttn_2025.pdf",
    "5730_qd-dhbk-qcts.pdf"
]

PDF_FILEPATHS = [
    os.path.join(__root__, "data", "raw", "pdf", filename)
    for filename in PDF_FILENAMES
]

OUTPUT_DIR = os.path.join(
    __root__, "data", "processed", "markitdown_pdf"
)
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ---------------

md = MarkItDown(docintel_endpoint="<document_intelligence_endpoint>")

# PDF_FILEPATHS = PDF_FILEPATHS[:1]  # Process only the first PDF for testing
for pdf_filepath in PDF_FILEPATHS:
    result = md.convert(pdf_filepath)

    # Save the result to the output directory, markdown format
    output_filepath = os.path.join(
        OUTPUT_DIR,
        os.path.basename(pdf_filepath).replace(".pdf", ".md")
    )

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(result.text_content)  # type: ignore

    print(f"Processed {pdf_filepath} -> {output_filepath}")

# ---------------