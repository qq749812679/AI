from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import json
from datetime import datetime, timedelta

# RAG 组件
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# 用户认证和数据存储
import sqlite3
from pathlib import Path
import hashlib
import jwt
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="RAG Agent API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 目录设置
UPLOAD_DIR = Path("uploads")
DB_PATH = Path("database.db")
VECTOR_STORE_PATH = Path("vector_store")

UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_STORE_PATH.mkdir(exist_ok=True)

# 设置数据库
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        hashed_password TEXT,
        created_at TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        filename TEXT,
        path TEXT,
        uploaded_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        content TEXT,
        is_user BOOLEAN,
        timestamp TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# 模型定义
class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Question(BaseModel):
    query: str
    conversation_id: Optional[str] = None

class DocumentInfo(BaseModel):
    id: str
    filename: str
    uploaded_at: str

class ConversationInfo(BaseModel):
    id: str
    title: str
    created_at: str

class Message(BaseModel):
    id: str
    content: str
    is_user: bool
    timestamp: str

# 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {"id": user[0], "username": user[1]}

# RAG 功能
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
llm = ChatOpenAI(temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))

def process_document(file_path, doc_id):
    if file_path.suffix.lower() == '.pdf':
        loader = PyPDFLoader(str(file_path))
    else:
        loader = TextLoader(str(file_path))
    
    documents = loader.load()
    text_chunks = text_splitter.split_documents(documents)
    
    # 创建或更新向量存储
    vector_store = FAISS.from_documents(text_chunks, embeddings)
    vector_store.save_local(str(VECTOR_STORE_PATH / doc_id))
    
    return len(text_chunks)

def get_user_vector_store(user_id):
    # 获取用户所有文档
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM documents WHERE user_id = ?", (user_id,))
    doc_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not doc_ids:
        return None
    
    # 加载所有文档的向量存储并合并
    vector_stores = []
    for doc_id in doc_ids:
        if (VECTOR_STORE_PATH / doc_id).exists():
            vs = FAISS.load_local(str(VECTOR_STORE_PATH / doc_id), embeddings)
            vector_stores.append(vs)
    
    if not vector_stores:
        return None
    
    # 合并向量存储
    if len(vector_stores) == 1:
        return vector_stores[0]
    else:
        main_vs = vector_stores[0]
        for vs in vector_stores[1:]:
            main_vs.merge_from(vs)
        return main_vs

# API 路由
@app.post("/register", response_model=Token)
async def register(user: User):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 检查用户是否已存在
    cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 创建新用户
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (id, username, hashed_password, created_at) VALUES (?, ?, ?, ?)",
        (user_id, user.username, hashed_password, datetime.utcnow())
    )
    conn.commit()
    conn.close()
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, hashed_password FROM users WHERE username = ?", 
        (form_data.username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user[0]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # 保存文件
    doc_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = UPLOAD_DIR / f"{doc_id}{file_extension}"
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # 处理文档并创建向量索引
    try:
        chunks_count = process_document(file_path, doc_id)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to process document: {str(e)}")
    
    # 保存文档信息到数据库
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (id, user_id, filename, path, uploaded_at) VALUES (?, ?, ?, ?, ?)",
        (doc_id, current_user["id"], file.filename, str(file_path), datetime.utcnow())
    )
    conn.commit()
    conn.close()
    
    return {
        "id": doc_id,
        "filename": file.filename,
        "chunks_processed": chunks_count,
        "message": "Document processed successfully"
    }

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, filename, uploaded_at FROM documents WHERE user_id = ?",
        (current_user["id"],)
    )
    documents = [
        {"id": row[0], "filename": row[1], "uploaded_at": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()
    
    return documents

@app.post("/ask")
async def ask_question(question: Question, current_user: dict = Depends(get_current_user)):
    # 获取用户向量存储
    vector_store = get_user_vector_store(current_user["id"])
    if not vector_store:
        raise HTTPException(status_code=400, detail="No documents found for retrieval")
    
    # 创建问答链
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True
    )
    
    # 获取答案
    result = qa_chain({"query": question.query})
    answer = result["result"]
    sources = [doc.page_content[:100] + "..." for doc in result["source_documents"]]
    
    # 保存对话
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    conversation_id = question.conversation_id
    if not conversation_id:
        # 创建新对话
        conversation_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, current_user["id"], question.query[:50], datetime.utcnow())
        )
    
    # 保存用户问题
    question_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO messages (id, conversation_id, content, is_user, timestamp) VALUES (?, ?, ?, ?, ?)",
        (question_id, conversation_id, question.query, True, datetime.utcnow())
    )
    
    # 保存AI回答
    answer_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO messages (id, conversation_id, content, is_user, timestamp) VALUES (?, ?, ?, ?, ?)",
        (answer_id, conversation_id, answer, False, datetime.utcnow())
    )
    
    conn.commit()
    conn.close()
    
    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation_id
    }

@app.get("/conversations", response_model=List[ConversationInfo])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
        (current_user["id"],)
    )
    conversations = [
        {"id": row[0], "title": row[1], "created_at": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()
    
    return conversations

@app.get("/conversations/{conversation_id}", response_model=List[Message])
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 验证对话属于当前用户
    cursor.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, current_user["id"])
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 获取对话消息
    cursor.execute(
        "SELECT id, content, is_user, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp",
        (conversation_id,)
    )
    messages = [
        {"id": row[0], "content": row[1], "is_user": bool(row[2]), "timestamp": row[3]}
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 