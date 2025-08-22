import sqlite3
import re
import fitz  # PyMuPDF

DB_PATH = "questions.db"
PDF_PATH = "Provas-Inteli.pdf"


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            a TEXT,
            b TEXT,
            c TEXT,
            d TEXT,
            e TEXT,
            gabarito TEXT,
            fonte TEXT DEFAULT 'Provas-Inteli-2022.1',
            imagens TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()


def extract_text_from_pdf(pdf_path):
    """Extrai texto cru do PDF"""
    doc = fitz.open(pdf_path)
    all_text = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        if text:
            all_text.append(text)
    doc.close()
    return "\n".join(all_text)


def extract_questions_from_text(text):
    """Extrai apenas alternativas e gabarito"""
    blocks = re.split(r'QUESTÃO\s+\d+\s*\|', text)[1:]
    questions = []

    for block in blocks:
        # Gabarito
        gab_match = re.search(r'ALTERNATIVA\s+CORRETA:\s*([A-E])', block, re.IGNORECASE)
        if not gab_match:
            continue
        gab_letter = gab_match.group(1).lower()

        # Alternativas
        alts = re.findall(r'^\s*([A-E])[\)\.\-]?\s*(.+)', block, re.MULTILINE)
        alts_dict = {a.lower(): txt.strip() for a, txt in alts}

        questions.append({
            'a': alts_dict.get('a', ''),
            'b': alts_dict.get('b', ''),
            'c': alts_dict.get('c', ''),
            'd': alts_dict.get('d', ''),
            'e': alts_dict.get('e', ''),
            'gabarito': gab_letter,
            'images': []
        })

    return questions


def save_to_database(questions):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for q in questions:
        cursor.execute('''
            INSERT INTO questoes (a, b, c, d, e, gabarito, imagens)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            q['a'], q['b'], q['c'], q['d'], q['e'],
            q['gabarito'], '[]'
        ))
    conn.commit()
    conn.close()


def export_questions_to_text(questions, out="questoes_alternativas.txt"):
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
    print("➡ Criando banco...")
    create_database()

    print(f"➡ Extraindo texto do PDF: {PDF_PATH}")
    text = extract_text_from_pdf(PDF_PATH)

    print("➡ Processando alternativas + gabaritos...")
    questions = extract_questions_from_text(text)
    print(f"✅ {len(questions)} questões extraídas")

    print("➡ Salvando no banco...")
    save_to_database(questions)

    print("➡ Exportando para TXT...")
    export_questions_to_text(questions)

    print("🎉 Finalizado! Alternativas + gabaritos salvos no banco e em 'questoes_alternativas.txt'")
