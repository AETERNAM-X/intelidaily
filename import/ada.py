import sqlite3
import os

def get_available_databases():
    """Retorna lista de bancos de dados disponíveis"""
    db_files = []
    candidates = ['questions1.db', 'questions(sem imagem em alternativa).db', 'questions.db']
    
    for db_file in candidates:
        if os.path.exists(db_file) and os.path.getsize(db_file) > 0:
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='questoes'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM questoes")
                    count = cursor.fetchone()[0]
                    db_files.append((db_file, count))
                conn.close()
            except:
                pass
    
    return db_files


def get_available_exams(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT fonte FROM questoes ORDER BY fonte DESC")
    exams = cursor.fetchall()
    conn.close()
    return [exam[0] for exam in exams]


def get_questions_by_exam(db_path, exam_name):
    """Retorna questões de uma prova específica"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, enunciado FROM questoes WHERE fonte = ? ORDER BY id", (exam_name,))
    questions = cursor.fetchall()
    conn.close()
    return questions


def save_as_original(image_path, base_folder):
    """
    Retorna caminho relativo ao servidor Flask, com prefixo da pasta base.
    Exemplo: questions_alts/2024_30/A.webp
    """
    parent_folder = os.path.basename(base_folder.rstrip("/\\"))
    file_name = os.path.basename(image_path)
    return f"questions_alts/{parent_folder}/{file_name}"


def import_images_for_question(db_path, exam_name, question_id, folder_path, shared=False):
    """Importa imagens para uma questão"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM questoes WHERE id = ? AND fonte = ?", (question_id, exam_name))
        question = cursor.fetchone()
        
        if not question:
            print(f"❌ Questão {question_id} não encontrada na prova {exam_name}")
            return False

        images = {}
        for alt in ["A", "B", "C", "D", "E"]:
            found = None
            for ext in [".webp", ".png", ".jpg", ".jpeg"]:
                candidate = os.path.join(folder_path, f"{alt}{ext}")
                if os.path.exists(candidate):
                    found = candidate
                    break
            if found:
                rel_path = save_as_original(found, folder_path).replace("\\", "/")
                images[alt.lower()] = rel_path
                if not shared:
                    print(f"✅ Alternativa {alt} salva como {rel_path}")
            else:
                if not shared:
                    print(f"⚠️ {alt} não encontrada em {folder_path}, ignorado.")

        gabarito_file = os.path.join(folder_path, "gabarito.txt")
        correct_alt = None
        if os.path.exists(gabarito_file):
            with open(gabarito_file, "r", encoding="utf-8") as f:
                correct_alt = f.read().strip().upper()
            if correct_alt not in ["A", "B", "C", "D", "E"]:
                correct_alt = None

        for alt, rel_path in images.items():
            cursor.execute(
                f"UPDATE questoes SET {alt} = ? WHERE id = ? AND fonte = ?",
                (rel_path, question_id, exam_name),
            )
        
        if correct_alt:
            cursor.execute(
                "UPDATE questoes SET gabarito = ? WHERE id = ? AND fonte = ?",
                (correct_alt.lower(), question_id, exam_name),
            )
        
        conn.commit()
        if not shared:
            print(f"🎉 Questão {question_id} da prova '{exam_name}' foi atualizada!")
            if correct_alt:
                print(f"🎯 Gabarito definido como {correct_alt}")
        return True
        
    finally:
        conn.close()


def import_images_for_all_questions(db_path, exam_name, folder_path):
    """Importa as mesmas imagens para TODAS as questões de uma prova"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM questoes WHERE fonte = ? ORDER BY id", (exam_name,))
    questions = cursor.fetchall()
    conn.close()

    print(f"🔄 Encontradas {len(questions)} questões na prova {exam_name}.")
    for (question_id,) in questions:
        try:
            import_images_for_question(db_path, exam_name, question_id, folder_path, shared=True)
            print(f"✅ Questão {question_id} atualizada com as imagens compartilhadas")
        except Exception as e:
            print(f"❌ Erro ao importar questão {question_id}: {e}")


def main():
    print("🖼️ Importador de imagens para questões")
    print("=" * 50)
    
    databases = get_available_databases()
    if not databases:
        print("❌ Nenhum banco de dados encontrado!")
        return
    
    print("\n💾 Bancos de dados disponíveis:")
    for i, (db_file, count) in enumerate(databases, 1):
        print(f"{i}. {db_file} ({count} questões)")

    while True:
        try:
            db_choice = int(input(f"\n> Escolha o banco de dados (1-{len(databases)}): ")) - 1
            if 0 <= db_choice < len(databases):
                selected_db, _ = databases[db_choice]
                break
            else:
                print("❌ Opção inválida!")
        except ValueError:
            print("❌ Digite um número válido!")
    
    print(f"✅ Banco selecionado: {selected_db}")
    
    exams = get_available_exams(selected_db)
    print("\n📚 Provas disponíveis:")
    for i, exam in enumerate(exams, 1):
        print(f"{i}. {exam}")

    while True:
        try:
            exam_choice = int(input(f"\n> Escolha a prova (1-{len(exams)}): ")) - 1
            if 0 <= exam_choice < len(exams):
                selected_exam = exams[exam_choice]
                break
            else:
                print("❌ Opção inválida!")
        except ValueError:
            print("❌ Digite um número válido!")
    
    print(f"✅ Prova selecionada: {selected_exam}")

    mode = input("\n> Deseja importar (1) uma questão específica ou (2) TODAS as questões da prova (mesma pasta)? [1/2]: ").strip()
    
    if mode == "1":
        questions = get_questions_by_exam(selected_db, selected_exam)
        print(f"\n📝 Questões disponíveis na prova {selected_exam}:")
        for q_id, enunciado in questions:
            print(f"ID {q_id}: {enunciado[:50]}...")

        while True:
            try:
                question_id = int(input(f"\n> Digite o ID da questão: "))
                if any(q[0] == question_id for q in questions):
                    break
                else:
                    print("❌ ID inválido!")
            except ValueError:
                print("❌ Digite um número válido!")

        folder_path = input("\n> Digite o caminho da pasta com as imagens (A-E + gabarito.txt): ").strip().strip('"\'')
        if not os.path.exists(folder_path):
            print(f"❌ Pasta não encontrada: {folder_path}")
            return
        
        print(f"\n📋 Importando questão {question_id} da prova {selected_exam}...")
        import_images_for_question(selected_db, selected_exam, question_id, folder_path)

    else:
        folder_path = input("\n> Digite o caminho da pasta (mesma para TODAS as questões, contém A-E + gabarito.txt): ").strip().strip('"\'')
        if not os.path.exists(folder_path):
            print(f"❌ Pasta não encontrada: {folder_path}")
            return
        
        print(f"\n📋 Importando TODAS as questões da prova {selected_exam} usando a mesma pasta...")
        import_images_for_all_questions(selected_db, selected_exam, folder_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n❌ Operação cancelada pelo usuário!")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    
    input("\nPressione Enter para sair...")
