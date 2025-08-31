from flask import Flask, render_template, jsonify, request, session
import sqlite3
import json
import os
from datetime import datetime
from simulados_system_v2_improved import SimuladosSystemV2Improved

# Instanciar o sistema de simulados
simulados_system_v2 = SimuladosSystemV2Improved()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'inteli_simulados_2024_dev')  # Chave secreta para sessões

# Configurações para lidar com respostas grandes
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configurações de sessão
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos

# ----------------------
# Helpers
# ----------------------

def get_db_connection():
    conn = sqlite3.connect('questions.db')
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------
# Páginas
# ----------------------

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/test')
def test():
    return render_template('index.html')

@app.route('/api/test')
def test_api():
    """Rota de teste para verificar se a API está funcionando"""
    return jsonify({
        'status': 'ok',
        'message': 'API funcionando',
        'timestamp': datetime.now().isoformat()
    })

# ----------------------
# Questões (CRUD leve)
# ----------------------

@app.route('/api/questions')
def get_questions():
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questoes').fetchall()
    conn.close()

    questions_list = []
    for q in questions:
        # Limitar tamanho dos dados para evitar respostas muito grandes
        questions_list.append({
            'id': q['id'],
            'enunciado': (q['enunciado'] or f"Questão {q['id']}")[:300],
            'a': (q['a'] or '')[:100],
            'b': (q['b'] or '')[:100],
            'c': (q['c'] or '')[:100],
            'd': (q['d'] or '')[:100],
            'e': (q['e'] or '')[:100],
            'gabarito': q['gabarito'],
            'fonte': q['fonte'],
            'imagens': '[]'  # Não retornar imagens nesta rota
        })
    return jsonify(questions_list)

