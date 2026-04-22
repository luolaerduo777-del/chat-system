# 💬 Chat System（支持 AI 的可嵌入式聊天模块）

## 📌 项目简介

这是一个基于 Flask + Socket.IO 构建的实时聊天系统，支持多用户在线聊天、房间管理，并集成 DeepSeek AI，实现 @AI 智能回复。

项目定位为 **轻量级可嵌入聊天模块**，可用于为没有聊天功能的应用快速接入即时通信能力（如校园系统、内部工具等）。

---

## 🌐 在线体验

👉 https://chat-system-r9tp.onrender.com

（建议使用电脑访问）

---

## ✨ 功能特点

* ✅ 用户注册 / 登录系统
* ✅ 多人实时聊天（WebSocket）
* ✅ 多房间聊天
* ✅ 聊天记录持久化（SQLite）
* ✅ AI 助手（DeepSeek API）
* ✅ @AI 触发智能回复
* ✅ AI开关控制（可启用/禁用）

---

## 🤖 AI 使用方式

1. 打开 AI 开关
2. 在聊天中输入：

```
@ai 你好
```

👉 AI 才会参与回复

---

## 🖼 项目截图

![聊天界面](screenshot1.png)
![AI回复](screenshot2.png)
![房间聊天](screenshot3.png)

---

## ⚙ 技术栈

* Python
* Flask
* Flask-SocketIO
* SQLite
* HTML / CSS / JavaScript
* DeepSeek API

---

## 🛠 本地运行

```bash
pip install -r requirements.txt
python app.py
```

访问：http://127.0.0.1:5000

---

## ☁ 部署说明（Render）

1. 上传代码到 GitHub
2. 在 Render 创建 Web Service
3. 选择仓库
4. 设置启动命令：

```
python app.py
```

5. 设置环境变量（DeepSeek API Key）
6. 等待部署完成

---

## ⚠ 注意事项

* 当前使用 SQLite，线上数据为临时存储（Render 免费版）
* 若需持久化数据，建议接入 PostgreSQL

---

## 🚀 项目亮点（简历可用）

* 基于 WebSocket 实现实时通信系统
* 设计多房间聊天架构
* 接入大模型 API，实现 AI 聊天功能
* 实现 AI 按需触发机制（@AI + 开关控制）
* 前后端分离 + 模块化设计（AI服务解耦）

---

## 📌 项目定位

👉 轻量级即时通信模块（可嵌入系统）
👉 AI增强聊天组件
