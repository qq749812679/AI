import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchDocuments, uploadDocument, fetchConversations } from '../services/api';
import './Dashboard.css';

interface Document {
  id: string;
  filename: string;
  uploaded_at: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

const Dashboard: React.FC = () => {
  const { token } = useAuth();
  
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');
  
  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);
  
  const loadData = async () => {
    try {
      const [docsData, convsData] = await Promise.all([
        fetchDocuments(token!),
        fetchConversations(token!)
      ]);
      
      setDocuments(docsData);
      setConversations(convsData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };
  
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    try {
      setUploading(true);
      setUploadProgress(0);
      setUploadError('');
      setUploadSuccess('');
      
      // 创建进度监控
      const interval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 95) {
            clearInterval(interval);
            return prev;
          }
          return prev + 5;
        });
      }, 500);
      
      await uploadDocument(file, token!);
      
      clearInterval(interval);
      setUploadProgress(100);
      setUploadSuccess(`文件 "${file.name}" 上传并处理成功！`);
      
      // 重新加载文档列表
      const docsData = await fetchDocuments(token!);
      setDocuments(docsData);
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadError('文件上传失败');
    } finally {
      setUploading(false);
      // 清除文件输入
      e.target.value = '';
    }
  };
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };
  
  return (
    <div className="dashboard-container">
      <div className="dashboard-section">
        <div className="section-header">
          <h2>文档管理</h2>
          <div className="upload-container">
            <label className="upload-button">
              上传新文档
              <input
                type="file"
                accept=".pdf,.txt,.docx"
                onChange={handleFileUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>
        
        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <div className="progress-text">{uploadProgress}% - 处理中...</div>
          </div>
        )}
        
        {uploadError && <div className="upload-error">{uploadError}</div>}
        {uploadSuccess && <div className="upload-success">{uploadSuccess}</div>}
        
        <div className="documents-list">
          {documents.length === 0 ? (
            <div className="empty-state">
              <p>还没有上传文档。上传一些文档来开始使用RAG功能！</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>文件名</th>
                  <th>上传时间</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.filename}</td>
                    <td>{formatDate(doc.uploaded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      <div className="dashboard-section">
        <div className="section-header">
          <h2>对话历史</h2>
          <Link to="/chat" className="new-chat-button">
            新建对话
          </Link>
        </div>
        
        <div className="conversations-list">
          {conversations.length === 0 ? (
            <div className="empty-state">
              <p>还没有对话记录。开始一个新的对话来提问关于您文档的问题！</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>标题</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {conversations.map((conv) => (
                  <tr key={conv.id}>
                    <td>{conv.title}</td>
                    <td>{formatDate(conv.created_at)}</td>
                    <td>
                      <Link to={`/chat/${conv.id}`} className="view-chat-link">
                        查看
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 