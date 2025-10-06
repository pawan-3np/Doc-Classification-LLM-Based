# import os
# import fitz  # PyMuPDF
# import google.generativeai as genai
# import json
# import re
# from tqdm import tqdm
# import logging
# from time import sleep

# import pytesseract
# from pdf2image import convert_from_path
# from PIL import Image

# # If Tesseract is not in PATH, set manually:
# # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# # ========== CONFIG ==========
# PDF_PATH = r"C:\Users\PawanMagapalli\Downloads\Paystub (1)_merged.pdf"
# GOOGLE_API_KEY = "AIzaSyDOYqZRXyCVkzWe6zX3ZXOpcZh5k9C0tsM"
# EXTRACTED_TEXT_DIR = "extracted_text"
# OUTPUT_DIR = "output_docs"
# LOCAL_MATCH_THRESHOLD = 0.2  # 20% keyword match to skip Gemini

# # ========== LOGGER ==========
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # ========== GEMINI SETUP ==========
# genai.configure(api_key=GOOGLE_API_KEY)
# model = genai.GenerativeModel("models/gemini-2.0-flash")

# # ========== DOCUMENT TYPES ==========
# doc_types = {
#     "W2": {
#         "match_keywords": [
#             "w2", "form w2", "wage and tax statement", "wages, tips, other compensation",
#             "w4", "employee's social security number", "employer identification number",
#             "medicare wages and tips", "federal income tax withheld", "notice to employee"
#         ]
#     },
#     "Social Security Award Letter": {
#         "match_keywords": [
#             "social security administration", "supplemental security income", "claim number",
#             "bnc number", "we are writing to tell you", "important information",
#             "you may be eligible for additional benefits"
#         ]
#     },
#     "Borrower Authorization": {
#         "match_keywords": [
#             "borrower's certification & authorization certification",
#             "Signature Addendum",
#             "certification and authorization to release information", "borrower signature",
#             "co borrower signature", "co applicant signature", "borrower signature date",
#             "co borrower signature date", "co applicant signature date", "signature addendum"
#         ]
#     },
#     "Paystub": {
#         "match_keywords": [
#             "pay statement", "paystub", "earnings description", "gross wages", "net pay",
#             "deductions", "payroll period", "taxable wages", "year to date",
#             "employer name", "employee id", "withholding"
#         ]
#     },
#     "Driver License": {
#         "match_keywords": [
#             "class", "dl number", "date of birth", "first name of borrower", "middle name of borrower",
#             "last name of borrower", "expiry date", "issue date"
#         ]
#     }
# }

# # ========== TEXT EXTRACTION WITH OCR FALLBACK ==========
# def extract_text_from_pdf(pdf_path):
#     logging.info("Extracting text from PDF...")
#     os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)
#     doc = fitz.open(pdf_path)
#     images = convert_from_path(pdf_path, dpi=300)
#     pages = []

#     for i, page in enumerate(doc):
#         text = page.get_text().strip()
#         page_num = i + 1

#         # Use OCR if text is empty or too short
#         if len(text) < 50:
#             logging.info(f"🔍 Page {page_num}: using OCR")
#             image = images[i]
#             text = pytesseract.image_to_string(image)

#         # Save for debugging
#         filename = os.path.join(EXTRACTED_TEXT_DIR, f"page_{page_num}.txt")
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(text)

#         pages.append({"page_number": page_num, "text": text})

#     return pages

# # ========== LOCAL KEYWORD MATCH ==========
# # def local_keyword_match(page_text, doc_types):
# #     page_text_lower = page_text.lower()
# #     best_match = {"type": "Unknown", "ratio": 0}

# #     for doc_type, data in doc_types.items():
# #         keywords = data["match_keywords"]
# #         matched_keywords = sum(1 for kw in keywords if kw.lower() in page_text_lower)
# #         ratio = matched_keywords / len(keywords) if keywords else 0

# #         if ratio > best_match["ratio"]:
# #             best_match = {"type": doc_type, "ratio": ratio}

# #     return best_match["type"] if best_match["ratio"] >= LOCAL_MATCH_THRESHOLD else "Unknown"

# # ========== GEMINI CLASSIFICATION ==========
# def classify_pages_with_gemini(pages, doc_types):
#     logging.info("Classifying ALL pages using Gemini only (no local keyword matching)...")
#     results = []

#     doc_types_str = json.dumps(doc_types, indent=2)

#     for page in tqdm(pages):
#         prompt = f"""
# You are a mortgage document classifier.

