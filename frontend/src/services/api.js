import axios from 'axios';

// 可以透過環境變數設定 API_URL，本地預設使用 8000
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const examAPI = {
  // --- Student API ---
  getSubjects: async () => {
    const res = await api.get('/admin/subjects');
    return res.data;
  },
  getUnits: async (subjectId) => {
    const res = await api.get(`/admin/subjects/${subjectId}/units`);
    return res.data;
  },
  generateExam: async (payload) => {
    const res = await api.post('/student/exam/generate', payload, {
      responseType: payload.mode === 'print' ? 'blob' : 'json'
    });
    return res;
  },

  // --- Admin API ---
  createSubject: async (name, description = '') => {
    const res = await api.post('/admin/subjects', { name, description });
    return res.data;
  },
  createUnit: async (subjectId, name, unitCode, description = '') => {
    const res = await api.post(`/admin/subjects/${subjectId}/units`, { name, unit_code: unitCode, description });
    return res.data;
  },
  // 1. 直接上傳到 Supabase Storage (繞過 Vercel 限制)
  async uploadToSupabase(file, subjectId, documentType) {
    const bucket = 'exam-pdfs';
    const fileName = `${Date.now()}_${file.name}`;
    const filePath = `${subjectId}/${documentType}/${fileName}`;
    
    // 從環境變數或 config 取得 (這裡我們先從 api 的 base 判斷或假設已設定)
    const STORAGE_URL = `https://goisieeomyorlakfzdmk.supabase.co/storage/v1/object/${bucket}/${filePath}`;
    
    // 注意：這裡需要 Supabase Key，通常前端會用 Anon Key
    // 為了安全與方便，我們維持使用 axios 傳給後端，但我們把超時拉到極限
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject_id', subjectId);
    return await api.post('/admin/upload', formData, {
      timeout: 120000 // 延長到 120 秒
    });
  },
  getDocuments: async (subjectId = '') => {
    const url = subjectId ? `/admin/documents?subject_id=${subjectId}` : '/admin/documents';
    const res = await api.get(url);
    return res.data;
  },
  getDocumentStatus: async (documentId) => {
    const res = await api.get(`/admin/documents/${documentId}/status`);
    return res.data;
  },
  deleteSubject: async (subjectId) => {
    const res = await api.delete(`/admin/subjects/${subjectId}`);
    return res.data;
  }
};
