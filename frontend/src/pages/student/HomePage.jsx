import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, FileText, Smartphone, Settings2, Loader2, Download } from 'lucide-react';
import { examAPI } from '../../services/api';

export default function HomePage() {
  const navigate = useNavigate();
  
  // Form State
  const [subjects, setSubjects] = useState([]);
  const [units, setUnits] = useState([]);
  
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedUnits, setSelectedUnits] = useState([]);
  const [questionCount, setQuestionCount] = useState(10);
  const [mode, setMode] = useState('quiz'); // 'quiz' or 'print'
  
  // UI State
  const [loading, setLoading] = useState(false);
  const [fetchingData, setFetchingData] = useState(true);

  // Initialize
  useEffect(() => {
    examAPI.getSubjects()
      .then(data => {
        setSubjects(data.subjects);
        setFetchingData(false);
      })
      .catch(err => {
        console.error("Failed to load subjects:", err);
        setFetchingData(false);
      });
  }, []);

  // Fetch units when subject changes
  useEffect(() => {
    if (selectedSubject) {
      examAPI.getUnits(selectedSubject)
        .then(data => {
          setUnits(data.units);
          setSelectedUnits([]); // Reset units
        })
        .catch(console.error);
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
        question_count: parseInt(questionCount),
        mode: mode,
        difficulty: 3, // Default to medium
      };

      const res = await examAPI.generateExam(payload);

      if (mode === 'print') {
        // Handle DOCX Blob download
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        // The backend sends a filename in headers, but we can set a fallback here
        link.setAttribute('download', `模擬考卷_${Date.now()}.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        // Mode Quiz: Redirect to QuizPage with data
        navigate('/quiz', { state: { examData: res.data } });
      }
    } catch (err) {
      console.error(err);
      alert("生成失敗，請檢查後端是否正常運作。");
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
          <p className="text-base sm:text-lg text-slate-600">
            針對範圍精準打擊，10秒產出專屬試題
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden">
          <div className="p-6 sm:p-8 space-y-8">

            
            {/* Step 1: Subject */}
            <div className="space-y-4">
              <label className="flex items-center text-lg font-bold text-slate-800">
                <BookOpen className="w-5 h-5 mr-2 text-blue-500" />
                第一步：選擇科目
              </label>
              <select
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-lg rounded-xl focus:ring-blue-500 focus:border-blue-500 block p-3"
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
              <div className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-300">
                <label className="flex items-center text-lg font-bold text-slate-800">
                  <Settings2 className="w-5 h-5 mr-2 text-indigo-500" />
                  第二步：選擇範圍 (可複選)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {units.length === 0 ? (
                    <p className="text-slate-500 text-sm">此科目尚無單元資料</p>
                  ) : (
                    units.map(u => (
                      <div
                        key={u.id}
                        onClick={() => toggleUnit(u.unit_code)}
                        className={`cursor-pointer border rounded-xl p-4 transition-all duration-200 ${
                          selectedUnits.includes(u.unit_code) 
                            ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500' 
                            : 'bg-white border-slate-200 hover:border-indigo-300'
                        }`}
                      >
                        <div className="font-semibold text-slate-800">{u.unit_code}</div>
                        <div className="text-sm text-slate-500 mt-1">{u.name}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Configuration */}
            <div className="space-y-6 pt-4 border-t border-slate-100">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Mode Selection */}
                <div className="space-y-3">
                  <label className="block text-sm font-bold text-slate-700">輸出模式</label>
                  <div className="flex bg-slate-100 p-1 rounded-xl">
                    <button
                      className={`flex-1 flex items-center justify-center py-2.5 text-sm font-medium rounded-lg transition-colors ${
                        mode === 'quiz' ? 'bg-white shadow text-blue-700' : 'text-slate-500 hover:text-slate-700'
                      }`}
                      onClick={() => setMode('quiz')}
                    >
                      <Smartphone className="w-4 h-4 mr-2" />
                      手機刷題
                    </button>
                    <button
                      className={`flex-1 flex items-center justify-center py-2.5 text-sm font-medium rounded-lg transition-colors ${
                        mode === 'print' ? 'bg-white shadow text-blue-700' : 'text-slate-500 hover:text-slate-700'
                      }`}
                      onClick={() => setMode('print')}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      下載 Word
                    </button>
                  </div>
                </div>

                {/* Question Count */}
                <div className="space-y-3">
                  <label className="block text-sm font-bold text-slate-700">生成題數</label>
                  <input 
                    type="range" 
                    min="5" max="50" step="5"
                    value={questionCount}
                    onChange={(e) => setQuestionCount(e.target.value)}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="text-right text-sm font-medium text-blue-600">
                    {questionCount} 題
                  </div>
                </div>

              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-6">
              <button
                onClick={handleGenerate}
                disabled={loading || selectedUnits.length === 0}
                className={`w-full flex items-center justify-center py-4 px-8 border border-transparent text-lg font-bold rounded-xl text-white transition-all shadow-lg
                  ${loading || selectedUnits.length === 0 
                    ? 'bg-slate-400 cursor-not-allowed shadow-none' 
                    : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-indigo-500/25 active:scale-[0.98]'
                  }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
                    AI 腦力激盪中...
                  </>
                ) : mode === 'print' ? (
                  <>
                    <Download className="-ml-1 mr-3 h-5 w-5" />
                    一鍵生成 Word
                  </>
                ) : (
                  <>
                    <Smartphone className="-ml-1 mr-3 h-5 w-5" />
                    開始線上測驗
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
        
      </div>
    </div>
  );
}
