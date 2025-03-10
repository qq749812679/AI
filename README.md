<img width="829" alt="image" src="https://github.com/user-attachments/assets/36201a1d-3db1-4ed2-b62e-cc789b21e37f" /># AI
AI -Agent project
# RAG Agent System
一个完整的 RAG（检索增强生成）Agent 的智能问答系统 项目，包含前后端实现。，包含文档上传、索引构建、语义搜索和AI回答功能。我选择使用 Python FastAPI 作为后端，React 作为前端，这样可以构建一个现代化、高效的 AI 应用。


## 技术栈
- 后端：Python FastAPI
- 前端：React + TypeScript
- 向量数据库：FAISS
- LLM 集成：OpenAI API
- 文档处理：LangChain

## 功能
1. 文档上传与管理
2. 自动文档解析与索引
3. 智能问答（基于文档内容）
4. 对话历史管理
5. 用户认证

## 使用说明
查看 `backend/README.md` 和 `frontend/README.md` 获取详细部署信息。

访问应用：
打开浏览器，访问 http://localhost:3000
项目 URL
本地开发环境：
前端：http://localhost:3000
后端 API：http://localhost:8000

后续改进 RAG Agent 项目流程架构图
架构说明：
这个流程架构图展示了 RAG Agent 项目的主要组件和数据流：
前端 (React)
用户界面：应用的主要界面组件
认证组件：处理用户登录和注册
文档管理：上传和管理文档的界面
对话界面：与 RAG 系统交互的聊天界面
AuthContext：管理用户认证状态
API 服务：与后端通信的服务层
后端 (FastAPI)
认证API：处理用户登录和注册
文档API：处理文档上传和管理
问答API：处理用户问题并返回基于文档的回答
对话API：管理和存储对话历史
JWT认证：基于令牌的认证系统
文档处理：解析和处理上传的文档
RAG引擎：检索增强生成引擎的核心组件
数据存储
SQLite数据库：存储用户信息、文档元数据和对话历史
FAISS向量存储：存储文档的嵌入向量，用于相似性搜索
外部服务
OpenAI API：提供嵌入生成和文本生成能力
数据流
用户通过前端界面登录或注册
登录后，用户可以上传文档或开始新的对话
3. 上传的文档被后端处理，生成嵌入向量并存储
用户提问时，系统从向量存储中检索相关文本
结合检索的文本和用户问题，系统通过 OpenAI API 生成回答
对话历史被存储在数据库中，用户可以查看历史对话


您可以使用这个 Mermaid 代码在 Mermaid Live Editor 中生成一个可视化的流程图，然后下载为图片文件。
flowchart TD
    subgraph Client["前端 (React)"]
        A[用户界面] --> B[认证组件]
        A --> C[文档管理]
        A --> D[对话界面]
        B --> E[AuthContext]
        E --> F[API 服务]
    end

    subgraph Server["后端 (FastAPI)"]
        G[认证API] --> H[JWT认证]
        I[文档API] --> J[文档处理]
        K[问答API] --> L[RAG引擎]
        M[对话API] --> N[对话历史]
    end

    subgraph Database["数据存储"]
        O[SQLite数据库]
        P[FAISS向量存储]
    end

    subgraph ExternalServices["外部服务"]
        Q[OpenAI API]
    end

    F -->|登录/注册| G
    F -->|上传/获取文档| I
    F -->|提问| K
    F -->|管理对话| M

    J -->|存储文档信息| O
    J -->|生成嵌入向量| P
    N -->|存储对话记录| O
    H -->|存储用户信息| O

    L -->|获取相关文档| P
    L -->|获取文本嵌入| Q
    L -->|文本生成| Q


##  声明：
未经作者允许禁止用于商业途径！！！！

##  欢迎交流讨论联系作者
