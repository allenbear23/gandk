import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Globe, RefreshCcw, Sparkles, BookOpen } from 'lucide-react';
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
  const [analyzingId, setAnalyzingId] = useState(null);
  const [errorInfo, setErrorInfo] = useState('');
  
  const fileInputRef = useRef(null);

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

  const loadDocs = async (subjectId) => {
    if (!subjectId) return;
    setLoadingDocs(true);
    setErrorInfo('');
    try {
      const data = await examAPI.getDocuments(subjectId);
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
      await examAPI.uploadDocument(file, selectedSubject, isGlobal ? null : selectedUnitId, documentType);
      alert("上傳成功！檔案已進入背景解析。");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTimeout(() => loadDocs(selectedSubject), 800);
    } catch (err) {
      alert("上傳失敗: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyzeStyle = async (subjectId, documentId) => {
    if (!window.confirm("將根據此考卷內容分析並更新該科目的『風格提示詞』，確定嗎？")) return;
    
    setAnalyzingId(documentId);
    try {
      const res = await examAPI.analyzeStyle(subjectId, documentId);
      alert("風格分析完成！\n\n產出的指令：\n" + res.style_prompt);
    } catch (err) {
      alert("分析失敗: " + (err.response?.data?.detail || err.message));
    } finally {
      setAnalyzingId(null);
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
          <h2 className="text-3xl font-black text-slate-800 tracking-tight">教材與風格管理</h2>
          <p className="text-slate-500 mt-1 font-medium">建立知識庫與定義考卷風格</p>
        </div>
        <button 
          onClick={() => loadDocs(selectedSubject)}
          className="flex items-center justify-center px-6 py-3 bg-white hover:bg-slate-50 text-slate-600 rounded-2xl text-sm font-black shadow-sm border border-slate-100 transition-all active:scale-95"
        >
          <RefreshCcw className={`w-4 h-4 mr-2 ${loadingDocs ? 'animate-spin' : ''}`} />
          重新整理列表
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* 上傳區塊 */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white p-6 rounded-[32px] shadow-xl border border-slate-100 h-fit space-y-6">
            <form onSubmit={handleUpload} className="space-y-5">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3">1. 選擇科目</label>
                <select className="w-full bg-slate-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl p-4 font-bold outline-none transition-all appearance-none cursor-pointer" value={selectedSubject} onChange={e => setSelectedSubject(e.target.value)} required>
                  <option value="">請選擇科目...</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3">2. 文件類型</label>
                <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                  <button type="button" onClick={() => setDocumentType('textbook')} className={`flex-1 py-3 text-sm rounded-xl font-black transition-all ${documentType === 'textbook' ? 'bg-white shadow-lg text-blue-600' : 'text-slate-400 hover:text-slate-600'}`}>教材 PDF</button>
                  <button type="button" onClick={() => setDocumentType('past_exam')} className={`flex-1 py-3 text-sm rounded-xl font-black transition-all ${documentType === 'past_exam' ? 'bg-white shadow-lg text-indigo-600' : 'text-slate-400 hover:text-slate-600'}`}>考古題 PDF</button>
                </div>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">3. 對應範圍</label>
                  <button type="button" onClick={() => setIsGlobal(!isGlobal)} className={`flex items-center px-3 py-1.5 rounded-xl text-[10px] font-black uppercase transition-all ${isGlobal ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' : 'bg-slate-200 text-slate-500 hover:bg-slate-300'}`}>
                    <Globe className="w-3.5 h-3.5 mr-1.5" />
                    {isGlobal ? '全域模式' : '指定單元'}
                  </button>
                </div>
                {!isGlobal ? (
                  <select className="w-full bg-slate-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl p-4 font-bold disabled:opacity-50 outline-none transition-all appearance-none cursor-pointer" value={selectedUnitId} onChange={e => setSelectedUnitId(e.target.value)} required={!isGlobal} disabled={!selectedSubject}>
                    <option value="">請選擇單元範圍...</option>
                    {units.map(u => <option key={u.id} value={u.id}>單元 {u.unit_code}: {u.name}</option>)}
                  </select>
                ) : (
                  <div className="p-5 bg-gradient-to-br from-blue-50 to-indigo-50 text-blue-700 text-xs rounded-2xl border border-blue-100 leading-relaxed font-bold shadow-inner">
                    <Sparkles className="w-4 h-4 mb-2 text-blue-500" />
                    <strong>全域模式已開啟：</strong>AI 將此文件視為整門學科的風格或背景知識參考。
                  </div>
                )}
              </div>

              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3">4. 選擇檔案</label>
                <div onClick={() => fileInputRef.current?.click()} className={`border-3 border-dashed rounded-[32px] p-10 text-center cursor-pointer transition-all ${file ? 'border-blue-400 bg-blue-50/50 shadow-inner' : 'border-slate-100 hover:border-blue-200 hover:bg-slate-50'}`}>
                  <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
                  <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center transition-all ${file ? 'bg-blue-500 text-white animate-bounce' : 'bg-slate-50 text-slate-300'}`}>
                    <Upload className="w-8 h-8" />
                  </div>
                  {file ? <div className="text-sm font-black text-slate-700 truncate px-4">{file.name}</div> : <div className="text-sm font-black text-slate-400">點擊或拖放 PDF</div>}
                </div>
              </div>

              <button type="submit" disabled={uploading || !file || !selectedSubject} className={`w-full py-5 rounded-2xl font-black text-xl text-white shadow-2xl transition-all flex items-center justify-center ${uploading || !file || !selectedSubject ? 'bg-slate-200 shadow-none cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-700 hover:scale-[1.02] hover:shadow-blue-300 active:scale-95'}`}>
                {uploading ? <><Loader2 className="w-6 h-6 mr-3 animate-spin" />正在上傳解析...</> : '上傳並開始分析'}
              </button>
            </form>
          </div>
        </div>

        {/* 列表區塊 */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-[32px] shadow-xl border border-slate-100 overflow-hidden min-h-[500px]">
            <div className="p-6 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
              <h3 className="font-black text-slate-800 flex items-center">
                <BookOpen className="w-5 h-5 mr-2 text-blue-600" />
                已上傳文件庫
              </h3>
              <span className="text-[10px] font-black text-slate-400 bg-white px-3 py-1 rounded-full border border-slate-100">{documents.length} 份文件</span>
            </div>
            
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-50/30">
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">文件詳情</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">單元範圍</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">狀態</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {loadingDocs ? (
                  <tr><td colSpan="4" className="px-6 py-32 text-center"><Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" /><p className="text-slate-400 font-black">正在同步文件庫...</p></td></tr>
                ) : documents.length === 0 ? (
                  <tr><td colSpan="4" className="px-6 py-32 text-center"><div className="max-w-xs mx-auto space-y-4 opacity-20"><FileText className="w-20 h-20 text-slate-800 mx-auto" /><p className="text-slate-800 font-black text-lg">目前尚無文件</p></div></td></tr>
                ) : documents.map(doc => (
                  <tr key={doc.id} className="group hover:bg-slate-50/80 transition-all">
                    <td className="px-6 py-6">
                      <div className="flex items-start">
                        <div className={`p-3 rounded-2xl mr-4 ${doc.document_type === 'textbook' ? 'bg-blue-50 text-blue-600' : 'bg-indigo-50 text-indigo-600'}`}>
                          <FileText className="w-6 h-6" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-black text-slate-800 truncate max-w-[200px] sm:max-w-xs text-base">
                            {doc.filename}
                          </div>
                          <div className="flex items-center mt-1.5 space-x-2">
                            <span className={`px-2 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-tighter ${doc.document_type === 'textbook' ? 'bg-blue-100 text-blue-700' : 'bg-indigo-100 text-indigo-700'}`}>
                              {doc.document_type === 'textbook' ? '教材' : '考古題'}
                            </span>
                            <span className="text-[10px] font-bold text-slate-300">
                              {new Date(doc.uploaded_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-6">
                      <div className="flex flex-col items-center">
                        {doc.units ? (
                          <div className="text-center">
                            <div className="text-xs font-black text-slate-700 bg-slate-100 px-3 py-1 rounded-xl inline-block">
                              單元 {doc.units.unit_code}
                            </div>
                            <div className="text-[10px] font-bold text-slate-400 mt-1.5 truncate max-w-[100px]">{doc.units.name}</div>
                          </div>
                        ) : (
                          <span className="flex items-center text-[10px] font-black text-blue-600 bg-blue-50 px-3 py-1 rounded-xl">
                            <Globe className="w-3.5 h-3.5 mr-1.5" /> 全域
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-6">
                      {doc.status === 'indexed' ? (
                        <div className="space-y-2">
                          <div className="flex items-center text-green-500 font-black text-xs">
                            <CheckCircle2 className="w-4 h-4 mr-2" /> 
                            已解析
                          </div>
                          {/* 考古題專屬按鈕 */}
                          {doc.document_type === 'past_exam' && (
                            <button 
                              onClick={() => handleAnalyzeStyle(selectedSubject, doc.id)}
                              disabled={analyzingId === doc.id}
                              className={`flex items-center px-3 py-1.5 rounded-xl text-[10px] font-black transition-all ${analyzingId === doc.id ? 'bg-slate-100 text-slate-400' : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:scale-105 shadow-lg shadow-indigo-100'}`}
                            >
                              {analyzingId === doc.id ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1.5" />}
                              提取風格
                            </button>
                          )}
                        </div>
                      ) : doc.status === 'processing' ? (
                        <div className="flex items-center text-blue-600 font-black text-xs animate-pulse">
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" /> 
                          處理中...
                        </div>
                      ) : (
                        <div className="flex items-center text-red-500 font-black text-xs">
                          <AlertCircle className="w-4 h-4 mr-2" /> 
                          失敗
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-6 text-right">
                      <button onClick={() => handleDelete(doc.id)} className="p-3 text-slate-200 hover:text-red-500 hover:bg-red-50 rounded-2xl transition-all opacity-0 group-hover:opacity-100">
                        <Trash2 className="w-6 h-6" />
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
