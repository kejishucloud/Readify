# Readify - 智能阅读助手

## 🚀 快速启动

### 环境要求
- Python 3.8+
- Conda (推荐使用Anaconda或Miniconda)

### 安装步骤

1. **激活conda环境**
   ```bash
   conda activate DL
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **检查项目状态**
   ```bash
   python check_status.py
   ```

4. **启动服务器**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

### 一键启动
- Windows批处理: 双击 `start_server.bat`
- PowerShell: 运行 `.\start_server.ps1`

### 访问地址
- 本地访问: http://localhost:8000
- 网络访问: http://0.0.0.0:8000

---

## 📖 项目介绍

一款功能强大的人工智能阅读应用程序，支持多种电子书格式、语言翻译和可定制的 TTS（文本转语音），为用户带来沉浸式的智能阅读体验。

## 🌟 主要功能

### 📚 多格式支持
- **PDF** - 支持文本提取和章节识别
- **EPUB** - 完整的电子书格式支持
- **MOBI** - Kindle格式兼容
- **TXT** - 纯文本文件
- **DOCX** - Word文档格式
- **HTML** - 网页格式

### 🤖 AI智能功能
- **智能摘要** - 使用大语言模型自动生成书籍摘要
- **问答系统** - 基于书籍内容的智能问答
- **关键词提取** - 自动识别和提取核心概念
- **内容分析** - 深度理解书籍结构和主题

### 🔊 语音功能
- **TTS语音合成** - 高质量的文本转语音
- **多语言支持** - 支持中文、英文等多种语言
- **语音缓存** - 智能缓存机制提升性能
- **自定义语音** - 可调节语速和音调

### 🌐 翻译服务
- **实时翻译** - 支持多种语言互译
- **上下文翻译** - 基于书籍内容的智能翻译
- **翻译缓存** - 提升翻译效率

### 📖 阅读体验
- **进度跟踪** - 详细的阅读进度记录
- **智能笔记** - 支持文本选择和标注
- **个性化设置** - 字体、主题、布局自定义
- **阅读统计** - 全面的阅读数据分析

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Django 5.0+
- Redis (用于Celery任务队列)
- SQLite/PostgreSQL

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/kejishucloud/readify.git
cd readify
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

5. **数据库迁移**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **创建超级用户**
```bash
python manage.py createsuperuser
```

7. **启动开发服务器**
```bash
python manage.py runserver
```

8. **启动Celery工作进程**（新终端）
```bash
celery -A readify worker -l info
```

## ⚙️ 配置说明

### 环境变量配置

在 `.env` 文件中配置以下变量：

```env
# Django设置
SECRET_KEY=your-secret-key-here
DEBUG=True

# AI服务配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Redis配置（用于Celery）
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 数据库配置（可选，默认使用SQLite）
# DATABASE_URL=postgresql://user:password@localhost:5432/readify
```

### AI服务配置

1. **OpenAI API**
   - 注册 OpenAI 账户
   - 获取 API Key
   - 配置到环境变量中

2. **模型选择**
   - 支持 GPT-3.5-turbo、GPT-4 等模型
   - 可根据需求调整模型参数

## 📁 项目结构

```
Readify/
├── readify/                    # Django项目主目录
│   ├── books/                  # 书籍管理应用
│   ├── ai_services/           # AI服务应用
│   ├── tts_service/           # TTS语音服务
│   ├── translation_service/   # 翻译服务
│   ├── user_management/       # 用户管理
│   └── settings.py            # 项目配置
├── frontend/                  # 前端资源
│   ├── static/               # 静态文件
│   │   ├── css/             # 样式文件
│   │   ├── js/              # JavaScript文件
│   │   └── images/          # 图片资源
│   └── templates/           # HTML模板
├── media/                    # 用户上传文件
├── logs/                     # 日志文件
├── requirements.txt          # Python依赖
└── README.md                # 项目文档
```

## 🎨 功能模块

### 书籍管理 (books)
- 书籍上传和存储
- 内容解析和处理
- 章节管理
- 阅读进度跟踪
- 笔记和标注

### AI服务 (ai_services)
- 大语言模型集成
- 智能摘要生成
- 问答系统
- 关键词提取
- 任务队列管理

### TTS服务 (tts_service)
- 文本转语音
- 多语言支持
- 语音缓存
- 音频文件管理

### 翻译服务 (translation_service)
- 多语言翻译
- 上下文理解
- 翻译缓存
- 批量翻译

### 用户管理 (user_management)
- 用户认证
- 个人资料管理
- 阅读偏好设置
- 数据统计

## 🔧 开发指南

### 添加新的电子书格式

1. 在 `books/models.py` 中添加新格式
2. 创建对应的解析器
3. 更新文件处理逻辑

### 集成新的AI模型

1. 在 `ai_services/services.py` 中添加新模型
2. 配置模型参数
3. 更新API接口

### 自定义前端样式

1. 编辑 `frontend/static/css/main.css`
2. 添加新的组件样式
3. 更新JavaScript交互

## 📊 性能优化

### 缓存策略
- Redis缓存热点数据
- 文件系统缓存静态资源
- 数据库查询优化

### 异步处理
- Celery处理耗时任务
- 后台AI分析
- 批量数据处理

### 前端优化
- 静态资源压缩
- 图片懒加载
- 代码分割

## 🔒 安全考虑

### 文件安全
- 文件类型验证
- 大小限制
- 恶意文件检测

### 数据保护
- 用户数据加密
- API访问控制
- 输入验证

### 隐私保护
- 用户数据隔离
- 敏感信息脱敏
- 访问日志记录

## 🚀 部署指南

### Docker部署

```bash
# 构建镜像
docker build -t readify .

# 运行容器
docker run -p 8000:8000 readify
```

### 生产环境

1. 使用PostgreSQL数据库
2. 配置Nginx反向代理
3. 使用Gunicorn作为WSGI服务器
4. 设置SSL证书
5. 配置监控和日志

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系我们

- 项目主页：[GitHub](https://github.com/kejishucloud/readify)
- 问题反馈：[Issues](https://github.com/kejishucloud/readify/issues)
- 邮箱：kejishucloud@gmail.com

## 🙏 致谢

感谢以下开源项目的支持：
- Django
- OpenAI
- Bootstrap
- Font Awesome
- jQuery

---

**Readify** - 让阅读更智能，让知识更易得！
