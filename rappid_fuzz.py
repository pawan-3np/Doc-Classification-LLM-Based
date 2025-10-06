import fitz  # PyMuPDF
import yaml
import os
from collections import defaultdict
from PIL import Image, ImageEnhance
import pytesseract
from rapidfuzz import fuzz
import re
import logging

def load_doc_type_rules(yml_path):
    if not os.path.exists(yml_path):
        print(f"Error: The rules file '{yml_path}' does not exist.")
        return None
    with open(yml_path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    return rules.get("doc_types", None)

def extract_text_with_ocr(page):
    text = page.get_text("text").strip()
    if text:
        return text.lower()
    # Fallback to OCR
    pix = page.get_pixmap(dpi=400)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = img.convert("L")
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.5)
    threshold = 110
    img = img.point(lambda x: 0 if x < threshold else 255, '1')
    text = pytesseract.image_to_string(img, config='--psm 6')
    return text.lower().strip() if text.strip() else "[empty]"

def split_into_sentences(text):
    # Basic sentence splitter (you can improve with nltk if needed)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def identify_doc_type_fuzzy(text, rules, threshold=90):
    matched_keywords = defaultdict(list)
    for doc_type, props in rules.items():
        if not props or "match_keywords" not in props or not props["match_keywords"]:
            continue
        for kw in props["match_keywords"]:
            score = fuzz.token_set_ratio(kw.lower(), text.lower())
            if score >= threshold:
                matched_keywords[doc_type].append((kw, score))
    return matched_keywords

def classify_page(sentences, rules, threshold=90, min_matches=3):
    doc_type_match_counts = defaultdict(int)
    doc_type_matched_keywords = defaultdict(list)

    for sentence in sentences:
        matched = identify_doc_type_fuzzy(sentence, rules, threshold=threshold)
        for doc_type, kw_list in matched.items():
            doc_type_match_counts[doc_type] += len(kw_list)
            doc_type_matched_keywords[doc_type].extend(kw_list)

    # Select doc_type with max matches over min_matches threshold
    if not doc_type_match_counts:
        return None, [], 0

    best_doc_type = max(doc_type_match_counts, key=doc_type_match_counts.get)
    best_count = doc_type_match_counts[best_doc_type]

    if best_count >= min_matches:
        return best_doc_type, doc_type_matched_keywords[best_doc_type], best_count
    else:
        return None, [], 0

