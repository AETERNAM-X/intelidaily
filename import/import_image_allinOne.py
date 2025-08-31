import sqlite3
import os
import base64


def get_available_exams():
    conn = sqlite3.connect("questions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT fonte FROM questoes ORDER BY fonte DESC")
    exams = cursor.fetchall()
    conn.close()
    return [exam[0] for exam in exams]


def encode_image(image_path):
    if not os.path.exists(image_path):
        return None, None
    with open(image_path, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode("utf-8"), len(data)


def import_images_for_exam(conn, exam_name, folder_path):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM questoes WHERE fonte = ? ORDER BY id", (exam_name,))
    questions = cursor.fetchall()

    if not questions:
        print(f"❌ Nenhuma questão encontrada na prova {exam_name}")
        return False

    # Carregar todas as imagens uma vez
    images = {}
    for alt in ["A", "B", "C", "D", "E"]:
        file_path = os.path.join(folder_path, f"{alt}.webp")
        img_b64, size = encode_image(file_path)
        if img_b64:
            images[alt.lower()] = img_b64
            print(f"✅ Imagem {alt}.webp carregada ({size} bytes)")
        else:
            print(f"⚠️ {file_path} não encontrado, ignorado.")

    # Ler gabarito
    gabarito_file = os.path.join(folder_path, "gabarito.txt")
    correct_alt = None
    if os.path.exists(gabarito_file):
        with open(gabarito_file, "r", encoding="utf-8") as f:
            correct_alt = f.read().strip().upper()
        if correct_alt not in ["A", "B", "C", "D", "E"]:
            correct_alt = None

    # Atualizar todas as questões da prova
    for (qid,) in questions:
        for alt, img_b64 in images.items():
            cursor.execute(
                f"UPDATE questoes SET {alt} = ? WHERE id = ? AND fonte = ?",
                (img_b64, qid, exam_name),
            )
        if correct_alt:
            cursor.execute(
                "UPDATE questoes SET gabarito = ? WHERE id = ? AND fonte = ?",
                (correct_alt.lower(), qid, exam_name),
            )
    conn.commit()
    print(f"🎉 Todas as {len(questions)} questões da prova '{exam_name}' foram atualizadas!")
    if correct_alt:
        print(f"🎯 Gabarito definido como {correct_alt} em todas as questões")
    return True


def main():
    print("🖼️ Importador em lote de imagens para TODAS as questões da prova")
    exams = get_available_exams()
    print("\n📚 Provas disponíveis:")
    for i, exam in enumerate(exams, 1):
        print(f"{i}. {exam}")

    exam_choice = int(input(f"\n> Escolha a prova (1-{len(exams)}): ")) - 1
    selected_exam = exams[exam_choice]
    print(f"✅ Prova selecionada: {selected_exam}")

    folder_path = input("> Digite o caminho da pasta com as imagens (A-E.webp + gabarito.txt): ").strip()

    conn = sqlite3.connect("questions.db")
    try:
        import_images_for_exam(conn, selected_exam, folder_path)
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()