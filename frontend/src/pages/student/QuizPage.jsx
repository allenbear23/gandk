import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle, Brain, ArrowLeft, Zap, Info, Award, HelpCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function QuizPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const examData = location.state?.examData;
  const loading = location.state?.loading;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#d8d8d8] flex flex-col items-center justify-center text-black font-sans">
        <div className="roc-bevel-outset p-6 max-w-sm text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#002d62] mx-auto mb-4" />
          <h2 className="font-bold text-lg">系統出題作業中</h2>
          <p className="text-xs text-gray-600 mt-2">正在與內政部考試評量檢定處之 AI 命題系統進行即時連線，請勿中斷連線。</p>
        </div>
      </div>
    );
  }

  if (!examData || !examData.questions) {
    return (
      <div className="min-h-screen bg-[#d8d8d8] flex flex-col items-center justify-center text-black font-sans">
        <div className="roc-bevel-outset p-6 text-center max-w-sm">
          <p className="font-bold mb-4 text-[#cc0000]">【系統錯誤】找不到任何測驗資料，請重新申辦！</p>
          <button 
            onClick={() => navigate('/')} 
            className="roc-btn-glossy roc-btn-primary"
          >
            ← 返回首頁申辦專區
          </button>
        </div>
      </div>
    );
  }

  const questions = examData.questions;
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // userAnswers[index] = 'A'
  const [userAnswers, setUserAnswers] = useState({});
  const [showExplanation, setShowExplanation] = useState({});

  const currentQ = questions[currentIndex] || { question: '', choices: [], answer: '', explanation: '' };
  const isAnswered = !!userAnswers[currentIndex];
  const isCorrect = userAnswers[currentIndex] === currentQ.answer;

  const handleSelect = (key) => {
    if (isAnswered) return; // Only allow one selection per question
    setUserAnswers(prev => ({ ...prev, [currentIndex]: key }));
    setShowExplanation(prev => ({ ...prev, [currentIndex]: true }));
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    }
  };

  // Calculate Progress
  const answeredCount = Object.keys(userAnswers).length;
  const correctCount = Object.entries(userAnswers).filter(([idx, ans]) => ans === questions[idx]?.answer).length;
  // 換算分數 (e.g. 每題權重一致，滿分100分)
  const score = Math.round((correctCount / questions.length) * 100);

  return (
    <div className="min-h-screen bg-[#d8d8d8] text-black flex flex-col font-sans">
      
      {/* 頂部雙線藍色導覽列 */}
      <header className="roc-navbar-blue sticky top-0 z-10 shadow-md">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <button 
            onClick={() => {
               if(window.confirm("【確定退回】您目前測驗正在進行中，確定要中斷測驗並返回申辦首頁嗎？")) navigate('/');
            }}
            className="roc-btn-glossy roc-btn-warning text-xs"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> ← 放棄測驗返回首頁
          </button>
          
          <div className="flex flex-col items-center">
            <span className="text-[10px] font-bold text-yellow-300 tracking-widest uppercase mb-0.5">
              科別：{examData.subject} ‧ 範圍單元：{(examData.units || []).join(', ')}
            </span>
            <div className="text-sm font-black text-white font-mono">
              答題進度：第 {currentIndex + 1} 題 / 共 {questions.length} 題
            </div>
          </div>

          <div className="text-xs font-bold text-[#ffff00] bg-[#cc0000] border border-yellow-400 px-3 py-1 font-mono">
            ★ 目前得點：{correctCount} 題 (換算分數 {score} 分)
          </div>
        </div>
        
        {/* 行政表格感的高對比進度條 */}
        <div className="h-2 bg-[#808080] border-b border-black">
          <div 
            className="h-full bg-yellow-400 transition-all duration-300 shadow-inner"
            style={{ width: `${(answeredCount / (questions?.length || 1)) * 100}%` }}
          />
        </div>
      </header>

      {/* 國家級考試宣導標語 */}
      <div className="bg-yellow-100 text-yellow-900 border-b border-yellow-300 text-center py-1 text-[11px] font-bold">
        ※ 溫馨提醒：請慢慢作答，仔細閱讀試題，每一項選擇都很重要喔！祝各位學子順利過關！
      </div>

      {/* 主測驗視窗 */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 py-6 space-y-6">
        
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="space-y-6"
          >
            
            {/* 題目描述卡 (立體 outset Bevel) */}
            <div className="roc-bevel-outset p-6">
              <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-sm mb-4 flex justify-between items-center">
                <span>◎ 測驗試題主體說明專區</span>
                <span className="bg-red-600 text-white px-2 py-0.5 text-[10px] font-bold font-mono">第 {currentIndex + 1} 題</span>
              </div>
              
              <div className="flex items-start">
                <span className="flex-shrink-0 w-8 h-8 bg-[#cc0000] border-2 border-yellow-400 text-yellow-300 font-black flex items-center justify-center mr-4 select-none font-mono text-lg shadow-sm">
                  Q
                </span>
                <h2 className="text-lg sm:text-xl font-bold text-black leading-relaxed font-mono">
                  {currentQ.question}
                </h2>
              </div>
            </div>

            {/* 選項選擇列表 */}
            <div className="space-y-3">
              <div className="text-xs font-bold text-gray-700 pl-1">
                【請由下列選項中點選唯一正確答案】：
              </div>
              
              {currentQ.choices.map((choice) => {
                const isSelected = userAnswers[currentIndex] === choice.key;
                const isCorrectAns = currentQ.answer === choice.key;
                
                let stateClass = "bg-white border-gray-400 text-black hover:bg-yellow-50";
                let badgeClass = "bg-gray-200 text-black border border-gray-500";
                
                if (isAnswered) {
                  if (isCorrectAns) {
                    stateClass = "bg-green-100 text-green-950 border-green-600 font-bold ring-2 ring-green-600 shadow-inner";
                    badgeClass = "bg-green-600 text-white border border-green-700";
                  } else if (isSelected) {
                    stateClass = "bg-red-100 text-red-950 border-red-600 font-bold ring-2 ring-red-600 shadow-inner";
                    badgeClass = "bg-red-600 text-white border border-red-700";
                  } else {
                    stateClass = "bg-white border-gray-300 text-gray-400 opacity-60";
                    badgeClass = "bg-gray-100 text-gray-300 border border-gray-200";
                  }
                }

                return (
                  <button
                    key={choice.key}
                    onClick={() => handleSelect(choice.key)}
                    disabled={isAnswered}
                    className={`w-full text-left p-4 border-2 transition-none flex items-center relative overflow-hidden ${
                      isAnswered ? '' : 'active:translate-y-[1px] active:translate-x-[1px]'
                    } ${stateClass}`}
                    style={{ borderRadius: '0px' }}
                  >
                    {/* 選項編號 */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-none flex items-center justify-center font-black text-sm mr-4 ${badgeClass}`}>
                      {choice.key}
                    </div>
                    
                    <span className="text-base sm:text-lg flex-1 leading-normal font-mono pr-8">
                      {choice.text}
                    </span>

                    {/* 勾叉反饋圖示 */}
                    {isAnswered && isCorrectAns && (
                      <div className="absolute right-4 text-green-600 flex items-center font-bold text-xs font-mono">
                        <CheckCircle2 className="w-5 h-5 mr-1" /> 正確
                      </div>
                    )}
                    {isAnswered && isSelected && !isCorrectAns && (
                      <div className="absolute right-4 text-red-600 flex items-center font-bold text-xs font-mono">
                        <XCircle className="w-5 h-5 mr-1" /> 錯誤
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* AI 詳解 (Bevel 相同色微差 notice-drift) */}
            {showExplanation[currentIndex] && (
              <div className="roc-notice-drift space-y-3">
                <div className="bg-[#cc0000] text-yellow-300 p-2 font-bold font-mono text-xs flex items-center justify-between">
                  <div className="flex items-center">
                    <Brain className="w-4 h-4 mr-2" />
                    <span>【AI 智慧科別評量局 - 試題詳解分析專區】</span>
                  </div>
                  <span>核准日期：中華民國115年</span>
                </div>
                
                <div className="bg-white border border-yellow-400 p-4">
                  <div className="flex items-center mb-2">
                    <span className={`px-2 py-0.5 text-xs font-black text-white mr-2 ${isCorrect ? 'bg-green-600' : 'bg-red-600'}`}>
                      {isCorrect ? '★ 恭喜答對！' : '★ 尚待加強！'}
                    </span>
                    <span className="text-xs font-bold text-slate-700">
                      正確答案為：【{currentQ.answer}】
                    </span>
                  </div>
                  <p className="text-black text-sm sm:text-base leading-relaxed font-mono whitespace-pre-line">
                    {currentQ.explanation}
                  </p>
                </div>
                
                <div className="text-[10px] text-yellow-950 font-bold leading-normal text-right">
                  ※ 本解說係由本系統智慧教學e化算力產生，僅供學術模擬與複習參考。
                </div>
              </div>
            )}

            {/* 下方控制按鈕列 */}
            <div className="flex justify-between items-center pt-4 border-t border-gray-400">
              <button
                onClick={handlePrev}
                disabled={currentIndex === 0}
                className={`roc-btn-glossy ${
                  currentIndex === 0 
                    ? 'bg-gray-400 border-gray-500 text-gray-600 cursor-not-allowed shadow-none' 
                    : 'roc-btn-warning text-xs'
                }`}
              >
                <ChevronLeft className="w-4 h-4 mr-1 inline" /> 【返回上一題】
              </button>
              
              <button
                onClick={handleNext}
                disabled={currentIndex === questions.length - 1}
                className={`roc-btn-glossy ${
                  currentIndex === questions.length - 1 
                    ? 'bg-gray-400 border-gray-500 text-gray-600 cursor-not-allowed shadow-none' 
                    : 'roc-btn-primary text-xs'
                }`}
              >
                【前進下一題】 <ChevronRight className="w-4 h-4 ml-1 inline" />
              </button>
            </div>

          </motion.div>
        </AnimatePresence>

        {/* 成績統計與分析報告區 (只有在全部回答後，可以做為參考，但即使還沒回答完，也顯示在最下方做為政府系統特色) */}
        <div className="roc-bevel-outset p-4 space-y-3 mt-8">
          <div className="bg-[#5a5a5a] text-white p-2 font-bold font-mono text-xs">
            ◎ 學員模擬答題進度分析看板
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-bold font-mono">
            <div className="bg-white border border-gray-400 p-2">
              <div className="text-gray-500">總試題數</div>
              <div className="text-base text-black mt-1">{questions.length} 題</div>
            </div>
            <div className="bg-white border border-gray-400 p-2">
              <div className="text-gray-500">已作答數</div>
              <div className="text-base text-blue-800 mt-1">{answeredCount} 題</div>
            </div>
            <div className="bg-white border border-gray-400 p-2">
              <div className="text-gray-500">答對題數</div>
              <div className="text-base text-green-700 mt-1">{correctCount} 題</div>
            </div>
            <div className="bg-white border border-gray-400 p-2">
              <div className="text-gray-500">預估換算得分</div>
              <div className="text-base text-red-600 mt-1">{score} 分</div>
            </div>
          </div>
          {answeredCount === questions.length && (
            <div className="p-3 bg-green-50 border border-green-300 text-xs font-bold text-green-800 leading-normal text-center">
              🎉 恭喜！您已完成本次智慧e化線上模擬測驗全數題目！可點選上方按鈕返回首頁重新申辦其他檢定！
            </div>
          )}
        </div>

      </main>

      {/* 頁尾版權 */}
      <footer className="max-w-4xl mx-auto w-full mt-12 mb-8 border-t border-gray-400 pt-4 text-center text-[11px] text-gray-600 space-y-1">
        <p className="font-bold">
          中華民國教育部考試評量局 智慧型線上模擬學習專區 版權所有 © GEAB All Rights Reserved.
        </p>
        <p>
          如作答時發生異常，請備妥您的學員身分代碼並致電免付費服務專線：0800-091-091。
        </p>
      </footer>
    </div>
  );
}
