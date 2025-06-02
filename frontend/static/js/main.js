// 全局JavaScript功能
$(document).ready(function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 自动隐藏消息提示
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // 平滑滚动
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if( target.length ) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });

    // 搜索功能
    $('#searchInput').on('input', function() {
        var searchTerm = $(this).val().toLowerCase();
        $('.book-card').each(function() {
            var bookTitle = $(this).find('.book-title').text().toLowerCase();
            var bookAuthor = $(this).find('.book-author').text().toLowerCase();
            
            if (bookTitle.includes(searchTerm) || bookAuthor.includes(searchTerm)) {
                $(this).closest('.col-md-4').show();
            } else {
                $(this).closest('.col-md-4').hide();
            }
        });
    });

    // 文件上传预览
    $('#id_file').on('change', function() {
        var file = this.files[0];
        if (file) {
            var fileName = file.name;
            var fileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';
            
            $('#fileInfo').html(`
                <div class="alert alert-info">
                    <i class="fas fa-file me-2"></i>
                    <strong>已选择文件：</strong> ${fileName} (${fileSize})
                </div>
            `);
        }
    });

    // 封面图片预览
    $('#id_cover').on('change', function() {
        var file = this.files[0];
        if (file) {
            var reader = new FileReader();
            reader.onload = function(e) {
                $('#coverPreview').html(`
                    <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px;">
                `);
            };
            reader.readAsDataURL(file);
        }
    });
});

// AI功能相关
class AIService {
    constructor() {
        this.baseUrl = '/ai/';
    }

