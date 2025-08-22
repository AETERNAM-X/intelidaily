import fitz
import re
import os
import sqlite3
import json
import base64

def create_database():
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enunciado TEXT,
            a TEXT,
            b TEXT,
            c TEXT,
            d TEXT,
            e TEXT,
            gabarito TEXT,
            fonte TEXT DEFAULT 'Processo-Seletivo-2024.1',
            imagens TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

def find_question_blocks_by_text(pdf_path):
    """
    Localiza as partes de cada bloco de questão no PDF usando o cabeçalho
    da página como ponto de referência. Suporta questões que se estendem por múltiplas páginas.
    Ajusta o retângulo final para excluir as alternativas, parando antes de 'a)' ou linha separadora.
    """
    doc = fitz.open(pdf_path)
    question_parts = []  # Lista de listas: cada sublista contém partes {'page': int, 'rect': fitz.Rect}
    
    # Texto do cabeçalho
    header_text = "Processo de Admissão 2024.1 – Instituto de Tecnologia e Liderança"
    all_headers = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        header_rects = page.search_for(header_text)
        if header_rects:
            header_rect = sorted(header_rects, key=lambda r: r.y0)[0]
            all_headers.append({'page': page_num, 'rect': header_rect})

    if len(all_headers) < 2:
        print("Erro: Apenas 1 ou nenhum cabeçalho de questão encontrado no documento.")
        doc.close()
        return []

    # Ignora a primeira ocorrência (página de título)
    for i in range(1, len(all_headers)):
        current = all_headers[i]
        next_h = all_headers[i + 1] if i + 1 < len(all_headers) else None
        
        parts = []
        current_page_num = current['page']
        next_page_num = next_h['page'] if next_h else len(doc) - 1
        
        for p in range(current_page_num, next_page_num + 1):
            page = doc[p]
            if p == current_page_num:
                y_start = current['rect'].y1 + 10  # Após o cabeçalho atual
            else:
                y_start = page.rect.y0 + 20  # Margem superior para páginas intermediárias
            
            y_end = page.rect.y1 - 20  # Default: final da página
            
            # Se for a última página da questão, ajuste y_end para antes das alternativas
            if p == next_page_num:
                # Extrair blocos de texto
                text_blocks = page.get_text("blocks")
                alt_found = False
                for block in sorted(text_blocks, key=lambda b: b[1]):  # Ordenar por y0
                    text = block[4]  # Texto do bloco
                    y0 = block[1]    # Coordenada y0 do bloco
                    
                    # Ignorar blocos antes de y_start
                    if y0 < y_start:
                        continue
                    
                    # Procurar por 'a)', 'A)', ou variações
                    if re.search(r'^\s*[aA][\)\.]', text, re.MULTILINE | re.IGNORECASE):
                        y_end = min(y_end, y0 - 5)  # Ajuste menor para evitar cortar conteúdo
                        alt_found = True
                        print(f"Questão {i}: Encontrou 'a)' na página {p}, y_end ajustado para {y_end}")
                        break
                    # Procurar por linha separadora (flexível: 10+ traços, igual ou til)
                    if re.search(r'[-=~]{10,}', text, re.MULTILINE):
                        y_end = min(y_end, y0 - 5)
                        alt_found = True
                        print(f"Questão {i}: Encontrou linha separadora na página {p}, y_end ajustado para {y_end}")
                        break
                    # Procurar por início da próxima questão (ex.: "1.", "2.", etc.)
                    if re.search(r'^\s*\d+\.\s*', text, re.MULTILINE):
                        y_end = min(y_end, y0 - 5)
                        alt_found = True
                        print(f"Questão {i}: Encontrou início da próxima questão na página {p}, y_end ajustado para {y_end}")
                        break
                
                if not alt_found:
                    print(f"Aviso: Não encontrou 'a)', linha separadora ou início da próxima questão na questão {i}, página {p}. Usando final da página (y_end={y_end}).")
            
            # Ajustar y_end para antes do próximo cabeçalho, se aplicável
            if next_h and p == next_page_num:
                y_end = min(y_end, next_h['rect'].y0 - 20)
            
            x0 = page.rect.x0 + 20
            x1 = page.rect.x1 - 20
            
            # Validar retângulo
            if y_start < y_end:
                rect = fitz.Rect(x0, y_start, x1, y_end)
                parts.append({'page': p, 'rect': rect})
            else:
                print(f"Aviso: Retângulo inválido para questão {i} na página {p} (y_start={y_start}, y_end={y_end}). Ignorando parte.")
        
        if parts:
            question_parts.append(parts)
    
    doc.close()
    return question_parts

