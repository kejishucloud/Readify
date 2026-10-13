# Readify V2 · 第一批实际代码交付

分支：`feature/readify-v2-foundation`，面向原仓库 `kejishucloud/Readify`。这是**基础版本**，尚未宣称完成所有平台的独立安装包和所有 AI 模式。

## 已实现（代码级）

- 进入书籍详情页面，点击 **新版阅读器 V2**，地址 `/books/<id>/v2/`。
- V2 页面适配手机、平板、桌面：折叠目录、设置面板、护眼/暗色主题、字号、行高、章节导航。
- `/api/v2/books/<id>/chapters/<number>/` 和 `/api/v2/books/<id>/progress/`：登录及书籍归属验证，保存章节与段落位置。
- 内置浏览器系统 TTS（Web Speech API），有声音色选择、语速调整和逐段朗读。移动端系统 TTS 的后台播放能力还需要原生容器插件。
- `/api/v2/voices/`、`/api/v2/voices/create/`：显式声音权利确认，3–30s WAV 样本校验，非公开文件存储。最多每用户 10 个音色。
- `/api/v2/tts/synthesize/`：根据当前用户拥有的声音档案，将克隆/跨语种请求代理至独立 CosyVoice 服务；**若未配置 GPU worker，克隆选项禁用**。
- `services/voice_worker/app.py`：封装上游 CosyVoice `AutoModel` 的零样本、跨语言、风格指令推理，使用服务端 Bearer Token，输出真正的 WAV 音频。
- 初步收紧 `ALLOWED_HOSTS` 和 CORS；加入 V2 权限测试、静态语法 CI、敏感数据 `.gitignore`。

## 开发环境启动

```bash
python -m venv .venv
source .venv/bin/activate
cp env.v2.example .env
bash scripts/bootstrap_v2_dev.sh
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

当前主分支**未包含旧五个业务模块的历史迁移文件**。该脚本仅用于新开发库，自动生成 Django migrations。**已有业务数据的环境必须先备份、识别已存在表及迁移历史，人工审核迁移方案；不可直接在生产执行此脚本。** 所有旧业务迁移需要生成、审阅并提交后才能称为可重复部署。

## 可选 CosyVoice GPU 服务

参考上游官方项目 [QwenAudio/CosyVoice](https://github.com/QwenAudio/CosyVoice) 的 README 和 FastAPI 实现。请在隔离的 Python 环境按**指定版本**安装官方 CosyVoice 及其依赖、模型权重（本项目不复制或再分发上游代码和权重）。

```bash
git clone --recursive https://github.com/QwenAudio/CosyVoice.git
# 按 upstream 安装要求准备 CUDA/PyTorch/CosyVoice 依赖和模型
export PYTHONPATH=/path/to/CosyVoice:/path/to/CosyVoice/third_party/Matcha-TTS
export READIFY_COSYVOICE_MODEL_DIR=/path/to/CosyVoice/pretrained_models/CosyVoice2-0.5B
export READIFY_VOICE_WORKER_TOKEN=replace-with-long-random-secret
python -m pip install -r services/voice_worker/requirements-worker.txt
uvicorn services.voice_worker.app:app --host 127.0.0.1 --port 9001 --workers 1
```

然后主 Django 环境的 `.env`：

```dotenv
READIFY_VOICE_WORKER_URL=http://127.0.0.1:9001
READIFY_VOICE_WORKER_TOKEN=replace-with-the-same-secret
```

主 Django 和 GPU worker 若部署在不同机器上，必须使用 TLS 或受信任的私有隧道，不得把包含参考音频的 HTTP 流量直接暴露在公共网络。GPU worker 不允许直接公网无鉴权访问。语音质量、不同版本模型的 `inference_instruct2` 兼容性、并发限制须在 GPU 环境实测；没有运行 GPU 集成测试的情况不能宣称已验证克隆质量。

## 当前已知的限制与第二阶段工作

1. 目前手机、平板、桌面均可在浏览器访问响应式 Web，但未生成 Windows/macOS/Linux 原生安装包，也未发布 Android APK 或 iOS IPA。
2. PWA 配置只提供基础 Manifest；尚未提供加密离线书籍下载、双向冲突解决与真实离线客户端。
3. 现有旧版模块的 CSRF 豁免、API Key 明文存储、分类跨用户隔离及迁移历史仍需治理；不能直接暴露公共互联网。
4. 语音克隆仍依赖单独下载安装的授权模型及 GPU，当前提交没有打包预训练权重或冒充支持全部方言/情绪。
5. 后续按照 V2 计划引入成熟渲染器、RAG、长篇任务队列、跨设备增量同步、桌面/移动容器及全链路 E2E。

**上线门槛**：完善旧模块迁移和安全审查 → 数据备份与迁移演练 → 压测和 GPU 测试 → 手动验收各操作系统 → 再合并到 main。