def split_pdf_by_doc_type(pdf_path, yml_path, output_dir, threshold=90, min_matches=3):
    os.makedirs(output_dir, exist_ok=True)
    rules = load_doc_type_rules(yml_path)
    if not rules:
        print("No rules found or failed to load rules.")
        return
    pdf = fitz.open(pdf_path)
    print(f"Total pages in PDF: {len(pdf)}")
    grouped_pages = defaultdict(list)
    unknown_pages = []
    page_summaries = []

    for i, page in enumerate(pdf):
        print(f"\n--- Processing Page {i + 1} ---")
        text = extract_text_with_ocr(page)
        sentences = split_into_sentences(text)
        text_file_path = os.path.join(output_dir, f"page_{i + 1}_extracted.txt")
        with open(text_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(text)

        doc_type, matched_keywords, match_count = classify_page(
            sentences, rules, threshold=threshold, min_matches=min_matches
        )

        preview = text[:200].replace('\n', ' ')
        print(f"Classified as: {doc_type if doc_type else 'Unknown'}")
        print(f"Matched keywords ({match_count}): {matched_keywords}")
        print(f"Preview: {preview}...")

        page_summaries.append({
            "page": i + 1,
            "type": doc_type if doc_type else 'Unknown',
            "matched_keywords": matched_keywords,
            "match_count": match_count,
            "preview": preview
        })
        if doc_type:
            grouped_pages[doc_type].append(i)
        else:
            unknown_pages.append(i)

    print("\n=== Summary ===")
    for summary in page_summaries:
        print(f"Page {summary['page']}: {summary['type']} | Matched keywords ({summary['match_count']}): {summary['matched_keywords']} | {summary['preview']}...")

    for doc_type, page_indices in grouped_pages.items():
        new_doc = fitz.open()
        for idx in page_indices:
            new_doc.insert_pdf(pdf, from_page=idx, to_page=idx)
        output_file = os.path.join(output_dir, f"{doc_type}.pdf")
        new_doc.save(output_file)
        new_doc.close()
        print(f"✅ Saved: {output_file} ({len(page_indices)} pages)")

    if unknown_pages:
        print(f"\n⚠️ {len(unknown_pages)} pages could not be classified.")
        unknown_doc = fitz.open()
        for idx in unknown_pages:
            unknown_doc.insert_pdf(pdf, from_page=idx, to_page=idx)
        unknown_path = os.path.join(output_dir, "unclassified.pdf")
        unknown_doc.save(unknown_path)
        unknown_doc.close()
        print(f"⚠️ Saved unclassified pages: {unknown_path}")

    print(f"\nTotal pages: {len(pdf)}")
    total_classified = sum(len(pages) for pages in grouped_pages.values())
    print(f"Classified pages: {total_classified}")
    print(f"Unclassified pages: {len(unknown_pages)}")

if __name__ == "__main__":
    split_pdf_by_doc_type(
        pdf_path=r"C:\Users\PawanMagapalli\Downloads\ilovepdf_merged (2).pdf",
        yml_path=r"rule.yml",
        output_dir="output_docs",
        threshold=90,
        min_matches=1
    )

# import fitz  # PyMuPDF
# import yaml
# import os
# from collections import defaultdict
# from PIL import Image, ImageEnhance
# import pytesseract
# from rapidfuzz import fuzz
# import re

# def load_doc_type_rules(yml_path):
#     if not os.path.exists(yml_path):
#         print(f"Error: The rules file '{yml_path}' does not exist.")
#         return None
#     with open(yml_path, "r", encoding="utf-8") as f:
#         rules = yaml.safe_load(f)
#     return rules.get("doc_types", None)

# def extract_text_with_ocr(page):
#     text = page.get_text("text").strip()
#     if text:
#         return text.lower()
#     # Fallback to OCR
#     pix = page.get_pixmap(dpi=400)
#     img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
#     img = img.convert("L")
#     enhancer = ImageEnhance.Contrast(img)
#     img = enhancer.enhance(2.5)
#     threshold = 110
#     img = img.point(lambda x: 0 if x < threshold else 255, '1')
#     text = pytesseract.image_to_string(img, config='--psm 6')
#     return text.lower().strip() if text.strip() else "[empty]"

# def split_into_sentences(text):
#     sentences = re.split(r'(?<=[.!?])\s+', text)
#     return [s.strip() for s in sentences if s.strip()]

# def identify_doc_type_fuzzy(text, rules, threshold=90):
#     matched_keywords = defaultdict(list)
#     for doc_type, props in rules.items():
#         if not props or "match_keywords" not in props or not props["match_keywords"]:
#             continue
#         for kw in props["match_keywords"]:
#             score = fuzz.token_set_ratio(kw.lower(), text.lower())
#             if score >= threshold:
#                 matched_keywords[doc_type].append((kw, score))
#     return matched_keywords

# def classify_page(sentences, rules, threshold=90, min_match_percentage=100):
#     doc_type_match_counts = defaultdict(int)
#     doc_type_matched_keywords = defaultdict(list)

#     for sentence in sentences:
#         matched = identify_doc_type_fuzzy(sentence, rules, threshold=threshold)
#         for doc_type, kw_list in matched.items():
#             doc_type_match_counts[doc_type] += len(kw_list)
#             doc_type_matched_keywords[doc_type].extend(kw_list)

#     if not doc_type_match_counts:
#         return None, [], 0

#     match_percentages = {}
#     for doc_type, count in doc_type_match_counts.items():
#         total_keywords = len(rules.get(doc_type, {}).get("match_keywords", []))
#         if total_keywords == 0:
#             continue
#         match_percentages[doc_type] = (count / total_keywords) * 100

#     if not match_percentages:
#         return None, [], 0

#     best_doc_type = max(match_percentages, key=match_percentages.get)
#     best_percentage = match_percentages[best_doc_type]
#     best_count = doc_type_match_counts[best_doc_type]

#     if best_percentage >= min_match_percentage:
#         return best_doc_type, doc_type_matched_keywords[best_doc_type], best_count
#     else:
#         return None, [], 0

# def split_pdf_by_doc_type(pdf_path, yml_path, output_dir, threshold=90, min_match_percentage=100):
#     os.makedirs(output_dir, exist_ok=True)
#     rules = load_doc_type_rules(yml_path)
#     if not rules:
#         print("No rules found or failed to load rules.")
#         return

#     pdf = fitz.open(pdf_path)
#     print(f"Total pages in PDF: {len(pdf)}")

#     grouped_pages = defaultdict(list)
#     unknown_pages = []
#     page_summaries = []

#     for i, page in enumerate(pdf):
#         print(f"\n--- Processing Page {i + 1} ---")
#         text = extract_text_with_ocr(page)
#         sentences = split_into_sentences(text)
#         text_file_path = os.path.join(output_dir, f"page_{i + 1}_extracted.txt")
#         with open(text_file_path, "w", encoding="utf-8") as txt_file:
#             txt_file.write(text)

#         doc_type, matched_keywords, match_count = classify_page(
#             sentences, rules, threshold=threshold, min_match_percentage=min_match_percentage
#         )

#         preview = text[:200].replace('\n', ' ')
#         print(f"Classified as: {doc_type if doc_type else 'Unknown'}")
#         print(f"Matched keywords ({match_count}): {matched_keywords}")
#         print(f"Preview: {preview}...")

#         page_summaries.append({
#             "page": i + 1,
#             "type": doc_type if doc_type else 'Unknown',
#             "matched_keywords": matched_keywords,
#             "match_count": match_count,
#             "preview": preview
#         })

#         if doc_type:
#             grouped_pages[doc_type].append(i)
#         else:
#             unknown_pages.append(i)

#     print("\n=== Summary ===")
#     for summary in page_summaries:
#         print(f"Page {summary['page']}: {summary['type']} | Matched keywords ({summary['match_count']}): {summary['matched_keywords']} | {summary['preview']}...")

#     for doc_type, page_indices in grouped_pages.items():
#         new_doc = fitz.open()
#         for idx in page_indices:
#             new_doc.insert_pdf(pdf, from_page=idx, to_page=idx)
#         output_file = os.path.join(output_dir, f"{doc_type}.pdf")
#         new_doc.save(output_file)
#         new_doc.close()
#         print(f"✅ Saved: {output_file} ({len(page_indices)} pages)")

#     if unknown_pages:
#         print(f"\n⚠️ {len(unknown_pages)} pages could not be classified.")
#         unknown_doc = fitz.open()
#         for idx in unknown_pages:
#             unknown_doc.insert_pdf(pdf, from_page=idx, to_page=idx)
#         unknown_path = os.path.join(output_dir, "unclassified.pdf")
#         unknown_doc.save(unknown_path)
#         unknown_doc.close()
#         print(f"⚠️ Saved unclassified pages: {unknown_path}")

#     print(f"\nTotal pages: {len(pdf)}")
#     total_classified = sum(len(pages) for pages in grouped_pages.values())
#     print(f"Classified pages: {total_classified}")
#     print(f"Unclassified pages: {len(unknown_pages)}")

# if __name__ == "__main__":
#     split_pdf_by_doc_type(
#         pdf_path=r"C:\Users\PawanMagapalli\Downloads\document\Doc-Classification\merged doc.pdf",
#         yml_path=r"rule.yml",
#         output_dir="output_docs",
#         threshold=90,
#         min_match_percentage=100  # ✅ Only classify if 100% of keywords are matched
#     )
