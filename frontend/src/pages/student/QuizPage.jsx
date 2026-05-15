import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle, Brain, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function QuizPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const examData = location.state?.examData;

  if (!examData || !examData.questions) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-800">
        <p className="mb-4">找不到測驗資料，請重新生成。</p>
        <button onClick={() => navigate('/')} className="text-blue-600 font-medium">返回首頁</button>
      </div>
    );
  }

  const questions = examData.questions;
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // userAnswers[index] = 'A'
  const [userAnswers, setUserAnswers] = useState({});
  const [showExplanation, setShowExplanation] = useState({});

  const currentQ = questions[currentIndex];
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
  const correctCount = Object.values(userAnswers).filter((ans, idx) => ans === questions[idx].answer).length;

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      {/* Top Navbar */}
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center justify-between">
          <button 
            onClick={() => {
               if(window.confirm("確定要放棄測驗返回首頁嗎？")) navigate('/');
            }}
            className="text-slate-500 hover:text-slate-900 flex items-center text-sm font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> 首頁
          </button>
          
          <div className="flex flex-col items-center">
            <span className="text-xs font-bold text-slate-400 tracking-wider uppercase mb-1">
              {examData.subject} • {examData.units.join(', ')}
            </span>
            <div className="text-sm font-semibold text-slate-800">
              {currentIndex + 1} / {questions.length}
            </div>
          </div>

          <div className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded-full">
            {correctCount} 分
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="h-1 bg-slate-200">
          <div 
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${(answeredCount / questions.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 max-w-3xl w-full mx-auto p-4 sm:p-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="space-y-6"
          >
            {/* Question Text */}
            <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-start mb-4">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center mr-4 mt-1">
                  {currentIndex + 1}
                </span>
                <h2 className="text-xl sm:text-2xl font-bold text-slate-800 leading-relaxed">
                  {currentQ.question}
                </h2>
              </div>
            </div>

            {/* Choices */}
            <div className="space-y-3">
              {currentQ.choices.map((choice) => {
                const isSelected = userAnswers[currentIndex] === choice.key;
                const isCorrectAns = currentQ.answer === choice.key;
                
                let stateClass = "bg-white border-slate-200 hover:border-blue-400 hover:bg-blue-50";
                
                if (isAnswered) {
                  if (isCorrectAns) {
                    stateClass = "bg-green-50 border-green-500 ring-1 ring-green-500 z-10";
                  } else if (isSelected) {
                    stateClass = "bg-red-50 border-red-500 ring-1 ring-red-500 z-10";
                  } else {
                    stateClass = "bg-white border-slate-200 opacity-60";
                  }
                }

                return (
                  <button
                    key={choice.key}
                    onClick={() => handleSelect(choice.key)}
                    disabled={isAnswered}
                    className={`w-full text-left p-4 sm:p-5 rounded-xl sm:rounded-2xl border-2 transition-all duration-200 flex items-center group relative overflow-hidden active:scale-[0.99] ${stateClass}`}
                  >
                    <div className={`flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center font-bold text-xs sm:text-sm mr-3 sm:mr-4 transition-colors
                      ${isAnswered && isCorrectAns ? 'bg-green-500 text-white' : 
                        isAnswered && isSelected ? 'bg-red-500 text-white' :
                        'bg-slate-100 text-slate-600 group-hover:bg-blue-200'}
                    `}>
                      {choice.key}
                    </div>
                    
                    <span className={`text-base sm:text-lg flex-1 ${isAnswered && (isCorrectAns || isSelected) ? 'font-medium' : ''}`}>
                      {choice.text}
                    </span>

                    {/* Result Icon */}
                    {isAnswered && isCorrectAns && (
                      <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6 text-green-500 absolute right-4 sm:right-5" />
                    )}
                    {isAnswered && isSelected && !isCorrectAns && (
                      <XCircle className="w-5 h-5 sm:w-6 sm:h-6 text-red-500 absolute right-4 sm:right-5" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* AI Explanation */}
            {showExplanation[currentIndex] && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-6 rounded-2xl border-l-4 ${isCorrect ? 'bg-green-50/80 border-green-400' : 'bg-orange-50/80 border-orange-400'}`}
              >
                <div className="flex items-center mb-3">
                  <Brain className={`w-5 h-5 mr-2 ${isCorrect ? 'text-green-600' : 'text-orange-600'}`} />
                  <h3 className={`font-bold ${isCorrect ? 'text-green-800' : 'text-orange-800'}`}>
                    AI 詳解
                  </h3>
                </div>
                <p className="text-slate-700 leading-relaxed text-lg">
                  {currentQ.explanation}
                </p>
              </motion.div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between items-center pt-8">
              <button
                onClick={handlePrev}
                disabled={currentIndex === 0}
                className="flex items-center px-5 py-3 rounded-xl font-medium text-slate-600 hover:bg-slate-200 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
              >
                <ChevronLeft className="w-5 h-5 mr-1" /> 上一題
              </button>
              
              <button
                onClick={handleNext}
                disabled={currentIndex === questions.length - 1}
                className="flex items-center px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold disabled:opacity-50 transition-colors shadow-lg shadow-slate-900/20"
              >
                下一題 <ChevronRight className="w-5 h-5 ml-1" />
              </button>
            </div>

          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
