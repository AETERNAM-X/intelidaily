import fitz
import re
import os

PDF_PATH = "Provas-Inteli.pdf"

def find_question_blocks_by_text(pdf_path):
    """Localiza blocos de enunciado no PDF usando 'QUESTÃO XX |' até antes das alternativas"""
    doc = fitz.open(pdf_path)
    question_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        matches = list(re.finditer(r'QUESTÃO\s+\d+\s*\|', text))
        for match in matches:
            y_start = match.start()
            y_end = page.rect.y1

            # cortar no início das alternativas (A) )
            blocks = page.get_text("blocks")
            for block in blocks:
                btext = block[4]
                if re.match(r'^\s*A[\)\.]', btext):
                    y_end = min(y_end, block[1] - 5)
                    break

            rect = fitz.Rect(page.rect.x0 + 20, 50, page.rect.x1 - 20, y_end)
            question_parts.append([{'page': page_num, 'rect': rect}])

    doc.close()
    return question_parts


def capture_question_images(pdf_path, question_parts, output_dir="question_images"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)
    for idx, parts in enumerate(question_parts, 1):
        for part_idx, part in enumerate(parts, 1):
            page = doc[part['page']]
            pix = page.get_pixmap(clip=part['rect'])
            filename = f"questao_{idx}_{part_idx}.png"
            path = os.path.join(output_dir, filename)
            pix.save(path)
    doc.close()
    print(f"✅ Imagens de {len(question_parts)} questões salvas em {output_dir}")


if __name__ == "__main__":
    print(f"➡ Processando PDF: {PDF_PATH}")
    question_parts = find_question_blocks_by_text(PDF_PATH)
    capture_question_images(PDF_PATH, question_parts)
    print("🎉 Finalizado! Enunciados exportados como imagens.")
