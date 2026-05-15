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
  // 1. 終極方案：前端直傳 Supabase Storage (完全繞過 Vercel 4.5MB 限制)
  async uploadDocument(file, subjectId, unitId, documentType) {
    const bucket = 'exam-pdfs';
    const fileName = `${Date.now()}_${file.name}`;
    const filePath = `${subjectId}/${documentType}/${fileName}`;
    
    // 從環境變數讀取 (請確保已在 Vercel 設定)
    const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
    const ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

    if (!SUPABASE_URL || !ANON_KEY) {
      throw new Error("請先設定 VITE_SUPABASE_URL 與 VITE_SUPABASE_ANON_KEY 環境變數");
    }

    // Step A: 直接上傳到 Supabase Storage
    const storageUrl = `${SUPABASE_URL}/storage/v1/object/${bucket}/${filePath}`;
    const uploadRes = await fetch(storageUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${ANON_KEY}`,
        'apikey': ANON_KEY,
        'Content-Type': file.type,
        'x-upsert': 'true'
      },
      body: file
    });

    if (!uploadRes.ok) {
      const errorData = await uploadRes.json();
      throw new Error(`Storage 上傳失敗: ${errorData.message || uploadRes.statusText}`);
    }

    // Step B: 告知後端「檔案上傳好了，請開始解析」
    const res = await api.post('/admin/upload/notify', {
      subject_id: subjectId,
      unit_id: unitId,
      document_type: documentType,
      filename: file.name,
      storage_path: filePath
    });
    
    return res.data;
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
