import React, { useState, useEffect } from 'react';
import { Plus, BookOpen, Layers, Trash2, Loader2 } from 'lucide-react';
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

  const loadSubjects = () => {
    examAPI.getSubjects().then(data => setSubjects(data.subjects)).catch(console.error);
  };

  useEffect(() => {
    loadSubjects();
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject.id).then(data => setUnits(data.units)).catch(console.error);
    } else {
      setUnits([]);
    }
  }, [selectedSubject]);

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    if (!newSubject) return;
    try {
      await examAPI.createSubject(newSubject);
      setNewSubject('');
      loadSubjects();
    } catch (err) {
      alert('建立科目失敗');
    }
  };

  const handleCreateUnit = async (e) => {
    e.preventDefault();
    if (!newUnitCode || !newUnitName || !selectedSubject) return;
    try {
      await examAPI.createUnit(selectedSubject.id, newUnitName, newUnitCode);
      setNewUnitCode('');
      setNewUnitName('');
      // Reload units
      const data = await examAPI.getUnits(selectedSubject.id);
      setUnits(data.units);
    } catch (err) {
      alert('建立單元失敗');
    }
  };

  const handleDeleteSubject = async (e, subjectId) => {
    e.stopPropagation(); // 避免點擊垃圾桶時觸發選擇科目
    if (!window.confirm('確定要刪除此科目嗎？這將會連同底下的單元與文件一併刪除且無法復原。')) return;
    
    setIsDeleting(subjectId);
    try {
      await examAPI.deleteSubject(subjectId);
      if (selectedSubject?.id === subjectId) setSelectedSubject(null);
      loadSubjects();
    } catch (err) {
      alert('刪除失敗');
    } finally {
      setIsDeleting(null);
    }
  };

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-800">科目與單元管理</h2>
        <p className="text-slate-500 mt-1">管理供學生選擇的測驗範圍架構</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Subjects List */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold flex items-center">
              <BookOpen className="w-5 h-5 mr-2 text-blue-500" />
              所有科目
            </h3>
          </div>
          
          <form onSubmit={handleCreateSubject} className="flex gap-2 mb-6">
            <input 
              type="text" 
              placeholder="新科目名稱 (例如: 歷史)" 
              value={newSubject}
              onChange={e => setNewSubject(e.target.value)}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
            />
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center">
              <Plus className="w-4 h-4" />
            </button>
          </form>

          <div className="space-y-2">
            {subjects.length === 0 && <p className="text-slate-400 text-center py-4">尚無科目，請先建立</p>}
            {subjects.map(sub => (
              <div 
                key={sub.id} 
                onClick={() => setSelectedSubject(sub)}
                className={`group cursor-pointer p-4 rounded-xl border transition-colors flex justify-between items-center ${
                  selectedSubject?.id === sub.id ? 'bg-blue-50 border-blue-400 ring-1 ring-blue-400' : 'bg-white border-slate-100 hover:border-slate-300'
                }`}
              >
                <div className="font-bold text-slate-800">{sub.name}</div>
                <button
                  onClick={(e) => handleDeleteSubject(e, sub.id)}
                  className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  disabled={isDeleting === sub.id}
                >
                  {isDeleting === sub.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Units List */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 opacity-100 transition-opacity">
          {!selectedSubject ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 min-h-[300px]">
              <Layers className="w-12 h-12 mb-4 opacity-20" />
              <p>請先在左側選擇一個科目</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold flex items-center">
                  <Layers className="w-5 h-5 mr-2 text-indigo-500" />
                  {selectedSubject.name} - 單元列表
                </h3>
              </div>
              
              <form onSubmit={handleCreateUnit} className="flex gap-2 mb-6">
                <input 
                  type="text" 
                  placeholder="代碼 (如: 1-1)" 
                  value={newUnitCode}
                  onChange={e => setNewUnitCode(e.target.value)}
                  className="w-1/3 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
                />
                <input 
                  type="text" 
                  placeholder="單元名稱" 
                  value={newUnitName}
                  onChange={e => setNewUnitName(e.target.value)}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
                />
                <button type="submit" className="bg-indigo-600 text-white px-3 py-2 rounded-lg font-medium hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />
                </button>
              </form>

              <div className="space-y-2">
                {units.length === 0 && <p className="text-slate-400 text-center py-4">尚無單元</p>}
                {units.map(u => (
                  <div key={u.id} className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex items-center">
                    <span className="font-bold text-indigo-600 mr-3 min-w-[3rem]">{u.unit_code}</span>
                    <span className="text-slate-700">{u.name}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
