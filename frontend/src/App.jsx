import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// Student Pages
import HomePage from './pages/student/HomePage';
import QuizPage from './pages/student/QuizPage';

// Admin Pages
import AdminLayout from './pages/admin/AdminLayout';
import SubjectPage from './pages/admin/SubjectPage';
import UploadPage from './pages/admin/UploadPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Student Routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/quiz" element={<QuizPage />} />

        {/* Admin Routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<SubjectPage />} />
          <Route path="upload" element={<UploadPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
