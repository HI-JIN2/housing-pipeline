import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, ChevronRight, Loader2, AlertCircle, Home, MapPin, BadgeCent } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface House {
  id: string;
  name: string;
  address: string;
  house_type: string;
  deposit: number;
  monthly_rent: number;
  raw_text_reference: string;
}

interface Announcement {
  id: string;
  title: string;
  description: string;
  house_count: number;
  filename: string;
}

const App: React.FC = () => {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<House[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasGeminiKey, setHasGeminiKey] = useState(true);
  const [geminiInput, setGeminiInput] = useState('');

  useEffect(() => {
    checkConfig();
    fetchAnnouncements();
  }, []);

  const checkConfig = async () => {
    try {
      const res = await axios.get('/api/config');
      setHasGeminiKey(res.data.has_gemini_key);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAnnouncements = async () => {
    try {
      const res = await axios.get('/api/announcements');
      if (res.data.status === 'success') {
        setAnnouncements(res.data.data);
      }
    } catch (e) {
      setError('공고 목록을 불러오는데 실패했습니다.');
    }
  };

  const fetchDetail = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`/api/announcements/${id}`);
      if (res.data.status === 'success') {
        setDetail(res.data.data);
        setSelectedId(id);
      }
    } catch (e) {
      setError('상세 정보를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    Array.from(files).forEach(f => formData.append('files', f));
    if (geminiInput) {
      formData.append('gemini_key', geminiInput);
    }

    setUploading(true);
    setError(null);
    try {
      const res = await axios.post('/api/upload', formData);
      if (res.status === 200) {
        await fetchAnnouncements();
        // Automatically select the first one if successful
        // Or just show success state
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || '업로드 중 오류가 발생했습니다.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <header className="text-center mb-12">
        <h1 className="text-4xl font-extrabold bg-gradient-to-r from-indigo-600 to-pink-500 bg-clip-text text-transparent mb-2">
          Housing Pipeline
        </h1>
        <p className="text-slate-500 text-lg">청약/매물 문서를 업로드하면 AI가 자동으로 구조화합니다.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Upload & History */}
        <div className="lg:col-span-5 space-y-6">
          {/* Upload Area */}
          <section className={cn(
            "p-8 rounded-3xl border-2 border-dashed transition-all cursor-pointer bg-white/50 backdrop-blur-xl",
            "hover:border-indigo-500 hover:bg-indigo-50/30 border-slate-200"
          )}
          onClick={() => document.getElementById('file-upload')?.click()}
          >
            <input 
              id="file-upload"
              type="file" 
              className="hidden" 
              multiple 
              accept=".pdf,.xlsx"
              onChange={handleFileUpload}
            />
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-indigo-100 text-indigo-600 rounded-2xl flex items-center justify-center mb-4">
                {uploading ? <Loader2 className="w-8 h-8 animate-spin" /> : <Upload className="w-8 h-8" />}
              </div>
              <h3 className="text-xl font-bold mb-1">문서 업로드</h3>
              <p className="text-slate-500 text-sm">PDF, XLSX (최대 3개)</p>
            </div>
          </section>

          {!hasGeminiKey && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl">
              <input 
                type="password"
                placeholder="Gemini API Key 입력"
                className="w-full p-3 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-indigo-500"
                value={geminiInput}
                onChange={(e) => setGeminiInput(e.target.value)}
              />
            </div>
          )}

          {/* History List */}
          <section className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-50 flex justify-between items-center">
              <h2 className="font-bold text-slate-800">최근 분석된 공고</h2>
              <span className="text-xs font-semibold px-2 py-1 bg-slate-100 text-slate-500 rounded-lg">{announcements.length}</span>
            </div>
            <ul className="divide-y divide-slate-50 max-h-[500px] overflow-y-auto">
              {announcements.map((item) => (
                <li 
                  key={item.id}
                  className={cn(
                    "px-6 py-4 cursor-pointer transition-colors flex items-center justify-between group",
                    selectedId === item.id ? "bg-indigo-50" : "hover:bg-slate-50"
                  )}
                  onClick={() => fetchDetail(item.id)}
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <h4 className={cn(
                      "font-semibold truncate",
                      selectedId === item.id ? "text-indigo-700" : "text-slate-700"
                    )}>
                      {item.title}
                    </h4>
                    <p className="text-xs text-slate-400 truncate">{item.description || item.filename}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-slate-100 text-slate-500 rounded-md">
                      {item.house_count}호
                    </span>
                    <ChevronRight className={cn(
                      "w-4 h-4 transition-transform",
                      selectedId === item.id ? "text-indigo-500 translate-x-1" : "text-slate-300"
                    )} />
                  </div>
                </li>
              ))}
              {announcements.length === 0 && (
                <li className="px-6 py-12 text-center text-slate-400 italic">표시할 공고가 없습니다.</li>
              )}
            </ul>
          </section>
        </div>

        {/* Right Column: Detail View */}
        <div className="lg:col-span-7">
          <section className="bg-white rounded-3xl shadow-xl border border-slate-100 min-h-[600px] flex flex-col">
            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                <Loader2 className="w-10 h-10 animate-spin mb-4" />
                <p>데이터를 불러오고 있습니다...</p>
              </div>
            ) : detail ? (
              <>
                <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/50 rounded-t-3xl">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded-md text-[10px] font-bold uppercase tracking-wider">Analysis Result</span>
                  </div>
                  <h2 className="text-2xl font-bold text-slate-800">
                    {announcements.find(a => a.id === selectedId)?.title}
                  </h2>
                </div>
                <div className="flex-1 p-8 space-y-6 overflow-y-auto max-h-[800px]">
                  {detail.map((house, idx) => (
                    <div key={idx} className="p-6 rounded-2xl border border-slate-100 bg-white hover:border-indigo-200 transition-all shadow-sm hover:shadow-md">
                      <div className="flex justify-between items-start mb-4">
                        <h3 className="text-xl font-bold text-slate-800">{house.name}</h3>
                        <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-xs font-bold">{house.house_type}</span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div className="flex items-start gap-3">
                          <MapPin className="w-5 h-5 text-slate-400 shrink-0" />
                          <div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase">Address</p>
                            <p className="text-sm text-slate-600">{house.address}</p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <BadgeCent className="w-5 h-5 text-slate-400 shrink-0" />
                          <div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase">Financials</p>
                            <p className="text-sm text-slate-600 font-semibold">
                              보증금 {house.deposit.toLocaleString()} / 월세 {house.monthly_rent.toLocaleString()} (만원)
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="p-4 bg-slate-50 rounded-xl">
                        <p className="text-[10px] font-bold text-slate-400 mb-2 uppercase flex items-center gap-1">
                          <FileText className="w-3 h-3" /> Raw Reference
                        </p>
                        <p className="text-xs text-slate-500 whitespace-pre-wrap leading-relaxed">{house.raw_text_reference}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-300 p-12 text-center">
                <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                  <Home className="w-10 h-10" />
                </div>
                <h3 className="text-xl font-bold text-slate-400 mb-2">공고를 선택해 주세요</h3>
                <p className="text-sm max-w-[280px]">왼쪽 목록에서 공고를 선택하면 상세 분석 내용을 여기서 확인할 수 있습니다.</p>
              </div>
            )}
          </section>
        </div>
      </div>

      {error && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-red-500 text-white px-6 py-3 rounded-2xl shadow-2xl animate-in fade-in slide-in-from-bottom-4">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium text-sm">{error}</span>
          <button onClick={() => setError(null)} className="ml-4 hover:opacity-70 transition-opacity">
            <ChevronRight className="w-4 h-4 rotate-90" />
          </button>
        </div>
      )}

      {/* Retro-style Button for Kakao Pay (Maintaining previous functionality) */}
      <a 
        href="https://qr.kakaopay.com/Ej88F1kMG" 
        target="_blank" 
        rel="noreferrer"
        className="fixed bottom-8 right-8 group hover:-translate-y-1 transition-transform z-50"
      >
        <img 
          src="http://localhost:8000/static/images/btn_send_regular.png" 
          alt="카카오페이" 
          className="h-12 shadow-lg rounded-xl"
          onError={(e) => (e.currentTarget.style.display = 'none')}
        />
      </a>
    </div>
  );
};

export default App;
