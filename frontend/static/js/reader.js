class BookReader {
    constructor(options) {
        this.bookId = options.bookId;
        this.currentChapter = options.currentChapter;
        this.assistantEnabled = options.assistantEnabled;
        this.preferences = options.preferences;
        
        // 状态管理
        this.readingSessionId = null;
        this.selectedText = '';
        this.isReading = false;
        this.currentAudio = null;
        
        // DOM元素
        this.elements = {
            sidebar: document.getElementById('readerSidebar'),
            content: document.getElementById('readerContent'),
            chapterContent: document.getElementById('chapterContent'),
            chapterList: document.getElementById('chapterList'),
            aiAssistant: document.getElementById('aiAssistant'),
            aiChat: document.getElementById('aiChat'),
            aiInput: document.getElementById('aiInput'),
            aiSendBtn: document.getElementById('aiSendBtn'),
            questionType: document.getElementById('questionType'),
            summaryPanel: document.getElementById('summaryPanel'),
            summaryContent: document.getElementById('summaryContent'),
            loadingModal: new bootstrap.Modal(document.getElementById('loadingModal')),
            ttsPlayer: document.getElementById('ttsPlayer')
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadChapter(this.currentChapter);
        this.startReadingSession();
        this.setupTextSelection();
        this.loadQAHistory();
    }
    
    bindEvents() {
        // 工具栏按钮事件
        document.getElementById('toggleSidebar').addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        document.getElementById('toggleAssistant').addEventListener('click', () => {
            this.toggleAssistant();
        });
        
        document.getElementById('generateSummary').addEventListener('click', () => {
            this.generateSummary();
        });
        
        document.getElementById('toggleTTS').addEventListener('click', () => {
            this.toggleTTS();
        });
        
        document.getElementById('fontSizeDown').addEventListener('click', () => {
            this.adjustFontSize(-1);
        });
        
        document.getElementById('fontSizeUp').addEventListener('click', () => {
            this.adjustFontSize(1);
        });
        
        document.getElementById('readingMode').addEventListener('change', (e) => {
            this.changeReadingMode(e.target.value);
        });
        
        // 章节导航事件
        this.elements.chapterList.addEventListener('click', (e) => {
            if (e.target.classList.contains('chapter-item')) {
                const chapterNumber = parseInt(e.target.dataset.chapter);
                this.loadChapter(chapterNumber);
            }
        });
        
        // AI助手事件
        document.getElementById('aiAssistantHeader').addEventListener('click', () => {
            this.toggleAIPanel();
        });
        
        document.getElementById('toggleAIPanel').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleAIPanel();
        });
        
        document.getElementById('clearChat').addEventListener('click', () => {
            this.clearChat();
        });
        
        this.elements.aiSendBtn.addEventListener('click', () => {
            this.sendQuestion();
        });
        
        this.elements.aiInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendQuestion();
            }
        });
        
        // 页面离开时结束阅读会话
        window.addEventListener('beforeunload', () => {
            this.endReadingSession();
        });
        
        // 定期保存阅读进度
        setInterval(() => {
            this.saveReadingProgress();
        }, 30000); // 每30秒保存一次
    }
    
    async loadChapter(chapterNumber) {
        try {
            this.showLoading('加载章节内容...');
            
            const response = await fetch(`/api/books/${this.bookId}/chapters/${chapterNumber}/`);
            const data = await response.json();
            
            if (data.success) {
                this.currentChapter = chapterNumber;
                this.displayChapter(data.chapter);
                this.updateChapterNavigation();
                this.updateReadingProgress();
                
                // 如果启用了自动朗读
                if (this.preferences.autoRead && this.preferences.voiceEnabled) {
                    setTimeout(() => {
                        this.readChapterAloud();
                    }, this.preferences.autoReadDelay * 1000);
                }
            } else {
                this.showError('加载章节失败: ' + data.error);
            }
        } catch (error) {
            this.showError('加载章节失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    displayChapter(chapter) {
        const html = `
            <div class="chapter-title">${chapter.title || `第${chapter.number}章`}</div>
            <div class="chapter-text">${this.formatChapterContent(chapter.content)}</div>
        `;
        this.elements.chapterContent.innerHTML = html;
        
        // 重新设置文本选择
        this.setupTextSelection();
        
        // 滚动到顶部
        this.elements.content.scrollTop = 0;
    }
    
    formatChapterContent(content) {
        // 将文本分段并格式化
        const paragraphs = content.split('\n').filter(p => p.trim());
        return paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
    }
    
    updateChapterNavigation() {
        // 更新章节导航的活跃状态
        document.querySelectorAll('.chapter-item').forEach(item => {
            item.classList.remove('active');
            if (parseInt(item.dataset.chapter) === this.currentChapter) {
                item.classList.add('active');
            }
        });
        
        // 更新当前章节显示
        document.getElementById('currentChapter').textContent = `第${this.currentChapter}章`;
    }
    
    setupTextSelection() {
        // 设置文本选择事件
        this.elements.chapterContent.addEventListener('mouseup', () => {
            const selection = window.getSelection();
            if (selection.toString().trim()) {
                this.selectedText = selection.toString().trim();
                this.highlightSelectedText();
                
                // 如果AI助手启用，自动设置问题类型为文本问答
                if (this.assistantEnabled) {
                    this.elements.questionType.value = 'text';
                }
            }
        });
    }
    
    highlightSelectedText() {
        // 高亮选中的文本（简单实现）
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const span = document.createElement('span');
            span.className = 'text-selection';
            try {
                range.surroundContents(span);
            } catch (e) {
                // 如果无法包围内容，清除选择
                selection.removeAllRanges();
            }
        }
    }
    
    async toggleAssistant() {
        try {
            const response = await fetch(`/api/books/${this.bookId}/assistant/toggle/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    enabled: !this.assistantEnabled
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.assistantEnabled = data.enabled;
                this.updateAssistantUI();
                this.showSuccess(data.message);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('操作失败: ' + error.message);
        }
    }
    
    updateAssistantUI() {
        const toggleBtn = document.getElementById('toggleAssistant');
        const assistant = this.elements.aiAssistant;
        
        if (this.assistantEnabled) {
            toggleBtn.classList.add('active');
            assistant.classList.remove('collapsed');
        } else {
            toggleBtn.classList.remove('active');
            assistant.classList.add('collapsed');
        }
    }
    
    async sendQuestion() {
        if (!this.assistantEnabled) {
            this.showError('AI助手未启用');
            return;
        }
        
        const question = this.elements.aiInput.value.trim();
        if (!question) {
            this.showError('请输入问题');
            return;
        }
        
        try {
            // 禁用发送按钮
            this.elements.aiSendBtn.disabled = true;
            
            // 添加用户消息到聊天
            this.addChatMessage('user', question);
            
            // 清空输入框
            this.elements.aiInput.value = '';
            
            // 发送请求
            const response = await fetch(`/api/books/${this.bookId}/assistant/ask/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    question: question,
                    question_type: this.elements.questionType.value,
                    selected_text: this.selectedText,
                    chapter_number: this.currentChapter
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.addChatMessage('assistant', data.answer);
                
                // 添加评价按钮
                this.addRatingButtons(data.qa_id);
            } else {
                this.addChatMessage('assistant', '抱歉，我无法回答这个问题：' + data.error);
            }
        } catch (error) {
            this.addChatMessage('assistant', '抱歉，发生了错误：' + error.message);
        } finally {
            // 重新启用发送按钮
            this.elements.aiSendBtn.disabled = false;
            
            // 清除选中文本
            this.selectedText = '';
            this.clearTextSelection();
        }
    }
    
    addChatMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${type}`;
        messageDiv.innerHTML = `<div>${content}</div>`;
        
        this.elements.aiChat.appendChild(messageDiv);
        
        // 滚动到底部
        this.elements.aiChat.scrollTop = this.elements.aiChat.scrollHeight;
    }
    
    addRatingButtons(qaId) {
        const ratingDiv = document.createElement('div');
        ratingDiv.className = 'ai-message-rating mt-2';
        ratingDiv.innerHTML = `
            <small class="text-muted">这个回答有帮助吗？</small>
            <div class="btn-group btn-group-sm ms-2" role="group">
                <button type="button" class="btn btn-outline-success" onclick="bookReader.rateAnswer(${qaId}, true)">
                    <i class="fas fa-thumbs-up"></i>
                </button>
                <button type="button" class="btn btn-outline-danger" onclick="bookReader.rateAnswer(${qaId}, false)">
                    <i class="fas fa-thumbs-down"></i>
                </button>
            </div>
        `;
        
        this.elements.aiChat.appendChild(ratingDiv);
        this.elements.aiChat.scrollTop = this.elements.aiChat.scrollHeight;
    }
    
    async rateAnswer(qaId, isHelpful) {
        try {
            const response = await fetch(`/api/qa/${qaId}/rate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    is_helpful: isHelpful
                })
            });
            
            const data = await response.json();
            if (data.success) {
                // 移除评价按钮
                const ratingDiv = event.target.closest('.ai-message-rating');
                if (ratingDiv) {
                    ratingDiv.innerHTML = `<small class="text-success">感谢您的反馈！</small>`;
                }
            }
        } catch (error) {
            console.error('评价失败:', error);
        }
    }
    
    async generateSummary() {
        try {
            this.showLoading('生成章节总结...');
            
            const response = await fetch(`/api/books/${this.bookId}/assistant/summary/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    chapter_number: this.currentChapter,
                    summary_type: 'auto'
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.displaySummary(data);
                this.showSuccess(data.cached ? '已加载缓存的总结' : '总结生成成功');
            } else {
                this.showError('生成总结失败: ' + data.error);
            }
        } catch (error) {
            this.showError('生成总结失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    displaySummary(summaryData) {
        const html = `
            <div class="summary-text">
                <p>${summaryData.summary}</p>
            </div>
            <div class="key-points">
                <strong>关键要点：</strong>
                <ul>
                    ${summaryData.key_points.map(point => `<li>${point}</li>`).join('')}
                </ul>
            </div>
            ${summaryData.compression_ratio ? `
                <div class="summary-stats mt-2">
                    <small class="text-muted">压缩比: ${(summaryData.compression_ratio * 100).toFixed(1)}%</small>
                </div>
            ` : ''}
        `;
        
        this.elements.summaryContent.innerHTML = html;
        this.elements.summaryPanel.style.display = 'block';
    }
    
    async toggleTTS() {
        const ttsBtn = document.getElementById('toggleTTS');
        
        if (this.currentAudio && !this.currentAudio.paused) {
            // 停止当前播放
            this.currentAudio.pause();
            this.currentAudio = null;
            ttsBtn.classList.remove('active');
            ttsBtn.innerHTML = '<i class="fas fa-volume-up"></i> 朗读';
        } else {
            // 开始朗读
            await this.readChapterAloud();
        }
    }
    
    async readChapterAloud() {
        try {
            const chapterText = this.elements.chapterContent.textContent;
            if (!chapterText.trim()) {
                this.showError('没有可朗读的内容');
                return;
            }
            
            this.showLoading('生成语音...');
            
            const response = await fetch(`/api/books/${this.bookId}/tts/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    text: chapterText.substring(0, 1000) // 限制长度
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.playAudio(data.audio_url);
                
                const ttsBtn = document.getElementById('toggleTTS');
                ttsBtn.classList.add('active');
                ttsBtn.innerHTML = '<i class="fas fa-pause"></i> 暂停';
            } else {
                this.showError('语音生成失败: ' + data.error);
            }
        } catch (error) {
            this.showError('语音生成失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    playAudio(audioUrl) {
        this.currentAudio = new Audio(audioUrl);
        
        this.currentAudio.addEventListener('ended', () => {
            const ttsBtn = document.getElementById('toggleTTS');
            ttsBtn.classList.remove('active');
            ttsBtn.innerHTML = '<i class="fas fa-volume-up"></i> 朗读';
            this.currentAudio = null;
        });
        
        this.currentAudio.addEventListener('error', () => {
            this.showError('音频播放失败');
            const ttsBtn = document.getElementById('toggleTTS');
            ttsBtn.classList.remove('active');
            ttsBtn.innerHTML = '<i class="fas fa-volume-up"></i> 朗读';
            this.currentAudio = null;
        });
        
        this.currentAudio.play();
    }
    
    adjustFontSize(delta) {
        const currentSize = parseInt(this.elements.content.style.fontSize) || this.preferences.fontSize;
        const newSize = Math.max(12, Math.min(24, currentSize + delta));
        
        this.elements.content.style.fontSize = newSize + 'px';
        this.preferences.fontSize = newSize;
        
        // 保存偏好设置
        this.savePreferences();
    }
    
    changeReadingMode(mode) {
        const container = document.querySelector('.reader-container');
        
        // 移除所有模式类
        container.classList.remove('normal-mode', 'focus-mode', 'immersive-mode');
        
        // 添加新模式类
        container.classList.add(mode + '-mode');
        
        this.preferences.readingMode = mode;
        this.savePreferences();
    }
    
    toggleSidebar() {
        this.elements.sidebar.classList.toggle('collapsed');
    }
    
    toggleAIPanel() {
        this.elements.aiAssistant.classList.toggle('collapsed');
        
        const toggleIcon = document.querySelector('#toggleAIPanel i');
        if (this.elements.aiAssistant.classList.contains('collapsed')) {
            toggleIcon.className = 'fas fa-chevron-up';
        } else {
            toggleIcon.className = 'fas fa-chevron-down';
        }
    }
    
    clearChat() {
        this.elements.aiChat.innerHTML = `
            <div class="ai-message assistant">
                <div>你好！我是你的AI阅读助手。你可以：</div>
                <ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">
                    <li>选中文本后提问</li>
                    <li>询问章节内容</li>
                    <li>请求概念解释</li>
                    <li>生成内容总结</li>
                </ul>
            </div>
        `;
    }
    
    clearTextSelection() {
        // 清除文本选择高亮
        document.querySelectorAll('.text-selection').forEach(el => {
            const parent = el.parentNode;
            parent.replaceChild(document.createTextNode(el.textContent), el);
            parent.normalize();
        });
        
        // 清除浏览器选择
        window.getSelection().removeAllRanges();
    }
    
    async startReadingSession() {
        try {
            const response = await fetch(`/api/books/${this.bookId}/session/start/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    chapter_number: this.currentChapter
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.readingSessionId = data.tracker_id;
                this.isReading = true;
            }
        } catch (error) {
            console.error('开始阅读会话失败:', error);
        }
    }
    
    async endReadingSession() {
        if (!this.readingSessionId || !this.isReading) {
            return;
        }
        
        try {
            const wordsRead = this.estimateWordsRead();
            
            const response = await fetch('/api/session/end/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    tracker_id: this.readingSessionId,
                    words_read: wordsRead
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.isReading = false;
                this.readingSessionId = null;
                this.updateReadingStats(data);
            }
        } catch (error) {
            console.error('结束阅读会话失败:', error);
        }
    }
    
    estimateWordsRead() {
        // 简单估算已读字数（基于章节内容长度）
        const content = this.elements.chapterContent.textContent;
        return content ? content.length : 0;
    }
    
    updateReadingStats(stats) {
        if (stats.duration) {
            const timeElement = document.getElementById('readingTime');
            const currentTime = parseInt(timeElement.textContent) || 0;
            timeElement.textContent = (currentTime + stats.duration) + '秒';
        }
    }
    
    async saveReadingProgress() {
        if (!this.isReading) return;
        
        try {
            await fetch(`/api/books/${this.bookId}/progress/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    chapter_number: this.currentChapter,
                    position: this.elements.content.scrollTop
                })
            });
        } catch (error) {
            console.error('保存阅读进度失败:', error);
        }
    }
    
    async updateReadingProgress() {
        try {
            const response = await fetch(`/api/books/${this.bookId}/assistant/statistics/`);
            const data = await response.json();
            
            if (data.success) {
                const stats = data.statistics;
                document.getElementById('readingProgress').textContent = 
                    stats.progress_percentage.toFixed(1) + '%';
                document.getElementById('readingTime').textContent = 
                    stats.total_reading_time + '秒';
                
                // 更新进度条
                const progressFill = document.querySelector('.progress-fill');
                progressFill.style.width = stats.progress_percentage + '%';
            }
        } catch (error) {
            console.error('更新阅读进度失败:', error);
        }
    }
    
    async loadQAHistory() {
        try {
            const response = await fetch(`/api/books/${this.bookId}/assistant/qa-history/`);
            const data = await response.json();
            
            if (data.success && data.qa_history.length > 0) {
                // 显示最近的几条问答记录
                const recentQA = data.qa_history.slice(0, 3);
                recentQA.reverse().forEach(qa => {
                    this.addChatMessage('user', qa.question);
                    this.addChatMessage('assistant', qa.answer);
                });
            }
        } catch (error) {
            console.error('加载问答历史失败:', error);
        }
    }
    
    async savePreferences() {
        try {
            await fetch('/user/preferences/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    reading_font_size: this.preferences.fontSize,
                    reading_mode: this.preferences.readingMode
                })
            });
        } catch (error) {
            console.error('保存偏好设置失败:', error);
        }
    }
    
    // 工具方法
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    showLoading(text = '加载中...') {
        document.getElementById('loadingText').textContent = text;
        this.elements.loadingModal.show();
    }
    
    hideLoading() {
        this.elements.loadingModal.hide();
    }
    
    showSuccess(message) {
        // 简单的成功提示
        this.showToast(message, 'success');
    }
    
    showError(message) {
        // 简单的错误提示
        this.showToast(message, 'error');
    }
    
    showToast(message, type = 'info') {
        // 创建简单的toast提示
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} 
                          position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
} 