# You will be given:
# 1. A set of document types, each with a list of match_keywords.
# 2. The full text of a page from a mortgage PDF.

# Your job is to return the most likely document type this page belongs to.

# Rules:
# - Only return one of the provided document types.
# - If no clear match, return "Unknown"
# - Use case-insensitive and partial keyword matching.
# - Some documents like Driver License are usually only one page.

# Document types and keywords:
# {doc_types_str}

# Text of page {page['page_number']}:
# \"\"\"
# {page['text'][:5000]}
# \"\"\"

# Return format:
# {{"page": {page['page_number']}, "document_type": "TYPE"}}
# """

#         for attempt in range(3):
#             try:
#                 response = model.generate_content(prompt)
#                 match = re.search(r"\{.*\}", response.text, re.DOTALL)
#                 if match:
#                     result = json.loads(match.group(0))
#                     results.append(result)
#                     break
#                 else:
#                     logging.warning(f"⚠️ Could not parse JSON on page {page['page_number']}")
#                     results.append({"page": page['page_number'], "document_type": "Unknown"})
#                     break
#             except Exception as e:
#                 logging.error(f"Error classifying page {page['page_number']} (attempt {attempt + 1}): {e}")
#                 if attempt < 2:
#                     logging.info("Retrying...")
#                     sleep(2)
#                 else:
#                     results.append({"page": page['page_number'], "document_type": "Unknown"})

#     return results


# # ========== SPLIT AND SAVE ==========
# def split_pdf(original_pdf_path, grouped_docs):
#     logging.info("Saving grouped PDFs...")
#     os.makedirs(OUTPUT_DIR, exist_ok=True)
#     pdf = fitz.open(original_pdf_path)

#     for group in grouped_docs:
#         doc_type = group["type"] or "Unknown"
#         output_pdf = fitz.open()
#         for page_num in group["pages"]:
#             output_pdf.insert_pdf(pdf, from_page=page_num - 1, to_page=page_num - 1)

#         start = group["pages"][0]
#         end = group["pages"][-1]
#         filename = f"{doc_type.replace(' ', '_')}_{start}-{end}.pdf" if start != end else f"{doc_type.replace(' ', '_')}_{start}.pdf"
#         filepath = os.path.join(OUTPUT_DIR, filename)
#         output_pdf.save(filepath)
#         logging.info(f"✅ Saved: {filepath}")

# # ========== MAIN ==========
# def main():
#     pages = extract_text_from_pdf(PDF_PATH)
#     classified = classify_pages_with_gemini(pages, doc_types)
#     grouped = group_pages(classified, contiguous=True)
#     split_pdf(PDF_PATH, grouped)
#     logging.info("✅ All done.")

# if __name__ == "__main__":
#     main()


import os
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
from tqdm import tqdm
import logging
from time import sleep

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# ========= CONFIG ==========
PDF_PATH = r"C:\Users\PawanMagapalli\Downloads\ilovepdf_merged (4).pdf"
GOOGLE_API_KEY = "AIzaSyBTjC6ptrYbiZ_glKf-hSBTjRS3RvawZxw"  # Replace with your actual key
EXTRACTED_TEXT_DIR = "extracted_text"
OUTPUT_DIR = "output_docs"

# ========= LOGGER ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ========= GEMINI SETUP ==========
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-2.0-flash")

