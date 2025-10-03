#!/usr/bin/env python3
"""
Script de build para otimização do InteliDaily
Inclui minificação de CSS e JS, otimização de imagens e outras melhorias
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Executa um comando e trata erros"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao {description.lower()}:")
        print(f"   Comando: {command}")
        print(f"   Erro: {e.stderr}")
        return False

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    # Verificar se Node.js está instalado
    if not run_command("node --version", "Verificar Node.js"):
        print("❌ Node.js não encontrado. Instale Node.js primeiro.")
        return False
    
    # Verificar se npm está disponível
    if not run_command("npm --version", "Verificar npm"):
        print("❌ npm não encontrado. Instale npm primeiro.")
        return False
    
    return True

def install_dependencies():
    """Instala as dependências do npm"""
    print("📦 Instalando dependências...")
    
    if not os.path.exists("package.json"):
        print("❌ package.json não encontrado!")
        return False
    
    return run_command("npm install", "Instalar dependências do npm")

def build_css():
    """Minifica e otimiza o CSS usando LightningCSS"""
    print("🎨 Otimizando CSS...")
    
    css_file = "static/css/style.css"
    output_file = "static/css/style.min.css"
    
    if not os.path.exists(css_file):
        print(f"❌ Arquivo CSS não encontrado: {css_file}")
        return False
    
    # Comando LightningCSS para minificar e otimizar
    command = f"npx lightningcss --minify --bundle {css_file} -o {output_file}"
    return run_command(command, "Minificar CSS com LightningCSS")

def build_js():
    """Minifica o JavaScript usando Terser"""
    print("⚡ Otimizando JavaScript...")
    
    js_file = "static/js/script.js"
    output_file = "static/js/script.min.js"
    
    if not os.path.exists(js_file):
        print(f"❌ Arquivo JS não encontrado: {js_file}")
        return False
    
    # Comando Terser para minificar
    command = f"npx terser {js_file} -o {output_file} -c -m"
    return run_command(command, "Minificar JavaScript com Terser")

def optimize_images():
    """Otimiza imagens (se tiver ferramentas disponíveis)"""
    print("🖼️ Verificando otimização de imagens...")
    
    # Verificar se tem imagens para otimizar
    image_dirs = ["2022_questions_imgs", "2023_questions_imgs", "2024_questions_imgs", "2025_questions_imgs"]
    has_images = any(os.path.exists(d) for d in image_dirs)
    
    if not has_images:
        print("ℹ️ Nenhuma imagem encontrada para otimizar")
        return True
    
    print("ℹ️ Para otimizar imagens, considere usar:")
    print("   - imagemin-cli: npm install -g imagemin-cli")
    print("   - sharp-cli: npm install -g sharp-cli")
    print("   - ou ferramentas online como TinyPNG")
    
    return True

def create_optimized_templates():
    """Cria versões otimizadas dos templates"""
    print("📄 Criando templates otimizados...")
    
    # Ler template original
    with open("templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Substituir referências para arquivos minificados
    content = content.replace("style.css", "style.min.css")
    content = content.replace("script.js", "script.min.js")
    
    # Salvar template otimizado
    with open("templates/index.optimized.html", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Template otimizado criado: templates/index.optimized.html")
    return True

def generate_report():
    """Gera relatório de otimização"""
    print("\n📊 Relatório de Otimização:")
    print("=" * 50)
    
    # Verificar tamanhos dos arquivos
    files_to_check = [
        ("static/css/style.css", "CSS Original"),
        ("static/css/style.min.css", "CSS Minificado"),
        ("static/js/script.js", "JS Original"),
        ("static/js/script.min.js", "JS Minificado")
    ]
    
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            size_kb = size / 1024
            print(f"{description}: {size_kb:.2f} KB")
        else:
            print(f"{description}: Arquivo não encontrado")
    
    print("\n💡 Próximos passos:")
    print("1. Teste o site com os arquivos minificados")
    print("2. Configure o servidor para usar os arquivos .min")
    print("3. Configure cache headers para arquivos estáticos")
    print("4. Considere usar CDN para recursos externos")

def main():
    """Função principal"""
    print("🚀 Iniciando build do InteliDaily...")
    print("=" * 50)
    
    # Verificar dependências
    if not check_dependencies():
        sys.exit(1)
    
    # Instalar dependências
    if not install_dependencies():
        print("❌ Falha ao instalar dependências")
        sys.exit(1)
    
    # Build CSS
    if not build_css():
        print("❌ Falha ao otimizar CSS")
        sys.exit(1)
    
    # Build JS
    if not build_js():
        print("❌ Falha ao otimizar JavaScript")
        sys.exit(1)
    
    # Otimizar imagens
    optimize_images()
    
    # Criar templates otimizados
    create_optimized_templates()
    
    # Gerar relatório
    generate_report()
    
    print("\n🎉 Build concluído com sucesso!")
    print("=" * 50)

if __name__ == "__main__":
    main()
