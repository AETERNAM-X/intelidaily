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

    // Funções auxiliares
    function formatTime(d) {
        return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
        let acc = 0;
        for (let i = 0; i < blockStructure.length; i++) {
            acc += blockStructure[i];
            if (qIndex < acc) return i + 1;
        }
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

        if (elements.questionTitle) elements.questionTitle.textContent = `Questão ${String(index + 1).padStart(2, '0')}`;
        if (elements.questionText) {
            elements.questionText.textContent = q.enunciado;
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

            // Função para processar alternativas (texto ou imagem)
            function processAlternative(alt, content) {
                if (!content) return '';
                
                // Verificar se é uma imagem base64 direta (formato novo)
                if (typeof content === 'string' && content.length > 100 && /^[A-Za-z0-9+/=]+$/.test(content)) {
                    // Provavelmente é uma imagem base64 direta
                    return `
                        <div class="flex items-center space-x-2">
                            <span class="font-medium">${alt})</span>
                            <img src="data:image/png;base64,${content}" 
                                 alt="Alternativa ${alt}" 
                                 class="max-w-[200px] max-h-[150px] object-contain border border-gray-300 rounded cursor-pointer hover:opacity-80 transition-opacity"
                                 onclick="showImageModal('${content}', 'Alternativa ${alt}')"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                            <span class="text-red-500 text-xs" style="display:none;">Erro ao carregar imagem</span>
                        </div>
                    `;
                }
                
                // Verificar se é uma imagem (JSON com base64 - formato antigo)
                if (typeof content === 'string' && content.includes('base64')) {
                    try {
                        const parsed = JSON.parse(content);
                        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].base64) {
                            const imgInfo = parsed[0];
                            return `
                                <div class="flex items-center space-x-2">
                                    <span class="font-medium">${alt})</span>
                                    <img src="data:image/png;base64,${imgInfo.base64}" 
                                         alt="Alternativa ${alt}" 
                                         class="max-w-[200px] max-h-[150px] object-contain border border-gray-300 rounded cursor-pointer hover:opacity-80 transition-opacity"
                                         onclick="showImageModal('${imgInfo.base64}', 'Alternativa ${alt}')"
                                         onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                                    <span class="text-red-500 text-xs" style="display:none;">Erro ao carregar imagem</span>
                                </div>
                            `;
                        }
                    } catch (e) {
                        console.error(`Erro ao processar alternativa ${alt}:`, e);
                    }
                }
                
                // Se não for imagem, retornar como texto
                return `<span>${alt}) ${content}</span>`;
            }

            elements.answerForm.innerHTML = `
                <label class="flex items-center space-x-2 cursor-pointer ${isCurrentSkipped ? 'opacity-50 pointer-events-none' : ''}">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="a" ${currentAnswer === 'a' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    ${processAlternative('A', q.a)}
                </label>
                <label class="flex items-center space-x-2 cursor-pointer ${isCurrentSkipped ? 'opacity-50 pointer-events-none' : ''}">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="b" ${currentAnswer === 'b' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    ${processAlternative('B', q.b)}
                </label>
                <label class="flex items-center space-x-2 cursor-pointer ${isCurrentSkipped ? 'opacity-50 pointer-events-none' : ''}">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="c" ${currentAnswer === 'c' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    ${processAlternative('C', q.c)}
                </label>
                <label class="flex items-center space-x-2 cursor-pointer ${isCurrentSkipped ? 'opacity-50 pointer-events-none' : ''}">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="d" ${currentAnswer === 'd' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    ${processAlternative('D', q.d)}
                </label>
                <label class="flex items-center space-x-2 cursor-pointer ${isCurrentSkipped ? 'opacity-50 pointer-events-none' : ''}">
                    <input class="form-radio text-[#3B4151]" name="answer-${index}" type="radio" value="e" ${currentAnswer === 'e' && !isCurrentSkipped ? 'checked' : ''} ${isCurrentSkipped ? 'disabled' : ''}>
                    ${processAlternative('E', q.e)}
                </label>
            `;

            elements.answerForm.onchange = (e) => {
                if (!isCurrentSkipped && e.target.name === `answer-${index}`) {
                    answeredQuestions.set(index, e.target.value);
                    updateAnsweredCount();
                    updateQuestionNavigation();
                }
            };
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

        if (!confirm('Você revisou todas as respostas deste bloco?')) {
            return;
        }

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
            if (!confirm(`Você tem ${unanswered} questão(ões) não respondida(s) no Bloco ${currentBlock}. Deseja finalizar mesmo assim?`)) {
                return;
            }
        }
        
        // Confirmação final antes de finalizar o bloco/prova
        let confirmMessage = `Tem certeza que deseja finalizar o Bloco ${currentBlock}?`;
        if (currentBlock === 4) {
            confirmMessage = 'Você está prestes a encerrar o bloco 4 e finalizar a prova, deseja continuar?';
        }
        if (!confirm(confirmMessage)) {
            return;
        }

        blockCompleted.add(currentBlock);
        showNotification(`Bloco ${currentBlock} finalizado!`, 'success');

        if (currentBlock < 4) {
            elements.finalizeBlockBtn.textContent = `Finalizar Bloco ${currentBlock + 1}`;
            currentBlock++;
            const nextBlockStartIndex = getBlockStartIndex(currentBlock);
            currentQuestionIndex = nextBlockStartIndex;
            await generateQuestionNavigation();
            updateBlockIndicators();
            await displayQuestion(currentQuestionIndex);
        } else {
            elements.finalizeBlockBtn.classList.add('hidden');
            endExam();
        }
    }

    // Função para encerrar prova
    function endExam() {
        if (!isExamStarted) return;

        if (confirm('Tem certeza que deseja encerrar a prova?')) {
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
                const correctAnswer = q.gabarito; // Usar gabarito em vez de correta
                const block = getCurrentBlock(i);

                if (skippedQuestions.has(i)) {
                    resultsDetails.skipped.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        correta: correctAnswer
                    });
                } else if (userAnswer === correctAnswer) {
                    correct++;
                    accuracies[block - 1]++;
                    resultsDetails.correct.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        resposta: userAnswer,
                        correta: correctAnswer
                    });
                } else {
                    incorrect++;
                    resultsDetails.incorrect.push({
                        numero: i + 1,
                        enunciado: q.enunciado,
                        imagens: q.imagens,
                        respostaUsuario: userAnswer || 'Nenhuma',
                        correta: correctAnswer
                    });
                }
            });

            // Os resultados agora são exibidos no dashboard após o redirecionamento
            // Não é mais necessário exibir o modal de resultados aqui
            
            // Aplicar efeito de blur e redirecionar para o dashboard
            applyBlurEffect();
            
            // Aguardar um pouco antes de redirecionar para mostrar o efeito
            setTimeout(() => {
                // Enviar resultados e redirecionar para o dashboard
                submitResults();
            }, 1000);
        }
    }

    // Função para enviar resultados e redirecionar para o dashboard
    async function submitResults() {
        try {
            const answers = {};
            allQuestions.forEach((q, i) => {
                const userAnswer = answeredQuestions.get(i);
                if (userAnswer && q && q.id != null) {
                    answers[q.id] = userAnswer; // usar ID da questão
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
            
            // Verificar se o base64 é válido - usar campo 'data' em vez de 'base64'
            const base64Data = image.data || image.base64;
            if (!base64Data || typeof base64Data !== 'string') {
                console.error(`Base64 inválido para imagem ${index}:`, base64Data);
                return;
            }
            
            // Limpar o base64 (remover espaços e quebras de linha)
            const cleanBase64 = base64Data.replace(/\s/g, '');
            
            img.src = `data:image/png;base64,${cleanBase64}`;
            img.alt = `Imagem ${index + 1} da questão`;
            img.className = 'question-image';
            img.onclick = () => openImageModal(cleanBase64, image.filename);

            imageDiv.appendChild(img);
            gallery.appendChild(imageDiv);
        });

        elements.questionImages.appendChild(gallery);
    }

    function openImageModal(base64Data, filename) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
        modal.onclick = () => modal.remove();

        const img = document.createElement('img');
        // Usar o base64Data que já foi limpo
        img.src = `data:image/png;base64,${base64Data}`;
        img.alt = filename;
        img.className = 'max-w-[90vw] max-h-[90vh] object-contain';

        modal.appendChild(img);
        document.body.appendChild(modal);
    }

    // Função para exibir imagem em modal (para alternativas)
    function showImageModal(base64Data, altText) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
        modal.onclick = () => modal.remove();

        const img = document.createElement('img');
        img.src = `data:image/png;base64,${base64Data}`;
        img.alt = altText;
        img.className = 'max-w-[90vw] max-h-[90vh] object-contain';

        modal.appendChild(img);
        document.body.appendChild(modal);
    }
    // tornar acessível globalmente para onclick inline
    window.showImageModal = showImageModal;

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

    // Inicializar
    fetchQuestions();
});