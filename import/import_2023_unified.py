import sqlite3
import re
import unicodedata
import json
import os
import base64

def create_database():
    """Cria o banco de dados se não existir"""
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
            fonte TEXT DEFAULT 'Processo Seletivo 2023',
            imagens TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

def normalize_text(text: str) -> str:
    """Normaliza texto para comparação"""
    if text is None:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9%\s]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def map_gabarito_to_letter(alternatives_ordered, gabarito_text):
    """Mapeia o texto do gabarito para a letra correspondente"""
    norm_gab = normalize_text(gabarito_text)
    letters = ['a', 'b', 'c', 'd', 'e']
    for idx, alt in enumerate(alternatives_ordered):
        norm_alt = normalize_text(alt)
        if norm_alt and (norm_alt == norm_gab or norm_alt in norm_gab or norm_gab in norm_alt):
            return letters[idx]
    return None

def parse_gabarito_letter(gabarito_raw, alternatives_ordered):
    """Extrai a letra do gabarito"""
    m = re.match(r'^\s*([a-eA-E])\b', gabarito_raw)
    if m:
        return m.group(1).lower()
    letter = map_gabarito_to_letter(alternatives_ordered, gabarito_raw)
    return letter if letter else '?'

def extract_questions_from_txt_2023(txt_path="2023_questions_alt.txt"):
    """Extrai questões da prova 2023 do arquivo .txt"""
    print(f"Lendo arquivo: {txt_path}")
    
    if not os.path.exists(txt_path):
        print(f"Arquivo {txt_path} não encontrado!")
        return []
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    questions = extract_questions_from_text_2023(text)
    return questions

def extract_questions_from_text_2023(text):
    """Extrai questões do texto da prova 2023"""
    question_pattern = r'QUESTÃO\s+(\d+)\s*\n(.*?)(?=QUESTÃO\s+\d+|$)'
    questions = []
    
    matches = re.finditer(question_pattern, text, re.DOTALL)
    
    for match in matches:
        question_num = match.group(1)
        question_content = match.group(2).strip()
        
        alternatives = {}
        
        lines = question_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            alt_match = re.match(r'^([A-E])\s*\)\s*(.*)', line)
            if alt_match:
                letter = alt_match.group(1).lower()
                content = alt_match.group(2).strip()
                alternatives[letter] = content
        
        gabarito_match = re.search(r'GABARITO:\s*([A-E])', question_content)
        if gabarito_match:
            gabarito = gabarito_match.group(1).lower()
        else:
            gabarito = '?'
        
        for letter in ['a', 'b', 'c', 'd', 'e']:
            if letter not in alternatives:
                alternatives[letter] = ''
        
        questions.append({
            'a': alternatives.get('a', ''),
            'b': alternatives.get('b', ''),
            'c': alternatives.get('c', ''),
            'd': alternatives.get('d', ''),
            'e': alternatives.get('e', ''),
            'gabarito': gabarito,
            'numero': question_num
        })
    
    return questions

def get_image_files_2023():
    """Obtém lista de arquivos de imagem ordenados numericamente"""
    images_dir = "2023_questions_imgs"
    
    if not os.path.exists(images_dir):
        print(f"Pasta {images_dir} não encontrada!")
        return []
    
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.webp'))]
    
    if not image_files:
        print(f"Nenhuma imagem encontrada em {images_dir}")
        return []
    
    # Ordenar arquivos numericamente (questao_1.png, questao_2.png, etc.)
    def sort_key(filename):
        match = re.search(r'questao_(\d+)', filename)
        if match:
            return int(match.group(1))
        return 0
    
    image_files.sort(key=sort_key)
    return image_files

def import_questions_with_images_2023():
    """Importa questões com imagens e alternativas para 2023"""
    print("IMPORTADOR UNIFICADO - PROVA 2023")
    print("=" * 50)
    
    # Criar banco
    create_database()
    
    # Extrair questões do arquivo .txt
    questions = extract_questions_from_txt_2023()
    if not questions:
        print("Nenhuma questão encontrada no arquivo de texto!")
        return False
    
    print(f"Extraídas {len(questions)} questões do arquivo de texto")
    
    # Obter arquivos de imagem
    image_files = get_image_files_2023()
    if not image_files:
        print("Nenhuma imagem encontrada!")
        return False
    
    print(f"Encontradas {len(image_files)} imagens")
    
    # Criar dicionário de questões por número
    questions_dict = {q['numero']: q for q in questions}
    
    try:
        conn = sqlite3.connect('questions.db')
        cursor = conn.cursor()
        
        # Limpar questões existentes da fonte 2023
        cursor.execute("DELETE FROM questoes WHERE fonte = ?", ('Processo Seletivo 2023',))
        print("Removidas questões existentes da fonte: Processo Seletivo 2023")
        
        imported_count = 0
        
        for filename in image_files:
            try:
                # Extrair número da questão do nome do arquivo
                questao_match = re.search(r'questao_(\d+)', filename)
                if questao_match:
                    questao_num = questao_match.group(1)
                else:
                    print(f"Arquivo {filename} não segue o padrão esperado")
                    continue
                
                # Verificar se temos as alternativas para esta questão
                if questao_num not in questions_dict:
                    print(f"⚠️  Questão {questao_num} não encontrada no arquivo de texto")
                    continue
                
                question_data = questions_dict[questao_num]
                
                # Ler e converter imagem para base64
                image_path = os.path.join("2023_questions_imgs", filename)
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()
                
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                images_list = [{
                    'filename': filename,
                    'data': img_base64,
                    'type': 'image/png'
                }]
                
                # Inserir questão com imagem e alternativas
                cursor.execute("""
                    INSERT INTO questoes (enunciado, a, b, c, d, e, gabarito, fonte, imagens)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"Questão {questao_num} - Processo Seletivo 2023",
                    question_data['a'],
                    question_data['b'],
                    question_data['c'],
                    question_data['d'],
                    question_data['e'],
                    question_data['gabarito'],
                    'Processo Seletivo 2023',
                    json.dumps(images_list, ensure_ascii=False)
                ))
                
                imported_count += 1
                print(f"✅ Questão {questao_num:2s}: {filename} + alternativas importada")
                
            except Exception as e:
                print(f"❌ Erro ao processar {filename}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 50)
        print("IMPORTAÇÃO CONCLUÍDA!")
        print(f"Questões importadas: {imported_count}")
        print(f"Total de questões no arquivo: {len(questions)}")
        print(f"Total de imagens encontradas: {len(image_files)}")
        
        if imported_count < len(questions):
            print(f"⚠️  {len(questions) - imported_count} questões não foram importadas (sem imagem correspondente)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no banco de dados: {e}")
        return False

def main():
    """Função principal para importar prova 2023 unificada"""
    success = import_questions_with_images_2023()
    
    if success:
        print("\n🎉 Importação da prova 2023 concluída com sucesso!")
        print("Cada questão agora possui sua imagem e alternativas corretamente associadas.")
    else:
        print("\n💥 Falha na importação.")

if __name__ == "__main__":
    main()
