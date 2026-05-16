import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, FileText, Smartphone, Settings2, Loader2, Download, Zap, Sparkles } from 'lucide-react';
import { examAPI } from '../../services/api';

export default function HomePage() {
  const navigate = useNavigate();
  
  const [subjects, setSubjects] = useState([]);
  const [units, setUnits] = useState([]);
  
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedUnits, setSelectedUnits] = useState([]);
  const [questionCount, setQuestionCount] = useState(10);
  const [mode, setMode] = useState('quiz'); // 'quiz' or 'print'
  
  const [loading, setLoading] = useState(false);
  const [fetchingData, setFetchingData] = useState(true);
  const [loadingUnits, setLoadingUnits] = useState(false);

  useEffect(() => {
    examAPI.getSubjects()
      .then(data => {
        setSubjects(data.subjects || []);
        setFetchingData(false);
      })
      .catch(err => {
        console.error("Failed to load subjects:", err);
        setFetchingData(false);
      });
  }, []);

  useEffect(() => {
    if (selectedSubject) {
      setLoadingUnits(true);
      examAPI.getUnits(selectedSubject)
        .then(data => {
          setUnits(data.units || []);
          setSelectedUnits([]);
        })
        .catch(err => console.error("Failed to load units:", err))
        .finally(() => setLoadingUnits(false));
    } else {
      setUnits([]);
    }
  }, [selectedSubject]);

  const toggleUnit = (unitCode) => {
    if (selectedUnits.includes(unitCode)) {
      setSelectedUnits(selectedUnits.filter(u => u !== unitCode));
    } else {
      setSelectedUnits([...selectedUnits, unitCode]);
    }
  };

  const handleGenerate = async () => {
    if (!selectedSubject || selectedUnits.length === 0) {
      alert("請選擇科目與至少一個單元！");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        subject_id: selectedSubject,
        unit_codes: selectedUnits,
        // 如果是 print 模式，傳 0 代表後端自動偵測
        question_count: mode === 'print' ? 0 : parseInt(questionCount),
        mode: mode,
        difficulty: 3,
      };

      const res = await examAPI.generateExam(payload);

      if (mode === 'print') {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        // 嘗試從 Content-Disposition 取得檔名（可選）
        link.setAttribute('download', `考卷生成中.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        navigate('/quiz', { state: { examData: res.data } });
      }
    } catch (err) {
      console.error(err);
      alert("生成失敗，可能是 API 次數限制或教材不足。");
    } finally {
      setLoading(false);
    }
  };

  if (fetchingData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="relative text-center space-y-2">
          <button 
            onClick={() => navigate('/admin')}
            className="absolute right-0 -top-6 text-slate-400 hover:text-blue-500 text-xs font-medium transition-colors sm:static sm:mb-2"
          >
            進入後台管理 →
          </button>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            AI 智慧模擬考卷生成系統
          </h1>
          <p className="text-base sm:text-lg text-slate-600 italic font-medium">
            " 整合課本知識，複刻考古題風格 "
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden">
          <div className="p-6 sm:p-10 space-y-10">

            {/* Step 1: Subject */}
            <div className="space-y-4">
              <label className="flex items-center text-xl font-black text-slate-800">
                <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mr-3">1</div>
                選擇科目
              </label>
              <select
                className="w-full bg-slate-50 border-2 border-slate-100 text-slate-900 text-lg rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 block p-4 font-bold outline-none transition-all"
                value={selectedSubject}
                onChange={(e) => setSelectedSubject(e.target.value)}
              >
                <option value="">-- 請選擇科目 --</option>
                {subjects.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            {/* Step 2: Units */}
            {selectedSubject && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
                <label className="flex items-center text-xl font-black text-slate-800">
                  <div className="w-8 h-8 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center mr-3">2</div>
                  選擇範圍 (多選)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {loadingUnits ? (
                    <div className="col-span-full py-12 flex flex-col items-center justify-center text-slate-400 bg-slate-50 rounded-3xl border-2 border-dashed border-slate-100">
                      <Loader2 className="w-10 h-10 animate-spin mb-3 text-blue-500" />
                      <p className="font-bold">深度掃描單元中...</p>
                    </div>
                  ) : units.length === 0 ? (
                    <div className="col-span-full py-12 text-center text-slate-400 bg-slate-50 rounded-3xl border-2 border-dashed border-slate-100 font-bold">
                      此科目目前沒有可用教材
                    </div>
                  ) : (
                    units.map(unit => (
                      <button
                        key={unit.id}
                        onClick={() => toggleUnit(unit.unit_code)}
                        className={`p-5 rounded-2xl border-2 transition-all text-left relative overflow-hidden group ${
                          selectedUnits.includes(unit.unit_code) 
                            ? 'bg-blue-600 border-blue-600 text-white shadow-xl shadow-blue-200 scale-[1.02]' 
                            : 'bg-white border-slate-100 text-slate-700 hover:border-blue-200 hover:shadow-lg'
                        }`}
                      >
                        <div className={`text-[10px] font-black mb-1 uppercase tracking-widest ${selectedUnits.includes(unit.unit_code) ? 'text-blue-100' : 'text-blue-500'}`}>
                          Unit {unit.unit_code}
                        </div>
                        <div className="font-black text-sm leading-tight">
                          {unit.name}
                        </div>
                        {selectedUnits.includes(unit.unit_code) && (
                          <div className="absolute -right-2 -bottom-2 opacity-20">
                            <Zap className="w-12 h-12 text-white" />
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Config */}
            <div className="space-y-8 pt-8 border-t-2 border-slate-50">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                
                <div className="space-y-4">
                  <label className="block text-sm font-black text-slate-400 uppercase tracking-widest">輸出模式</label>
                  <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                    <button
                      className={`flex-1 flex items-center justify-center py-3 text-sm font-black rounded-xl transition-all ${
                        mode === 'quiz' ? 'bg-white shadow-xl text-blue-600 scale-[1.02]' : 'text-slate-400 hover:text-slate-600'
                      }`}
                      onClick={() => setMode('quiz')}
                    >
                      <Smartphone className="w-4 h-4 mr-2" />
                      手機刷題
                    </button>
                    <button
                      className={`flex-1 flex items-center justify-center py-3 text-sm font-black rounded-xl transition-all ${
                        mode === 'print' ? 'bg-white shadow-xl text-blue-600 scale-[1.02]' : 'text-slate-400 hover:text-slate-600'
                      }`}
                      onClick={() => setMode('print')}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      下載 Word
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  <label className="block text-sm font-black text-slate-400 uppercase tracking-widest">
                    {mode === 'print' ? '生成題數' : '練習題數'}
                  </label>
                  
                  {mode === 'print' ? (
                    <div className="bg-blue-50 p-4 rounded-2xl border border-blue-100 flex items-center animate-in zoom-in duration-300">
                      <Sparkles className="w-5 h-5 text-blue-500 mr-3 flex-shrink-0" />
                      <p className="text-xs text-blue-700 font-bold leading-relaxed">
                        <strong>自動偵測模式：</strong>系統將自動分析考古題範例，複刻其原始題數與排版架構。
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4 animate-in slide-in-from-right-4 duration-300">
                      <input 
                        type="range" min="5" max="50" step="5"
                        value={questionCount}
                        onChange={(e) => setQuestionCount(e.target.value)}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                      />
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-black text-slate-300 uppercase">Speed Run</span>
                        <span className="text-lg font-black text-blue-600">{questionCount} 題</span>
                        <span className="text-[10px] font-black text-slate-300 uppercase">Deep Dive</span>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            </div>

            {/* Submit */}
            <div className="pt-4">
              <button
                onClick={handleGenerate}
                disabled={loading || selectedUnits.length === 0}
                className={`w-full flex items-center justify-center py-5 px-8 border-none text-xl font-black rounded-2xl text-white transition-all shadow-2xl
                  ${loading || selectedUnits.length === 0 
                    ? 'bg-slate-200 shadow-none' 
                    : 'bg-gradient-to-br from-blue-600 to-indigo-700 hover:scale-[1.02] active:scale-95 shadow-blue-200'
                  }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-3 h-6 w-6 text-white" />
                    正在分析教材與模仿排版...
                  </>
                ) : mode === 'print' ? (
                  <>
                    <Download className="-ml-1 mr-3 h-6 w-6" />
                    立即生成考古題風格 Word
                  </>
                ) : (
                  <>
                    <Zap className="-ml-1 mr-3 h-6 w-6" />
                    開始線上刷題
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
        
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[100] flex items-center justify-center p-6">
          <div className="bg-white rounded-[40px] p-10 max-w-sm w-full shadow-2xl border border-white/20">
            <div className="relative mx-auto w-24 h-24 mb-8">
              <div className="absolute inset-0 border-4 border-blue-50 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
              <div className="absolute inset-4 bg-blue-600 rounded-full flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-white animate-pulse" />
              </div>
            </div>
            <h3 className="text-2xl font-black text-slate-900 mb-2">排版基因提取中</h3>
            <p className="text-slate-400 text-sm font-bold leading-relaxed">
              正在分析考古題的「題數」、「標題」與「命題口吻」...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
