import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, Loader2, Home, Layers, Upload, X
} from 'lucide-react';
import type { House, Announcement } from '../types';
import { useNavigate } from 'react-router-dom';

const AdminPortal: React.FC = () => {
  const navigate = useNavigate();
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [uploading, setUploading] = useState(false);
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [previewData, setPreviewData] = useState<{title: string, desc: string, houses: House[]} | null>(null);
  
  // States for upload process
  const [pendingFiles, setPendingFiles] = useState<FileList | null>(null);
  const [isConfirmingUpload, setIsConfirmingUpload] = useState(false);
  const [userApiKey, setUserApiKey] = useState(localStorage.getItem('gemini_api_key') || '');
  const [parsingStatus, setParsingStatus] = useState('');

  useEffect(() => {
    if (isAdminAuthenticated) {
      fetchAnnouncements();
    }
  }, [isAdminAuthenticated]);

  const fetchAnnouncements = async () => {
    try {
      const res = await axios.get('/api/announcements');
      setAnnouncements(res.data.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    }
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminPassword) {
      setIsAdminAuthenticated(true);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setPendingFiles(e.target.files);
    setIsConfirmingUpload(true);
  };

  const onFileUpload = async () => {
    if (!pendingFiles) return;
    setUploading(true);
    setParsingStatus('문서 분석 중...');
    const jobId = Math.random().toString(36).substring(7);

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/admin/status/${jobId}`);
        
        if (res.data.result) {
          clearInterval(pollInterval);
          setPreviewData({
            title: res.data.result.announcement_title,
            desc: res.data.result.announcement_description,
            houses: res.data.result.houses
          });
          setUploading(false);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);

    const formData = new FormData();
    formData.append('file', pendingFiles[0]);
    
    try {
      await axios.post('/api/admin/upload', formData, {
        headers: {
          'x-job-id': jobId,
          'x-gemini-key': userApiKey,
          'x-admin-password': adminPassword
        }
      });
    } catch (err) {
      console.error('Upload failed:', err);
      clearInterval(pollInterval);
      setUploading(false);
    }
  };

  const onFinalSave = async () => {
    if (!previewData) return;
    setUploading(true);
    try {
      await axios.post('/api/admin/save', {
        announcement_title: previewData.title,
        announcement_description: previewData.desc,
        houses: previewData.houses
      }, {
        headers: { 'x-admin-password': adminPassword }
      });
      setPreviewData(null);
      fetchAnnouncements();
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const deleteAnnouncement = async (id: string) => {
     if (!window.confirm('정말 삭제하시겠습니까?')) return;
     try {
       await axios.delete(`/api/admin/announcements/${id}`, {
         headers: { 'x-admin-password': adminPassword }
       });
       fetchAnnouncements();
     } catch (err) {
       console.error('Delete failed:', err);
     }
  };

  if (!isAdminAuthenticated) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-900 px-4">
        <div className="w-full max-w-md bg-white p-8 rounded-[2rem] shadow-2xl">
          <div className="flex flex-col items-center mb-8">
             <div className="w-16 h-16 bg-amber-400 rounded-3xl flex items-center justify-center mb-4">
               <Layers className="w-8 h-8 text-slate-900" />
             </div>
             <h1 className="text-2xl font-black text-slate-800 tracking-tight">Admin Portal</h1>
             <p className="text-sm text-slate-400 font-medium">관리자 전용 페이지입니다.</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
             <input 
               type="password" 
               placeholder="ADMIN PASSWORD" 
               className="w-full px-6 py-4 bg-slate-100 rounded-2xl font-bold focus:ring-2 focus:ring-amber-400 outline-none"
               value={adminPassword}
               onChange={(e) => setAdminPassword(e.target.value)}
             />
             <button className="w-full py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all">
               입장하기
             </button>
             <button 
               type="button"
               onClick={() => navigate('/')}
               className="w-full py-2 text-slate-400 font-bold hover:text-slate-600"
             >
               메인 페이지로 돌아가기
             </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen bg-[#f8fafc] font-sans text-slate-900 overflow-hidden">
      {/* 1. Admin Nav Rail */}
      <nav className="w-20 bg-amber-400 flex flex-col items-center py-8 gap-10 shrink-0 border-r border-amber-500/20 shadow-xl">
        <div className="w-12 h-12 bg-slate-900 rounded-2xl flex items-center justify-center shadow-lg">
          <Layers className="w-6 h-6 text-white" />
        </div>
        <button onClick={() => navigate('/')} className="p-3 text-slate-900 hover:bg-amber-500 rounded-2xl transition-all" title="View Portal">
          <Home className="w-6 h-6" />
        </button>
      </nav>

      <main className="flex-1 flex flex-col overflow-hidden">
         <header className="p-8 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
            <div>
              <h2 className="text-3xl font-black text-slate-800 tracking-tight">Management</h2>
              <p className="text-sm text-slate-400 font-medium italic">공고 업로드 및 데이터 관리</p>
            </div>
            <label className="px-8 py-3 bg-slate-900 text-white rounded-2xl font-black hover:bg-slate-800 transition-all cursor-pointer shadow-lg active:scale-95 flex items-center gap-2">
               <Upload className="w-5 h-5" /> 새 공고 가져오기
               <input type="file" className="hidden" onChange={handleFileChange} />
            </label>
         </header>

         {/* Entry List */}
         <div className="flex-1 overflow-y-auto p-8 space-y-4">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Saved Announcements ({announcements.length})</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {announcements.map(a => (
                <div key={a.id} className="p-6 bg-white border border-slate-100 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all group flex items-center justify-between">
                   <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center">
                        <FileText className="w-6 h-6" />
                      </div>
                      <div>
                         <h4 className="font-black text-slate-800">{a.title}</h4>
                         <p className="text-xs text-slate-400 font-medium">{a.filename} • {a.house_count} units</p>
                      </div>
                   </div>
                   <button 
                     onClick={() => deleteAnnouncement(a.id)}
                     className="p-3 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-2xl transition-all"
                   >
                     <X className="w-6 h-6" />
                   </button>
                </div>
              ))}
            </div>
         </div>
      </main>

      {/* Preview Overlay */}
      {previewData && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[100] flex items-center justify-center p-8 animate-in zoom-in-95">
           <div className="bg-white w-full max-w-7xl h-full rounded-[3.5rem] shadow-4xl flex flex-col overflow-hidden">
              <div className="p-10 border-b border-slate-100 flex items-center justify-between">
                 <div>
                    <h2 className="text-3xl font-black text-slate-800 tracking-tight">Preview & Edit</h2>
                    <p className="text-slate-400 font-medium">총 {previewData.houses.length}건이 분석되었습니다. 설정을 확인하고 저장하세요.</p>
                 </div>
                 <div className="flex gap-4">
                    <button onClick={() => setPreviewData(null)} className="px-8 py-4 bg-slate-100 text-slate-600 font-bold rounded-2xl">취소</button>
                    <button onClick={onFinalSave} className="px-10 py-4 bg-indigo-600 text-white font-black rounded-2xl shadow-xl hover:bg-indigo-700">최종 저장</button>
                 </div>
              </div>
              <div className="flex-1 overflow-auto p-10">
                 <table className="w-full text-left border-separate border-spacing-y-2">
                    <thead>
                       <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">
                          <th className="pb-4 pl-4">주소</th>
                          <th className="pb-4">유형</th>
                          <th className="pb-4">보증금</th>
                          <th className="pb-4">월세</th>
                       </tr>
                    </thead>
                    <tbody className="space-y-2">
                       {previewData.houses.map((h, i) => (
                         <tr key={i} className="bg-slate-50 hover:bg-indigo-50 transition-colors">
                            <td className="pl-4 py-4 rounded-l-2xl text-sm font-bold text-slate-700">{h.address}</td>
                            <td className="py-4 text-xs font-black text-amber-600 uppercase">{h.house_type}</td>
                            <td className="py-4 text-sm font-bold text-indigo-600">{h.deposit}</td>
                            <td className="py-4 pr-4 rounded-r-2xl text-sm font-bold text-indigo-600">{h.monthly_rent}</td>
                         </tr>
                       ))}
                    </tbody>
                 </table>
              </div>
           </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {isConfirmingUpload && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[200] flex items-center justify-center p-4 animate-in fade-in">
           <div className="bg-white w-[450px] p-10 rounded-[3rem] shadow-2xl text-center">
              <div className="w-20 h-20 bg-indigo-50 text-indigo-600 rounded-[2rem] flex items-center justify-center mx-auto mb-6">
                <FileText className="w-10 h-10" />
              </div>
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">분석 시작</h2>
              <p className="text-sm text-slate-400 mt-2 mb-8">Gemini API를 사용하여 공고 내용을 파싱합니다.</p>
              
              <div className="space-y-4 mb-8">
                 <input 
                   type="password" 
                   placeholder="Gemini API Key (Optional if server set)" 
                   className="w-full px-6 py-4 bg-slate-50 rounded-2xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                   value={userApiKey}
                   onChange={(e) => setUserApiKey(e.target.value)}
                 />
              </div>

              <div className="flex gap-4">
                 <button onClick={() => setIsConfirmingUpload(false)} className="flex-1 py-4 bg-slate-100 text-slate-600 font-bold rounded-2xl">취소</button>
                 <button onClick={onFileUpload} className="flex-1 py-4 bg-indigo-600 text-white font-black rounded-2xl shadow-lg">시작하기</button>
              </div>
           </div>
        </div>
      )}

      {/* Loading Overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-xl z-[300] flex flex-col items-center justify-center text-white">
           <div className="relative mb-8">
              <div className="w-24 h-24 border-4 border-indigo-400/20 border-t-indigo-500 rounded-full animate-spin" />
              <Loader2 className="w-10 h-10 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse text-indigo-400" />
           </div>
           <p className="text-xl font-black tracking-tight mb-2">분석 및 저장 진행 중</p>
           <p className="text-slate-400 font-medium">{parsingStatus || '잠시만 기다려주세요...'}</p>
        </div>
      )}
    </div>
  );
};

export default AdminPortal;
