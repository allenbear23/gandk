import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, File, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { examAPI } from '../../services/api';

export default function UploadPage() {
  const [subjects, setSubjects] = useState([]);
  const [units, setUnits] = useState([]);
  const [documents, setDocuments] = useState([]);
  
  // Form state
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedUnitCode, setSelectedUnitCode] = useState('');
  const [documentType, setDocumentType] = useState('textbook');
  const [file, setFile] = useState(null);
  
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const loadDocs = () => {
    examAPI.getDocuments().then(data => setDocuments(data.documents)).catch(console.error);
  };

  useEffect(() => {
    examAPI.getSubjects().then(data => setSubjects(data.subjects)).catch(console.error);
    loadDocs();
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject).then(data => setUnits(data.units)).catch(console.error);
    } else {
      setUnits([]);
    }
  }, [selectedSubject]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !selectedSubject || (!isGlobal && !selectedUnitCode)) {
      alert("請填寫完整資訊並選擇檔案");
      return;
    }
    
    setUploading(true);
    try {
      await examAPI.uploadDocument(file, selectedSubject, isGlobal ? null : selectedUnitCode, documentType);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadDocs();
    } catch (err) {
      alert("上傳失敗: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-800">教材 PDF 上傳</h2>
        <p className="text-slate-500 mt-1">上傳課本或考古題 PDF 供 AI 建立知識庫</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Upload Form */}
        <div className="lg:col-span-1 bg-white p-6 rounded-2xl shadow-sm border border-slate-200 h-fit">
          <form onSubmit={handleUpload} className="space-y-5">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">科目</label>
              <select 
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5"
                value={selectedSubject} onChange={e => { setSelectedSubject(e.target.value); setSelectedUnitCode(''); }} required
              >
                <option value="">選擇科目</option>
                {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">文件類型</label>
              <div className="flex bg-slate-100 p-1 rounded-lg">
                <button type="button" onClick={() => { setDocumentType('textbook'); setIsGlobal(false); }} className={`flex-1 py-1.5 text-sm rounded-md font-medium ${documentType === 'textbook' ? 'bg-white shadow text-blue-700' : 'text-slate-500'}`}>課本內容</button>
                <button type="button" onClick={() => setDocumentType('past_exam')} className={`flex-1 py-1.5 text-sm rounded-md font-medium ${documentType === 'past_exam' ? 'bg-white shadow text-indigo-700' : 'text-slate-500'}`}>考古題範例</button>
              </div>
            </div>

            {documentType === 'past_exam' && (
              <div className="flex items-center p-3 bg-blue-50 rounded-xl border border-blue-100">
                <input 
                  type="checkbox" 
                  id="global_check"
                  checked={isGlobal}
                  onChange={e => setIsGlobal(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <label htmlFor="global_check" className="ml-2 text-sm font-medium text-blue-800 cursor-pointer">
                  此為「全科目通用」參考資料
                </label>
              </div>
            )}

            {!isGlobal && (
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">對應單元</label>
                <select 
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5"
                  value={selectedUnitCode} onChange={e => setSelectedUnitCode(e.target.value)} required
                  disabled={!selectedSubject}
                >
                  <option value="">選擇單元</option>
                  {units.map(u => <option key={u.id} value={u.unit_code}>{u.unit_code} - {u.name}</option>)}
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">選擇 PDF</label>
              <input 
                type="file" accept=".pdf" ref={fileInputRef} required
                onChange={e => setFile(e.target.files[0])}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            <button 
              type="submit" disabled={uploading || !file}
              className="w-full flex items-center justify-center py-3 bg-slate-900 text-white rounded-xl font-bold transition-colors hover:bg-slate-800 disabled:bg-slate-400"
            >
              {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><UploadCloud className="w-5 h-5 mr-2" />上傳並解析</>}
            </button>
          </form>
        </div>

        {/* Document List */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold flex items-center">
              <File className="w-5 h-5 mr-2 text-slate-500" />
              已上傳文件狀態
            </h3>
            <button onClick={loadDocs} className="text-slate-400 hover:text-blue-500 transition-colors" title="重新整理">
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="py-3 px-4 rounded-tl-lg">檔名</th>
                  <th className="py-3 px-4">類型</th>
                  <th className="py-3 px-4">單元</th>
                  <th className="py-3 px-4 text-center rounded-tr-lg">狀態</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-medium text-slate-800 max-w-[200px] truncate" title={doc.filename}>{doc.filename}</td>
                    <td className="py-3 px-4">
                      {doc.document_type === 'textbook' ? (
                        <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-md text-xs font-bold">課本</span>
                      ) : (
                        <span className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded-md text-xs font-bold">考古題</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">{doc.unit_code}</td>
                    <td className="py-3 px-4 text-center">
                      {doc.status === 'pending' && <span className="inline-flex items-center text-slate-500"><Loader2 className="w-4 h-4 mr-1 animate-spin" /> 等待中</span>}
                      {doc.status === 'processing' && <span className="inline-flex items-center text-blue-500"><Loader2 className="w-4 h-4 mr-1 animate-spin" /> 解析中</span>}
                      {doc.status === 'indexed' && <span className="inline-flex items-center text-green-600"><CheckCircle className="w-4 h-4 mr-1" /> 已完成 ({doc.chunk_count} 段)</span>}
                      {doc.status === 'error' && <span className="inline-flex items-center text-red-500" title={doc.error_message}><XCircle className="w-4 h-4 mr-1" /> 失敗</span>}
                    </td>
                  </tr>
                ))}
                {documents.length === 0 && (
                  <tr>
                    <td colSpan="4" className="py-8 text-center text-slate-400">尚無上傳紀錄</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