# ========= DOCUMENT TYPES ==========
doc_types = {
    "W2": {
        "match_keywords": [
            "w2", "form w2", "wage and tax statement", "wages, tips, other compensation",
            "w4", "employee's social security number", "employer identification number",
            "medicare wages and tips", "federal income tax withheld", "notice to employee"
        ]
    },
    "Social Security Award Letter": {
        "match_keywords": [
            "social security administration", "supplemental security income", "claim number",
            "bnc number", "we are writing to tell you", "important information",
            "you may be eligible for additional benefits"
        ]
    },
    "Borrower Authorization": {
        "match_keywords": [
            "borrower's certification & authorization certification",
            "Signature Addendum",
            "certification and authorization to release information", "borrower signature",
            "co borrower signature", "co applicant signature", "borrower signature date",
            "co borrower signature date", "co applicant signature date", "signature addendum"
        ]
    },
    "Paystub": {
        "match_keywords": [
           "pay statement",
      "paystub",
      "earnings description",
      "gross wages",
      "net pay",
      "deductions",
      "payroll period",
      "taxable wages",
      "year to date",
      "employer name",
      "employee id",
      "withholding"
        ]
    },
    "Driver License": {
        "match_keywords": [
            "class", "dl number", "date of birth", "first name of borrower", "middle name of borrower",
            "last name of borrower", "expiry date", "issue date"
        ]
    },
    "Tax_certificate": {
        "match_keywords": [
            "tax certificate", "tax document", "tax statement", "tax year", "taxpayer identification number",
            "income tax", "withholding tax", "tax authority", "tax payment", "tax return"
        ]
},
  "Verification of Employment (VOE)": {
        "match_keywords": [
           "verification of employment", "voe", "employer verification", "employment status","original hire date","current employment status","position title","annual salary","supervisor name","contact information","employment verification"
           "pay details information", "pay frequency", "year to date earnings", "gross pay", "net pay", "deductions"
        ]
    },

    "EMD":{
        "match_keywords": [
           "pay to the order of", "earnest money deposit", "escrow", "deposit amount", "buyer", "seller", "transaction", "agreement", "contract", "real estate"
        ]
    },

    "GIFT":{
        "match_keywords": [
            "To whom it may concern", "this letter confirms that the undersigned is making a financial gift of"
            , "for use toward the purchase that the undersigned is making a financial gift", "we, the undersigned recipients and donors , hereby certify " ,""
            "the donor is an imediate family memeber "
            "thse funds are a genuine gift from the the doinors; as such, are not required to be repaid at any time"
            "No part of tje finanacial gift is being provided by any third party having any interest(direct or indirect) in the sale of the subject property"
        ]
    },

    
  "Purchase Contract": {
    "match_keywords": [
      "Contract Date",
      "Buyer Name",
      "Seller Name",
      "Property Address",
      "Purchase Price",
      "EMD",
      "Parcel Number",
      "Property Identifier",
      "Other Deposit",
      "Loan Amount",
      "Interest Rate",
      "Loan Type",
      "Seller Credit",
      "Buydown fees",
      "Allocation of Cost",
      "Closing Date",
      "Expiration of Offer",
      "Inspection",
      "List of attached Addendum and Disclosures",
      "Counter Offer",
      "Possession",
      "Repairs",
      "Contigencies",
      "Non-Realty Items",
      "Buyer's Signature",
      "Buyer's Signature Date",
      "Seller's Signature",
      "Seller Signature date",
      "Buyer's Initial",
      "Seller's Initial",
      "Seller's Agent Name",
      "Seller's Agent Address",
      "Seller's Agent License Number",
      "Seller's Agent Phone number",
      "Seller's Agent Email",
      "Buyer's Agent Name",
      "Buyer's Agent Address",
      "Buyer's Agent License Number",
      "Buyer's Agent Phone number",
      "Buyer's Agent Email",
      "Seller Agent Company Name",
      "Seller Agent Company Address",
      "Seller Agent Company License",
      "Buyer's agent Company address",
      "Buyer's agent Company Name",
      "Buyer's agent Company License",
      "Seller's agent signature",
      "Buyer's agent signature",
      "FSBO",
      "Title Company Name",
      "FHA Amendatory Clause Text",
      "Real Estate Certification Clause",
      "Appraised Value amount"
    ]
  }, 

  "Flood Certificate": {
    "match_keywords": [
      "Lender",
      "Subject Property Address line 1",
      "City",
      "State",
      "Zip code",
      "Borrower first name",
      "Borrower middle name",
      "Borrower last name",
      "Loan Number",
      "County Name",
      "NFIP Map Number",
      "NFIP Map Date",
      "Flood Zone Code",
      "Subject is in flood zone or not",
      "Flood Cert Date",
      "Flood cert order ID",
      "Life of Loan",
      "Flood Cert Provider's Name",
      "Flood Cert Provider's Address line 1",
      "Flood Cert Provider's City",
      "Flood Cert Provider's State",
      "Flood Cert Provider's Zip code",
      "Flood Cert Provider's phone number"
    ]
  }

}

