import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, FileText, Smartphone, Settings2, Loader2, Download, Zap, Info, ShieldAlert, PhoneCall, HelpCircle } from 'lucide-react';
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
  const [loadingUnits, setLoadingUnits] = useState(false);

  // Initialize
  useEffect(() => {
    examAPI.getSubjects()
      .then(data => {
        setSubjects(data?.subjects || []);
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
      setLoadingUnits(true);
      examAPI.getUnits(selectedSubject)
        .then(data => {
          setUnits(data?.units || []);
          setSelectedUnits([]); // Reset units
        })
        .catch(err => {
          console.error("Failed to load units:", err);
        })
        .finally(() => {
          setLoadingUnits(false);
        });
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
      alert("【系統警示】請選擇欲檢定之科目與至少一個單元範圍！");
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
        // 使用更嚴謹的雙重保底機制封裝 Blob，強制帶入正確的 Word 檔案 MIME-Type
        const blob = res.data instanceof Blob 
          ? res.data 
          : new Blob([res.data], { type: 'application/msword' });
          
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `中華民國智慧e化模擬考卷_${Date.now()}.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url); // 釋放記憶體
      } else {
        // Mode Quiz: Redirect to QuizPage with data
        navigate('/quiz', { state: { examData: res.data } });
      }
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || "發生未知系統錯誤";
      alert(`【申辦失敗】系統出題失敗！詳細原因如下：\n${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  if (fetchingData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#d8d8d8] text-black">
        <div className="roc-bevel-outset p-8 max-w-sm text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#002d62] mx-auto mb-4" />
          <h2 className="font-bold text-lg font-mono">系統連線中...</h2>
          <p className="text-xs text-gray-600 mt-2">正在同步內政部教育考試評量檢定處伺服器資料，請稍候。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#d8d8d8] text-black pb-12 font-sans">
      
      {/* 1. 最上方閃爍紅色跑馬燈帶 */}
      <div className="roc-marquee-container">
        <span className="roc-marquee-text">
          ★★★ 歡迎蒞臨本局『智慧e化線上模擬考卷申辦服務系統』！本系統落實便民措施，推動服務e化作業，誠摯歡迎各界學子多加利用！ ★★★ 【重要公告】為提升系統效能，本平台將於每週日凌晨 02:00 至 04:00 進行資料庫備份與系統維護作業，屆時請勿點選申辦服務！ ★★★ 保護個人資料安全，防範網路詐騙！本局絕對不會以電話要求您前往 ATM 進行任何轉帳或設定變更操作，請務必提高警覺！ ★★★
        </span>
      </div>

      {/* 2. 雙橫幅 e化公部門機關 Logo & 標題 */}
      <header className="roc-navbar-blue py-6 px-4 shadow-md">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* 中華民國國旗感或金色標誌 */}
            <div className="w-12 h-12 bg-[#cc0000] border-2 border-yellow-400 flex items-center justify-center text-white text-2xl font-black rounded-none shadow-sm select-none">
              ★
            </div>
            <div>
              <div className="text-xs tracking-[0.3em] text-red-200 font-bold">
                EDUCATION EXAMINATION SERVICE PLATFORM
              </div>
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-wider text-white">
                教育部考試評量局・智慧e化線上學習便民系統
              </h1>
            </div>
          </div>
          
          <div className="mt-4 md:mt-0 flex space-x-3">
            <button 
              onClick={() => navigate('/admin')}
              className="roc-btn-glossy roc-btn-warning text-xs"
            >
              ⚙️ 進入後台系統管理專區 →
            </button>
          </div>
        </div>
      </header>

      {/* 3. 雙層宣導口號 */}
      <div className="bg-[#cc0000] text-yellow-300 py-2 text-center text-xs sm:text-sm font-black tracking-[0.4em] border-b-2 border-yellow-400 shadow-inner">
        【 落實便民措施 ‧ 全面推動服務e化作業 ‧ 共創學子美好前程 】
      </div>

      {/* 4. 主要雙欄式布局 */}
      <main className="max-w-6xl mx-auto mt-6 px-4 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* 左欄：行政宣導、注意事項、最新公告專區 (佔 4 欄) */}
        <section className="lg:col-span-4 space-y-6">
          
          {/* 最新公告專區 */}
          <div className="roc-bevel-outset p-4">
            <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-sm mb-3">
              ◎ 最新公告資訊專區
            </div>
            <div className="space-y-3">
              <div className="roc-announcement-belt">
                <span>【一般公告】本系統AI出題技術符合國家級標準，10秒快速產出試題！</span>
              </div>
              <div className="border-b border-gray-400 pb-2 bg-yellow-50 p-1.5 border-l-4 border-red-600">
                <span className="text-[10px] text-red-600 block font-black">2026-05-17 【最新版更資訊】</span>
                <a href="#" onClick={(e) => { 
                  e.preventDefault(); 
                  alert("【教育部考試評量檢定處 ‧ 智慧e化命題系統 - 重大版本更新】\n\n" + 
                        "為貫徹政府e化便民政策，提升學子複習效率，本平台已於 2026 年 5 月 17 日完成核心算力大改版：\n\n" +
                        "1. 🏛️【考古題 100% 精準克隆】：升級文件分析器，自動對齊上傳考古題之「總題數限制」、「大題結構（Sections）」與「頁首考生基本資料區」。\n" +
                        "2. ✍️【全面支援非選擇題型】：突破傳統選擇題限制，新增對「句子情境字彙填寫」、「中翻英填空式翻譯」等無選項題型的完美命題與解析驗證。\n" +
                        "3. 📄【高還原度實體 Word 匯出】：重構 Word 考卷電子檔排版，支援標楷體底線大題、選項橫向並列排版及強制分頁答案解析表。\n" +
                        "4. 💻【刷題介面智慧填空作答】：線上刷題專區智慧適配非選擇題，自動呈現「e化手寫作答模擬輸入區」，供學子打字模擬提交答案並觀看 AI 智慧詳解。\n\n" +
                        "※ 本局將持續推動便民e化措施，祝各位考生金榜題名！"); 
                }} className="text-red-700 underline text-xs font-black hover:text-blue-900 block leading-snug">
                  ★ 智慧e化命題系統重大版本更新成果暨非選擇題型與考古格式克隆功能上線說明
                </a>
              </div>
              <div className="border-b border-gray-400 pb-2">
                <span className="text-[10px] text-gray-500 block">2026-05-17</span>
                <a href="#" onClick={(e) => { e.preventDefault(); alert("請詳見內政部考試資訊手冊相關附件。"); }} className="text-blue-800 underline text-xs font-bold hover:text-red-600 block">
                  ★ 推動服務e化政策成果報告暨後續功能擴充計畫說明
                </a>
              </div>
              <div className="border-b border-gray-400 pb-2">
                <span className="text-[10px] text-gray-500 block">2026-05-10</span>
                <a href="#" onClick={(e) => { e.preventDefault(); alert("已整合。"); }} className="text-blue-800 underline text-xs font-bold hover:text-red-600 block">
                  ★ 智慧考卷生成系統整合大專院校最新學科範圍通知
                </a>
              </div>
              <div className="pb-1">
                <span className="text-[10px] text-gray-500 block">2026-04-25</span>
                <a href="#" onClick={(e) => { e.preventDefault(); alert("請勿於維護期間送出申請。"); }} className="text-blue-800 underline text-xs font-bold hover:text-red-600 block">
                  ★ 網路安全防護聲明暨定期資料維護配合宣導事項
                </a>
              </div>
            </div>
          </div>

          {/* 相同色微差公告框 (Same-Color Drift) */}
          <div className="roc-notice-drift">
            <div className="flex items-center text-[#ff0000] font-black text-sm mb-1">
              <ShieldAlert className="w-5 h-5 mr-1 flex-shrink-0" />
              【請務必詳閱以下規定事項】
            </div>
            <p className="text-xs text-red-800 leading-relaxed font-bold">
              為維護您的考試權益，請使用者在申辦智慧線上模擬測驗或下載 Word 電子檔考卷前，詳加確認所選範圍是否正確。
            </p>
            <div className="roc-notice-drift-inner">
              <p className="text-[11px] text-yellow-950 font-bold leading-normal">
                ※ 注意事項：<br/>
                1. 每次申請線上出題，系統將透過先進 AI 深度學習算力，即時分析並生成最具指標性之試題。<br/>
                2. 答題完畢後，本系統將立即提供詳細的「AI 詳解分析」，協助各位考生查漏補缺，請務必安心作答！
              </p>
            </div>
          </div>

          {/* 服務熱線與窗口 */}
          <div className="roc-bevel-outset p-4">
            <div className="bg-[#5a5a5a] text-white p-2 font-bold font-mono text-sm mb-3">
              ◎ 聯絡資訊與服務窗口
            </div>
            <div className="text-xs space-y-2 leading-relaxed">
              <p className="flex items-center font-bold">
                <PhoneCall className="w-4 h-4 mr-1 text-[#002d62]" />
                免付費服務熱線：0800-091-091
              </p>
              <p className="font-bold">
                承辦單位：考試評量局 資訊推動處 第四科
              </p>
              <p className="text-gray-600">
                服務時間：週一至週五 08:30 - 17:30<br/>
                (例假日及國定假日除外)
              </p>
              <div className="bg-gray-300 h-[1px] my-2"></div>
              <p className="text-blue-900 font-bold">
                【e化政府宣導網站連結】
              </p>
              <ul className="list-disc list-inside pl-1 text-[11px] space-y-1 text-blue-800">
                <li><a href="https://www.gov.tw" target="_blank" rel="noreferrer" className="underline hover:text-red-600">中華民國政府入口網</a></li>
                <li><a href="#" onClick={(e) => { e.preventDefault(); alert("本頁面為最優化e化宣導專區。"); }} className="underline hover:text-red-600">資訊化成果宣導資訊網</a></li>
              </ul>
            </div>
          </div>

        </section>

        {/* 右欄：e化線上模擬測驗申請表單 (佔 8 欄) */}
        <section className="lg:col-span-8">
          
          <div className="roc-bevel-outset p-6 space-y-6">
            
            {/* 標題與文字藝術師 */}
            <div className="text-center border-b-2 border-dashed border-gray-400 pb-4">
              <div className="roc-wordart-container">
                <span className="roc-wordart-main">智慧e化出題系統</span>
                <span className="roc-wordart-sub">【線上模擬測驗暨實體考卷申辦專區】</span>
              </div>
              <p className="text-xs text-gray-600 mt-2">
                請依循下列步驟完成申辦程序，本系統將於10秒內快速為您產出專屬的測驗試題！
              </p>
            </div>

            {/* 步驟一：選擇科目 */}
            <div className="roc-double-border space-y-3">
              <label className="flex items-center text-base font-bold text-[#002d62]">
                <BookOpen className="w-5 h-5 mr-2 text-[#cc0000]" />
                【第一階段：請選擇檢定學科種類】
              </label>
              <div className="relative">
                <select
                  className="w-full bg-white border-2 border-black text-black font-bold text-base block p-2.5 focus:bg-yellow-50 focus:border-[#002d62] outline-none"
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                >
                  <option value="">-- 請下拉選取欲檢定之科目 --</option>
                  {(subjects || []).map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 步驟二：選擇範圍 */}
            {selectedSubject && (
              <div className="roc-double-border space-y-3">
                <label className="flex items-center text-base font-bold text-[#002d62]">
                  <Settings2 className="w-5 h-5 mr-2 text-[#cc0000]" />
                  【第二階段：請選取考驗單元範圍 (可複選)】
                </label>
                
                {loadingUnits ? (
                  <div className="py-8 flex flex-col items-center justify-center text-gray-500 bg-white border border-gray-300">
                    <Loader2 className="w-8 h-8 animate-spin mb-2 text-[#002d62]" />
                    <p className="text-xs font-mono">範圍單元資料封包載入中，請稍候...</p>
                  </div>
                ) : (units || []).length === 0 ? (
                  <div className="py-8 text-center text-gray-600 bg-white border-2 border-dashed border-gray-400 font-bold">
                    ⚠️ 所選之科目目前尚無單元資料建置！
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                    {(units || []).map(unit => (
                      <button
                        key={unit.id}
                        onClick={() => toggleUnit(unit.unit_code)}
                        className={`p-3 border-2 text-left font-bold text-xs leading-snug transition-none flex flex-col justify-between h-20 ${
                          selectedUnits.includes(unit.unit_code) 
                            ? 'bg-[#002d62] border-black text-white shadow-inner' 
                            : 'bg-white border-gray-400 text-black hover:bg-yellow-50'
                        }`}
                      >
                        <div className={`text-[10px] font-mono border-b ${selectedUnits.includes(unit.unit_code) ? 'text-yellow-300 border-yellow-600' : 'text-blue-800 border-blue-200'} pb-0.5 mb-1`}>
                          ◎ 單元編號 {unit.unit_code}
                        </div>
                        <div className="line-clamp-2 text-[11px]">
                          {unit.name}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 步驟三：設定出題細節 */}
            <div className="roc-double-border">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* 模式選取 */}
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-[#002d62]">【第三階段：請選擇系統輸出模式】</label>
                  <div className="grid grid-cols-2 gap-2 bg-gray-300 p-1.5 border border-gray-400">
                    <button
                      className={`py-2 text-xs font-bold flex items-center justify-center ${
                        mode === 'quiz' 
                          ? 'bg-[#002d62] text-white border-2 border-black' 
                          : 'bg-white text-black border border-transparent hover:bg-yellow-50'
                      }`}
                      onClick={() => setMode('quiz')}
                    >
                      <Smartphone className="w-3.5 h-3.5 mr-1" />
                      行動載具智慧刷題
                    </button>
                    <button
                      className={`py-2 text-xs font-bold flex items-center justify-center ${
                        mode === 'print' 
                          ? 'bg-[#002d62] text-white border-2 border-black' 
                          : 'bg-white text-black border border-transparent hover:bg-yellow-50'
                      }`}
                      onClick={() => setMode('print')}
                    >
                      <FileText className="w-3.5 h-3.5 mr-1" />
                      下載 Word 電子考卷
                    </button>
                  </div>
                </div>

                {/* 題數拉條 */}
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-[#002d62] flex justify-between">
                    <span>【第四階段：請選取生成試題題數】</span>
                    <span className="text-[#cc0000] font-mono text-base font-black">{questionCount} 題</span>
                  </label>
                  <div className="p-1 bg-white border border-gray-400 flex items-center">
                    <input 
                      type="range" 
                      min="5" max="50" step="5"
                      value={questionCount}
                      onChange={(e) => setQuestionCount(e.target.value)}
                      className="w-full h-4 bg-gray-200 accent-[#002d62] cursor-pointer"
                    />
                  </div>
                  <div className="text-[10px] text-gray-500 font-mono text-right">
                    ※ 最少 5 題，最多 50 題。
                  </div>
                </div>

              </div>
            </div>

            {/* 提交申辦按鈕 */}
            <div className="pt-2">
              <button
                onClick={handleGenerate}
                disabled={loading || selectedUnits.length === 0}
                className={`w-full roc-btn-glossy py-4 px-6 text-xl tracking-widest ${
                  loading || selectedUnits.length === 0 
                    ? 'bg-gray-400 border-gray-500 text-gray-600 shadow-none cursor-not-allowed' 
                    : 'roc-btn-primary'
                }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-3 h-6 w-6 text-white" />
                    【系統出題中】AI 腦力激盪進行智慧組卷作業，請勿關閉視窗...
                  </>
                ) : mode === 'print' ? (
                  <>
                    <Download className="-ml-1 mr-2 h-6 w-6" />
                    核准申辦！一鍵下載 Microsoft Word 實體考卷電子檔
                  </>
                ) : (
                  <>
                    <Smartphone className="-ml-1 mr-2 h-6 w-6" />
                    核准申辦！立即啟動 e化線上模擬智慧測驗
                  </>
                )}
              </button>
            </div>

            {/* 承諾警示框 */}
            <div className="bg-[#eef4fa] border-l-4 border-[#002d62] p-3 text-xs leading-relaxed text-slate-700">
              <p className="font-bold text-[#002d62] flex items-center mb-1">
                <Info className="w-4 h-4 mr-1 text-[#002d62]" />
                【推動政府e化與便民服務承諾】
              </p>
              本項服務係屬考試評量局「智慧e化線上學習便民政策」之便民措施，旨在提供考生即時且客觀的模擬自我檢測機制。本系統所生成之試題係基於您上傳之教材庫進行科學化命題，祝您考試順利，邁向成功之路！
            </div>

          </div>
        </section>

      </main>

      {/* 5. 滿版申辦中 Loading 遮罩 */}
      {loading && (
        <div className="fixed inset-0 bg-black/70 z-[100] flex items-center justify-center p-6 text-center">
          <div className="bg-[#d4d0c8] border-4 border-white shadow-2xl p-6 max-w-md w-full text-black font-sans roc-bevel-outset">
            
            <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-sm mb-4 text-left flex justify-between items-center">
              <span>🖨️ 中華民國智慧出題系統 - 作業進行中</span>
              <span className="cursor-not-allowed">🗙</span>
            </div>

            <div className="relative mx-auto w-16 h-16 mb-4 flex items-center justify-center bg-white border border-gray-400">
              <Loader2 className="w-10 h-10 animate-spin text-[#002d62]" />
              <Zap className="absolute w-4 h-4 text-[#cc0000] animate-pulse" />
            </div>

            <h3 className="text-lg font-black text-black mb-2">【AI 智慧命題組卷作業進行中】</h3>
            
            <div className="text-left bg-white border border-gray-400 p-3 text-xs font-mono space-y-1 text-slate-700 max-h-36 overflow-y-auto mb-4 leading-normal">
              <p className="text-blue-800">→ [系統資訊] 成功連結教材與考古題資料庫...</p>
              <p className="text-blue-800">→ [AI 解析] 正在深度比對相關知識點範圍...</p>
              <p className="text-green-700">→ [命題進度] 根據風格提示詞，即時撰寫選擇題...</p>
              <p className="text-green-700">→ [題目核對] 產生詳細解析說明文字中...</p>
              <p className="text-orange-600 animate-pulse">→ [封包傳輸] 正在打包考卷封包，即將提供服務...</p>
            </div>

            <p className="text-xs text-red-700 font-bold leading-relaxed mb-2">
              ※ 作業時間約需 5-10 秒，命題完成後系統將自動引導至測驗專區，切勿重新整理或關閉瀏覽器。
            </p>
          </div>
        </div>
      )}

      {/* 6. 最下方版權與行政章 */}
      <footer className="max-w-6xl mx-auto mt-8 px-4 border-t border-gray-400 pt-4 text-center text-xs text-gray-600 space-y-1">
        <p className="font-bold">
          中華民國教育部考試評量局 版權所有 © 2026-2027 Government Examination Assessment Bureau. All Rights Reserved.
        </p>
        <p>
          本網站推薦使用 Google Chrome 或 Microsoft Edge 瀏覽器，並設定螢幕解析度為 1280x1024 以上以獲得最佳 e化便民瀏覽體驗。
        </p>
        <p>
          系統維護安全專線：(02) 2393-9999 分機 999 ‧ 諮詢信箱：service@geab.gov.tw
        </p>
      </footer>
    </div>
  );
}
