import sqlite3
import re
import unicodedata
import json
import os
import base64
from PIL import Image
import fitz  # PyMuPDF

def create_database():
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enunciado TEXT NOT NULL,
            a TEXT NOT NULL,
            b TEXT NOT NULL,
            c TEXT NOT NULL,
            d TEXT NOT NULL,
            e TEXT NOT NULL,
            gabarito TEXT NOT NULL,
            fonte TEXT DEFAULT 'Processo-Seletivo-2024.1',
            imagens TEXT DEFAULT '[]'
        )
    ''')
    
    # Garantir que a coluna 'fonte' exista mesmo em tabelas antigas
    cursor.execute("PRAGMA table_info(questoes)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'fonte' not in cols:
        cursor.execute("ALTER TABLE questoes ADD COLUMN fonte TEXT DEFAULT 'Processo-Seletivo-2024.1'")
    if 'imagens' not in cols:
        cursor.execute("ALTER TABLE questoes ADD COLUMN imagens TEXT DEFAULT '[]'")
    
    conn.commit()
    conn.close()

def extract_pdf_with_spaces(pdf_path, output_path):
    """Extrai texto do PDF preservando espaços e formatação"""
    
    print(f"Extraindo PDF com preservação de espaços: {pdf_path}")
    
    with fitz.open(pdf_path) as doc:
        all_text = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            
            if text:
                # Adicionar marcador de página
                all_text.append(f"--- PÁGINA {page_num + 1} ---")
                all_text.append(text)
                all_text.append("")  # Linha em branco entre páginas
    
    # Juntar todo o texto
    full_text = "\n".join(all_text)
    
    # Salvar no arquivo
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"Texto extraído salvo em: {output_path}")
    return full_text

def extract_images_from_pdf(pdf_path, output_dir="images"):
    """Extrai imagens do PDF"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Extraindo imagens do PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    images_data = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        image_list = page.get_images()
        
        print(f"Página {page_num + 1}: {len(image_list)} imagens encontradas")
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                if pix.n - pix.alpha < 4:  # RGB ou RGBA
                    img_data = pix.tobytes("png")
                    
                    # Salvar imagem
                    img_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                    img_path = os.path.join(output_dir, img_filename)
                    
                    with open(img_path, "wb") as img_file:
                        img_file.write(img_data)
                    
                    # Converter para base64
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    images_data.append({
                        'page': page_num + 1,
                        'index': img_index + 1,
                        'filename': img_filename,
                        'path': img_path,
                        'base64': img_base64,
                        'size': len(img_data)
                    })
                
                pix = None
                
            except Exception as e:
                print(f"Erro ao extrair imagem {img_index + 1} da página {page_num + 1}: {e}")
    
    doc.close()
    
    # Salvar metadados das imagens
    metadata_path = os.path.join(output_dir, "images_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(images_data, f, indent=2, ensure_ascii=False)
    
    print(f"Total de imagens extraídas: {len(images_data)}")
    return images_data

def normalize_text(text: str) -> str:
    if text is None:
        return ''
    # remover acentos
    nfkd = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    # baixar caixa e remover pontuação simples/extras
    text = text.lower()
    text = re.sub(r'[^a-z0-9%\s]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_questions_from_text(text):
    """Extrai questões do texto preservando formatação"""
    
    questions = []
    
    # Encontrar todas as ocorrências de "Processo de Admissão 2024.1 – Instituto de Tecnologia e Liderança"
    headers = list(re.finditer(r'Processo de Admissão 2024\.1 – Instituto de Tecnologia e Liderança', text))
    
    print(f"Encontrados {len(headers)} cabeçalhos no arquivo")
    
    # Pular o primeiro cabeçalho (cabeçalho geral)
    for i, header in enumerate(headers[1:], 1):  # Começar do segundo cabeçalho
        print(f"Processando cabeçalho {i+1}...")
        question_data = extract_question_from_header(text, header)
        if question_data:
            questions.append(question_data)
            print(f"Questão {len(questions)} extraída com sucesso")
        else:
            print(f"Falha ao extrair questão do cabeçalho {i+1}")
    
    return questions

def map_gabarito_to_letter(alternatives_ordered, gabarito_text):
    """Tenta mapear o gabarito textual para uma letra a-e comparando com as alternativas."""
    norm_gab = normalize_text(gabarito_text)
    letters = ['a', 'b', 'c', 'd', 'e']
    for idx, alt in enumerate(alternatives_ordered):
        norm_alt = normalize_text(alt)
        if norm_alt and (norm_alt == norm_gab or norm_alt in norm_gab or norm_gab in norm_alt):
            return letters[idx]
    return None

def extract_question_from_header(text, header_match):
    """Extrai uma questão a partir de um cabeçalho específico"""
    try:
        # Pegar o texto a partir do cabeçalho até o próximo cabeçalho ou fim do arquivo
        start_pos = header_match.end()
        
        # Encontrar o próximo cabeçalho
        next_header = re.search(r'Processo de Admissão 2024\.1 – Instituto de Tecnologia e Liderança', text[start_pos:])
        if next_header:
            end_pos = start_pos + next_header.start()
        else:
            end_pos = len(text)
        
        question_block = text[start_pos:end_pos].strip()
        
        # Encontrar a linha separadora
        separator_match = re.search(r'-{80,}', question_block)
        if not separator_match:
            print(f"Separador não encontrado no bloco")
            return None
        
        separator_pos = separator_match.start()
        
        # Texto da questão (antes do separador)
        question_text = question_block[:separator_pos].strip()
        
        # Texto após o separador (gabarito)
        gabarito_text = question_block[separator_match.end():].strip()
        
        # Extrair gabarito (linha imediatamente abaixo de 'Gabarito:')
        gabarito_match = re.search(r'Gabarito:\s*(.+)', gabarito_text)
        if not gabarito_match:
            print(f"Gabarito não encontrado")
            return None
        gabarito_raw = gabarito_match.group(1).strip()
        
        # Extrair enunciado e alternativas
        lines = [line.strip() for line in question_text.split('\n') if line.strip()]
        # Remover cabeçalho
        lines = [line for line in lines if 'Processo de Admissão' not in line]
        
        # Pegar as últimas 5 linhas como alternativas (mesmo sem rótulos)
        if len(lines) < 5:
            print(f"Poucas linhas no bloco: {len(lines)}")
            return None
        
        alternatives_raw = lines[-5:]
        enunciado_lines = lines[:-5]
        
        # Se houver rótulos (a) b) ...), removê-los; senão, manter como está
        alternatives_clean = []
        for alt in alternatives_raw:
            m = re.match(r'^[a-eA-E][\)\.\-]\s*(.+)', alt)
            alternatives_clean.append(m.group(1).strip() if m else alt)
        
        # Mapear gabarito textual para letra
        gab_letter = map_gabarito_to_letter(alternatives_clean, gabarito_raw)
        if not gab_letter:
            print(f"Aviso: não foi possível mapear gabarito para letra. Armazenando '?' | gabarito_raw='{gabarito_raw}'")
            gab_letter = '?'
        
        # Montar enunciado preservando formatação
        enunciado = '\n'.join(enunciado_lines)
        
        return {
            'enunciado': enunciado,
            'a': alternatives_clean[0],
            'b': alternatives_clean[1],
            'c': alternatives_clean[2],
            'd': alternatives_clean[3],
            'e': alternatives_clean[4],
            'gabarito': gab_letter,
            'gabarito_raw': gabarito_raw
        }
        
    except Exception as e:
        print(f"Erro ao extrair questão: {e}")
        return None

def associate_images_with_questions(images_data, questions_data):
    """Associa imagens às questões baseado na página"""
    
    print("Associando imagens às questões...")
    
    for question in questions_data:
        question['images'] = []
    
    # Agrupar imagens por página
    images_by_page = {}
    for img in images_data:
        page = img['page']
        if page not in images_by_page:
            images_by_page[page] = []
        images_by_page[page].append(img)
    
    # Associar imagens às questões (assumindo que questões estão em páginas sequenciais)
    question_index = 0
    for page_num in sorted(images_by_page.keys()):
        if question_index < len(questions_data):
            questions_data[question_index]['images'] = images_by_page[page_num]
            print(f"Questão {question_index + 1} associada com {len(images_by_page[page_num])} imagens da página {page_num}")
            question_index += 1
    
    return questions_data

def export_questions_to_text(questions, output_file="questoes_extraidas.txt"):
    """Exporta as questões extraídas para um arquivo de texto"""
    
    print(f"\nExportando {len(questions)} questões para: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== QUESTÕES EXTRAÍDAS DO PROCESSO SELETIVO 2024.1 ===\n\n")
        
        for i, q in enumerate(questions, 1):
            f.write(f"QUESTÃO {i}\n")
            f.write("=" * 50 + "\n")
            f.write(f"ENUNCIADO:\n{q['enunciado']}\n\n")
            f.write("ALTERNATIVAS:\n")
            f.write(f"A) {q['a']}\n")
            f.write(f"B) {q['b']}\n")
            f.write(f"C) {q['c']}\n")
            f.write(f"D) {q['d']}\n")
            f.write(f"E) {q['e']}\n\n")
            f.write(f"GABARITO: {q['gabarito']} ({q.get('gabarito_raw', 'N/A')})\n")
            
            # Adicionar informações sobre imagens
            if q.get('images'):
                f.write(f"IMAGENS: {len(q['images'])} imagens associadas\n")
                for img in q['images']:
                    f.write(f"  - {img['filename']} (Página {img['page']})\n")
            else:
                f.write("IMAGENS: Nenhuma imagem associada\n")
            
            f.write("-" * 50 + "\n\n")
    
    print(f"Questões exportadas com sucesso para: {output_file}")

def insert_questions_with_images(questions):
    """Insere questões com imagens no banco de dados"""
    
    if not questions:
        print("Nenhuma questão para inserir!")
        return
    
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    
    # Limpar questões existentes
    cursor.execute("DELETE FROM questoes")
    
    for question in questions:
        # Converter imagens para JSON
        images_json = json.dumps(question.get('images', []), ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO questoes (enunciado, a, b, c, d, e, gabarito, fonte, imagens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            question['enunciado'],
            question['a'],
            question['b'],
            question['c'],
            question['d'],
            question['e'],
            question['gabarito'],
            'Processo-Seletivo-2024.1',
            images_json
        ))
    
    conn.commit()
    conn.close()
    print(f"Inseridas {len(questions)} questões no banco de dados")

def main():
    print("=== IMPORTADOR COMPLETO - PROCESSO SELETIVO 2024.1 ===")
    print("Este script irá:")
    print("1. Extrair texto do PDF preservando espaços")
    print("2. Extrair imagens do PDF")
    print("3. Processar questões e associar imagens")
    print("4. Exportar questões para arquivo de texto")
    print("5. Inserir no banco de dados")
    print()
    
    pdf_file = "Processo-Seletivo-2024.1.pdf"
    
    try:
        # 1. Extrair texto com espaços preservados
        print("1. Extraindo texto do PDF...")
        text_with_spaces = extract_pdf_with_spaces(pdf_file, "extracted_text_with_spaces.txt")
        
        # 2. Extrair imagens
        print("\n2. Extraindo imagens do PDF...")
        images_data = extract_images_from_pdf(pdf_file)
        
        # 3. Processar questões
        print("\n3. Processando questões...")
        create_database()
        questions = extract_questions_from_text(text_with_spaces)
        
        if questions:
            # 4. Associar imagens às questões
            print("\n4. Associando imagens às questões...")
            questions_with_images = associate_images_with_questions(images_data, questions)
            
            # 5. Exportar questões para texto
            print("\n5. Exportando questões para arquivo de texto...")
            export_questions_to_text(questions_with_images)
            
            # 6. Mostrar resumo
            print(f"\nResumo:")
            print(f"- Questões encontradas: {len(questions)}")
            print(f"- Imagens extraídas: {len(images_data)}")
            print(f"- Questões com imagens: {sum(1 for q in questions if q.get('images'))}")
            
            # 7. Confirmar inserção no banco
            confirm = input(f"\nInserir {len(questions)} questões no banco? (s/n): ").strip().lower()
            
            if confirm == 's':
                print("\n6. Inserindo no banco de dados...")
                insert_questions_with_images(questions_with_images)
                print("Processo concluído com sucesso!")
            else:
                print("Operação cancelada.")
        else:
            print("Nenhuma questão encontrada!")
            
    except FileNotFoundError:
        print(f"Erro: Arquivo PDF '{pdf_file}' não encontrado!")
    except Exception as e:
        print(f"Erro durante o processo: {e}")

if __name__ == "__main__":
    main()