# ========= TEXT EXTRACTION WITH OCR ==========
def extract_text_from_pdf(pdf_path):
    logging.info("Extracting text from PDF...")
    os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)
    doc = fitz.open(pdf_path)
    images = convert_from_path(pdf_path, dpi=300)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text().strip()
        page_num = i + 1

        # Use OCR if text is missing or too short
        if len(text) < 50:
            logging.info(f"🔍 Page {page_num}: using OCR fallback")
            image = images[i]
            text = pytesseract.image_to_string(image)

        # Save text to file for inspection
        filename = os.path.join(EXTRACTED_TEXT_DIR, f"page_{page_num}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)

        pages.append({"page_number": page_num, "text": text})

    return pages

# ========= CLASSIFY USING GEMINI ==========
def classify_pages_with_gemini(pages, doc_types):
    logging.info("Classifying pages using Gemini (semantic understanding enabled)...")
    results = []

    doc_types_str = json.dumps(doc_types, indent=2)

    for page in tqdm(pages):
        prompt = f"""
You are a highly skilled mortgage document classifier AI.

You will receive:
1. A list of document types. Each type has associated keywords or key phrases that may occur in documents of that type.
2. The full extracted text from a single page of a mortgage-related PDF document.

Your task is to determine the **most appropriate document type** this page represents by **analyzing both direct keyword matches and semantic meaning** (i.e., even if the exact phrase doesn't appear, use your understanding of language to detect equivalent or related terms).

Rules:
- You must return exactly one of the provided document types, or return "Unknown" if no type is a strong fit.
- Do not rely solely on exact keyword matching; use your understanding of the intent and meaning behind the keywords.
- Consider edge cases like abbreviations (e.g., "SSN" for "Social Security Number"), rephrased content, missing headers, or unusual formatting.
- Some documents like "Driver License" or "Paystub" may have only one page.
- Ignore unrelated information like page numbers, footers, or scanned artifacts.

Example Edge Cases to Handle:
- If a paystub doesn’t say “paystub” but shows net pay, gross pay, and tax info, classify it as Paystub.
- If the page looks like a Social Security Award letter but uses informal wording, still classify it correctly.
- If it's a scanned image OCR’d poorly, focus on whatever partial data is available.

Document types and their keyword indicators:
{doc_types_str}

Text of the document (Page {page['page_number']}):
\"\"\"
{page['text'][:5000]}
\"\"\"

Expected Output:
Return only a valid JSON object in the following format:
{{"page": {page['page_number']}, "document_type": "TYPE"}}
"""

        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if match:
                    result = json.loads(match.group(0))
                    results.append(result)
                    break
                else:
                    logging.warning(f"⚠️ Could not parse JSON on page {page['page_number']}")
                    results.append({"page": page['page_number'], "document_type": "Unknown"})
                    break
            except Exception as e:
                logging.error(f"Error classifying page {page['page_number']} (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    logging.info("Retrying...")
                    sleep(2)
                else:
                    results.append({"page": page['page_number'], "document_type": "Unknown"})

    return results

# ========= GROUP PAGES ==========
def group_pages(classified_pages, contiguous=True):
    logging.info("Grouping classified pages...")
    if contiguous:
        groups = []
        current_doc = {"type": None, "pages": []}

        for item in classified_pages:
            if item["document_type"] != current_doc["type"]:
                if current_doc["type"] and current_doc["pages"]:
                    groups.append(current_doc)
                current_doc = {"type": item["document_type"], "pages": [item["page"]]}
            else:
                current_doc["pages"].append(item["page"])

        if current_doc["type"] and current_doc["pages"]:
            groups.append(current_doc)

        return groups
    else:
        # Non-contiguous grouping
        groups = {}
        for item in classified_pages:
            doc_type = item["document_type"] or "Unknown"
            groups.setdefault(doc_type, []).append(item["page"])
        return [{"type": k, "pages": v} for k, v in groups.items()]

# ========= SPLIT AND SAVE ==========
def split_pdf(original_pdf_path, grouped_docs):
    logging.info("Saving grouped PDFs...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf = fitz.open(original_pdf_path)

    for group in grouped_docs:
        doc_type = group["type"] or "Unknown"
        output_pdf = fitz.open()
        for page_num in group["pages"]:
            output_pdf.insert_pdf(pdf, from_page=page_num - 1, to_page=page_num - 1)

        start = group["pages"][0]
        end = group["pages"][-1]
        filename = f"{doc_type.replace(' ', '_')}_{start}-{end}.pdf" if start != end else f"{doc_type.replace(' ', '_')}_{start}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        output_pdf.save(filepath)
        logging.info(f"✅ Saved: {filepath}")

# ========= MAIN ==========
def main():
    pages = extract_text_from_pdf(PDF_PATH)
    classified = classify_pages_with_gemini(pages, doc_types)
    grouped = group_pages(classified, contiguous=True)
    split_pdf(PDF_PATH, grouped)
    logging.info("✅ All done.")

if __name__ == "__main__":
    main()
