import fitz
import re
import os

PDF_FILE = "Processo-Seletivo-2024.1.pdf"
OUTPUT_DIR = "2024_questions_imgs"

def find_question_blocks(pdf_path):
    doc = fitz.open(pdf_path)
    question_parts = []
    header_text = "Processo de Admissão 2024.1 – Instituto de Tecnologia e Liderança"
    all_headers = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        header_rects = page.search_for(header_text)
        if header_rects:
            header_rect = sorted(header_rects, key=lambda r: r.y0)[0]
            all_headers.append({'page': page_num, 'rect': header_rect})

    if len(all_headers) < 2:
        doc.close()
        return []

    for i in range(1, len(all_headers)):
        current = all_headers[i]
        next_h = all_headers[i + 1] if i + 1 < len(all_headers) else None

        parts = []
        current_page_num = current['page']
        next_page_num = next_h['page'] if next_h else len(doc) - 1

        for p in range(current_page_num, next_page_num + 1):
            page = doc[p]
            y_start = current['rect'].y1 + 10 if p == current_page_num else page.rect.y0 + 20
            y_end = page.rect.y1 - 20

            if p == next_page_num:
                text_blocks = page.get_text("blocks")
                for block in sorted(text_blocks, key=lambda b: b[1]):
                    text = block[4]
                    y0 = block[1]
                    if y0 < y_start:
                        continue
                    if re.search(r'^\s*[aA][\)\.]', text) or re.search(r'[-=~]{10,}', text) or re.search(r'^\s*\d+\.\s*', text):
                        y_end = min(y_end, y0 - 5)
                        break

            if next_h and p == next_page_num:
                y_end = min(y_end, next_h['rect'].y0 - 20)

            x0, x1 = page.rect.x0 + 20, page.rect.x1 - 20
            if y_start < y_end:
                parts.append({'page': p, 'rect': fitz.Rect(x0, y_start, x1, y_end)})

        if parts:
            question_parts.append(parts)

    doc.close()
    return question_parts

def capture_question_images(pdf_path, question_parts, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)
    for q_num, q_parts in enumerate(question_parts, 1):
        rects = [part['rect'] for part in q_parts]
        pages = [part['page'] for part in q_parts]
        combined_pixmaps = []
        for page_num, rect in zip(pages, rects):
            page = doc.load_page(page_num)
            combined_pixmaps.append(page.get_pixmap(clip=rect, dpi=300))
        if combined_pixmaps:
            pix = combined_pixmaps[0]
            filename = f"questao_{q_num}.png"
            path = os.path.join(output_dir, filename)
            pix.save(path)
    doc.close()

if __name__ == "__main__":
    question_parts = find_question_blocks(PDF_FILE)
    if question_parts:
        capture_question_images(PDF_FILE, question_parts, OUTPUT_DIR)