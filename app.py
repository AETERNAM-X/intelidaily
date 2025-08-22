# app.py (sem alterações, pois o problema está no frontend)
from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import base64
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('questions.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return render_template('test_frontend.html')

@app.route('/api/questions')
def get_questions():
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questoes').fetchall()
    conn.close()
    
    questions_list = []
    for question in questions:
        questions_list.append({
            'id': question['id'],
            'enunciado': question['enunciado'],
            'a': question['a'],
            'b': question['b'],
            'c': question['c'],
            'd': question['d'],
            'e': question['e'],
            'gabarito': question['gabarito'],
            'fonte': question['fonte'],
            'imagens': question['imagens'] if 'imagens' in question.keys() else '[]'
        })
    
    return jsonify(questions_list)

@app.route('/api/questions/<int:question_id>')
def get_question(question_id):
    conn = get_db_connection()
    question = conn.execute('SELECT * FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    
    if question:
        return jsonify({
            'id': question['id'],
            'enunciado': question['enunciado'],
            'a': question['a'],
            'b': question['b'],
            'c': question['c'],
            'd': question['d'],
            'e': question['e'],
            'gabarito': question['gabarito'],
            'fonte': question['fonte'],
            'imagens': question['imagens'] if 'imagens' in question.keys() else '[]'
        })
    else:
        return jsonify({'error': 'Questão não encontrada'}), 404

@app.route('/api/exam/submit', methods=['POST'])
def submit_exam():
    data = request.get_json()
    
    # Calcular resultados
    total_questions = len(data.get('answers', {}))
    correct_answers = 0
    incorrect_answers = 0
    wrong_answers_details = []
    
    # Buscar gabaritos do banco
    conn = get_db_connection()
    
    for question_id, user_answer in data.get('answers', {}).items():
        question = conn.execute('SELECT gabarito FROM questoes WHERE id = ?', (question_id,)).fetchone()
        if question:
            correct_answer = question['gabarito'].lower()
            if user_answer.lower() == correct_answer:
                correct_answers += 1
            else:
                incorrect_answers += 1
                # Buscar detalhes da questão errada
                question_details = conn.execute('SELECT enunciado, a, b, c, d, e FROM questoes WHERE id = ?', (question_id,)).fetchone()
                if question_details:
                    wrong_answers_details.append({
                        'question_id': question_id,
                        'user_answer': user_answer.upper(),
                        'correct_answer': correct_answer.upper(),
                        'enunciado': question_details['enunciado'][:100] + '...' if len(question_details['enunciado']) > 100 else question_details['enunciado'],
                        'alternatives': {
                            'a': question_details['a'],
                            'b': question_details['b'],
                            'c': question_details['c'],
                            'd': question_details['d'],
                            'e': question_details['e']
                        }
                    })
    
    conn.close()
    
    # Calcular tempo utilizado
    start_time = datetime.fromisoformat(data.get('start_time', datetime.now().isoformat()))
    end_time = datetime.now()
    time_used = end_time - start_time
    
    results = {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'answered_questions': len(data.get('answers', {})),
        'skipped_questions': len(data.get('skipped_questions', [])),
        'time_used': str(time_used).split('.')[0],  # Remover microssegundos
        'wrong_answers_details': wrong_answers_details
    }
    
    return jsonify(results)

@app.route('/api/images/<int:question_id>')
def get_question_images(question_id):
    """Endpoint para obter imagens de uma questão específica"""
    conn = get_db_connection()
    question = conn.execute('SELECT imagens FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    
    if question and question['imagens']:
        try:
            images = json.loads(question['imagens'])
            return jsonify(images)
        except json.JSONDecodeError:
            return jsonify([])
    else:
        return jsonify([])

@app.route('/api/images/<int:question_id>/<int:image_index>')
def get_question_image(question_id, image_index):
    """Endpoint para obter uma imagem específica de uma questão"""
    conn = get_db_connection()
    question = conn.execute('SELECT imagens FROM questoes WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    
    if question and question['imagens']:
        try:
            images = json.loads(question['imagens'])
            if 0 <= image_index < len(images):
                image_data = images[image_index]
                return jsonify({
                    'base64': image_data.get('base64', ''),
                    'filename': image_data.get('filename', ''),
                    'size': image_data.get('size', 0)
                })
        except json.JSONDecodeError:
            pass
    
    return jsonify({'error': 'Imagem não encontrada'}), 404

if __name__ == '__main__':
    app.run(debug=True)