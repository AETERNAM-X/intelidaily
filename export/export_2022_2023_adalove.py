import re
import fitz

PDF_PATH = "Provas-Inteli.pdf"

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        if text:
            all_text.append(text)
    doc.close()
    return "\n".join(all_text)

def extract_questions_from_text(text):
    blocks = re.split(r'QUESTÃO\s+\d+\s*\|', text)[1:]
    questions = []

    for block in blocks:
        gab_match = re.search(r'ALTERNATIVA\s+CORRETA:\s*([A-E])', block, re.IGNORECASE)
        if not gab_match:
            continue
        gab_letter = gab_match.group(1).lower()

        alts = re.findall(r'^\s*([A-E])[\)\.\-]?\s*(.+)', block, re.MULTILINE)
        alts_dict = {a.lower(): txt.strip() for a, txt in alts}

        questions.append({
            'a': alts_dict.get('a', ''),
            'b': alts_dict.get('b', ''),
            'c': alts_dict.get('c', ''),
            'd': alts_dict.get('d', ''),
            'e': alts_dict.get('e', ''),
            'gabarito': gab_letter
        })

    return questions

def export_questions_to_text(questions, out="2022_2023_questions_alt.txt"):
    with open(out, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions, 1):
            f.write(f"QUESTÃO {i}\n")
            f.write(f"A) {q['a']}\n")
            f.write(f"B) {q['b']}\n")
            f.write(f"C) {q['c']}\n")
            f.write(f"D) {q['d']}\n")
            f.write(f"E) {q['e']}\n")
            f.write(f"GABARITO: {q['gabarito'].upper()}\n\n")

if __name__ == "__main__":
    text = extract_text_from_pdf(PDF_PATH)
    questions = extract_questions_from_text(text)
    export_questions_to_text(questions)