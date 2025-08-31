import fitz  # PyMuPDF
import os
import sys

def capture_all_pages(pdf_path, output_dir="2025_questions_imgs"):
    """
    Captura screenshot de todas as páginas do PDF
    """
    try:
        # Abre o PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"📄 PDF aberto: {pdf_path}")
        print(f"📊 Total de páginas: {total_pages}")
        
        # Cria pasta de saída
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 Pasta criada: {output_dir}")
        
        # Processa cada página
        for page_num in range(total_pages):
            try:
                # Carrega a página
                page = doc.load_page(page_num)
                
                # Captura screenshot em alta resolução
                pix = page.get_pixmap(dpi=300)
                
                # Nome do arquivo
                filename = f"questao_{page_num + 1:03d}.png"
                filepath = os.path.join(output_dir, filename)
                
                # Salva a imagem
                pix.save(filepath)
                
                print(f"✅ Página {page_num + 1:3d}/{total_pages}: {filename}")
                
            except Exception as e:
                print(f"❌ Erro na página {page_num + 1}: {e}")
                continue
        
        # Fecha o documento
        doc.close()
        
        print(f"\n🎉 Processamento concluído!")
        print(f"📁 Imagens salvas em: {output_dir}")
        print(f"📊 Total de páginas processadas: {total_pages}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {e}")
        return False

def main():
    """Função principal"""
    pdf_file = "Gabarito-Final-Prova-PS-2025.1.pdf"
    
    # Verifica se o PDF existe
    if not os.path.exists(pdf_file):
        print(f"❌ Arquivo PDF não encontrado: {pdf_file}")
        print("💡 Certifique-se de que o arquivo está na mesma pasta do script")
        return False
    
    print("🚀 Iniciando captura de screenshots...")
    print("=" * 50)
    
    # Executa a captura
    success = capture_all_pages(pdf_file)
    
    if success:
        print("\n✅ Script executado com sucesso!")
        print("📖 Use as imagens geradas para análise manual das questões")
    else:
        print("\n❌ Erro durante a execução")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        sys.exit(1)