def capture_question_images(pdf_path, question_parts, output_dir="question_images"):
    """
    Captura e salva as imagens de cada parte de cada questão com base em suas coordenadas.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    doc = fitz.open(pdf_path)
    image_groups = []  # Lista de listas de caminhos de imagens (um grupo por questão)
    
    for q_num, q_parts in enumerate(question_parts):
        q_paths = []
        for part_num, part in enumerate(q_parts):
            page = doc.load_page(part['page'])
            rect = part['rect']
            
            pix = page.get_pixmap(clip=rect, dpi=300)
            
            img_filename = f"questao_{q_num+1}_part{part_num+1}.png"
            img_path = os.path.join(output_dir, img_filename)
            
            pix.save(img_path)
            q_paths.append(img_path)
            print(f"Imagem da questão {q_num+1} parte {part_num+1} salva em: {img_path}")
        
        image_groups.append(q_paths)
    
    doc.close()
    return image_groups

def insert_image_questions_into_db(image_groups):
    """
    Insere as questões no banco de dados com referência às imagens, incluindo base64.
    """
    if not image_groups:
        print("Nenhuma imagem de questão para inserir!")
        return
        
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questoes")
    
    for i, q_paths in enumerate(image_groups):
        image_data = []
        for p in q_paths:
            with open(p, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            image_data.append({
                'filename': os.path.basename(p),
                'path': p,
                'base64': b64
            })
        images_json = json.dumps(image_data, ensure_ascii=False)
        enunciado = f"Questão {i+1} - Ver imagem"
        
        cursor.execute('''
            INSERT INTO questoes (enunciado, a, b, c, d, e, gabarito, fonte, imagens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (enunciado, '', '', '', '', '', '?', 'Processo-Seletivo-2024.1', images_json))
        
    conn.commit()
    conn.close()
    print(f"\nInseridas {len(image_groups)} questões no banco de dados com referências a imagens.")

def main():
    print("=== IMPORTADOR DE QUESTÕES (CAPTURA DE IMAGENS) ===")
    pdf_file = "Processo-Seletivo-2024.1.pdf"
    
    try:
        if not os.path.exists(pdf_file):
            print(f"Erro: Arquivo PDF '{pdf_file}' não encontrado!")
            return
        
        print("1. Localizando as coordenadas de cada questão no PDF...")
        question_parts = find_question_blocks_by_text(pdf_file)
        
        if not question_parts:
            print("Nenhum bloco de questão encontrado. Verifique se o PDF contém o cabeçalho 'Processo de Admissão 2024.1 – Instituto de Tecnologia e Liderança' em páginas separadas.")
            return

        print(f"\n{len(question_parts)} questões encontradas. Gerando imagens...")
        
        print("\n2. Capturando e salvando as imagens das questões...")
        image_groups = capture_question_images(pdf_file, question_parts)
        
        if image_groups:
            print("\n3. Inserindo referências das imagens no banco de dados...")
            create_database()
            insert_image_questions_into_db(image_groups)
            print("\nProcesso concluído com sucesso!")
        else:
            print("Nenhuma imagem foi gerada. Processo finalizado.")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()