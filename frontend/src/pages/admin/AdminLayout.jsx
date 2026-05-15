import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Database, Upload, ArrowLeft } from 'lucide-react';

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <h1 className="text-xl font-bold text-slate-800">系統後台管理</h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <Link
            to="/admin"
            className={`flex items-center px-4 py-3 rounded-xl font-medium transition-colors ${
              location.pathname === '/admin' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Database className="w-5 h-5 mr-3" />
            科目與單元管理
          </Link>
          <Link
            to="/admin/upload"
            className={`flex items-center px-4 py-3 rounded-xl font-medium transition-colors ${
              location.pathname === '/admin/upload' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Upload className="w-5 h-5 mr-3" />
            教材上傳 (PDF)
          </Link>
        </nav>

        <div className="p-4 border-t border-slate-200">
          <Link
            to="/"
            className="flex items-center px-4 py-3 rounded-xl font-medium text-slate-500 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 mr-3" />
            返回前台首頁
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8 max-w-5xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
