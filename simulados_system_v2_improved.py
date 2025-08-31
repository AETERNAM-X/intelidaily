import sqlite3
import json
import random
from datetime import datetime

class SimuladosSystemV2Improved:
    def __init__(self, db_path='questions.db'):
        self.db_path = db_path
        self.create_simulados_table()
    
    def create_simulados_table(self):
        """Cria tabela para armazenar simulados realizados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                provas_selecionadas TEXT,
                num_questoes INTEGER,
                questoes_ids TEXT,
                tempo_total TEXT,
                acertos INTEGER,
                erros INTEGER,
                puladas INTEGER,
                percentual_acerto REAL
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_available_exams(self):
        """Retorna lista de provas disponíveis no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fonte, COUNT(*) as total_questoes
            FROM questoes 
            GROUP BY fonte
            ORDER BY fonte DESC
        ''')
        
        exams_data = cursor.fetchall()
        conn.close()
        
        exam_mapping = {
            'Processo Seletivo 2025': 'Processo Seletivo 2025',
            'Processo Seletivo 2024': 'Processo Seletivo 2024',
            'Processo Seletivo 2023': 'Processo Seletivo 2023',
            'Processo Seletivo 2022': 'Processo Seletivo 2022'
        }
        
        available_exams = []
        for exam in exams_data:
            fonte, total_questoes = exam
            display_name = exam_mapping.get(fonte, fonte)
            year = fonte.split()[-1] if ' ' in fonte else 'N/A'
            
            available_exams.append({
                'id': fonte,
                'name': display_name,
                'year': year,
                'question_count': total_questoes
            })
        
        return available_exams
    
    def create_randomized_exam(self, selected_exams, num_questions=24, exam_distribution=None):
        """Cria um simulado randomizado com opção de distribuição personalizada
        
        Args:
            selected_exams: Lista de provas selecionadas
            num_questions: Total de questões (padrão: 24)
            exam_distribution: Dicionário com distribuição por prova (ex: {'2024': 16, '2023': 8})
        """
        
        # Estrutura fixa dos blocos conforme especificação
        BLOCK_STRUCTURE = {
            'bloco_1': 8,   # 8 questões
            'bloco_2': 6,   # 6 questões  
            'bloco_3': 6,   # 6 questões
            'bloco_4': 4    # 4 questões
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if exam_distribution:
            # Modo personalizado: distribuição específica por prova
            print(f"🎯 Criando simulado com distribuição personalizada: {exam_distribution}")
            
            all_questions = []
            selected_ids = set()
            current_block = 1
            questions_in_current_block = 0
            
            for exam_id, num_questions_from_exam in exam_distribution.items():
                if num_questions_from_exam <= 0:
                    continue
                    
                print(f"   📚 Selecionando {num_questions_from_exam} questões de {exam_id}")
                
                # Buscar questões da prova específica
                cursor.execute('''
                    SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens
                    FROM questoes 
                    WHERE fonte = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (exam_id, num_questions_from_exam * 2))  # Buscar mais para ter opções
                
                exam_questions = cursor.fetchall()
                
                # Selecionar questões únicas
                questions_selected = 0
                for q in exam_questions:
                    if questions_selected >= num_questions_from_exam:
                        break
                        
                    if q[0] not in selected_ids and self._is_valid_question(q):
                        selected_ids.add(q[0])
                        
                        # Atribuir bloco baseado na estrutura dos blocos
                        if questions_in_current_block >= BLOCK_STRUCTURE[f'bloco_{current_block}']:
                            current_block += 1
                            questions_in_current_block = 0
                        
                        all_questions.append({
                            'id': q[0],
                            'enunciado': q[1] or f"Questão {q[0]}",
                            'a': q[2] or '',
                            'b': q[3] or '',
                            'c': q[4] or '',
                            'd': q[5] or '',
                            'e': q[6] or '',
                            'gabarito': q[7] or '?',
                            'fonte': q[8],
                            'imagens': '[]',  # Não retornar imagens grandes na criação
                            'bloco': current_block
                        })
                        
                        questions_in_current_block += 1
                        questions_selected += 1
                
                print(f"      ✅ {questions_selected} questões selecionadas de {exam_id}")
                
        else:
            # Modo aleatório tradicional
            print(f"🎲 Criando simulado com seleção aleatória")
            
            # Buscar questões das provas selecionadas
            placeholders = ','.join(['?' for _ in selected_exams])
            
            cursor.execute(f'''
                SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens
                FROM questoes 
                WHERE fonte IN ({placeholders})
                ORDER BY RANDOM()
            ''', selected_exams)
            
            all_questions_raw = cursor.fetchall()
            
            if len(all_questions_raw) < num_questions:
                print(f"⚠️  Aviso: Apenas {len(all_questions_raw)} questões disponíveis, mas são necessárias {num_questions}")
                return []
            
            # Conjunto para controlar IDs já selecionados (evita duplicatas)
            selected_ids = set()
            all_questions = []
            
            # Selecionar questões únicas para cada bloco
            for block_num, block_size in enumerate(BLOCK_STRUCTURE.values(), 1):
                block_questions = []
                attempts = 0
                max_attempts = len(all_questions_raw) * 2  # Evita loop infinito
                
                while len(block_questions) < block_size and attempts < max_attempts:
                    attempts += 1
                    
                    # Encontrar questão não selecionada
                    for q in all_questions_raw:
                        if q[0] not in selected_ids and len(block_questions) < block_size:
                            # Verificar se a questão tem alternativas válidas
                            if self._is_valid_question(q):
                                selected_ids.add(q[0])
                                block_questions.append({
                                    'id': q[0],
                                    'enunciado': q[1] or f"Questão {q[0]}",
                                    'a': q[2] or '',
                                    'b': q[3] or '',
                                    'c': q[4] or '',
                                    'd': q[5] or '',
                                    'e': q[6] or '',
                                    'gabarito': q[7] or '?',
                                    'fonte': q[8],
                                    'imagens': '[]',  # Não retornar imagens grandes na criação
                                    'bloco': block_num
                                })
                                break
                    
                    # Se não encontrou questão válida, parar
                    if len(block_questions) == 0:
                        break
                
                # Adicionar questões do bloco à lista principal
                all_questions.extend(block_questions)
                
                print(f"✅ Bloco {block_num}: {len(block_questions)} questões selecionadas")
        
        conn.close()
        
        # Verificar se conseguimos o número de questões solicitado
        if len(all_questions) < num_questions:
            print(f"⚠️  Apenas {len(all_questions)} questões válidas encontradas")
            return all_questions
        
        # Garantir exatamente o número de questões solicitado
        return all_questions[:num_questions]
    
    def _assign_block(self, question_index, block_structure):
        """Atribui cada questão ao bloco correto baseado no índice"""
        if question_index < block_structure['bloco_1']:
            return 1
        elif question_index < (block_structure['bloco_1'] + block_structure['bloco_2']):
            return 2
        elif question_index < (block_structure['bloco_1'] + block_structure['bloco_2'] + block_structure['bloco_3']):
            return 3
        else:
            return 4
    
    def _is_valid_question(self, question):
        """Verifica se uma questão é válida para o simulado"""
        # Verificar se tem pelo menos algumas alternativas
        alternatives = [question[2], question[3], question[4], question[5], question[6]]  # a, b, c, d, e
        valid_alternatives = [alt for alt in alternatives if alt and alt.strip()]
        
        # Questão é válida se tem pelo menos 3 alternativas
        # Temporariamente aceitamos gabarito "?" devido a problemas de dados
        return len(valid_alternatives) >= 3
    
    def save_simulado_result(self, provas_selecionadas, num_questoes, questoes_ids, 
                           tempo_total, acertos, erros, puladas):
        """Salva resultado de um simulado realizado"""
        percentual = (acertos / num_questoes) * 100 if num_questoes > 0 else 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO simulados 
            (data_criacao, provas_selecionadas, num_questoes, questoes_ids, tempo_total, 
             acertos, erros, puladas, percentual_acerto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            json.dumps(provas_selecionadas),
            num_questoes,
            json.dumps(questoes_ids),
            tempo_total,
            acertos,
            erros,
            puladas,
            percentual
        ))
        
        simulado_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return simulado_id
    
    def get_simulados_history(self):
        """Retorna histórico de simulados realizados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM simulados 
            ORDER BY data_criacao DESC 
            LIMIT 50
        ''')
        
        simulados = []
        for row in cursor.fetchall():
            simulado = {
                'id': row[0],
                'data_criacao': row[1],
                'provas_selecionadas': json.loads(row[2]) if row[2] else [],
                'num_questoes': row[3],
                'questoes_ids': json.loads(row[4]) if row[4] else [],
                'tempo_total': row[5],
                'acertos': row[6],
                'erros': row[7],
                'puladas': row[8],
                'percentual_acerto': row[9]
            }
            simulados.append(simulado)
        
        conn.close()
        return simulados
    
    def get_simulado_by_id(self, simulado_id):
        """Retorna um simulado específico por ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM simulados 
            WHERE id = ?
        ''', (simulado_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'data_criacao': row[1],
                'provas_selecionadas': json.loads(row[2]) if row[2] else [],
                'num_questoes': row[3],
                'questoes_ids': json.loads(row[4]) if row[4] else [],
                'tempo_total': row[5],
                'acertos': row[6],
                'erros': row[7],
                'puladas': row[8],
                'percentual_acerto': row[9]
            }
        return None
    
    def get_statistics(self):
        """Retorna estatísticas gerais dos simulados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM simulados')
        total_simulados = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(percentual_acerto) FROM simulados')
        media_acertos = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT MAX(percentual_acerto) FROM simulados')
        melhor_resultado = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(num_questoes) FROM simulados')
        total_questoes = cursor.fetchone()[0] or 0
        
        # Calcular tempo médio
        cursor.execute('SELECT tempo_total FROM simulados WHERE tempo_total IS NOT NULL AND tempo_total != ""')
        tempos = cursor.fetchall()
        
        tempo_medio = "00:00:00"
        if tempos:
            try:
                # Converter tempos para segundos e calcular média
                total_segundos = 0
                tempos_validos = 0
                
                for tempo_row in tempos:
                    tempo_str = tempo_row[0]
                    if tempo_str and ':' in tempo_str:
                        # Formato esperado: HH:MM:SS ou MM:SS
                        parts = tempo_str.split(':')
                        if len(parts) == 3:  # HH:MM:SS
                            horas, minutos, segundos = map(int, parts)
                            segundos_total = horas * 3600 + minutos * 60 + segundos
                        elif len(parts) == 2:  # MM:SS
                            minutos, segundos = map(int, parts)
                            segundos_total = minutos * 60 + segundos
                        else:
                            continue
                        
                        total_segundos += segundos_total
                        tempos_validos += 1
                
                if tempos_validos > 0:
                    media_segundos = total_segundos / tempos_validos
                    horas = int(media_segundos // 3600)
                    minutos = int((media_segundos % 3600) // 60)
                    segundos = int(media_segundos % 60)
                    tempo_medio = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
                    
            except Exception as e:
                print(f"Erro ao calcular tempo médio: {e}")
                tempo_medio = "00:00:00"
        
        conn.close()
        
        return {
            'total_simulados': total_simulados,
            'media_acertos': round(media_acertos, 2),
            'melhor_resultado': round(melhor_resultado, 2),
            'total_questoes': total_questoes,
            'tempo_medio': tempo_medio
        }
    
    def get_exam_statistics(self):
        """Retorna estatísticas por prova específica"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fonte, COUNT(*) as total_questoes
            FROM questoes 
            GROUP BY fonte
        ''')
        
        exam_stats = []
        for row in cursor.fetchall():
            fonte = row[0]
            total_questoes = row[1]
            
            # Buscar simulados que usaram esta prova
            cursor.execute('''
                SELECT COUNT(*) as uso_simulados
                FROM simulados 
                WHERE provas_selecionadas LIKE ?
            ''', (f'%{fonte}%',))
            
            uso_simulados = cursor.fetchone()[0]
            
            exam_stats.append({
                'fonte': fonte,
                'total_questoes': total_questoes,
                'uso_simulados': uso_simulados
            })
        
        conn.close()
        return exam_stats
    
    def verify_no_duplicates(self, questoes_ids):
        """Verifica se não há questões duplicadas no simulado"""
        if not questoes_ids:
            return True
        
        # Converter para lista se for string JSON
        if isinstance(questoes_ids, str):
            questoes_ids = json.loads(questoes_ids)
        
        # Verificar se há duplicatas
        unique_ids = set(questoes_ids)
        has_duplicates = len(unique_ids) != len(questoes_ids)
        
        if has_duplicates:
            print(f"⚠️  ALERTA: Encontradas questões duplicadas!")
            print(f"   Total de questões: {len(questoes_ids)}")
            print(f"   IDs únicos: {len(unique_ids)}")
            
            # Encontrar duplicatas
            from collections import Counter
            duplicates = [item for item, count in Counter(questoes_ids).items() if count > 1]
            print(f"   IDs duplicados: {duplicates}")
        
        return not has_duplicates

# Instância global do sistema melhorado
simulados_system_v2_improved = SimuladosSystemV2Improved()
