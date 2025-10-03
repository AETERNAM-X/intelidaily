import os
import re
import json
import sqlite3
from io import BytesIO

try:
    from PIL import Image
except Exception:
    Image = None

DB_PATH = 'questions.db'

YEARS = [2022, 2023, 2024, 2025]
TEXT_FILES = {
    2022: '2022_questions_alt.txt',
    2023: '2023_questions_alt.txt',
    2024: '2024_questions_alt.txt',
    2025: '2025_questions_alt.txt',
}
IMG_DIRS = {
    2022: '2022_questions_imgs',
    2023: '2023_questions_imgs',
    2024: '2024_questions_imgs',
    2025: '2025_questions_imgs',
}
FONTE = {
    2022: 'Processo Seletivo 2022',
    2023: 'Processo Seletivo 2023',
    2024: 'Processo Seletivo 2024',
    2025: 'Processo Seletivo 2025',
}


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def save_webp(src_path: str, out_dir: str, out_name: str) -> str:
    ensure_dir(out_dir)
    out_name = out_name if out_name.lower().endswith('.webp') else f"{out_name}.webp"
    out_path = os.path.join(out_dir, out_name)

    if Image is None:
        with open(src_path, 'rb') as s, open(out_path, 'wb') as d:
            d.write(s.read())
        return os.path.join(os.path.basename(out_dir), out_name).replace('\\', '/')

    with Image.open(src_path) as im:
        im = im.convert('RGBA') if im.mode in ('P', 'LA') else im.convert('RGB')
        im.save(out_path, format='WEBP', quality=90, method=6)

    return os.path.join(os.path.basename(out_dir), out_name).replace('\\', '/')


def parse_questions_from_txt(text: str):
    pattern = r'QUESTÃO\s+(\d+)\s*\n(.*?)(?=QUESTÃO\s+\d+|$)'
    questions = []
    for match in re.finditer(pattern, text, re.DOTALL):
        num = match.group(1)
        content = match.group(2).strip()
        alts = {}
        for line in content.split('\n'):
            m = re.match(r'^([A-E])\s*\)\s*(.*)', line.strip())
            if m:
                alts[m.group(1).lower()] = m.group(2).strip()
        gabarito = '?'
        gm = re.search(r'GABARITO:\s*([A-E])', content)
        if gm:
            gabarito = gm.group(1).lower()
        for letter in ['a', 'b', 'c', 'd', 'e']:
            alts.setdefault(letter, '')
        questions.append({'numero': num, 'a': alts['a'], 'b': alts['b'], 'c': alts['c'], 'd': alts['d'], 'e': alts['e'], 'gabarito': gabarito})
    return questions


def get_images_for_year(year: int):
    dir_ = IMG_DIRS[year]
    if not os.path.exists(dir_):
        return []
    files = [f for f in os.listdir(dir_) if f.lower().endswith('.webp') or f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    def key(f):
        m = re.search(r'questao_(\d+)', f)
        return int(m.group(1)) if m else 0
    files.sort(key=key)
    return files


def import_year(year: int):
    txt_file = TEXT_FILES[year]
    img_dir = IMG_DIRS[year]
    fonte = FONTE[year]

    if not os.path.exists(txt_file):
        print(f"[ {year} ] TXT não encontrado: {txt_file}")
        return 0

    with open(txt_file, 'r', encoding='utf-8') as f:
        text = f.read()
    questions = parse_questions_from_txt(text)
    qdict = {q['numero']: q for q in questions}

    images = get_images_for_year(year)
    if not images:
        print(f"[ {year} ] Nenhuma imagem encontrada em {img_dir}")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enunciado TEXT,
            a TEXT,
            b TEXT,
            c TEXT,
            d TEXT,
            e TEXT,
            gabarito TEXT,
            fonte TEXT,
            imagens TEXT DEFAULT '[]',
            tipo TEXT DEFAULT 'completa'
        )
    ''')

    cur.execute('DELETE FROM questoes WHERE fonte = ?', (fonte,))

    imported = 0
    for filename in images:
        m = re.search(r'questao_(\d+)', filename)
        if not m:
            continue
        num = m.group(1)
        if num not in qdict:
            print(f"[ {year} ] Sem alternativas para questão {num}")
            continue

        src_path = os.path.join(img_dir, filename)
        # Normalize/convert to webp in place directory
        rel_path = filename
        if not filename.lower().endswith('.webp'):
            rel_path = save_webp(src_path, img_dir, f"questao_{num}")
        else:
            rel_path = os.path.join(os.path.basename(img_dir), filename).replace('\\', '/')

        q = qdict[num]
        imagens_json = json.dumps([rel_path], ensure_ascii=False)

        cur.execute('''
            INSERT INTO questoes (enunciado, a, b, c, d, e, gabarito, fonte, imagens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"Questão {num} - {fonte}",
            q['a'], q['b'], q['c'], q['d'], q['e'],
            q['gabarito'], fonte, imagens_json
        ))
        imported += 1
        print(f"[ {year} ] ✅ Importada questão {num} -> {rel_path}")

    conn.commit()
    conn.close()
    print(f"[ {year} ] Importadas {imported} questões")
    return imported


def main():
    total = 0
    for y in YEARS:
        try:
            total += import_year(y)
        except Exception as e:
            print(f"[ {y} ] Erro: {e}")
    print(f"Total importadas: {total}")

if __name__ == '__main__':
    main()