    // 生成书籍摘要
    async generateSummary(bookId) {
        try {
            this.showLoading('正在生成摘要...');
            
            const response = await fetch(`${this.baseUrl}summary/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ book_id: bookId })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('摘要生成成功！');
                this.updateSummary(data.summary);
            } else {
                this.showError(data.message || '摘要生成失败');
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
        } finally {
            this.hideLoading();
        }
    }

    // 提问功能
    async askQuestion(bookId, question) {
        try {
            this.showLoading('AI正在思考...');
            
            const response = await fetch(`${this.baseUrl}question/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    book_id: bookId,
                    question: question 
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayAnswer(data.answer);
            } else {
                this.showError(data.message || '回答生成失败');
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
        } finally {
            this.hideLoading();
        }
    }

    // 提取关键词
    async extractKeywords(bookId) {
        try {
            this.showLoading('正在提取关键词...');
            
            const response = await fetch(`${this.baseUrl}keywords/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ book_id: bookId })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('关键词提取成功！');
                this.displayKeywords(data.keywords);
            } else {
                this.showError(data.message || '关键词提取失败');
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
        } finally {
            this.hideLoading();
        }
    }

    // 获取CSRF令牌
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // 显示加载状态
    showLoading(message = '处理中...') {
        const loadingHtml = `
            <div id="loadingModal" class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <div class="loading-spinner mb-3"></div>
                            <p class="mb-0">${message}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(loadingHtml);
        $('#loadingModal').modal('show');
    }

    // 隐藏加载状态
    hideLoading() {
        $('#loadingModal').modal('hide');
        setTimeout(() => {
            $('#loadingModal').remove();
        }, 300);
    }

    // 显示成功消息
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    // 显示错误消息
    showError(message) {
        this.showToast(message, 'danger');
    }

    // 显示提示消息
    showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast-container position-fixed top-0 end-0 p-3">
                <div class="toast" role="alert">
                    <div class="toast-header">
                        <i class="fas fa-info-circle text-${type} me-2"></i>
                        <strong class="me-auto">提示</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(toastHtml);
        const toast = new bootstrap.Toast($('.toast').last()[0]);
        toast.show();
        
        // 自动移除
        setTimeout(() => {
            $('.toast-container').last().remove();
        }, 5000);
    }

    // 更新摘要显示
    updateSummary(summary) {
        $('#bookSummary').html(summary);
        $('#summarySection').show();
    }

    // 显示回答
    displayAnswer(answer) {
        const answerHtml = `
            <div class="card mt-3">
                <div class="card-header">
                    <i class="fas fa-robot me-2"></i>AI回答
                </div>
                <div class="card-body">
                    ${answer}
                </div>
            </div>
        `;
        
        $('#questionAnswer').html(answerHtml);
    }

    // 显示关键词
    displayKeywords(keywords) {
        const keywordsHtml = keywords.map(keyword => 
            `<span class="tag">${keyword}</span>`
        ).join('');
        
        $('#bookKeywords').html(keywordsHtml);
        $('#keywordsSection').show();
    }
}

// ChatTTS功能
class ChatTTSService {
    constructor() {
        this.baseUrl = '/tts/';
        this.isPlaying = false;
        this.currentAudio = null;
        this.supportedLanguages = {
            'zh': '中文',
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'fr': 'Français',
            'de': 'Deutsch',
            'es': 'Español',
            'it': 'Italiano',
            'ru': 'Русский',
            'ar': 'العربية',
            'hi': 'हिन्दी',
            'pt': 'Português',
            'th': 'ไทย',
            'vi': 'Tiếng Việt'
        };
    }

    // 播放文本
    async playText(text, language = 'zh', speakerId = 'default') {
        try {
            if (this.isPlaying) {
                this.stop();
                return;
            }

            this.showLoading('正在生成语音...');
            
            const response = await fetch(`${this.baseUrl}generate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    text: text,
                    language: language,
                    speaker_id: speakerId,
                    use_cache: true
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.playAudio(data.audio_url);
                this.showSuccess(`语音生成成功！${data.from_cache ? '(来自缓存)' : ''}`);
            } else {
                this.showError(data.error || '语音生成失败');
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
        } finally {
            this.hideLoading();
        }
    }

    // 播放音频
    playAudio(audioUrl) {
        this.currentAudio = new Audio(audioUrl);
        this.currentAudio.play();
        this.isPlaying = true;
        
        this.currentAudio.onended = () => {
            this.isPlaying = false;
            this.updatePlayButton();
        };
        
        this.currentAudio.onerror = () => {
            this.isPlaying = false;
            this.updatePlayButton();
            this.showError('音频播放失败');
        };
        
        this.updatePlayButton();
    }

    // 停止播放
    stop() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
        }
        this.isPlaying = false;
        this.updatePlayButton();
    }

    // 更新播放按钮状态
    updatePlayButton() {
        const playBtn = $('#playBtn');
        if (this.isPlaying) {
            playBtn.html('<i class="fas fa-stop me-2"></i>停止');
            playBtn.removeClass('btn-primary').addClass('btn-danger');
        } else {
            playBtn.html('<i class="fas fa-play me-2"></i>播放');
            playBtn.removeClass('btn-danger').addClass('btn-primary');
        }
    }

    // 获取可用说话人
    async getSpeakers(language = null) {
        try {
            const url = language ? `${this.baseUrl}speakers/?language=${language}` : `${this.baseUrl}speakers/`;
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                return data.speakers;
            } else {
                this.showError('获取说话人列表失败');
                return [];
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            return [];
        }
    }

    // 获取CSRF令牌
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // 显示加载状态
    showLoading(message) {
        const aiService = new AIService();
        aiService.showLoading(message);
    }

    // 隐藏加载状态
    hideLoading() {
        const aiService = new AIService();
        aiService.hideLoading();
    }

    // 显示成功消息
    showSuccess(message) {
        const aiService = new AIService();
        aiService.showSuccess(message);
    }

    // 显示错误消息
    showError(message) {
        const aiService = new AIService();
        aiService.showError(message);
    }
}

// 翻译服务
class TranslationService {
    constructor() {
        this.baseUrl = '/translation/';
        this.supportedLanguages = {};
        this.loadSupportedLanguages();
    }

    // 加载支持的语言
    async loadSupportedLanguages() {
        try {
            const response = await fetch(`${this.baseUrl}languages/`);
            const data = await response.json();
            
            if (data.success) {
                this.supportedLanguages = data.languages;
            }
        } catch (error) {
            console.error('加载语言列表失败:', error);
        }
    }

    // 翻译文本
    async translateText(text, targetLanguage, sourceLanguage = 'auto', model = null) {
        try {
            this.showLoading('正在翻译...');
            
            const response = await fetch(`${this.baseUrl}translate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    text: text,
                    target_language: targetLanguage,
                    source_language: sourceLanguage,
                    model: model,
                    use_cache: true
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(`翻译成功！${data.from_cache ? '(来自缓存)' : ''}`);
                return data;
            } else {
                this.showError(data.error || '翻译失败');
                return null;
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            return null;
        } finally {
            this.hideLoading();
        }
    }

    // 批量翻译
    async batchTranslate(texts, targetLanguage, sourceLanguage = 'auto') {
        try {
            this.showLoading('正在批量翻译...');
            
            const response = await fetch(`${this.baseUrl}batch-translate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    texts: texts,
                    target_language: targetLanguage,
                    source_language: sourceLanguage
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('批量翻译完成！');
                return data.results;
            } else {
                this.showError(data.error || '批量翻译失败');
                return null;
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            return null;
        } finally {
            this.hideLoading();
        }
    }

    // 检测语言
    async detectLanguage(text) {
        try {
            const response = await fetch(`${this.baseUrl}detect-language/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ text: text })
            });

            const data = await response.json();
            
            if (data.success) {
                return {
                    language: data.detected_language,
                    name: data.language_name
                };
            } else {
                return null;
            }
        } catch (error) {
            console.error('语言检测失败:', error);
            return null;
        }
    }

