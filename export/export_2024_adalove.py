import re
import unicodedata
import os
import base64
import fitz  # PyMuPDF


def normalize_text(text: str) -> str:
    if text is None:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9%\s]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def map_gabarito_to_letter(alternatives_ordered, gabarito_text):
    norm_gab = normalize_text(gabarito_text)
    letters = ['a', 'b', 'c', 'd', 'e']
    for idx, alt in enumerate(alternatives_ordered):
        norm_alt = normalize_text(alt)
        if norm_alt and (norm_alt == norm_gab or norm_alt in norm_gab or norm_gab in norm_alt):
            return letters[idx]
    return None


def parse_gabarito_letter(gabarito_raw, alternatives_ordered):
    m = re.match(r'^\s*([a-eA-E])\b', gabarito_raw)
    if m:
        return m.group(1).lower()
    letter = map_gabarito_to_letter(alternatives_ordered, gabarito_raw)
    return letter if letter else '?'


def extract_questions_from_text(text):
    HEADER_PATTERN = r'Processo de Admissão 2024\.1 – Instituto de Tecnologia e Liderança'
    headers = list(re.finditer(HEADER_PATTERN, text))
    questions = []

    for i, header in enumerate(headers[1:], 1):
        start_pos = header.end()
        next_header = re.search(HEADER_PATTERN, text[start_pos:])
        end_pos = start_pos + next_header.start() if next_header else len(text)
        block = text[start_pos:end_pos].strip()

        sep = re.search(r'-{80,}', block)
        if not sep:
            continue

        question_text = block[:sep.start()].strip()
        tail_text = block[sep.end():].strip()

        gabarito_match = re.search(r'Gabarito:\s*(.+)', tail_text)
        if not gabarito_match:
            continue
        gabarito_raw = gabarito_match.group(1).strip()

        lines = [ln.strip() for ln in question_text.split('\n') if ln.strip()]
        if len(lines) < 5:
            continue
        alternatives_raw = lines[-5:]
        alternatives_clean = []
        for alt in alternatives_raw:
            m = re.match(r'^[a-eA-E][\)\.\-]\s*(.+)', alt)
            alternatives_clean.append(m.group(1).strip() if m else alt.strip())

        while len(alternatives_clean) < 5:
            alternatives_clean.append('')

        gab_letter = parse_gabarito_letter(gabarito_raw, alternatives_clean)

        questions.append({
            'a': alternatives_clean[0],
            'b': alternatives_clean[1],
            'c': alternatives_clean[2],
            'd': alternatives_clean[3],
            'e': alternatives_clean[4],
            'gabarito': gab_letter,
            'gabarito_raw': gabarito_raw,
            'images': []
        })

    return questions


def associate_images_with_questions(questions, folder="question_images"):
    if not os.path.exists(folder):
        return questions
    files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
    for idx, q in enumerate(questions, 1):
        imgs = sorted([f for f in files if f.startswith(f"questao_{idx}_")])
        q['images'] = []
        for name in imgs:
            path = os.path.join(folder, name)
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            q['images'].append({'filename': name, 'base64': b64})
    return questions


def export_questions_to_text(questions, out="2024_questions_alt.txt"):
    with open(out, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions, 1):
            f.write(f"QUESTÃO {i}\n")
            f.write(f"A) {q['a']}\n")
            f.write(f"B) {q['b']}\n")
            f.write(f"C) {q['c']}\n")
            f.write(f"D) {q['d']}\n")
            f.write(f"E) {q['e']}\n")
            f.write(f"GABARITO: {q['gabarito']} ({q['gabarito_raw']})\n")
            f.write("-" * 40 + "\n")


def extract_pdf_with_spaces(pdf_path):
    with fitz.open(pdf_path) as doc:
        all_text = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            all_text.append(page.get_text("text"))
    return "\n".join(all_text)


if __name__ == "__main__":
    pdf_path = "Processo-Seletivo-2024.1.pdf"
    text = extract_pdf_with_spaces(pdf_path)
    questions = extract_questions_from_text(text)
    questions = associate_images_with_questions(questions)
    export_questions_to_text(questions)