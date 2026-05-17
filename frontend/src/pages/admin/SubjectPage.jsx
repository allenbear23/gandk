import React, { useState, useEffect } from 'react';
import { Plus, BookOpen, Layers, Trash2, Loader2, Info } from 'lucide-react';
import { examAPI } from '../../services/api';

export default function SubjectPage() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [units, setUnits] = useState([]);
  const [isDeleting, setIsDeleting] = useState(null);

  // Forms
  const [newSubject, setNewSubject] = useState('');
  const [newUnitCode, setNewUnitCode] = useState('');
  const [newUnitName, setNewUnitName] = useState('');
  
  const [isCreatingSubject, setIsCreatingSubject] = useState(false);
  const [isCreatingUnit, setIsCreatingUnit] = useState(false);

  const loadSubjects = () => {
    examAPI.getSubjects().then(data => setSubjects(data?.subjects || [])).catch(console.error);
  };

  useEffect(() => {
    loadSubjects();
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject.id).then(data => setUnits(data?.units || [])).catch(console.error);
    } else {
      setUnits([]);
    }
  }, [selectedSubject]);

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    if (!newSubject) return;
    setIsCreatingSubject(true);
    try {
      await examAPI.createSubject(newSubject);
      setNewSubject('');
      loadSubjects();
    } catch (err) {
      alert('【建立失敗】新增科目失敗，請重試！');
    } finally {
      setIsCreatingSubject(false);
    }
  };

  const handleCreateUnit = async (e) => {
    e.preventDefault();
    if (!newUnitCode || !newUnitName || !selectedSubject) return;
    setIsCreatingUnit(true);
    try {
      await examAPI.createUnit(selectedSubject.id, newUnitName, newUnitCode);
      setNewUnitCode('');
      setNewUnitName('');
      const data = await examAPI.getUnits(selectedSubject.id);
      setUnits(data?.units || []);
    } catch (err) {
      alert('【建立失敗】新增單元失敗，請重試！');
    } finally {
      setIsCreatingUnit(false);
    }
  };

  const handleDeleteSubject = async (e, subjectId) => {
    e.stopPropagation();
    if (!window.confirm('【警告】確定要刪除此科目嗎？這將會連同底下的單元與文件一併刪除且無法復原。')) return;
    
    setIsDeleting(subjectId);
    try {
      await examAPI.deleteSubject(subjectId);
      if (selectedSubject?.id === subjectId) setSelectedSubject(null);
      loadSubjects();
    } catch (err) {
      alert('【刪除失敗】系統執行刪除作業失敗！');
    } finally {
      setIsDeleting(null);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* 標題頭部 */}
      <div className="border-b-2 border-dashed border-gray-400 pb-3">
        <h2 className="text-xl font-black font-mono text-[#002d62]">
          ◎ 科目暨範圍單元管理平台
        </h2>
        <p className="text-xs text-gray-600 mt-1 font-bold">
          本系統專供管理學科測驗之主科目與所屬細分單元，請妥善規劃以利 AI 線上智慧出題。
        </p>
      </div>

      {/* 主要管理雙欄 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* 左欄：科目清冊與新增 */}
        <div className="space-y-4">
          <div className="roc-double-border">
            <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-xs mb-3 flex items-center justify-between">
              <span>【第一階段：學科主科目建置清冊】</span>
              <BookOpen className="w-4 h-4 text-yellow-300" />
            </div>
            
            {/* 新增科目表單 */}
            <form onSubmit={handleCreateSubject} className="flex gap-2 mb-4">
              <input 
                type="text" 
                placeholder="請輸入欲新增之學科名稱 (如: 歷史)" 
                value={newSubject}
                onChange={e => setNewSubject(e.target.value)}
                className="flex-1 bg-white border border-gray-400 font-bold px-3 py-1.5 text-xs outline-none focus:bg-yellow-50 focus:border-black"
                style={{ borderRadius: '0px' }}
                required
              />
              <button 
                type="submit" 
                disabled={isCreatingSubject}
                className="roc-btn-glossy roc-btn-primary text-xs"
              >
                {isCreatingSubject ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5 mr-1" />}
                建置科目
              </button>
            </form>

            {/* 科目列表 */}
            <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
              {(subjects || []).length === 0 && (
                <p className="text-gray-500 text-center py-6 font-mono text-xs border border-gray-300 bg-white">
                  ⚠️ 目前尚未建置任何主學科，請先於上方建置！
                </p>
              )}
              {(subjects || []).map(sub => (
                <div 
                  key={sub.id} 
                  onClick={() => setSelectedSubject(sub)}
                  className={`group cursor-pointer p-3 border transition-none flex justify-between items-center ${
                    selectedSubject?.id === sub.id 
                      ? 'bg-[#eef4fa] border-[#002d62] font-black shadow-inner' 
                      : 'bg-white border-gray-300 hover:bg-yellow-50'
                  }`}
                  style={{ borderRadius: '0px' }}
                >
                  <div className="text-xs font-mono font-bold text-slate-800 flex items-center">
                    <span className="text-[#cc0000] mr-1.5">◎</span>
                    {sub.name}
                  </div>
                  
                  <button
                    onClick={(e) => handleDeleteSubject(e, sub.id)}
                    className="roc-btn-glossy roc-btn-danger text-[10px] py-1 px-2 opacity-0 group-hover:opacity-100"
                    disabled={isDeleting === sub.id}
                  >
                    {isDeleting === sub.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3 mr-1 inline" />}
                    廢止
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 右欄：單元管理與新增 */}
        <div className="space-y-4">
          <div className="roc-double-border min-h-[350px]">
            {!selectedSubject ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 py-16 text-center font-mono">
                <Layers className="w-12 h-12 mb-3 text-gray-400 animate-pulse" />
                <p className="text-xs font-bold">【提示】請先點選左側科目</p>
                <p className="text-[10px] text-gray-400 mt-1">選定科目後即可在此建置該科目的細部單元範圍。</p>
              </div>
            ) : (
              <>
                <div className="bg-[#5a5a5a] text-white p-2 font-bold font-mono text-xs mb-3 flex items-center justify-between">
                  <span>【第二階段：{selectedSubject.name} - 細分單元管理】</span>
                  <Layers className="w-4 h-4 text-yellow-300" />
                </div>
                
                {/* 新增單元表單 */}
                <form onSubmit={handleCreateUnit} className="flex gap-1 mb-4">
                  <input 
                    type="text" 
                    placeholder="序號 (如: 1-1)" 
                    value={newUnitCode}
                    onChange={e => setNewUnitCode(e.target.value)}
                    className="w-1/4 bg-white border border-gray-400 font-bold px-2 py-1.5 text-xs outline-none"
                    style={{ borderRadius: '0px' }}
                    required
                  />
                  <input 
                    type="text" 
                    placeholder="請輸入新增單元名稱" 
                    value={newUnitName}
                    onChange={e => setNewUnitName(e.target.value)}
                    className="flex-1 bg-white border border-gray-400 font-bold px-2 py-1.5 text-xs outline-none"
                    style={{ borderRadius: '0px' }}
                    required
                  />
                  <button type="submit" className="roc-btn-glossy roc-btn-success text-xs">
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    建置單元
                  </button>
                </form>

                {/* 單元清單表格 */}
                <table className="roc-table-classic text-xs font-mono">
                  <thead>
                    <tr>
                      <th className="w-1/4">單元代碼</th>
                      <th className="w-3/4">單元名稱</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(units || []).length === 0 ? (
                      <tr>
                        <td colSpan="2" className="text-center py-6 text-gray-500 font-bold">
                          ⚠️ 該學科目前尚未建置任何範圍單元！
                        </td>
                      </tr>
                    ) : (
                      (units || []).map(u => (
                        <tr key={u.id}>
                          <td className="font-bold text-center text-blue-900 bg-gray-100">{u.unit_code}</td>
                          <td className="text-left font-bold">{u.name}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </>
            )}
          </div>
        </div>

      </div>

      {/* 底部政策說明 */}
      <div className="bg-[#eef4fa] border-l-4 border-[#002d62] p-3 text-xs leading-relaxed text-slate-700">
        <p className="font-bold text-[#002d62] flex items-center mb-1">
          <Info className="w-4 h-4 mr-1 text-[#002d62]" />
          【學科架構申報須知說明】
        </p>
        此處建立之學科架構（如：歷史科底下有單元 1-1 台灣早期歷史）將成為前台「智慧e化出題系統」之依循指標。當學生選取特定單元時，AI 算力將只會讀取對應單元所屬的文件知識庫進行題目產出，請務必維持代碼與文件上傳之一致性，謝謝配合！
      </div>

    </div>
  );
}
