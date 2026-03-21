import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, ChevronRight, Loader2, AlertCircle, Home, 
  MapPin, BadgeCent, Layers, ChevronLeft, Search, Menu, X, Plus, Library
} from 'lucide-react';
import MapView from './components/KakaoMapView';
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
  lat?: number;
  lng?: number;
  nearest_station?: string;
  distance_meters?: number;
  walking_time_mins?: number;
}

interface Announcement {
  id: string;
  filename: string;
  title: string;
  description: string;
  house_count: number;
}

const App: React.FC = () => {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<House[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedHouseId, setSelectedHouseId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchAnnouncements();
  }, []);

  const fetchAnnouncements = async () => {
    try {
      const res = await axios.get('/api/announcements');
      setAnnouncements(res.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    }
  };

  const loadDetail = async (id: string) => {
    setSelectedId(id);
    setSelectedHouseId(null);
    setIsDrawerOpen(false);
    try {
      const res = await axios.get(`/api/announcements/${id}`);
      setDetail(res.data.data);
    } catch (err) {
      setError('상세 정보를 불러오지 못했습니다.');
    }
  };

  const onFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    
    setUploading(true);
    const formData = new FormData();
    Array.from(e.target.files).forEach(file => {
      formData.append('files', file);
    });
    
    try {
      await axios.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await fetchAnnouncements();
      setIsDrawerOpen(true);
    } catch (err) {
      setError('업로드 중 오류가 발생했습니다.');
    } finally {
      setUploading(false);
    }
  };

  const filteredHouses = detail?.filter(h => 
    h.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    h.address.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f8fafc] font-sans text-slate-900">
      
      {/* 1. Nav Rail (Far Left) */}
      <nav className="w-16 lg:w-20 bg-slate-900 flex flex-col items-center py-6 gap-8 z-50 border-r border-slate-800 shrink-0">
        <div className="w-10 h-10 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Home className="w-6 h-6 text-white" />
        </div>
        
        <div className="flex flex-col gap-4">
          <button 
            onClick={() => setIsDrawerOpen(true)}
            className={cn(
              "p-3 rounded-2xl transition-all relative group shadow-sm",
              isDrawerOpen ? "bg-white text-slate-900" : "text-slate-400 hover:text-white hover:bg-slate-800"
            )}
            title="공고 목록"
          >
            <Library className="w-6 h-6" />
            <div className="absolute left-full ml-3 px-2 py-1 bg-slate-800 text-white text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">공고 목록</div>
          </button>
          
          <label className={cn(
            "p-3 rounded-2xl transition-all relative group cursor-pointer shadow-sm",
            uploading ? "bg-indigo-600 text-white animate-pulse" : "text-slate-400 hover:text-white hover:bg-slate-800"
          )} title="새 공고 업로드">
            {uploading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Plus className="w-6 h-6" />}
            <input type="file" multiple className="hidden" onChange={onFileUpload} disabled={uploading} />
            <div className="absolute left-full ml-3 px-2 py-1 bg-slate-800 text-white text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">새 공고 업로드</div>
          </label>
        </div>
      </nav>

      {/* 2. Sidebar (House List) */}
      <aside className={cn(
        "bg-white border-r border-slate-200 flex flex-col transition-all duration-300 z-30 shadow-2xl relative",
        isSidebarOpen ? "w-[360px] lg:w-[400px]" : "w-0 -translate-x-full"
      )}>
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10 shrink-0">
          <div className="flex flex-col">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-tighter mb-1">Current Results</h2>
            <h1 className="text-lg font-black text-slate-800 truncate max-w-[280px]">
              {selectedId ? announcements.find(a => a.id === selectedId)?.title : '공고를 선택해주세요'}
            </h1>
          </div>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="p-2 hover:bg-slate-100 rounded-lg lg:hidden"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-slate-50">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text"
              placeholder="이름 또는 주소 검색..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-100 border-none rounded-2xl text-sm focus:ring-2 focus:ring-indigo-500 transition-all outline-none"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          {detail && (
            <div className="flex items-center justify-between mt-3 px-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">
                {searchTerm ? `RESULT ${filteredHouses.length}` : `TOTAL ${detail.length}`}
              </span>
              <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded text-[9px] font-black uppercase">
                {filteredHouses.filter(h => h.lat).length} GEOMAPPED
              </span>
            </div>
          )}
        </div>

        {/* House List Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {!detail ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-300 px-8 text-center">
              <Library className="w-12 h-12 mb-4 opacity-20" />
              <p className="text-sm font-bold opacity-60">왼쪽 메뉴에서 공고를 선택하거나<br/>파일을 올려주세요.</p>
            </div>
          ) : (
            filteredHouses.map((house) => (
              <div 
                key={house.id}
                onClick={() => setSelectedHouseId(house.id)}
                className={cn(
                  "p-4 rounded-[2rem] border transition-all cursor-pointer group animate-in fade-in slide-in-from-left-2 duration-300",
                  selectedHouseId === house.id 
                    ? "bg-indigo-50 border-indigo-200 shadow-sm"
                    : "bg-white border-slate-100 hover:border-indigo-100 hover:shadow-lg"
                )}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className={cn(
                    "font-bold text-slate-800 transition-colors leading-tight pr-4",
                    selectedHouseId === house.id ? "text-indigo-700" : "group-hover:text-indigo-600"
                  )}>{house.name}</h3>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full text-[9px] font-black shrink-0">{house.house_type}</span>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-300 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-slate-500 leading-snug">{house.address}</p>
                      {house.nearest_station && (
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className="text-[9px] font-black px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded flex items-center gap-0.5">
                            <Layers className="w-2.5 h-2.5" /> {house.nearest_station}역
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">도보 {house.walking_time_mins}분</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1 border-t border-slate-50">
                    <BadgeCent className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                    <p className="text-xs font-black text-indigo-600">
                      보증금 {house.deposit.toLocaleString()} / 월 {house.monthly_rent.toLocaleString()} <span className="text-[9px] text-slate-400 font-normal ml-0.5">(만원)</span>
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* 3. Main Content Area (Map) */}
      <main className="flex-1 flex flex-col relative overflow-hidden bg-slate-100">
        
        {/* Toggle Sidebar Button */}
        {!isSidebarOpen && (
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-6 left-6 z-40 p-3 bg-white shadow-2xl border border-slate-100 rounded-2xl hover:bg-slate-50 text-slate-600 transition-all hover:scale-105 active:scale-95 animate-in fade-in slide-in-from-left-4"
          >
            <Menu className="w-6 h-6" />
          </button>
        )}

        <div className="w-full h-full">
          <MapView houses={detail || []} selectedHouseId={selectedHouseId} />
        </div>

        {/* Global Error Alert */}
        {error && (
          <div className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-red-50 border border-red-100 px-6 py-4 rounded-3xl shadow-2xl flex items-center gap-3 z-[60] animate-in slide-in-from-bottom duration-500">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-sm font-bold text-red-700">{error}</p>
            <button onClick={() => setError(null)} className="ml-4 p-1 hover:bg-red-100 rounded-full transition-colors">
              <X className="w-4 h-4 text-red-400" />
            </button>
          </div>
        )}
      </main>

      {/* --- Overlay Drawer for Announcements --- */}
      {isDrawerOpen && (
        <>
          <div 
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-40 animate-in fade-in duration-300"
            onClick={() => setIsDrawerOpen(false)}
          />
          <div className="fixed top-0 bottom-0 left-20 w-[400px] bg-white shadow-2xl z-50 animate-in slide-in-from-left duration-500 border-r border-slate-100 flex flex-col rounded-r-3xl">
            <div className="p-8 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-black text-slate-800 tracking-tight">Library</h2>
                <p className="text-sm text-slate-400 mt-1 font-medium italic">분석된 공고 내역입니다.</p>
              </div>
              <button 
                onClick={() => setIsDrawerOpen(false)}
                className="p-3 hover:bg-slate-100 rounded-2xl transition-colors"
              >
                <X className="w-6 h-6 text-slate-400" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
              {announcements.map((a) => (
                <div 
                  key={a.id}
                  onClick={() => loadDetail(a.id)}
                  className={cn(
                    "p-6 rounded-[2.5rem] border transition-all cursor-pointer group relative overflow-hidden",
                    selectedId === a.id 
                      ? "bg-indigo-50 border-indigo-200"
                      : "bg-white border-slate-100 hover:border-indigo-100 hover:shadow-2xl hover:-translate-y-1"
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-indigo-600 text-white rounded-full text-[8px] font-black uppercase tracking-widest">
                      {a.house_count} UNITS
                    </span>
                  </div>
                  <h3 className={cn(
                    "text-lg font-black text-slate-800 leading-tight mb-2 group-hover:text-indigo-600 transition-colors",
                    selectedId === a.id && "text-indigo-700"
                  )}>{a.title}</h3>
                  <div className="flex items-center gap-2 text-slate-400 text-[10px] font-bold uppercase tracking-tight">
                    <FileText className="w-3.5 h-3.5" /> {a.filename}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Responsive Kakao Pay Button */}
      <a 
        href="https://qr.kakaopay.com/Ej88F1kMG" 
        target="_blank" 
        rel="noreferrer"
        className="fixed bottom-6 right-6 lg:bottom-10 lg:right-10 group hover:-translate-y-1 transition-transform z-50 flex items-center justify-center p-0 bg-transparent"
      >
        <picture>
          <source 
            media="(max-width: 640px)" 
            srcSet="http://localhost:8000/static/images/btn_send_tiny.png" 
          />
          <source 
            media="(max-width: 1024px)" 
            srcSet="http://localhost:8000/static/images/btn_send_small.png" 
          />
          <img 
            src="http://localhost:8000/static/images/btn_send_regular.png" 
            alt="카카오페이" 
            className="h-8 md:h-10 lg:h-12 block filter drop-shadow-[0_5px_8px_rgba(0,0,0,0.3)] rounded-xl"
            onError={(e) => (e.currentTarget.style.display = 'none')}
          />
        </picture>
      </a>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #e2e8f0;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #cbd5e1;
        }
      `}</style>
    </div>
  );
};

export default App;
