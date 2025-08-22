# Sistema de Vestibular - Prova Online

Um sistema completo de prova online desenvolvido em Python Flask com interface moderna e funcionalidades avançadas.

## 🚀 Funcionalidades

- **Sistema de Provas Dinâmico**: Carrega questões do banco de dados SQLite
- **Timer de 2 Horas**: Controle de tempo com alertas automáticos
- **Navegação Inteligente**: Botões para navegar entre questões
- **Contador de Questões**: Mostra quantas questões foram respondidas
- **Sistema de Blocos**: Organiza questões em 4 blocos de 24 questões cada
- **Interface Responsiva**: Funciona em desktop e dispositivos móveis
- **Persistência de Respostas**: Salva respostas durante a sessão
- **API RESTful**: Endpoints para gerenciar provas e resultados

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.7+, Flask
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Banco de Dados**: SQLite3
- **Estilização**: Tailwind CSS
- **Ícones**: Font Awesome
- **Fonte**: Inter (Google Fonts)

## 📋 Pré-requisitos

- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)
- Navegador web moderno

## 🚀 Instalação e Configuração

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd projeto_vestibular
```

### 2. Instale as dependências
```bash
pip install Flask
```

### 3. Configure o banco de dados
```bash
python db_manager.py
```

### 4. Execute a aplicação
```bash
python app.py
```

### 5. Acesse o sistema
Abra seu navegador e acesse: `http://localhost:5000`

## 📁 Estrutura do Projeto

```
projeto_vestibular/
├── app.py                 # Aplicação Flask principal
├── db_manager.py          # Gerenciador do banco de dados
├── questions.db           # Banco de dados SQLite
├── static/
│   ├── css/
│   │   └── style.css     # Estilos personalizados
│   └── js/
│       └── script.js     # Lógica do frontend
├── templates/
│   └── index.html        # Template principal
└── README.md             # Este arquivo
```

## 🎯 Como Usar

### Para Estudantes

1. **Acesse a prova**: Abra o sistema no navegador
2. **Inicie a prova**: Clique em "Iniciar Prova"
3. **Navegue pelas questões**: Use os botões numerados ou botões Anterior/Próximo
4. **Responda as questões**: Selecione uma opção (A, B, C, D ou E)
5. **Monitore o tempo**: Acompanhe o tempo restante no cabeçalho
6. **Finalize blocos**: Use o botão "Finalizar Bloco" quando terminar um bloco
7. **Encerre a prova**: Clique em "Encerrar prova" quando terminar

### Para Administradores

1. **Edite questões**: Modifique o arquivo `db_manager.py`
2. **Adicione novas questões**: Inclua na lista de questões
3. **Personalize o sistema**: Modifique templates e estilos
4. **Configure o tempo**: Altere a duração da prova no JavaScript

## 🔧 Configurações

### Alterar Tempo da Prova
No arquivo `static/js/script.js`, linha 15:
```javascript
const totalTime = 2 * 60 * 60 * 1000; // 2 horas em milissegundos
```

### Alterar Número de Questões por Bloco
No arquivo `static/js/script.js`, linha 16:
```javascript
const questionsPerBlock = 24; // Questões por bloco
```

### Adicionar Novas Questões
No arquivo `db_manager.py`, adicione na lista `questoes`:
```python
('Pergunta da questão?', 'Opção A', 'Opção B', 'Opção C', 'Opção D', 'Opção E', 'gabarito'),
```

## 📊 API Endpoints

### GET `/api/questions`
Retorna todas as questões disponíveis para a prova.

### GET `/api/questions/<id>`
Retorna uma questão específica por ID.

### POST `/api/exam/start`
Inicia uma nova sessão de prova.

### POST `/api/exam/end`
Encerra a sessão de prova atual.

### POST `/api/exam/submit`
Submete as respostas e calcula o resultado.

### GET `/api/stats`
Retorna estatísticas do sistema.

## 🎨 Personalização

### Cores do Sistema
As cores principais estão definidas em `static/css/style.css`:
- **Primária**: #FF3B3B (vermelho)
- **Secundária**: #3B4151 (azul escuro)
- **Sucesso**: #28a745 (verde)
- **Aviso**: #ffc107 (amarelo)

### Estilos
Modifique `static/css/style.css` para alterar:
- Animações e transições
- Layout responsivo
- Cores e tipografia
- Efeitos hover

## 📱 Responsividade

O sistema é totalmente responsivo e funciona em:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (até 767px)

## 🔒 Segurança

- **Validação de entrada**: Todas as entradas são validadas
- **Sanitização de dados**: Dados são limpos antes do processamento
- **Tratamento de erros**: Sistema robusto de tratamento de exceções

## 🐛 Solução de Problemas

### Erro: "Nenhuma questão encontrada"
- Execute `python db_manager.py` para criar o banco
- Verifique se o arquivo `questions.db` foi criado

### Erro: "Módulo Flask não encontrado"
- Instale o Flask: `pip install Flask`

### Erro: "Porta 5000 em uso"
- Altere a porta no arquivo `app.py`
- Ou pare outros serviços usando a porta 5000

### Questões não carregam
- Verifique a conexão com o banco de dados
- Confirme se `questions.db` existe e tem dados
- Verifique o console do navegador para erros JavaScript

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🎓 Sobre

Desenvolvido para o alunos estudarem para o vestibular do Instituto de Tecnologia e Liderança (Inteli).

---
Made By Juan Sales
**Versão**: 1.0.0