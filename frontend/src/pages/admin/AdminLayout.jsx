import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Database, Upload, ArrowLeft, ShieldAlert } from 'lucide-react';

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#d8d8d8] text-black flex flex-col font-sans">
      
      {/* 頂部主管機關章 header */}
      <header className="bg-[#cc0000] border-b-4 border-yellow-400 text-white py-3 px-4 shadow-sm select-none">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-[#002d62] border border-white flex items-center justify-center text-white font-black text-lg">
              ★
            </div>
            <div>
              <h1 className="text-lg md:text-xl font-black font-mono tracking-wider text-yellow-300">
                教育部考試評量局 ‧ 後台e化系統管理處
              </h1>
            </div>
          </div>
          <span className="text-[10px] text-red-200 font-bold hidden sm:inline">
            SECURE MANAGEMENT CONSOLE
          </span>
        </div>
      </header>

      {/* 主體雙選單佈局 */}
      <div className="flex-1 flex flex-col md:flex-row max-w-7xl w-full mx-auto p-4 gap-6">
        
        {/* 左側導覽列 (樹狀樹枝感雙線邊框) */}
        <nav className="bg-[#d4d0c8] border-3 outset p-4 space-y-3 md:w-64 md:h-fit roc-bevel-outset flex-shrink-0">
          
          <div className="bg-[#002d62] text-white p-2 font-bold font-mono text-xs text-center border border-black mb-3">
            ◎ 系統功能樹狀選單
          </div>
          
          <div className="space-y-1">
            <Link
              to="/admin"
              className={`w-full flex items-center px-3 py-2 text-xs font-bold border transition-none ${
                location.pathname === '/admin' 
                  ? 'bg-[#002d62] text-white border-black shadow-inner' 
                  : 'bg-white text-black border-gray-400 hover:bg-yellow-50'
              }`}
              style={{ borderRadius: '0px' }}
            >
              <Database className="w-4 h-4 mr-2 text-[#cc0000]" />
              <span>◎ 科目與範圍單元設定專區</span>
            </Link>

            <Link
              to="/admin/upload"
              className={`w-full flex items-center px-3 py-2 text-xs font-bold border transition-none ${
                location.pathname === '/admin/upload' 
                  ? 'bg-[#002d62] text-white border-black shadow-inner' 
                  : 'bg-white text-black border-gray-400 hover:bg-yellow-50'
              }`}
              style={{ borderRadius: '0px' }}
            >
              <Upload className="w-4 h-4 mr-2 text-[#cc0000]" />
              <span>◎ 教材與考古題PDF管理庫</span>
            </Link>
          </div>

          <div className="bg-gray-400 h-[1px] my-3"></div>

          {/* 回前台按鈕 */}
          <Link
            to="/"
            className="w-full flex items-center px-3 py-2 text-xs font-bold bg-[#ffffcc] text-[#cc0000] border border-gray-400 hover:bg-red-50 transition-none"
            style={{ borderRadius: '0px' }}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            <span>← 返回前台便民測驗首頁</span>
          </Link>

          {/* 後台安全宣告 */}
          <div className="bg-[#eef4fa] border-l-2 border-blue-800 p-2.5 text-[10px] leading-relaxed text-gray-700 font-mono mt-4">
            <div className="font-bold text-blue-900 flex items-center mb-1">
              <ShieldAlert className="w-3.5 h-3.5 mr-1" />
              【資安保護宣告】
            </div>
            本後台涉及學科維護與機密文件解析，非經授權之操作將受系統安全日誌稽核，請小心使用。
          </div>
        </nav>

        {/* 右側主要管理內容區 */}
        <main className="flex-1 roc-bevel-outset p-6 bg-[#f7f7f7] min-h-[500px]">
          <div className="max-w-4xl mx-auto">
            <Outlet />
          </div>
        </main>

      </div>

      {/* 頁尾 */}
      <footer className="w-full bg-[#5a5a5a] text-white text-center py-3 text-[10px] font-bold mt-auto border-t border-black">
        教育部考試評量局 ‧ 後台資訊維護中心 版權所有 © GEAB Admin Console
      </footer>
    </div>
  );
}
