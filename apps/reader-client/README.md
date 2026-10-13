# Readify V2 · Unified React Reader Client (Experimental)

`apps/reader-client` 是逐步替换 Django 旧模板的统一 React + TypeScript + Vite 客户端。

## Web/PWA 开发

后端运行在 `127.0.0.1:8000` 且已迁移数据库，并在后端同域端口代理登录：

```bash
cd apps/reader-client
npm install
npm run dev
# http://127.0.0.1:5173
```

新客户端复用 `/api/v2/books/`、章节/进度/私有笔记接口，支持手机/平板/电脑屏幕适配、主题、章节导航和系统朗读。**授权克隆声音的完整 UI 仍位于现有 `/books/<id>/v2/` Django 阅读器中；React 迁移尚未完成。**

## 桌面壳实验

```bash
cd apps/reader-client
npm install
npm run tauri dev
```

首次构建可能需要系统 Rust、Xcode、MSVC、WebKit2GTK 等工具链；应用 icon、安装包签名/升级均需要补齐。**Tauri 独立打包的客户端无法直接沿用 Django 同源 Session 登录，需接入正式的 Token/OIDC 登录与 OS 凭证保险库后才具备生产可用的联网访问。**

## Capacitor 移动端骨架

```bash
cd apps/reader-client
npm install && npm run build
npx cap add android     # Android SDK 必需
npx cap add ios         # 仅 macOS + Xcode
npx cap sync
```

当前 **只是可构建的容器配置及共享页面**：原生 `android/`、`ios/` 工程、后台播放、文件导入、深度链接、安全存储、移动 Token 登录及商店发布均未实现或验收。浏览器端可优先使用 Django V2 阅读器。

## 下一阶段

完善授权音色/分角色朗读 React UI、统一客户端登录、服务端安全权限模型、端上书籍加密缓存和队列同步，然后才能开启真实桌面和移动端打包 CI。