    // 翻译并朗读
    async translateAndSpeak(text, targetLanguage, sourceLanguage = 'auto') {
        const translationResult = await this.translateText(text, targetLanguage, sourceLanguage);
        
        if (translationResult && translationResult.success) {
            const ttsService = new ChatTTSService();
            await ttsService.playText(translationResult.translated_text, targetLanguage);
            return translationResult;
        }
        
        return null;
    }

    // 获取翻译历史
    async getTranslationHistory(limit = 50) {
        try {
            const response = await fetch(`${this.baseUrl}history/?limit=${limit}`);
            const data = await response.json();
            
            if (data.success) {
                return data.history;
            } else {
                this.showError('获取翻译历史失败');
                return [];
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            return [];
        }
    }

    // 获取CSRF令牌
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // 显示加载状态
    showLoading(message) {
        const aiService = new AIService();
        aiService.showLoading(message);
    }

    // 隐藏加载状态
    hideLoading() {
        const aiService = new AIService();
        aiService.hideLoading();
    }

    // 显示成功消息
    showSuccess(message) {
        const aiService = new AIService();
        aiService.showSuccess(message);
    }

    // 显示错误消息
    showError(message) {
        const aiService = new AIService();
        aiService.showError(message);
    }
}

// 阅读器功能
class Reader {
    constructor() {
        this.currentChapter = 1;
        this.totalChapters = 1;
        this.fontSize = 16;
        this.lineHeight = 1.8;
        this.theme = 'light';
    }

    // 初始化阅读器
    init(bookId, totalChapters) {
        this.bookId = bookId;
        this.totalChapters = totalChapters;
        this.bindEvents();
        this.loadChapter(1);
    }

    // 绑定事件
    bindEvents() {
        // 章节导航
        $('#prevChapter').on('click', () => this.prevChapter());
        $('#nextChapter').on('click', () => this.nextChapter());
        
        // 字体大小调整
        $('#increaseFontSize').on('click', () => this.changeFontSize(2));
        $('#decreaseFontSize').on('click', () => this.changeFontSize(-2));
        
        // 主题切换
        $('#themeToggle').on('click', () => this.toggleTheme());
        
        // 键盘快捷键
        $(document).on('keydown', (e) => {
            if (e.key === 'ArrowLeft') this.prevChapter();
            if (e.key === 'ArrowRight') this.nextChapter();
        });
    }

    // 加载章节
    async loadChapter(chapterNumber) {
        try {
            const response = await fetch(`/books/api/${this.bookId}/chapter/${chapterNumber}/`);
            const data = await response.json();
            
            if (data.success) {
                $('#readerContent').html(data.content);
                this.currentChapter = chapterNumber;
                this.updateProgress();
                this.updateNavigation();
                this.saveReadingProgress();
            }
        } catch (error) {
            console.error('加载章节失败:', error);
        }
    }

