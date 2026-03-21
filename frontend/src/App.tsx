import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, ChevronRight, Loader2, AlertCircle, Home, 
  MapPin, BadgeCent, Layers, ChevronLeft, Search, Menu, X 
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
      setIsDrawerOpen(true); // Open drawer after upload to see the new entry
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
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-900">
      
      {/* --- Sidebar (House List) --- */}
      <aside className={cn(
        "bg-white border-r border-slate-200 flex flex-col transition-all duration-300 z-30 shadow-xl",
        isSidebarOpen ? "w-[400px]" : "w-0 -translate-x-full"
      )}>
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Home className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Housing <span className="text-indigo-600">Pipeline</span></h1>
          </div>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="p-2 hover:bg-slate-100 rounded-lg lg:hidden"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Stats */}
        <div className="p-4 border-b border-slate-50 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text"
              placeholder="주택 이름 또는 주소 검색..."
              className="w-full pl-10 pr-4 py-2 bg-slate-100 border-none rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 transition-all outline-none"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          {detail && (
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                {searchTerm ? `검색 결과 ${filteredHouses.length}건` : `총 ${detail.length}호실`}
              </span>
              <div className="flex gap-1">
                <span className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-[10px] font-bold uppercase transition-colors">
                  {filteredHouses.filter(h => h.lat).length} Geocoded
                </span>
              </div>
            </div>
          )}
        </div>

        {/* House List Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {!detail ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-60 px-8 text-center mt-10">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <FileText className="w-8 h-8" />
              </div>
              <p className="text-sm font-medium">상단 메뉴에서 공고를 선택하거나<br/>새로운 파일을 업로드해주세요.</p>
            </div>
          ) : filteredHouses.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-sm">검색 결과가 없습니다.</div>
          ) : (
            filteredHouses.map((house) => (
              <div 
                key={house.id}
                onClick={() => setSelectedHouseId(house.id)}
                className={cn(
                  "p-4 rounded-2xl border transition-all cursor-pointer group",
                  selectedHouseId === house.id 
                    ? "bg-indigo-50 border-indigo-200 shadow-sm"
                    : "bg-white border-slate-100 hover:border-indigo-100 hover:shadow-md"
                )}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className={cn(
                    "font-bold text-slate-800 transition-colors",
                    selectedHouseId === house.id ? "text-indigo-700" : "group-hover:text-indigo-600"
                  )}>{house.name}</h3>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-bold">{house.house_type}</span>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-slate-500 leading-snug">{house.address}</p>
                      {house.nearest_station && (
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[10px] font-bold px-1 py-0.5 bg-emerald-50 text-emerald-600 rounded flex items-center gap-0.5">
                            <Layers className="w-2.5 h-2.5" /> {house.nearest_station}역
                          </span>
                          <span className="text-[10px] text-slate-400">도보 {house.walking_time_mins}분</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <BadgeCent className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <p className="text-xs font-semibold text-indigo-600">
                      보증금 {house.deposit.toLocaleString()} / 월 {house.monthly_rent.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* --- Main Content Area --- */}
      <main className="flex-1 flex flex-col relative">
        
        {/* Floating Header */}
        <header className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-2 pointer-events-auto">
            {!isSidebarOpen && (
              <button 
                onClick={() => setIsSidebarOpen(true)}
                className="p-3 bg-white shadow-lg border border-slate-100 rounded-2xl hover:bg-slate-50 text-slate-600 transition-all hover:scale-105 active:scale-95"
              >
                <Menu className="w-6 h-6" />
              </button>
            )}
            
            <div className="bg-white/80 backdrop-blur-md px-5 py-3 shadow-lg border border-white/50 rounded-2xl flex items-center gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Current Project</span>
                <span className="text-sm font-bold text-slate-800 truncate max-w-[200px]">
                  {selectedId ? announcements.find(a => a.id === selectedId)?.title : '공고를 선택해주세요'}
                </span>
              </div>
              <button 
                onClick={() => setIsDrawerOpen(true)}
                className="px-3 py-1.5 bg-slate-900 text-white text-xs font-bold rounded-xl hover:bg-slate-800 transition-all active:scale-95 flex items-center gap-2"
              >
                <ChevronRight className="w-3.5 h-3.5" /> Change
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 pointer-events-auto">
            <label className={cn(
              "px-5 py-3 bg-indigo-600 text-white shadow-lg shadow-indigo-200 rounded-2xl font-bold text-sm cursor-pointer hover:bg-indigo-700 transition-all flex items-center gap-3 active:scale-95",
              uploading && "opacity-80 pointer-events-none"
            )}>
              {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Upload className="w-5 h-5" />}
              <span>{uploading ? 'Parsing...' : 'New Announcement'}</span>
              <input type="file" multiple className="hidden" onChange={onFileUpload} disabled={uploading} />
            </label>
          </div>
        </header>

        {/* Full-screen Map */}
        <div className="w-full h-full bg-slate-200">
          <MapView houses={detail || []} selectedHouseId={selectedHouseId} />
        </div>

        {/* Global Error Alert */}
        {error && (
          <div className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-red-50 border border-red-100 px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 z-[60] animate-in slide-in-from-bottom">
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
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 animate-in fade-in"
            onClick={() => setIsDrawerOpen(false)}
          />
          <div className="fixed top-0 bottom-0 right-0 w-[400px] bg-white shadow-2xl z-50 animate-in slide-in-from-right duration-500 border-l border-slate-100 flex flex-col">
            <div className="p-8 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-black text-slate-800 tracking-tight">Announcements</h2>
                <p className="text-sm text-slate-400 mt-1 font-medium">분석된 공고 내역입니다.</p>
              </div>
              <button 
                onClick={() => setIsDrawerOpen(false)}
                className="p-3 hover:bg-slate-100 rounded-2xl transition-colors"
              >
                <X className="w-6 h-6 text-slate-400" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {announcements.map((a) => (
                <div 
                  key={a.id}
                  onClick={() => loadDetail(a.id)}
                  className={cn(
                    "p-6 rounded-3xl border transition-all cursor-pointer group",
                    selectedId === a.id 
                      ? "bg-indigo-50 border-indigo-200 shadow-sm"
                      : "bg-white border-slate-100 hover:border-indigo-100 hover:shadow-xl"
                  )}
                >
                  <div className="flex items-center gap-1 mb-2">
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-600 rounded text-[10px] font-black uppercase tracking-wider">
                      {a.house_count} items
                    </span>
                  </div>
                  <h3 className={cn(
                    "text-lg font-black text-slate-800 leading-tight mb-2 group-hover:text-indigo-600 transition-colors",
                    selectedId === a.id && "text-indigo-700"
                  )}>{a.title}</h3>
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-tighter">
                    <FileText className="w-3.5 h-3.5" /> {a.filename}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Retro-style Button for Kakao Pay (Maintaining previous functionality) */}
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

      {/* Global CSS for scrollbar */}
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
