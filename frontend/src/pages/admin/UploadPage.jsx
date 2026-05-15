import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Globe } from 'lucide-react';
import { examAPI } from '../../services/api';

export default function UploadPage() {
  const [subjects, setSubjects] = useState([]);
  const [units, setUnits] = useState([]);
  const [documents, setDocuments] = useState([]);
  
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [documentType, setDocumentType] = useState('textbook');
  const [isGlobal, setIsGlobal] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    examAPI.getSubjects().then(data => setSubjects(data.subjects));
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject).then(data => setUnits(data.units));
      loadDocs();
    } else {
      setUnits([]);
      setDocuments([]);
    }
  }, [selectedSubject]);

  const loadDocs = async () => {
    if (!selectedSubject) return;
    setLoadingDocs(true);
    try {
      const data = await examAPI.getDocuments(selectedSubject);
      setDocuments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleUpload = async (e) => {
    if (e) e.preventDefault();
    if (!file || !selectedSubject) {
      alert("請選擇檔案與科目");
      return;
    }

    if (!isGlobal && !selectedUnitId) {
      alert("請選擇單元，或者開啟『全域教材』模式");
      return;
    }
    
    setUploading(true);
    try {
      await examAPI.uploadDocument(
        file, 
        selectedSubject, 
        isGlobal ? null : selectedUnitId, 
        documentType
      );
      
      alert("上傳成功！檔案已進入背景解析隊列。");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadDocs();
    } catch (err) {
      console.error("上傳失敗詳細資訊:", err);
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' ? JSON.stringify(detail) : detail;
      alert("上傳失敗: " + (errorMsg || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("確定要刪除此文件及其所有解析數據嗎？")) return;
    try {
      await examAPI.deleteDocument(id);
      loadDocs();
    } catch (err) {
      alert("刪除失敗");
    }
  };

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-800">教材 PDF 上傳</h2>
        <p className="text-slate-500 mt-1">上傳課本或考古題 PDF 供 AI 建立知識庫（無檔案大小限制）</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Upload Form */}
        <div className="lg:col-span-1 bg-white p-6 rounded-2xl shadow-sm border border-slate-200 h-fit">
          <form onSubmit={handleUpload} className="space-y-5">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">1. 選擇科目</label>
              <select 
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5"
                value={selectedSubject} onChange={e => { setSelectedSubject(e.target.value); setSelectedUnitId(''); }} required
              >
                <option value="">選擇科目</option>
                {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">2. 文件類型</label>
              <div className="flex bg-slate-100 p-1 rounded-lg">
                <button 
                  type="button" 
                  onClick={() => setDocumentType('textbook')} 
                  className={`flex-1 py-1.5 text-sm rounded-md font-medium transition-all ${documentType === 'textbook' ? 'bg-white shadow text-blue-700' : 'text-slate-500'}`}
                >
                  課本/教材
                </button>
                <button 
                  type="button" 
                  onClick={() => setDocumentType('past_exam')} 
                  className={`flex-1 py-1.5 text-sm rounded-md font-medium transition-all ${documentType === 'past_exam' ? 'bg-white shadow text-indigo-700' : 'text-slate-500'}`}
                >
                  考古題範例
                </button>
              </div>
            </div>

            <div className="pt-2">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-bold text-slate-700">3. 對應單元</label>
                <button 
                  type="button"
                  onClick={() => setIsGlobal(!isGlobal)}
                  className={`flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider transition-all ${
                    isGlobal ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  <Globe className="w-3 h-3 mr-1" />
                  {isGlobal ? '全域模式 ON' : '指定單元'}
                </button>
              </div>
              
              {!isGlobal ? (
                <select 
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5"
                  value={selectedUnitId} onChange={e => setSelectedUnitId(e.target.value)} required
                  disabled={!selectedSubject}
                >
                  <option value="">選擇單元</option>
                  {units.map(u => <option key={u.id} value={u.id}>單元 {u.unit_code}: {u.name}</option>)}
                </select>
              ) : (
                <div className="p-3 bg-blue-50 text-blue-700 text-xs rounded-lg border border-blue-100 leading-relaxed">
                  <strong>全域模式：</strong>此文件將作為該科目的通識教材，不歸屬於特定單元。
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">4. 選擇 PDF 檔案</label>
              <div 
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  file ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
                }`}
              >
                <input 
                  type="file" ref={fileInputRef} className="hidden" accept=".pdf"
                  onChange={e => setFile(e.target.files[0])}
                />
                <Upload className={`w-8 h-8 mx-auto mb-2 ${file ? 'text-blue-500' : 'text-slate-400'}`} />
                {file ? (
                  <div className="text-sm font-medium text-blue-700 truncate px-2">{file.name}</div>
                ) : (
                  <div className="text-sm text-slate-500">點擊或拖曳 PDF 至此</div>
                )}
              </div>
            </div>

            <button 
              type="submit"
              disabled={uploading || !file || !selectedSubject}
              className={`w-full py-3 rounded-xl font-bold text-white shadow-lg transition-all flex items-center justify-center ${
                uploading || !file || !selectedSubject ? 'bg-slate-300' : 'bg-blue-600 hover:bg-blue-700 active:scale-95'
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  上傳中...
                </>
              ) : '開始上傳'}
            </button>
          </form>
        </div>

        {/* Documents List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-700">已上傳文件</h3>
            <button onClick={loadDocs} className="text-xs text-blue-600 hover:underline">重新整理</button>
          </div>
          
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                <tr>
                  <th className="px-6 py-3">檔案名稱</th>
                  <th className="px-6 py-3">類型</th>
                  <th className="px-6 py-3">解析狀態</th>
                  <th className="px-6 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingDocs ? (
                  <tr><td colSpan="4" className="px-6 py-12 text-center text-slate-400">載入中...</td></tr>
                ) : documents.length === 0 ? (
                  <tr><td colSpan="4" className="px-6 py-12 text-center text-slate-400">尚無上傳文件</td></tr>
                ) : documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-800 truncate max-w-xs">{doc.filename}</div>
                      <div className="text-[10px] text-slate-400">{new Date(doc.uploaded_at).toLocaleString()}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        doc.document_type === 'textbook' ? 'bg-blue-50 text-blue-600' : 'bg-indigo-50 text-indigo-600'
                      }`}>
                        {doc.document_type === 'textbook' ? '教材' : '考古題'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {doc.status === 'indexed' ? (
                        <div className="flex items-center text-green-600 font-bold text-xs">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> 已完成 ({doc.chunk_count} 段)
                        </div>
                      ) : doc.status === 'processing' ? (
                        <div className="flex items-center text-blue-600 text-xs animate-pulse">
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" /> 解析中...
                        </div>
                      ) : doc.status === 'error' ? (
                        <div className="flex items-center text-red-500 text-xs cursor-help" title={doc.error_message}>
                          <AlertCircle className="w-3 h-3 mr-1" /> 失敗
                        </div>
                      ) : (
                        <span className="text-slate-400 text-xs">排隊中</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <button 
                        onClick={() => handleDelete(doc.id)}
                        className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
