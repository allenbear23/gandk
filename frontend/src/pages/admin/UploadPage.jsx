import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Globe, RefreshCcw, Sparkles, BookOpen, Info } from 'lucide-react';
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
      alert("【系統警示】請選擇欲上傳之 PDF 檔案與對應科目！");
      return;
    }

    if (!isGlobal && !selectedUnitId) {
      alert("【系統警示】請指定本文件對應之範圍單元，或者開啟『全域教材』模式！");
      return;
    }
    
    setUploading(true);
    try {
      await examAPI.uploadDocument(file, selectedSubject, isGlobal ? null : selectedUnitId, documentType);
      alert("【上傳成功】檔案已成功傳輸至後台！系統已自動啟動背景解析作業。");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTimeout(() => loadDocs(selectedSubject), 800);
    } catch (err) {
      alert("【上傳失敗】系統寫入檔案失敗: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyzeStyle = async (subjectId, documentId) => {
    if (!window.confirm("【確定執行】將根據此考古題內容進行 AI 風格特徵分析，並更新更新該科目的『出題風格提示詞』，確定嗎？")) return;
    
    setAnalyzingId(documentId);
    try {
      const res = await examAPI.analyzeStyle(subjectId, documentId);
      alert("【分析完成】風格特徵提取成功！\n\n系統產出之風格指令如下：\n" + res.style_prompt);
    } catch (err) {
      alert("【分析失敗】AI 提取風格失敗: " + (err.response?.data?.detail || err.message));
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("【警告】確定要從系統中永久移除此文件資料嗎？此操作將無法復原。")) return;
    try {
      await examAPI.deleteDocument(id);
      loadDocs(selectedSubject);
    } catch (err) {
      alert("【刪除失敗】移除檔案作業失敗！");
    }
  };

  return (
    <div className="space-y-6">
      
      {/* 標題與重新整理 */}
      <div className="border-b-2 border-dashed border-gray-400 pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-black font-mono text-[#002d62]">
            ◎ 教材庫資料上傳暨考試風格提示分析專區
          </h2>
          <p className="text-xs text-gray-600 mt-1 font-bold">
            請在此申報上傳參考教材 PDF 或是考古題 PDF。考古題解析後可進行「出題風格提取」，作為 AI 出題的依據。
          </p>
        </div>
        <button 
          onClick={() => loadDocs(selectedSubject)}
          className="roc-btn-glossy roc-btn-warning text-xs"
        >
          <RefreshCcw className={`w-3.5 h-3.5 mr-1 inline ${loadingDocs ? 'animate-spin' : ''}`} />
          同步重整文件庫列表
        </button>
      </div>

      {/* 主要工作雙欄 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* 左欄：上傳與設定表單 (佔 5 欄) */}
        <div className="lg:col-span-5">
          <div className="roc-double-border space-y-4">
            <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-xs mb-1 flex items-center justify-between">
              <span>【教材/考古題 PDF 電子申報區】</span>
              <Upload className="w-4 h-4 text-yellow-300" />
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              
              {/* 科目 */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-blue-900">
                  【第一核對：請選取主學科名稱】
                </label>
                <select 
                  className="w-full bg-white border border-gray-400 font-bold p-2 text-xs outline-none focus:bg-yellow-50 focus:border-black cursor-pointer" 
                  value={selectedSubject} 
                  onChange={e => setSelectedSubject(e.target.value)} 
                  style={{ borderRadius: '0px' }}
                  required
                >
                  <option value="">-- 請選取欲申報之學科 --</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>

              {/* 性質 */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-blue-900">
                  【第二核對：請申報上傳文件性質】
                </label>
                <div className="grid grid-cols-2 gap-1 bg-gray-300 p-1 border border-gray-400">
                  <button 
                    type="button" 
                    onClick={() => setDocumentType('textbook')} 
                    className={`py-2 text-xs font-bold ${documentType === 'textbook' ? 'bg-[#002d62] text-white border border-black' : 'bg-white text-black hover:bg-yellow-50'}`}
                    style={{ borderRadius: '0px' }}
                  >
                    學科專用教材 PDF
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setDocumentType('past_exam')} 
                    className={`py-2 text-xs font-bold ${documentType === 'past_exam' ? 'bg-[#002d62] text-white border border-black' : 'bg-white text-black hover:bg-yellow-50'}`}
                    style={{ borderRadius: '0px' }}
                  >
                    歷屆考古題 PDF
                  </button>
                </div>
              </div>

              {/* 範圍 */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-blue-900">
                    【第三核對：指定考核單元範圍】
                  </label>
                  <button 
                    type="button" 
                    onClick={() => setIsGlobal(!isGlobal)} 
                    className={`px-2 py-0.5 text-[10px] font-bold border ${isGlobal ? 'bg-[#cc0000] text-white border-black' : 'bg-white text-black border-gray-400'}`}
                    style={{ borderRadius: '0px' }}
                  >
                    {isGlobal ? '★ 切換為單元考核' : '★ 切換為全域教材'}
                  </button>
                </div>
                {!isGlobal ? (
                  <select 
                    className="w-full bg-white border border-gray-400 font-bold p-2 text-xs outline-none focus:bg-yellow-50 disabled:opacity-50 cursor-pointer" 
                    value={selectedUnitId} 
                    onChange={e => setSelectedUnitId(e.target.value)} 
                    required={!isGlobal} 
                    disabled={!selectedSubject}
                    style={{ borderRadius: '0px' }}
                  >
                    <option value="">-- 請選取指定單元範圍 --</option>
                    {units.map(u => <option key={u.id} value={u.id}>單元 {u.unit_code}: {u.name}</option>)}
                  </select>
                ) : (
                  <div className="p-3 bg-yellow-100 text-yellow-950 text-xs border border-yellow-300 font-bold leading-normal">
                    💡 <strong>全域模式宣告：</strong><br/>
                    本文件將被視為整門學科的「全域背景資料」或「出題風格參考」，出題時將不侷限於單一單元。
                  </div>
                )}
              </div>

              {/* 選擇檔案 */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-blue-900">
                  【第四核對：選擇欲上傳之 PDF 電子文件】
                </label>
                <div 
                  onClick={() => fileInputRef.current?.click()} 
                  className={`border-2 border-dashed p-6 text-center cursor-pointer ${file ? 'border-[#002d62] bg-[#eef4fa]' : 'border-gray-400 bg-white hover:bg-yellow-50'}`}
                  style={{ borderRadius: '0px' }}
                >
                  <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
                  <Upload className="w-8 h-8 mx-auto mb-2 text-[#808080]" />
                  {file ? (
                    <div className="text-xs font-bold text-green-800 truncate px-2">
                      ✔ 檔案已就位：{file.name}
                    </div>
                  ) : (
                    <div className="text-[11px] text-gray-500 font-mono">
                      [點擊選取或拖曳 PDF 檔案至此]
                    </div>
                  )}
                </div>
              </div>

              <button 
                type="submit" 
                disabled={uploading || !file || !selectedSubject} 
                className={`w-full roc-btn-glossy py-3 text-sm tracking-wide ${uploading || !file || !selectedSubject ? 'bg-gray-400 border-gray-500 text-gray-600 cursor-not-allowed shadow-none' : 'roc-btn-primary'}`}
              >
                {uploading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin inline" />電子文件傳輸中...</>
                ) : (
                  '確認無誤！上傳檔案並啟動背景解析作業'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* 右欄：已上傳文件庫表格清冊 (佔 7 欄) */}
        <div className="lg:col-span-7">
          <div className="roc-double-border space-y-3 min-h-[480px]">
            <div className="bg-[#5a5a5a] text-white p-2 font-bold font-mono text-xs flex items-center justify-between">
              <span>【目前已上傳建置之學科文件清冊庫】</span>
              <span className="bg-white text-black px-2 py-0.5 text-[9px] font-bold font-mono">
                清單總數：{documents.length} 份
              </span>
            </div>
            
            <div className="overflow-x-auto">
              <table className="roc-table-classic text-xs font-mono">
                <thead>
                  <tr>
                    <th className="w-2/5">文件名稱與性質</th>
                    <th className="w-1/5 text-center">單元範圍</th>
                    <th className="w-1/5">背景解析狀態</th>
                    <th className="w-1/5 text-right">管理操作</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingDocs ? (
                    <tr>
                      <td colSpan="4" className="px-6 py-20 text-center">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
                        <p className="text-gray-500 font-bold">同步文件清冊資料中...</p>
                      </td>
                    </tr>
                  ) : documents.length === 0 ? (
                    <tr>
                      <td colSpan="4" className="px-6 py-24 text-center text-gray-500 font-bold">
                        ⚠️ 本學科目前尚無任何上傳文件，請由左側進行申報！
                      </td>
                    </tr>
                  ) : (
                    documents.map(doc => (
                      <tr key={doc.id}>
                        <td className="text-left font-bold py-3">
                          <div className="truncate max-w-[180px] text-blue-900" title={doc.filename}>
                            ◎ {doc.filename}
                          </div>
                          <div className="mt-1">
                            <span className={`px-1 text-[9px] font-bold text-white ${doc.document_type === 'textbook' ? 'bg-[#002d62]' : 'bg-[#cc0000]'}`}>
                              {doc.document_type === 'textbook' ? '參考教材' : '歷屆考古題'}
                            </span>
                            <span className="text-[9px] text-gray-500 ml-2 font-normal">
                              申報日:{new Date(doc.uploaded_at).toLocaleDateString()}
                            </span>
                          </div>
                        </td>
                        <td className="text-center font-bold">
                          {doc.units ? (
                            <span className="bg-gray-200 border border-gray-400 px-1.5 py-0.5 text-[10px] inline-block">
                              單元 {doc.units.unit_code}
                            </span>
                          ) : (
                            <span className="bg-blue-100 text-blue-800 border border-blue-300 px-1.5 py-0.5 text-[10px] inline-flex items-center">
                              <Globe className="w-3 h-3 mr-1" /> 全域
                            </span>
                          )}
                        </td>
                        <td className="font-bold">
                          {doc.status === 'indexed' ? (
                            <div className="space-y-1">
                              <div className="flex items-center text-green-700">
                                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> 已解析
                              </div>
                              {doc.document_type === 'past_exam' && (
                                <button 
                                  onClick={() => handleAnalyzeStyle(selectedSubject, doc.id)}
                                  disabled={analyzingId === doc.id}
                                  className="roc-btn-glossy roc-btn-success text-[9px] py-0.5 px-1.5"
                                >
                                  {analyzingId === doc.id ? <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin inline" /> : <Sparkles className="w-2.5 h-2.5 mr-1 inline" />}
                                  提取風格
                                </button>
                              )}
                            </div>
                          ) : doc.status === 'processing' ? (
                            <div className="flex items-center text-blue-600 animate-pulse">
                              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> 解析中
                            </div>
                          ) : (
                            <div className="flex items-center text-red-600">
                              <AlertCircle className="w-3.5 h-3.5 mr-1" /> 失敗
                            </div>
                          )}
                        </td>
                        <td className="text-right">
                          <button 
                            onClick={() => handleDelete(doc.id)} 
                            className="roc-btn-glossy roc-btn-danger text-[10px] py-1 px-2"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      {/* 底部須知 */}
      <div className="bg-[#eef4fa] border-l-4 border-[#002d62] p-3 text-xs leading-relaxed text-slate-700">
        <p className="font-bold text-[#002d62] flex items-center mb-1">
          <Info className="w-4 h-4 mr-1 text-[#002d62]" />
          【教材管理與AI出題風格須知】
        </p>
        1. <strong>參考教材：</strong>做為 AI 生成題目與解析時的背景知識點，以確保命題不超綱且符合專業水準。<br/>
        2. <strong>歷屆考古題：</strong>提供給 AI 作為出題「風格特徵」之學習對象。您上傳考古題並點選「提取風格」後，系統將分析該考卷的命題難度、題型偏好（如：情境題、記憶題、細節題）並記錄。當考生進行模擬測驗時，AI 將完美模擬該考古題風格進行命題組卷。
      </div>

    </div>
  );
}
