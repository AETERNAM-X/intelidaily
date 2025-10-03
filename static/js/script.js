document.addEventListener('DOMContentLoaded', () => {
    // Variáveis globais
    let allQuestions = [];
    let currentQuestionIndex = 0;
    let answeredQuestions = new Map();
    let examStartTime = null;
    let examTimer = null;
    let isExamStarted = false;
    let currentBlock = 1;
    let skippedQuestions = new Set();
    let blockCompleted = new Set();
    let timeSpent = new Map();
    let questionStartTime = Date.now();
    
    // Mapeamento das alternativas embaralhadas para cada questão
    let shuffledAlternatives = new Map();

    // Estrutura dos blocos
    const blockStructure = [8, 6, 6, 4];
    const totalQuestions = blockStructure.reduce((s, c) => s + c, 0);
    const totalTime = 2 * 60 * 60 * 1000;

    // Elementos DOM
    const elements = {
        startExamBtn: document.getElementById('start-exam-btn'),
        endExamBtn: document.getElementById('end-exam-btn'),
        startTimeElement: document.getElementById('start-time'),
        remainingTimeElement: document.getElementById('timer'),
        answeredCountElement: document.getElementById('answered-count'),
        answeredCountContainer: document.getElementById('answered-count-container'),
        questionNavigation: document.getElementById('question-nav'),
        questionContent: document.getElementById('question-content'),
        answerSection: document.getElementById('answer-section'),
        nextBtn: document.getElementById('next-btn'),
        finalizeBlockBtn: document.getElementById('finalize-block-btn'),
        skipQuestionBtn: document.getElementById('skip-question-btn'),
        skipToggle: document.getElementById('skip-toggle'),
        // resultsModal removido - resultados agora são exibidos no dashboard
        // closeResultsBtn removido - resultados agora são exibidos no dashboard
        skipChoiceModal: document.getElementById('skip-choice-modal'),
        skipChoiceList: document.getElementById('skip-choice-list'),
        // cancelSkipChoice: document.getElementById('cancel-skip-choice'),
        // confirmSkipChoice: document.getElementById('confirm-skip-choice'),
        questionTitle: document.getElementById('question-title'),
        questionText: document.getElementById('question-text'),
        questionImages: document.getElementById('question-images'),
        answerForm: document.getElementById('answer-form'),
    };

    // Estado de escolha de pulo
    let pendingFinalizeAfterSkipChoice = false;
    let chosenSkipIndex = null;
    
    // Controle de saída da tela
    let exitWarningShown = false;
    let exitWarningCount = 0;

    // Funções auxiliares
    function formatTime(d) {
        return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    // Função para detectar saída da tela
    function handleVisibilityChange() {
        if (document.hidden && isExamStarted) {
            if (!exitWarningShown) {
                exitWarningShown = true;
                exitWarningCount++;
                showExitWarning();
            }
        } else if (!document.hidden) {
            exitWarningShown = false;
        }
    }

    // Função para mostrar aviso de saída
    function showExitWarning() {
        const modal = document.getElementById('exit-warning-modal');
        if (modal) {
            modal.classList.remove('hidden');
            
            // Adicionar evento para fechar modal
            const continueBtn = document.getElementById('continue-exam-btn');
            
            if (continueBtn) {
                continueBtn.onclick = () => {
                    modal.classList.add('hidden');
                    exitWarningShown = false;
                };
            }
        }
    }

    // Função para mostrar modal de confirmação
    function showConfirmationModal(title, message, onConfirm, onCancel = null) {
        const modal = document.getElementById('confirmation-modal');
        const titleElement = document.getElementById('confirmation-title');
        const messageElement = document.getElementById('confirmation-message');
        const confirmBtn = document.getElementById('confirmation-confirm-btn');
        const cancelBtn = document.getElementById('confirmation-cancel-btn');
        
        if (modal && titleElement && messageElement && confirmBtn && cancelBtn) {
            titleElement.textContent = title;
            messageElement.textContent = message;
            modal.classList.remove('hidden');
            
            // Limpar eventos anteriores
            confirmBtn.onclick = null;
            cancelBtn.onclick = null;
            
            // Adicionar novos eventos
            confirmBtn.onclick = () => {
                modal.classList.add('hidden');
                if (onConfirm) onConfirm();
            };
            
            cancelBtn.onclick = () => {
                modal.classList.add('hidden');
                if (onCancel) onCancel();
            };
        }
    }

    function formatRemainingTime(ms) {
        if (ms <= 0) return '00:00:00';
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const h = Math.floor(m / 60);
        return `${h.toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    // Iniciar timer
    function startTimer() {
        let nextAlertMs = 30 * 60 * 1000; // 30 minutes
        examTimer = setInterval(() => {
            const now = new Date();
            const elapsed = now - examStartTime;
            const remaining = totalTime - elapsed;

            if (elements.remainingTimeElement) {
                elements.remainingTimeElement.textContent = formatRemainingTime(remaining);
                if (remaining < 10 * 60 * 1000) {
                    elements.remainingTimeElement.classList.add('time-warning');
                } else {
                    elements.remainingTimeElement.classList.remove('time-warning');
                }
            }

            // Popup a cada 30 minutos (mensagem sem emoji)
            if (elapsed >= nextAlertMs && remaining > 0) {
                const elapsedH = formatRemainingTime(elapsed);
                const remainingH = formatRemainingTime(remaining);
                alert(`Tempo de prova\n\nPassados: ${elapsedH}\nRestantes: ${remainingH}`);
                nextAlertMs += 30 * 60 * 1000;
            }

            if (remaining <= 0) {
                clearInterval(examTimer);
                alert('Tempo da prova esgotado!');
                endExam();
            }
        }, 1000);
    }

    // Funções de navegação por bloco
    function getBlockStartIndex(block) {
        let start = 0;
        for (let i = 0; i < block - 1; i++) {
            start += blockStructure[i];
        }
        return start;
    }

    function getBlockEndIndex(block) {
        return getBlockStartIndex(block) + blockStructure[block - 1];
    }

    function getCurrentBlock(qIndex) {
        // Validar entrada
        if (qIndex < 0 || qIndex >= totalQuestions) {
            console.warn(`Índice de questão inválido: ${qIndex}, retornando bloco 1`);
            return 1;
        }
        
        // Validar que qIndex é um número
        if (typeof qIndex !== 'number' || isNaN(qIndex)) {
            console.warn(`Índice de questão não é um número válido: ${qIndex}, retornando bloco 1`);
            return 1;
        }
        
        let acc = 0;
        for (let i = 0; i < blockStructure.length; i++) {
            acc += blockStructure[i];
            if (qIndex < acc) return i + 1;
        }
        // Garantir que sempre retorne um valor válido entre 1 e 4
        return 4;
    }

    // Funções de blur/desblur
    function applyBlurEffect() {
        elements.questionContent?.classList.add('blur-content');
        elements.answerSection?.classList.add('blur-content');

        if (elements.nextBtn) {
            elements.nextBtn.disabled = true;
            elements.nextBtn.classList.add("cursor-not-allowed", "opacity-50", "bg-gray-400");
            elements.nextBtn.classList.remove("bg-[#3B4151]", "hover:bg-[#2a2e3d]");
        }

        elements.finalizeBlockBtn?.classList.add('opacity-50', 'cursor-not-allowed');
        elements.answeredCountContainer?.classList.add('opacity-50');
        elements.questionNavigation?.classList.add('opacity-50');
    }

    function removeBlurEffect() {
        elements.questionContent?.classList.remove('blur-content');
        elements.answerSection?.classList.remove('blur-content');

        if (elements.nextBtn) {
            elements.nextBtn.disabled = false;
            elements.nextBtn.classList.add("bg-[#3B4151]", "hover:bg-[#2a2e3d]");
            elements.nextBtn.classList.remove("bg-gray-400", "cursor-not-allowed", "opacity-50");
        }

        elements.finalizeBlockBtn?.classList.remove('opacity-50', 'cursor-not-allowed');
        elements.answeredCountContainer?.classList.remove('opacity-50');
        elements.questionNavigation?.classList.remove('opacity-50');
    }

    // Atualizar indicadores de bloco
    function updateBlockIndicators() {
        for (let i = 1; i <= 4; i++) {
            const indicator = document.getElementById(`block-${i}`);
            const textElement = indicator?.nextElementSibling;

            if (indicator) {
                let indicatorClasses = 'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs select-none';
                let textClasses = 'text-xs mt-1 select-none';

                if (i === currentBlock) {
                    indicatorClasses += ' bg-[#FF3B3B] font-bold';
                    textClasses += ' text-[#FF3B3B] font-semibold';
                } else if (blockCompleted.has(i)) {
                    indicatorClasses += ' bg-[#3B4151] font-semibold';
                    textClasses += ' text-gray-600 font-semibold';
                } else {
                    indicatorClasses += ' bg-gray-400 font-semibold';
                    textClasses += ' text-gray-600 font-semibold';
                }

                indicator.className = indicatorClasses;
                if (textElement) textElement.className = textClasses;
            }
        }
    }

    // Gerar navegação de questões
    async function generateQuestionNavigation() {
        if (!elements.questionNavigation) return;

        elements.questionNavigation.innerHTML = '';
        const s = getBlockStartIndex(currentBlock);
        const e = getBlockEndIndex(currentBlock);

        for (let i = s; i < e; i++) {
            const btn = document.createElement('button');
            btn.className = 'w-7 h-7 rounded-full bg-gray-400 text-gray-700 text-xs font-semibold select-none question-btn transition-colors';
            btn.textContent = i + 1;
            btn.dataset.question = i;

            btn.addEventListener('click', async () => {
                await displayQuestion(i, currentQuestionIndex);
            });

            elements.questionNavigation.appendChild(btn);
        }
    }

    // Atualizar navegação de questões
function updateQuestionNavigation() {
    const buttons = elements.questionNavigation?.querySelectorAll('.question-btn') || [];
    buttons.forEach((btn) => {
        const i = parseInt(btn.dataset.question);
        btn.classList.remove('bg-gray-400', 'text-gray-700', 'bg-[#3B4151]', 'text-white', 'bg-yellow-500');

        if (answeredQuestions.has(i)) {
            btn.classList.add('bg-[#3B4151]', 'text-white');
        } else if (skippedQuestions.has(i)) {
            btn.classList.add('bg-yellow-500', 'text-white');
        } else {
            btn.classList.add('bg-gray-400', 'text-gray-700');
        }

        if (i === currentQuestionIndex) {
            // Aqui está a modificação para adicionar o círculo vermelho
            btn.classList.add('ring-2', 'ring-[#FF3B3B]'); // Adiciona o círculo vermelho ao redor da bolinha
        } else {
            btn.classList.remove('ring-2', 'ring-[#FF3B3B]'); // Remove o círculo vermelho quando não estiver selecionado
        }
    });
}

    // Verificar se pode pular questão atual
    function canSkipCurrentQuestion(index) {
        if (!isExamStarted) return false;
        if (skippedQuestions.has(index)) return true;

        const s = getBlockStartIndex(currentBlock);
        const e = getBlockEndIndex(currentBlock);
        for (let i = s; i < e; i++) {
            if (skippedQuestions.has(i)) return false;
        }
        return true;
    }

    // Exibir questão
    async function displayQuestion(index, previousIndex = null) {
        if (previousIndex !== null && isExamStarted) {
            const time = Date.now() - questionStartTime;
            timeSpent.set(previousIndex, (timeSpent.get(previousIndex) || 0) + time);
        }

        if (index < 0 || index >= allQuestions.length) return;

        currentQuestionIndex = index;
        const q = allQuestions[index];
        const newBlock = getCurrentBlock(index);

        if (newBlock !== currentBlock) {
            currentBlock = newBlock;
            await generateQuestionNavigation();
            updateBlockIndicators();
        }

        if (elements.questionTitle) elements.questionTitle.innerHTML = `Questão ${String(index + 1).padStart(2, '0')}`;
        if (elements.questionText) {
            elements.questionText.innerHTML = q.enunciado;
        }

        // Buscar imagens da questão usando a API correta
        if (q.id) {
            try {
                const imageResponse = await fetch(`/api/simulados/question/${q.id}`);
                if (imageResponse.ok) {
                    const questionData = await imageResponse.json();
                    
                    if (questionData.imagens && questionData.imagens !== '[]') {
                        try {
                            const images = JSON.parse(questionData.imagens);
                            displayQuestionImages(images);
                        } catch (e) {
                            console.error('Erro ao processar imagens:', e);
                            if (elements.questionImages) elements.questionImages.innerHTML = '';
                        }
                    } else {
                        if (elements.questionImages) elements.questionImages.innerHTML = '';
                    }
                } else {
                    console.error('Erro ao buscar questão:', imageResponse.status);
                    if (elements.questionImages) elements.questionImages.innerHTML = '';
                }
            } catch (e) {
                console.error('Erro ao buscar imagens:', e);
                if (elements.questionImages) elements.questionImages.innerHTML = '';
            }
        } else {
            if (elements.questionImages) elements.questionImages.innerHTML = '';
        }

        if (elements.answerForm) {
            const currentAnswer = answeredQuestions.get(index) || '';
            const isCurrentSkipped = skippedQuestions.has(index);
            
            // Obter alternativas embaralhadas
            const shuffledData = getShuffledAlternatives(index);
            if (!shuffledData) {
                console.error(`Não foi possível obter alternativas embaralhadas para questão ${index}`);
                elements.answerForm.innerHTML = '<p class="text-red-500">Erro ao carregar alternativas</p>';
                return;
            }
            
            const shuffledAlternatives = shuffledData.shuffled;
            const mapping = shuffledData.mapping;
            
            // Converter resposta salva para posição embaralhada correspondente
            let shuffledCurrentAnswer = '';
            if (currentAnswer) {
                // Encontrar qual posição embaralhada corresponde à resposta original
                for (let i = 0; i < shuffledAlternatives.length; i++) {
                    if (shuffledAlternatives[i].letter === currentAnswer) {
                        shuffledCurrentAnswer = String.fromCharCode(97 + i); // a, b, c, d, e
                        break;
                    }
                }
            }

            // Função para processar alternativas (texto ou imagem)
            function processAlternative(alt, content) {
                if (!content) return '';
                
                // Novo: caminho de arquivo/URL relativo
                if (typeof content === 'string' && (content.endsWith('.webp') || content.includes('2025_questions_imgs'))) {
                    const normalized = content.replace(/\\/g, '/');
                    const src = normalized.startsWith('/') ? normalized : `/${normalized}`;
                    return `
                        <img src="${src}"
                             alt="Alternativa ${alt}"
                             class="max-w-[200px] max-h-[150px] object-contain border border-gray-300 rounded"
                             loading="lazy"
                             decoding="async"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                        <span class="text-red-500 text-xs" style="display:none;">Erro ao carregar imagem</span>
                    `;
                }

                // Verificar se é uma imagem base64 direta (formato novo)
                if (typeof content === 'string' && content.length > 100 && /^[A-Za-z0-9+/=]+$/.test(content)) {
                    // Provavelmente é uma imagem base64 direta
                    return `
                        <img src="data:image/png;base64,${content}" 
                             alt="Alternativa ${alt}" 
                             class="max-w-[200px] max-h-[150px] object-contain border border-gray-300 rounded"
                             loading="lazy"
                             decoding="async"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                        <span class="text-red-500 text-xs" style="display:none;">Erro ao carregar imagem</span>
                    `;
                }
                
                // Verificar se é uma imagem (JSON com base64 - formato antigo)
                if (typeof content === 'string' && content.includes('base64')) {
                    try {
                        const parsed = JSON.parse(content);
                        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].base64) {
                            const imgInfo = parsed[0];
                            return `
                                <img src="data:image/png;base64,${imgInfo.base64}" 
                                     alt="Alternativa ${alt}" 
                                     class="max-w-[200px] max-h-[150px] object-contain border border-gray-300 rounded"
                                     loading="lazy"
                                     decoding="async"
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                                <span class="text-red-500 text-xs" style="display:none;">Erro ao carregar imagem</span>
                            `;
                        }
                    } catch (e) {
                        console.error(`Erro ao processar alternativa ${alt}:`, e);
                    }
                }
                
                // Se não for imagem, retornar como texto com suporte ao MathJax
                // Manter o conteúdo original para que o MathJax possa processá-lo corretamente
                // Adicionar classe específica para processamento do MathJax
                return `<span class="alternative-text mathjax-content">${content}</span>`;
            }

            elements.answerForm.innerHTML = `
                <div class="answer-alternative">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="a" ${shuffledCurrentAnswer === 'a' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    <span class="alternative-label">A)</span>
                    <div class="alternative-content">
                        ${processAlternative('A', shuffledAlternatives[0].content)}
                    </div>
                </div>
                <div class="answer-alternative">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="b" ${shuffledCurrentAnswer === 'b' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    <span class="alternative-label">B)</span>
                    <div class="alternative-content">
                        ${processAlternative('B', shuffledAlternatives[1].content)}
                    </div>
                </div>
                <div class="answer-alternative">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="c" ${shuffledCurrentAnswer === 'c' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    <span class="alternative-label">C)</span>
                    <div class="alternative-content">
                        ${processAlternative('C', shuffledAlternatives[2].content)}
                    </div>
                </div>
                <div class="answer-alternative">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="d" ${shuffledCurrentAnswer === 'd' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    <span class="alternative-label">D)</span>
                    <div class="alternative-content">
                        ${processAlternative('D', shuffledAlternatives[3].content)}
                    </div>
                </div>
                <div class="answer-alternative">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="e" ${shuffledCurrentAnswer === 'e' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    <span class="alternative-label">E)</span>
                    <div class="alternative-content">
                        ${processAlternative('E', shuffledAlternatives[4].content)}
                    </div>
                </div>
            `;

            elements.answerForm.onchange = (e) => {
                if (!isCurrentSkipped && e.target.name === `answer-${index}`) {
                    answeredQuestions.set(index, e.target.value);
                    updateAnsweredCount();
                    updateQuestionNavigation();
                }
            };

            // Adicionar eventos de clique para as alternativas
            const alternativeDivs = elements.answerForm.querySelectorAll('.answer-alternative');
            alternativeDivs.forEach((div, altIndex) => {
                const radio = div.querySelector('input[type="radio"]');
                const altValue = String.fromCharCode(97 + altIndex); // a, b, c, d, e
                
                div.addEventListener('click', () => {
                    if (!isCurrentSkipped) {
                        radio.checked = true;
                        answeredQuestions.set(index, altValue);
                        updateAnsweredCount();
                        updateQuestionNavigation();
                    }
                });
            });
        }

        const blockEnd = getBlockEndIndex(currentBlock) - 1;
        if (elements.nextBtn) {
            if (currentQuestionIndex === blockEnd) {
                elements.nextBtn.disabled = true;
                elements.nextBtn.classList.add("cursor-not-allowed", "opacity-50", "bg-gray-400");
                elements.nextBtn.classList.remove("bg-[#3B4151]", "hover:bg-[#2a2e3d]");
            } else {
                elements.nextBtn.disabled = false;
                elements.nextBtn.classList.add("bg-[#3B4151]", "hover:bg-[#2a2e3d]");
                elements.nextBtn.classList.remove("cursor-not-allowed", "opacity-50", "bg-gray-400");
            }
        }

        if (elements.skipToggle) {
            const isCurrentSkipped = skippedQuestions.has(index);
            elements.skipToggle.checked = isCurrentSkipped;
            const canSkip = canSkipCurrentQuestion(index);
            elements.skipToggle.disabled = !canSkip && !isCurrentSkipped;
            const label = elements.skipToggle.closest('label');
            if (label) {
                if (elements.skipToggle.disabled) {
                    label.classList.add('toggle-disabled');
                    label.classList.remove('cursor-pointer');
                } else {
                    label.classList.remove('toggle-disabled');
                    label.classList.add('cursor-pointer');
                }
            }
        }

        questionStartTime = Date.now();

        // Aplicar efeito visual nas alternativas
        updateAlternativeVisualState();

        // Processar MathJax imediatamente após a renderização
        if (window.MathJax && window.MathJax.typesetPromise) {
            try {
                // Processar apenas o container das alternativas para melhor performance
                const mathElements = elements.answerForm.querySelectorAll('.mathjax-content');
                if (mathElements.length > 0) {
                    MathJax.typesetPromise(mathElements).then(() => {
                        console.log('MathJax processado com sucesso para a questão', index + 1);
                    }).catch((error) => {
                        console.error('Erro ao processar MathJax:', error);
                        // Fallback: tentar processar todo o documento
                        MathJax.typesetPromise().catch((fallbackError) => {
                            console.error('Erro no fallback do MathJax:', fallbackError);
                        });
                    });
                }
            } catch (error) {
                console.error('Erro ao tentar processar MathJax:', error);
            }
        }
    }

    // Função para próxima questão
    async function nextQuestion() {
        const nextIndex = currentQuestionIndex + 1;
        if (nextIndex < allQuestions.length) {
            await displayQuestion(nextIndex, currentQuestionIndex);
        }
    }

    // Atualizar contador de questões respondidas
    function updateAnsweredCount() {
        if (elements.answeredCountElement) {
            elements.answeredCountElement.textContent = answeredQuestions.size;
        }
    }

    // Função para pular questão
    async function toggleSkipQuestion() {
        const currentIndex = currentQuestionIndex;
        const isCurrentlySkipped = skippedQuestions.has(currentIndex);
        const canToggle = canSkipCurrentQuestion(currentIndex);

        if (!canToggle && !isCurrentlySkipped) {
            showNotification('Você já usou o pulo neste bloco!', 'warning');
            return;
        }

        if (isCurrentlySkipped) {
            skippedQuestions.delete(currentIndex);
            showNotification('Pulo da questão desfeito.', 'info');
        } else {
            skippedQuestions.add(currentIndex);
            answeredQuestions.delete(currentIndex);
            showNotification('Questão pulada neste bloco.', 'success');
        }

        updateAnsweredCount();
        updateQuestionNavigation();
        await displayQuestion(currentQuestionIndex);
        
        // Aplicar efeito visual nas alternativas
        updateAlternativeVisualState();
    }

    // Função para atualizar o estado visual das alternativas
    function updateAlternativeVisualState() {
        const alternativeDivs = elements.answerForm?.querySelectorAll('.answer-alternative') || [];
        const isCurrentSkipped = skippedQuestions.has(currentQuestionIndex);
        
        alternativeDivs.forEach(div => {
            if (isCurrentSkipped) {
                div.classList.add('disabled');
            } else {
                div.classList.remove('disabled');
            }
        });
    }

    // Modal de escolha para pulo
    function openSkipChoiceModal() {
        if (!elements.skipChoiceList) {
            console.error('Elemento skip-choice-list não encontrado');
            return;
        }

        elements.skipChoiceList.innerHTML = '';
        const s = getBlockStartIndex(currentBlock);
        const e = getBlockEndIndex(currentBlock);

        for (let i = s; i < e; i++) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = i + 1;
            btn.className = `w-9 h-9 text-xs font-semibold rounded-full border ${i === chosenSkipIndex ? 'bg-yellow-500 text-white' : 'bg-white text-gray-700'} hover:bg-yellow-100`;
            btn.addEventListener('click', () => {
                chosenSkipIndex = i;
                openSkipChoiceModal();
            });
            elements.skipChoiceList.appendChild(btn);
        }

        if (elements.skipChoiceModal) {
            elements.skipChoiceModal.classList.remove('hidden');
        }
    }

    function closeSkipChoiceModal() {
        if (elements.skipChoiceModal) {
            elements.skipChoiceModal.classList.add('hidden');
        }
        chosenSkipIndex = null;
    }

    // Função para finalizar bloco
    async function finalizeBlock() {
        if (!isExamStarted) {
            showNotification('Você deve iniciar a prova primeiro!', 'warning');
            return;
        }

        // Primeira confirmação
        showConfirmationModal(
            'Revisão do Bloco',
            'Você revisou todas as respostas deste bloco?',
            () => {
                const s = getBlockStartIndex(currentBlock);
                const e = getBlockEndIndex(currentBlock);
                const blockQuestions = Array.from({ length: e - s }, (_, k) => s + k);
                const answeredInBlock = blockQuestions.filter((q) => answeredQuestions.has(q));
                const skippedInBlock = blockQuestions.filter((q) => skippedQuestions.has(q));
                const totalInBlock = blockQuestions.length;
                const completedInBlock = answeredInBlock.length + skippedInBlock.length;

                // Se nenhuma questão foi pulada, abre o modal de escolha.
                if (skippedInBlock.length === 0) {
                    showNotification('Você deve escolher uma questão para pular antes de finalizar este bloco!', 'warning');
                    pendingFinalizeAfterSkipChoice = true;
                    openSkipChoiceModal();
                    return;
                }

                if (completedInBlock < totalInBlock) {
                    const unanswered = totalInBlock - completedInBlock;
                    showConfirmationModal(
                        'Questões Não Respondidas',
                        `Você tem ${unanswered} questão(ões) não respondida(s) no Bloco ${currentBlock}. Deseja finalizar mesmo assim?`,
                        () => {
                            // Confirmação final
                            let confirmMessage = `Tem certeza que deseja finalizar o Bloco ${currentBlock}?`;
                            if (currentBlock === 4) {
                                confirmMessage = 'Você está prestes a encerrar o bloco 4 e finalizar a prova, deseja continuar?';
                            }
                            
                            showConfirmationModal(
                                'Confirmação Final',
                                confirmMessage,
                                () => {
                                    blockCompleted.add(currentBlock);
                                    showNotification(`Bloco ${currentBlock} finalizado!`, 'success');

                                    if (currentBlock < 4) {
                                        elements.finalizeBlockBtn.textContent = `Finalizar Bloco ${currentBlock + 1}`;
                                        currentBlock++;
                                        const nextBlockStartIndex = getBlockStartIndex(currentBlock);
                                        currentQuestionIndex = nextBlockStartIndex;
                                        generateQuestionNavigation();
                                        updateBlockIndicators();
                                        displayQuestion(currentQuestionIndex);
                                    } else {
                                        elements.finalizeBlockBtn.classList.add('hidden');
                                        endExam();
                                    }
                                }
                            );
                        }
                    );
                } else {
                    // Confirmação final
                    let confirmMessage = `Tem certeza que deseja finalizar o Bloco ${currentBlock}?`;
                    if (currentBlock === 4) {
                        confirmMessage = 'Você está prestes a encerrar o bloco 4 e finalizar a prova, deseja continuar?';
                    }
                    
                    showConfirmationModal(
                        'Confirmação Final',
                        confirmMessage,
                        () => {
                            blockCompleted.add(currentBlock);
                            showNotification(`Bloco ${currentBlock} finalizado!`, 'success');

                            if (currentBlock < 4) {
                                elements.finalizeBlockBtn.textContent = `Finalizar Bloco ${currentBlock + 1}`;
                                currentBlock++;
                                const nextBlockStartIndex = getBlockStartIndex(currentBlock);
                                currentQuestionIndex = nextBlockStartIndex;
                                generateQuestionNavigation();
                                updateBlockIndicators();
                                displayQuestion(currentQuestionIndex);
                            } else {
                                elements.finalizeBlockBtn.classList.add('hidden');
                                endExam();
                            }
                        }
                    );
                }
            }
        );
    }

    // Função para encerrar prova
    function endExam() {
        if (!isExamStarted) return;

        showConfirmationModal(
            'Encerrar Prova',
            'Tem certeza que deseja encerrar a prova?',
            () => {
            clearInterval(examTimer);
            isExamStarted = false;

            // Atualizar timeSpent para a questão atual
            const time = Date.now() - questionStartTime;
            timeSpent.set(currentQuestionIndex, (timeSpent.get(currentQuestionIndex) || 0) + time);

            const timeUsed = examStartTime ? new Date() - examStartTime : 0;

            let correct = 0, incorrect = 0;
            const resultsDetails = {
                correct: [],
                incorrect: [],
                skipped: []
            };

            // Calculando acertos por bloco
            const accuracies = Array(4).fill(0);
            const totals = blockStructure.slice();

            allQuestions.forEach((q, i) => {
                const userAnswer = answeredQuestions.get(i);
                // Converter resposta embaralhada para resposta original para comparação
                const originalUserAnswer = convertShuffledAnswer(i, userAnswer);
                const correctAnswer = q.gabarito; // Usar gabarito em vez de correta
                // Usar o campo bloco que vem do sistema de simulados em vez de calcular dinamicamente
                const block = q.bloco || getCurrentBlock(i);
                
                // Validar que o bloco está entre 1 e 4
                const validBlock = Math.min(Math.max(block, 1), 4);

                if (skippedQuestions.has(i)) {
                    resultsDetails.skipped.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        correta: correctAnswer
                    });
                } else if (originalUserAnswer === correctAnswer) {
                    correct++;
                    // Garantir que o índice do array seja válido
                    const arrayIndex = validBlock - 1;
                    if (arrayIndex >= 0 && arrayIndex < accuracies.length) {
                        accuracies[arrayIndex]++;
                    } else {
                        console.error(`Índice de array inválido: ${arrayIndex} para bloco ${validBlock}`);
                    }
                    resultsDetails.correct.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        resposta: originalUserAnswer,
                        correta: correctAnswer
                    });
                } else {
                    incorrect++;
                    resultsDetails.incorrect.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        respostaUsuario: originalUserAnswer || 'Nenhuma',
                        correta: correctAnswer
                    });
                }
            });
            
            // Validar que não há valores negativos
            const validatedAccuracies = accuracies.map(acc => Math.max(0, acc));
            console.log('Acertos por bloco (validados):', validatedAccuracies);

            // Aplicar efeito de blur
            applyBlurEffect();
            
            // Aguardar um pouco antes de redirecionar para mostrar o efeito
            setTimeout(() => {
                // Enviar resultados e redirecionar para o dashboard
                submitResults();
            }, 1000);
            }
        );
    }

    // Função para enviar resultados e redirecionar para o dashboard
    async function submitResults() {
        try {
            const answers = {};
            allQuestions.forEach((q, i) => {
                const userAnswer = answeredQuestions.get(i);
                if (userAnswer && q && q.id != null) {
                    // Converter resposta embaralhada para resposta original
                    const originalAnswer = convertShuffledAnswer(i, userAnswer);
                    answers[q.id] = originalAnswer; // usar ID da questão com resposta original
                }
            });
            
            const response = await fetch('/api/simulados/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    answers: answers,
                    skipped_questions: Array.from(skippedQuestions)
                })
            });
            
            const result = await response.json();
            if (result.success && result.redirect_url) {
                // Redirecionar para o dashboard com os resultados
                window.location.href = result.redirect_url;
            } else {
                // Fallback: redirecionar para o dashboard
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Erro ao enviar resultados:', error);
            // Fallback: redirecionar para o dashboard
            window.location.href = '/';
        }
    }

    // Função para iniciar prova
    async function startExam() {
    // libera navegação e botão
    document.getElementById("question-nav").classList.remove("nav-disabled");
    document.getElementById("finalize-block-btn").disabled = false;
        if (isExamStarted) return;

        examStartTime = new Date();
        isExamStarted = true;

        removeBlurEffect();

        if (elements.startTimeElement) {
            elements.startTimeElement.textContent = formatTime(examStartTime);
        }

        if (elements.startExamBtn) {
            elements.startExamBtn.classList.add('hidden');
        }

        if (elements.endExamBtn) {
            elements.endExamBtn.classList.remove('hidden');
        }

        startTimer();

        // Re-exibir questão atual
        await displayQuestion(currentQuestionIndex);
    }

    // Funções para exibir imagens
    function displayQuestionImages(images) {
        if (!elements.questionImages) {
            console.error('Elemento question-images não encontrado');
            return;
        }

        elements.questionImages.innerHTML = '';

        if (!images || images.length === 0) {
            return;
        }

        const gallery = document.createElement('div');
        gallery.className = 'image-gallery';

        images.forEach((image, index) => {
            
            const imageDiv = document.createElement('div');
            imageDiv.className = 'image-container';

            const img = document.createElement('img');

            // Suporta novo formato por path/url e legado base64
            if (typeof image === 'string') {
                const normalized = image.replace(/\\/g, '/');
                img.src = normalized.startsWith('/') ? normalized : `/${normalized}`;
            } else if (image && (image.path || image.url)) {
                const p = (image.path || image.url).replace(/\\/g, '/');
                img.src = p.startsWith('/') ? p : `/${p}`;
            } else {
                const base64Data = image?.data || image?.base64;
                if (!base64Data || typeof base64Data !== 'string') {
                    console.error(`Dados de imagem inválidos para imagem ${index}:`, image);
                    return;
                }
                const cleanBase64 = base64Data.replace(/\s/g, '');
                img.src = `data:image/png;base64,${cleanBase64}`;
            }
            img.alt = `Imagem ${index + 1} da questão`;
            img.className = 'question-image';
            img.loading = 'lazy';
            img.decoding = 'async';
            
            // Adicionar classe quando carregar
            img.onload = () => {
                img.classList.add('loaded');
            };

            imageDiv.appendChild(img);
            gallery.appendChild(imageDiv);
        });

        elements.questionImages.appendChild(gallery);
    }


    // Função para embaralhar alternativas de uma questão
    function shuffleAlternatives(question) {
        // Criar array com as alternativas e suas letras
        const alternatives = [
            { letter: 'a', content: question.a },
            { letter: 'b', content: question.b },
            { letter: 'c', content: question.c },
            { letter: 'd', content: question.d },
            { letter: 'e', content: question.e }
        ];
        
        // Embaralhar o array
        for (let i = alternatives.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [alternatives[i], alternatives[j]] = [alternatives[j], alternatives[i]];
        }
        
        // Retornar o array embaralhado e um mapeamento das letras originais
        return {
            shuffled: alternatives,
            mapping: alternatives.reduce((map, alt, index) => {
                map[String.fromCharCode(97 + index)] = alt.letter; // a->original, b->original, etc.
                return map;
            }, {})
        };
    }

    // Função para obter alternativas embaralhadas de uma questão
    function getShuffledAlternatives(questionIndex) {
        if (!shuffledAlternatives.has(questionIndex)) {
            const question = allQuestions[questionIndex];
            shuffledAlternatives.set(questionIndex, shuffleAlternatives(question));
        }
        return shuffledAlternatives.get(questionIndex);
    }

    // Função para converter resposta do usuário (letra embaralhada) para letra original
    function convertShuffledAnswer(questionIndex, shuffledAnswer) {
        try {
            const shuffledData = shuffledAlternatives.get(questionIndex);
            if (!shuffledData || !shuffledAnswer) return shuffledAnswer;
            
            // shuffledAnswer é a letra que o usuário selecionou (a, b, c, d, e)
            // Precisamos encontrar qual alternativa original está nessa posição
            const shuffledIndex = shuffledAnswer.charCodeAt(0) - 97; // a=0, b=1, c=2, etc.
            
            // Verificar se o índice é válido
            if (shuffledIndex < 0 || shuffledIndex >= shuffledData.shuffled.length) {
                console.warn(`Índice inválido: ${shuffledIndex} para resposta ${shuffledAnswer}`);
                return shuffledAnswer;
            }
            
            const originalLetter = shuffledData.shuffled[shuffledIndex].letter;
            return originalLetter;
        } catch (error) {
            console.error(`Erro ao converter resposta ${shuffledAnswer} da questão ${questionIndex}:`, error);
            return shuffledAnswer; // Fallback para resposta original
        }
    }

    // Buscar questões do simulado atual
    async function fetchQuestions() {
        try {
            // Primeiro, verificar se há um simulado ativo
            const simuladoResponse = await fetch('/api/simulados/current');
            if (!simuladoResponse.ok) {
                // Não há simulado ativo, mostrar mensagem amigável
                if (elements.questionContent) {
                    elements.questionContent.innerHTML = `
                        <div class="text-center text-gray-600 py-12">
                            <i class="fas fa-clipboard-list text-4xl mb-4 text-blue-500"></i>
                            <h3 class="text-xl font-semibold mb-2">Nenhum Simulado Ativo</h3>
                            <p class="text-sm mb-6">Você precisa criar um simulado primeiro para começar a estudar.</p>
                            <button onclick="window.location.href='/'" class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                                <i class="fas fa-arrow-left mr-2"></i>
                                Ir para o Dashboard
                            </button>
                        </div>
                    `;
                }
                return;
            }
            
            const simulado = await simuladoResponse.json();
            if (!simulado.questions || simulado.questions.length === 0) {
                throw new Error('Simulado não possui questões');
            }

            // Usar as questões do simulado (que já estão na sessão)
            allQuestions = simulado.questions;
            
            await generateQuestionNavigation();
            await displayQuestion(0);
            applyBlurEffect();
            updateBlockIndicators();
        } catch (error) {
            console.error('Erro ao carregar questões:', error);
            if (elements.questionContent) {
                elements.questionContent.innerHTML = `
                    <div class="text-center text-red-500 py-8">
                        <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                        <p>Erro ao carregar a prova.</p>
                        <p class="text-sm mt-2">${error.message}</p>
                        <button onclick="window.location.href='/'" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                            Voltar ao Dashboard
                        </button>
                    </div>
                `;
            }
        }
    }

    // Event listeners
    if (elements.startExamBtn) {
        elements.startExamBtn.addEventListener('click', startExam);
    } else {
        console.error('Elemento start-exam-btn não encontrado');
    }

    if (elements.endExamBtn) {
        elements.endExamBtn.addEventListener('click', endExam);
    } else {
        console.error('Elemento end-exam-btn não encontrado');
    }

    if (elements.nextBtn) {
        elements.nextBtn.addEventListener('click', nextQuestion);
    } else {
        console.error('Elemento next-btn não encontrado');
    }

    if (elements.finalizeBlockBtn) {
        elements.finalizeBlockBtn.addEventListener('click', finalizeBlock);
    } else {
        console.error('Elemento finalize-block-btn não encontrado');
    }

    if (elements.skipToggle) {
        elements.skipToggle.addEventListener('change', toggleSkipQuestion);
    } else {
        console.error('Elemento skip-toggle não encontrado');
    }

    if (elements.closeResultsBtn) {
        // Event listener removido - resultados agora são exibidos no dashboard
    } else {
        console.error('Elemento close-results-btn não encontrado');
    }

    // Elementos de skip-choice não existem no HTML atual, removendo para evitar erros
    // if (elements.cancelSkipChoice) {
    //     elements.cancelSkipChoice.addEventListener('click', () => {
    //         pendingFinalizeAfterSkipChoice = false;
    //         closeSkipChoiceModal();
    //     });
    // }

    // if (elements.confirmSkipChoice) {
    //     elements.confirmSkipChoice.addEventListener('click', () => {
    //         if (chosenSkipIndex == null) {
    //             showNotification('Selecione uma questão para pular.', 'warning');
    //             return;
    //         }
    //         skippedQuestions.add(chosenSkipIndex);
    //         answeredQuestions.delete(chosenSkipIndex);
    //         updateAnsweredCount();
    //         updateQuestionNavigation();
    //         closeSkipChoiceModal();
    //         if (pendingFinalizeAfterSkipChoice) {
    //                 finalizeBlock();
    //         }
    //     });
    // }

    // Event listener para detectar saída da tela
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Event listener para detectar mudança de foco da janela
    window.addEventListener('blur', () => {
        if (isExamStarted && !exitWarningShown) {
            exitWarningShown = true;
            exitWarningCount++;
            showExitWarning();
        }
    });
    
    window.addEventListener('focus', () => {
        exitWarningShown = false;
    });

    // Inicializar
    fetchQuestions();
});