@app.route('/api/questions/<int:question_id>')
def get_question(question_id):
    conn = get_db_connection()
    question = conn.execute('SELECT * FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    if not question:
        return jsonify({'error': 'Questão não encontrada'}), 404
    
    # Limitar tamanho dos dados para evitar respostas muito grandes
    return jsonify({
        'id': question['id'],
        'enunciado': (question['enunciado'] or f"Questão {question['id']}")[:500],
        'a': (question['a'] or '')[:200],
        'b': (question['b'] or '')[:200],
        'c': (question['c'] or '')[:200],
        'd': (question['d'] or '')[:200],
        'e': (question['e'] or '')[:200],
        'gabarito': question['gabarito'],
        'fonte': question['fonte'],
        'imagens': '[]'  # Não retornar imagens nesta rota
    })

# ----------------------
# Imagens das questões
# ----------------------

@app.route('/api/images/<int:question_id>')
def get_question_images(question_id):
    conn = get_db_connection()
    row = conn.execute('SELECT imagens FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    if row and row['imagens']:
        try:
            return jsonify(json.loads(row['imagens']))
        except json.JSONDecodeError:
            return jsonify([])
    return jsonify([])

@app.route('/api/images/<int:question_id>/<int:image_index>')
def get_question_image(question_id, image_index):
    conn = get_db_connection()
    row = conn.execute('SELECT imagens FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    if row and row['imagens']:
        try:
            images = json.loads(row['imagens'])
            if 0 <= image_index < len(images):
                img = images[image_index]
                return jsonify({
                    'base64': img.get('base64') or img.get('data') or '',
                    'filename': img.get('filename', ''),
                    'size': img.get('size', 0),
                })
        except json.JSONDecodeError:
            pass
    return jsonify({'error': 'Imagem não encontrada'}), 404

# ----------------------
# NOVAS ROTAS: provas & simulados (frontend depende destas)
# ----------------------

@app.route('/api/exams/available')
def get_available_exams():
    return jsonify(simulados_system_v2.get_available_exams())

@app.route('/api/exams/statistics')
def get_exam_statistics():
    return jsonify(simulados_system_v2.get_exam_statistics())

@app.route('/api/simulados/create', methods=['POST'])
def create_simulado():
    data = request.get_json() or {}
    selected_exams = data.get('selected_exams', [])
    exam_distribution = data.get('exam_distribution', None)  # Nova funcionalidade
    num_questions = data.get('num_questions', 24)  # Total de questões
    
    if not selected_exams:
        return jsonify({'error': 'Nenhuma prova selecionada'}), 400

    # Validar distribuição personalizada se fornecida
    if exam_distribution:
        total_distributed = sum(exam_distribution.values())
        if total_distributed != num_questions:
            return jsonify({
                'error': f'Distribuição inválida. Total: {total_distributed}, esperado: {num_questions}'
            }), 400
        
        # Verificar se todas as provas na distribuição estão selecionadas
        for exam_name in exam_distribution.keys():
            if exam_name not in selected_exams:
                return jsonify({
                    'error': f'Prova {exam_name} não está selecionada'
                }), 400

    try:
        # Gera questões com distribuição personalizada ou aleatória
        questions = simulados_system_v2.create_randomized_exam(
            selected_exams, 
            num_questions=num_questions,
            exam_distribution=exam_distribution
        )
        
        if not questions or len(questions) < num_questions:
            return jsonify({
                'error': f'Questões insuficientes. Apenas {len(questions) if questions else 0} disponíveis; são necessárias {num_questions}.'
            }), 400

        # Salva versão ENXUTA na sessão (sem imagens e com texto limitado)
        simplified = []
        for q in questions:
            # Limitar tamanho do enunciado e alternativas
            enunciado = q['enunciado'][:500] if q['enunciado'] else f"Questão {q['id']}"
            a = q['a'][:1000] if q['a'] else ''
            b = q['b'][:1000] if q['b'] else ''
            c = q['c'][:1000] if q['c'] else ''
            d = q['d'][:1000] if q['d'] else ''
            e = q['e'][:1000] if q['e'] else ''
            
            simplified.append({
                'id': q['id'],
                'enunciado': enunciado,
                'a': a, 'b': b, 'c': c, 'd': d, 'e': e,
                'gabarito': q['gabarito'],
                'fonte': q['fonte'],
                'tipo': q.get('tipo', 'completa'),
                'bloco': q.get('bloco', 1)
            })
            
    except Exception as e:
        print(f"Erro ao criar simulado: {e}")
        return jsonify({
            'error': f'Erro interno ao criar simulado: {str(e)}'
        }), 500

    # Salvar apenas dados essenciais na sessão
    session['current_simulado'] = {
        'questions': simplified,
        'selected_exams': selected_exams,
        'num_questoes': len(questions),
        'start_time': datetime.now().isoformat(),
    }
    
    # Retornar resposta mínima
    return jsonify({
        'success': True, 
        'num_questions': len(questions),
        'message': 'Simulado criado com sucesso'
    })

@app.route('/api/simulados/current')
def get_current_simulado():
    current = session.get('current_simulado')
    if not current:
        return jsonify({'error': 'Nenhum simulado ativo'}), 404

    # Completa com dados do banco (inclui imagens)
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(questoes)')
    cols = [c[1] for c in cursor.fetchall()]

    filled = []
    for q in current.get('questions', []):
        qid = q.get('id')
        if not qid:
            continue
        if 'enunciado' in cols:
            if 'tipo' in cols:
                cursor.execute('''
                    SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens, tipo
                    FROM questoes WHERE id = ?
                ''', (qid,))
            else:
                cursor.execute('''
                    SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens
                    FROM questoes WHERE id = ?
                ''', (qid,))
        else:
            cursor.execute('''
                SELECT id, a, b, c, d, e, gabarito, fonte, imagens
                FROM questoes WHERE id = ?
            ''', (qid,))
        row = cursor.fetchone()
        if not row:
            continue
        # Monta objeto homogêneo
        if 'enunciado' in cols:
            if 'tipo' in cols and len(row) > 10:
                filled.append({
                    'id': row[0], 'enunciado': row[1] or '',
                    'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
                    'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
                    'tipo': row[10] or 'completa', 'bloco': q.get('bloco', 1)
                })
            else:
                filled.append({
                    'id': row[0], 'enunciado': row[1] or '',
                    'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
                    'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
                    'tipo': 'completa', 'bloco': q.get('bloco', 1)
                })
        else:
            filled.append({
                'id': row[0], 'enunciado': row[1] or '',
                'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
                'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
                'tipo': 'completa', 'bloco': q.get('bloco', 1)
            })
    conn.close()

    return jsonify({
        'num_questoes': current.get('num_questoes', len(filled)),
        'questions': filled,
        'selected_exams': current.get('selected_exams', []),
        'start_time': current.get('start_time')
    })

@app.route('/api/simulados/question/<int:question_id>')
def get_simulado_question(question_id):
    """Retorna uma questão (com imagens). Não depende mais de sessão, para evitar 500."""
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(questoes)')
    cols = [c[1] for c in cursor.fetchall()]

    if 'enunciado' in cols:
        if 'tipo' in cols:
            cursor.execute('''
                SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens, tipo
                FROM questoes WHERE id = ?
            ''', (question_id,))
        else:
            cursor.execute('''
                SELECT id, enunciado, a, b, c, d, e, gabarito, fonte, imagens
                FROM questoes WHERE id = ?
            ''', (question_id,))
    else:
        cursor.execute('''
            SELECT id, a, b, c, d, e, gabarito, fonte, imagens
            FROM questoes WHERE id = ?
        ''', (question_id,))

    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Questão não encontrada'}), 404

    if 'enunciado' in cols:
        if 'tipo' in cols and len(row) > 10:
            return jsonify({
                'id': row[0], 'enunciado': row[1] or '',
                'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
                'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
                'tipo': row[10] or 'completa'
            })
        else:
            return jsonify({
                'id': row[0], 'enunciado': row[1] or '',
                'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
                'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
                'tipo': 'completa'
            })
    else:
        return jsonify({
            'id': row[0], 'enunciado': row[1] or '',
            'a': row[2] or '', 'b': row[3] or '', 'c': row[4] or '', 'd': row[5] or '', 'e': row[6] or '',
            'gabarito': row[7] or '', 'fonte': row[8] or '', 'imagens': row[9] or '[]',
            'tipo': 'completa'
        })

@app.route('/api/simulados/submit', methods=['POST'])
def submit_simulado():
    data = request.get_json() or {}
    current = session.get('current_simulado')
    if not current:
        return jsonify({'error': 'Nenhum simulado ativo'}), 400

    answers = data.get('answers', {})
    skipped = data.get('skipped_questions', [])

    total = current['num_questoes']
    correct = 0
    wrong = 0

    for qid, ans in answers.items():
        q = next((q for q in current['questions'] if str(q['id']) == str(qid)), None)
        if q and (ans or '').lower() == (q['gabarito'] or '').lower():
            correct += 1
        else:
            wrong += 1

    start_time = datetime.fromisoformat(current['start_time'])
    time_used = str(datetime.now() - start_time).split('.')[0]

    simulado_id = simulados_system_v2.save_simulado_result(
        current['selected_exams'], total, [q['id'] for q in current['questions']],
        time_used, correct, wrong, len(skipped)
    )

    session.pop('current_simulado', None)

    results_data = {
        'total_questions': total,
        'correct_answers': correct,
        'incorrect_answers': wrong,
        'skipped_questions': len(skipped),
        'time_used': time_used,
        'percentage': round((correct / total) * 100, 2),
        'simulado_id': simulado_id
    }
    
    import urllib.parse
    results_encoded = urllib.parse.quote(json.dumps(results_data))
    
    return jsonify({
        'success': True,
        'redirect_url': f'/?results={results_encoded}'
    })

@app.route('/api/simulados/history')
def get_simulados_history():
    return jsonify(simulados_system_v2.get_simulados_history())

@app.route('/api/simulados/history/<int:simulado_id>')
def get_simulado_by_id(simulado_id):
    simulado = simulados_system_v2.get_simulado_by_id(simulado_id)
    if simulado:
        return jsonify(simulado)
    else:
        return jsonify({'error': 'Simulado não encontrado'}), 404

@app.route('/api/simulados/statistics')
def get_simulados_statistics():
    return jsonify(simulados_system_v2.get_statistics())

# ----------------------
# Bootstrap
# ----------------------

if __name__ == '__main__':
    app.run(debug=True)
