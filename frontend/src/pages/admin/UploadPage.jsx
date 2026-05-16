import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Globe, RefreshCcw, Layers } from 'lucide-react';
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
  const [errorInfo, setErrorInfo] = useState('');
  
  const fileInputRef = useRef(null);

  // 1. 初始化科目列表
  useEffect(() => {
    examAPI.getSubjects()
      .then(data => {
        setSubjects(Array.isArray(data?.subjects) ? data.subjects : []);
      })
      .catch(err => {
        console.error("載入科目失敗:", err);
        setErrorInfo("科目載入失敗");
      });
  }, []);

  // 2. 獲取文件列表的函數
  const loadDocs = async (subjectId) => {
    if (!subjectId) return;
    setLoadingDocs(true);
    setErrorInfo('');
    try {
      const data = await examAPI.getDocuments(subjectId);
      // 後端現在回傳的是 { documents: [...] }
      const list = Array.isArray(data?.documents) ? data.documents : [];
      setDocuments(list);
    } catch (err) {
      console.error("載入文件列表失敗:", err);
      setErrorInfo("文件載入失敗: " + err.message);
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  // 3. 當科目改變時，獲取單元和文件
  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject)
        .then(data => {
          setUnits(Array.isArray(data?.units) ? data.units : []);
        })
        .catch(err => console.error("載入單元失敗:", err));
      
      loadDocs(selectedSubject);
      setSelectedUnitId('');
    } else {
      setUnits([]);
      setDocuments([]);
    }
  }, [selectedSubject]);

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
      
      alert("上傳成功！檔案已進入背景解析。");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTimeout(() => loadDocs(selectedSubject), 800);
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
    if (!window.confirm("確定要刪除嗎？")) return;
    try {
      await examAPI.deleteDocument(id);
      loadDocs(selectedSubject);
    } catch (err) {
      alert("刪除失敗");
    }
  };

  return (
    <div className="space-y-8 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">教材 PDF 管理</h2>
          <p className="text-slate-500 mt-1 text-sm">上傳 PDF 供 AI 建立單元知識庫</p>
        </div>
        <button 
          onClick={() => loadDocs(selectedSubject)}
          className="flex items-center justify-center px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-sm font-bold transition-all"
        >
          <RefreshCcw className={`w-4 h-4 mr-2 ${loadingDocs ? 'animate-spin' : ''}`} />
          重新整理列表
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* 上傳區塊 */}
        <div className="lg:col-span-1 bg-white p-6 rounded-3xl shadow-xl border border-slate-100 h-fit space-y-6">
          <form onSubmit={handleUpload} className="space-y-5">
            <div>
              <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2">1. 選擇科目</label>
              <select 
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl p-3 font-medium outline-none"
                value={selectedSubject} 
                onChange={e => setSelectedSubject(e.target.value)} 
                required
              >
                <option value="">選擇科目</option>
                {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2">2. 文件類型</label>
              <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                <button type="button" onClick={() => setDocumentType('textbook')} className={`flex-1 py-2 text-sm rounded-xl font-bold transition-all ${documentType === 'textbook' ? 'bg-white shadow-sm text-blue-600' : 'text-slate-400'}`}>教材</button>
                <button type="button" onClick={() => setDocumentType('past_exam')} className={`flex-1 py-2 text-sm rounded-xl font-bold transition-all ${documentType === 'past_exam' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-400'}`}>考古題</button>
              </div>
            </div>

            <div className="pt-2">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-black text-slate-400 uppercase tracking-widest">3. 對應單元範圍</label>
                <button type="button" onClick={() => setIsGlobal(!isGlobal)} className={`flex items-center px-2 py-1 rounded-lg text-[10px] font-black uppercase transition-all ${isGlobal ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' : 'bg-slate-200 text-slate-500'}`}>
                  <Globe className="w-3 h-3 mr-1" />
                  {isGlobal ? '全域模式 ON' : '指定單元'}
                </button>
              </div>
              {!isGlobal ? (
                <select className="w-full bg-slate-50 border border-slate-200 rounded-2xl p-3 font-medium disabled:opacity-50 outline-none" value={selectedUnitId} onChange={e => setSelectedUnitId(e.target.value)} required={!isGlobal} disabled={!selectedSubject}>
                  <option value="">選擇單元</option>
                  {units.map(u => <option key={u.id} value={u.id}>單元 {u.unit_code}: {u.name}</option>)}
                </select>
              ) : (
                <div className="p-4 bg-blue-50 text-blue-700 text-xs rounded-2xl border border-blue-100 leading-relaxed font-medium">
                  <strong>全域教材模式：</strong>AI 生成題目時會將此文件作為通識背景參考。
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2">4. 選擇 PDF 檔案</label>
              <div onClick={() => fileInputRef.current?.click()} className={`border-3 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all ${file ? 'border-blue-400 bg-blue-50/50 shadow-inner' : 'border-slate-100 hover:border-blue-200 hover:bg-slate-50'}`}>
                <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
                <Upload className={`w-10 h-10 mx-auto mb-3 ${file ? 'text-blue-500 animate-bounce' : 'text-slate-300'}`} />
                {file ? <div className="text-sm font-bold text-slate-700 truncate px-4">{file.name}</div> : <div className="text-sm font-bold text-slate-400">點擊選擇 PDF</div>}
              </div>
            </div>

            <button type="submit" disabled={uploading || !file || !selectedSubject} className={`w-full py-4 rounded-2xl font-black text-lg text-white shadow-2xl transition-all flex items-center justify-center ${uploading || !file || !selectedSubject ? 'bg-slate-200 shadow-none' : 'bg-gradient-to-br from-blue-600 to-indigo-700 hover:scale-[1.02] active:scale-95 shadow-blue-200'}`}>
              {uploading ? <><Loader2 className="w-6 h-6 mr-3 animate-spin" />上傳中...</> : '開始上傳'}
            </button>
          </form>
        </div>

        {/* 列表區塊 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden min-h-[400px]">
            <table className="w-full text-left">
              <thead className="bg-slate-50/50 border-b border-slate-100">
                <tr>
                  <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest">文件詳情</th>
                  <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest text-center">單元範圍</th>
                  <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest">解析狀態</th>
                  <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {loadingDocs ? (
                  <tr><td colSpan="4" className="px-6 py-20 text-center"><Loader2 className="w-10 h-10 animate-spin text-blue-600 mx-auto mb-3" /><p className="text-slate-400 font-bold">載入中...</p></td></tr>
                ) : documents.length === 0 ? (
                  <tr><td colSpan="4" className="px-6 py-20 text-center"><div className="max-w-xs mx-auto space-y-3"><FileText className="w-16 h-16 text-slate-100 mx-auto" /><p className="text-slate-400 font-bold">尚無文件</p></div></td></tr>
                ) : documents.map(doc => (
                  <tr key={doc.id} className="group hover:bg-blue-50/30 transition-all">
                    <td className="px-6 py-5">
                      <div className="font-bold text-slate-800 truncate max-w-md flex items-center">
                        {doc.filename}
                        <span className={`ml-2 px-2 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-tighter ${doc.document_type === 'textbook' ? 'bg-blue-100 text-blue-600' : 'bg-indigo-100 text-indigo-600'}`}>
                          {doc.document_type === 'textbook' ? '教材' : '考古題'}
                        </span>
                      </div>
                      <div className="text-[10px] font-bold text-slate-300 mt-0.5">{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : ''}</div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex flex-col items-center">
                        {doc.units ? (
                          <div className="flex flex-col items-center">
                            <span className="text-[11px] font-black text-slate-700 bg-slate-100 px-2 py-1 rounded-md">
                              單元 {doc.units.unit_code}
                            </span>
                            <span className="text-[9px] text-slate-400 mt-1 truncate max-w-[120px]">{doc.units.name}</span>
                          </div>
                        ) : (
                          <span className="flex items-center text-[10px] font-black text-blue-500 bg-blue-50 px-2 py-1 rounded-md">
                            <Globe className="w-3 h-3 mr-1" /> 全域
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      {doc.status === 'indexed' ? (
                        <div className="flex items-center text-green-500 font-black text-xs"><CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> 已完成 ({doc.chunk_count || 0})</div>
                      ) : doc.status === 'processing' ? (
                        <div className="flex items-center text-blue-600 font-black text-xs animate-pulse"><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> 解析中...</div>
                      ) : doc.status === 'error' ? (
                        <div className="flex items-center text-red-500 font-black text-xs cursor-help" title={doc.error_message}><AlertCircle className="w-3.5 h-3.5 mr-1.5" /> 失敗</div>
                      ) : (
                        <span className="text-slate-300 font-bold text-xs">排隊中</span>
                      )}
                    </td>
                    <td className="px-6 py-5 text-right">
                      <button onClick={() => handleDelete(doc.id)} className="p-2 text-slate-200 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all opacity-0 group-hover:opacity-100"><Trash2 className="w-5 h-5" /></button>
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
