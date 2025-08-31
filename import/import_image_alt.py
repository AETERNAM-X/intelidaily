import sqlite3
import os
import base64
import json
from pathlib import Path

def get_available_exams():
    """Retorna lista de provas disponíveis"""
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT fonte FROM questoes ORDER BY fonte DESC')
    exams = cursor.fetchall()
    conn.close()
    
    return [exam[0] for exam in exams]

def get_questions_by_exam(exam_name):
    """Retorna questões de uma prova específica"""
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, enunciado FROM questoes WHERE fonte = ? ORDER BY id', (exam_name,))
    questions = cursor.fetchall()
    conn.close()
    
    return questions

def import_image_as_alternative(exam_name, question_id, alternative, image_path, is_correct=False):
    """Importa uma imagem como alternativa para uma questão específica"""
    
    # Verificar se a imagem existe
    if not os.path.exists(image_path):
        print(f"❌ Erro: Arquivo {image_path} não encontrado!")
        return False
    
    # Ler e converter imagem para base64
    try:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
        # Obter informações do arquivo
        file_size = len(img_data)
        filename = os.path.basename(image_path)
        
        # Salvar apenas o base64 da imagem, não a estrutura JSON completa
        # Isso evita problemas de exibição no frontend
        
    except Exception as e:
        print(f"❌ Erro ao ler imagem: {e}")
        return False
    
    # Conectar ao banco
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se a questão existe
        cursor.execute('SELECT id, a, b, c, d, e, gabarito FROM questoes WHERE id = ? AND fonte = ?', 
                      (question_id, exam_name))
        question = cursor.fetchone()
        
        if not question:
            print(f"❌ Erro: Questão {question_id} não encontrada na prova {exam_name}")
            return False
        
        # Atualizar a alternativa com apenas o base64 da imagem
        # Não usar json.dumps para evitar estruturas JSON complexas
        update_query = f'UPDATE questoes SET {alternative.lower()} = ? WHERE id = ?'
        cursor.execute(update_query, (img_base64, question_id))
        
        # Se for a resposta correta, atualizar o gabarito
        if is_correct:
            cursor.execute('UPDATE questoes SET gabarito = ? WHERE id = ?', (alternative.lower(), question_id))
            print(f"✅ Gabarito atualizado para alternativa {alternative.upper()}")
        
        conn.commit()
        print(f"✅ Imagem importada com sucesso como alternativa {alternative.upper()} para questão {question_id}")
        print(f"   Tamanho da imagem: {file_size} bytes")
        print(f"   Nome do arquivo: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar banco: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Função principal do script"""
    print("🖼️  Script para Importar Imagens como Alternativas")
    print("=" * 50)
    
    # 1. Selecionar prova
    exams = get_available_exams()
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
    
    print(f"\n✅ Prova selecionada: {selected_exam}")
    
    # 2. Selecionar questão
    questions = get_questions_by_exam(selected_exam)
    print(f"\n📝 Questões disponíveis na prova {selected_exam}:")
    for q_id, enunciado in questions[:10]:  # Mostrar apenas as primeiras 10
        print(f"ID {q_id}: {enunciado[:50]}...")
    
    if len(questions) > 10:
        print(f"... e mais {len(questions) - 10} questões")
    
    while True:
        try:
            question_id = int(input(f"\n> Digite o ID da questão: "))
            if any(q[0] == question_id for q in questions):
                break
            else:
                print("❌ ID de questão inválido!")
        except ValueError:
            print("❌ Digite um número válido!")
    
    print(f"✅ Questão selecionada: ID {question_id}")
    
    # 3. Selecionar alternativa
    alternatives = ['A', 'B', 'C', 'D', 'E']
    print(f"\n🔤 Alternativas disponíveis: {', '.join(alternatives)}")
    
    while True:
        alternative = input("> Digite a alternativa (a, b, c, d, e): ").upper()
        if alternative in alternatives:
            break
        else:
            print("❌ Alternativa inválida!")
    
    print(f"✅ Alternativa selecionada: {alternative}")
    
    # 4. Caminho da imagem
    print(f"\n🖼️  Caminho da imagem")
    print("💡 Dica: Você pode arrastar e soltar o arquivo aqui, ou digitar o caminho completo")
    
    while True:
        image_path = input("> Caminho da imagem: ").strip()
        
        # Remover aspas se existirem
        image_path = image_path.strip('"\'')
        
        if os.path.exists(image_path):
            break
        else:
            print("❌ Arquivo não encontrado! Verifique o caminho.")
    
    print(f"✅ Imagem encontrada: {os.path.basename(image_path)}")
    
    # 5. Definir se é a resposta correta
    print(f"\n🎯 Esta é a resposta correta?")
    while True:
        is_correct = input("> Digite 'Y' para sim ou 'N' para não: ").upper()
        if is_correct in ['Y', 'N']:
            is_correct = (is_correct == 'Y')
            break
        else:
            print("❌ Digite 'Y' ou 'N'!")
    
    if is_correct:
        print("✅ Imagem será marcada como resposta correta")
    else:
        print("ℹ️  Imagem será apenas uma alternativa")
    
    # 6. Confirmar operação
    print(f"\n📋 Resumo da operação:")
    print(f"   Prova: {selected_exam}")
    print(f"   Questão: ID {question_id}")
    print(f"   Alternativa: {alternative}")
    print(f"   Imagem: {os.path.basename(image_path)}")
    print(f"   Resposta correta: {'Sim' if is_correct else 'Não'}")
    
    while True:
        confirm = input("\n> Confirmar operação? (Y/N): ").upper()
        if confirm in ['Y', 'N']:
            break
        else:
            print("❌ Digite 'Y' ou 'N'!")
    
    if confirm == 'N':
        print("❌ Operação cancelada!")
        return
    
    # 7. Executar importação
    print(f"\n🔄 Executando importação...")
    
    success = import_image_as_alternative(
        selected_exam, 
        question_id, 
        alternative, 
        image_path, 
        is_correct
    )
    
    if success:
        print(f"\n🎉 Importação concluída com sucesso!")
        print(f"   A imagem agora é a alternativa {alternative} da questão {question_id}")
        if is_correct:
            print(f"   E é a resposta correta da questão!")
    else:
        print(f"\n❌ Falha na importação!")
        print(f"   Verifique os logs acima para mais detalhes")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n❌ Operação cancelada pelo usuário!")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    
    input("\nPressione Enter para sair...")