    // 上一章
    prevChapter() {
        if (this.currentChapter > 1) {
            this.loadChapter(this.currentChapter - 1);
        }
    }

    // 下一章
    nextChapter() {
        if (this.currentChapter < this.totalChapters) {
            this.loadChapter(this.currentChapter + 1);
        }
    }

    // 调整字体大小
    changeFontSize(delta) {
        this.fontSize += delta;
        this.fontSize = Math.max(12, Math.min(24, this.fontSize));
        $('#readerContent').css('font-size', this.fontSize + 'px');
    }

    // 切换主题
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        
        if (this.theme === 'dark') {
            $('#readerContent').addClass('bg-dark text-light');
        } else {
            $('#readerContent').removeClass('bg-dark text-light');
        }
    }

    // 更新进度
    updateProgress() {
        const progress = (this.currentChapter / this.totalChapters) * 100;
        $('#readingProgress').css('width', progress + '%');
        $('#progressText').text(`${this.currentChapter} / ${this.totalChapters}`);
    }

    // 更新导航按钮
    updateNavigation() {
        $('#prevChapter').prop('disabled', this.currentChapter <= 1);
        $('#nextChapter').prop('disabled', this.currentChapter >= this.totalChapters);
    }

    // 保存阅读进度
    async saveReadingProgress() {
        try {
            await fetch('/books/api/progress/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    book_id: this.bookId,
                    chapter: this.currentChapter,
                    progress: (this.currentChapter / this.totalChapters) * 100
                })
            });
        } catch (error) {
            console.error('保存阅读进度失败:', error);
        }
    }
}

// 全局实例
window.aiService = new AIService();
window.chatTTSService = new ChatTTSService();
window.translationService = new TranslationService();
window.reader = new Reader();

// 工具函数
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
}

// 文本选择翻译功能
$(document).ready(function() {
    let selectedText = '';
    
    // 监听文本选择
    $(document).on('mouseup', function() {
        selectedText = window.getSelection().toString().trim();
        
        if (selectedText.length > 0 && selectedText.length < 1000) {
            showTranslationPopup();
        } else {
            hideTranslationPopup();
        }
    });
    
    function showTranslationPopup() {
        hideTranslationPopup();
        
        const popup = $(`
            <div id="translationPopup" class="translation-popup">
                <button class="btn btn-sm btn-primary me-2" onclick="translateSelectedText()">
                    <i class="fas fa-language me-1"></i>翻译
                </button>
                <button class="btn btn-sm btn-success" onclick="speakSelectedText()">
                    <i class="fas fa-volume-up me-1"></i>朗读
                </button>
            </div>
        `);
        
        $('body').append(popup);
        
        // 定位弹窗
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            
            popup.css({
                position: 'fixed',
                top: rect.bottom + 10,
                left: rect.left,
                zIndex: 9999
            });
        }
    }
    
    function hideTranslationPopup() {
        $('#translationPopup').remove();
    }
    
    // 全局函数
    window.translateSelectedText = async function() {
        if (selectedText) {
            const result = await window.translationService.translateText(selectedText, 'zh');
            if (result) {
                showTranslationResult(selectedText, result.translated_text, result.source_language, result.target_language);
            }
        }
        hideTranslationPopup();
    };
    
    window.speakSelectedText = async function() {
        if (selectedText) {
            await window.chatTTSService.playText(selectedText);
        }
        hideTranslationPopup();
    };
    
    function showTranslationResult(original, translated, sourceLang, targetLang) {
        const modal = $(`
            <div class="modal fade" id="translationModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-language me-2"></i>翻译结果
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">原文 (${sourceLang}):</label>
                                <div class="p-3 bg-light rounded">${original}</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">译文 (${targetLang}):</label>
                                <div class="p-3 bg-primary text-white rounded">${translated}</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-success" onclick="window.chatTTSService.playText('${translated}', '${targetLang}')">
                                <i class="fas fa-volume-up me-1"></i>朗读译文
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
        $('#translationModal').modal('show');
        
        $('#translationModal').on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }
    
    // 点击其他地方隐藏弹窗
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#translationPopup').length) {
            hideTranslationPopup();
        }
    });
}); 