import sqlite3
import json
import os

DB_PATH = 'questions.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
            fonte TEXT,
            imagens TEXT DEFAULT '[]',
            tipo TEXT DEFAULT 'completa'
        )
    ''')
    conn.commit()
    conn.close()


def import_questions(questions, fonte="Importação"):
    """
    Importa questões no formato padronizado.
    Cada questão deve ser um dicionário com as chaves:
    enunciado, a, b, c, d, e, gabarito, imagens, tipo
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for q in questions:
        enunciado = q.get('enunciado', '')
        a = q.get('a', '')
        b = q.get('b', '')
        c = q.get('c', '')
        d = q.get('d', '')
        e = q.get('e', '')
        gabarito = q.get('gabarito', '')
        tipo = q.get('tipo', 'completa')

        # 🔧 Padroniza imagens: sempre JSON válido
        imagens = q.get('imagens') or []
        if not isinstance(imagens, str):
            try:
                imagens = json.dumps(imagens)
            except Exception:
                imagens = '[]'

        cursor.execute('''
            INSERT INTO questoes (enunciado, a, b, c, d, e, gabarito, fonte, imagens, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (enunciado, a, b, c, d, e, gabarito, fonte, imagens, tipo))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()