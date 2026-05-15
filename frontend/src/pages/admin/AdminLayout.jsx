import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Database, Upload, ArrowLeft } from 'lucide-react';

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">
      
      {/* Sidebar (Desktop) / Bottom Nav (Mobile) */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 flex justify-around p-2 z-50 md:relative md:flex-col md:w-64 md:h-screen md:border-r md:border-t-0 md:p-4 md:space-y-2 shadow-[0_-4px_10px_rgba(0,0,0,0.05)] md:shadow-none">
        
        {/* Desktop Header */}
        <div className="hidden md:flex h-12 items-center px-4 mb-4">
          <h1 className="text-xl font-bold text-slate-800">後台管理</h1>
        </div>
        
        <Link
          to="/admin"
          className={`flex flex-col items-center justify-center p-2 rounded-xl transition-all md:flex-row md:justify-start md:px-4 md:py-3 ${
            location.pathname === '/admin' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-50'
          }`}
        >
          <Database className="w-6 h-6 md:w-5 md:h-5 md:mr-3" />
          <span className="text-[10px] mt-1 md:text-sm md:mt-0 font-medium">科目管理</span>
        </Link>

        <Link
          to="/admin/upload"
          className={`flex flex-col items-center justify-center p-2 rounded-xl transition-all md:flex-row md:justify-start md:px-4 md:py-3 ${
            location.pathname === '/admin/upload' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-50'
          }`}
        >
          <Upload className="w-6 h-6 md:w-5 md:h-5 md:mr-3" />
          <span className="text-[10px] mt-1 md:text-sm md:mt-0 font-medium">教材上傳</span>
        </Link>

        {/* Back to Home - Mobile Icons/Desktop Text */}
        <Link
          to="/"
          className="flex flex-col items-center justify-center p-2 rounded-xl text-slate-400 hover:bg-slate-50 md:flex-row md:justify-start md:px-4 md:py-3 md:mt-auto"
        >
          <ArrowLeft className="w-6 h-6 md:w-5 md:h-5 md:mr-3" />
          <span className="text-[10px] mt-1 md:text-sm md:mt-0 font-medium">回前台</span>
        </Link>
      </nav>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto pb-20 md:pb-0">
        <div className="p-4 sm:p-8 max-w-5xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
