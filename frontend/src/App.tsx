import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, Loader2, AlertCircle, Home, 
  MapPin, BadgeCent, Layers, ChevronLeft, Search, Menu, X, Plus, Library, ChevronRight,
  ChevronDown, Check, Upload
} from 'lucide-react';
import MapView from './components/KakaoMapView';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface House {
  id: string;
  index?: number;
  district?: string;
  complex_no?: string;
  address: string;
  unit_no?: string;
  area?: number;
  house_type?: string;
  elevator?: string;
  deposit: number;
  monthly_rent: number;
  raw_text_reference: string;
  extra_info?: Record<string, any>;
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
  const [expandedHouseId, setExpandedHouseId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminPassword, setAdminPassword] = useState<string>('');
  const [previewData, setPreviewData] = useState<{title: string, desc: string, houses: House[]} | null>(null);
  const [hasServerKey, setHasServerKey] = useState(false); // Added this state based on checkConfig content
  const [pendingFiles, setPendingFiles] = useState<FileList | null>(null); // Added this state based on handleFileChange content
  const [isConfirmingUpload, setIsConfirmingUpload] = useState(false); // Added this state based on handleFileChange content
  const [expectedCount, setExpectedCount] = useState(''); // Added this state based on handleFileChange content
  const [userApiKey, setUserApiKey] = useState(localStorage.getItem('gemini_api_key') || '');
  const [isCoffeeOpen, setIsCoffeeOpen] = useState(false);
  const [parsingStatus, setParsingStatus] = useState<string>('');
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [progressCount, setProgressCount] = useState<number>(0);
  const [progressTotal, setProgressTotal] = useState<number>(0);
  const [activeModel, setActiveModel] = useState<string>('');
  const [activeKeyIdx, setActiveKeyIdx] = useState<number>(-1);
  const [activeProvider, setActiveProvider] = useState<string>('gemini');
  const [selectedProvider, setSelectedProvider] = useState<'gemini' | 'openai'>(
    (localStorage.getItem('llm_provider') as 'gemini' | 'openai') || 'gemini'
  );
  const [selectedModel, setSelectedModel] = useState<string>(
    localStorage.getItem('llm_model') || 'gpt-4o'
  );
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [geocodingIndices, setGeocodingIndices] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchAnnouncements();
    checkConfig();
  }, []);

  const checkConfig = async () => {
    try {
      const res = await axios.get('/api/config');
      setHasServerKey(res.data.has_gemini_key);
    } catch (err) {
      console.error('Failed to check config:', err);
    }
  };

  const onGeocodeAll = async () => {
    if (!previewData) return;
    const houses = [...previewData.houses];
    // filter houses that need geocoding
    const indicesToProcess = houses
      .map((_, i) => i)
      .filter(i => !houses[i].lat || !houses[i].lng);
    
    if (indicesToProcess.length === 0) return;

    const batchSize = 3; // Reduced batch size for stability
    const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

    for (let i = 0; i < indicesToProcess.length; i += batchSize) {
      const batch = indicesToProcess.slice(i, i + batchSize);
      setGeocodingIndices(prev => new Set([...prev, ...batch]));
      
      await Promise.all(batch.map(async (idx) => {
        try {
          const res = await axios.get('/api/geocode', { params: { address: houses[idx].address } });
          if (res.data.lat && res.data.lng) {
            houses[idx] = { 
              ...houses[idx], 
              lat: res.data.lat, 
              lng: res.data.lng,
              nearest_station: res.data.nearest_station,
              distance_meters: res.data.distance_meters,
              walking_time_mins: res.data.walking_time_mins
            };
          }
        } catch (e) {
          console.error(`Geocoding failed for ${houses[idx].address}`, e);
        } finally {
          setGeocodingIndices(prev => {
            const next = new Set(prev);
            next.delete(idx);
            return next;
          });
        }
      }));
      
      // Update preview data once per batch
      setPreviewData(prev => prev ? { ...prev, houses: [...houses] } : null);
      
      // Give the UI thread a break between batches
      await delay(300);
    }
  };
  const fetchAnnouncements = async () => {
    try {
      const res = await axios.get('/api/announcements');
      setAnnouncements(res.data.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    }
  };

  const loadDetail = async (id: string) => {
    setSelectedId(id);
    setSelectedHouseId(null);
    setExpandedHouseId(null);
    setIsDrawerOpen(false);
    try {
      const res = await axios.get(`/api/announcements/${id}`);
      setDetail(res.data.data);
    } catch (err) {
      setError('상세 정보를 불러오지 못했습니다.');
    }
  };

  const deleteAnnouncement = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('정말 이 공고와 관련된 모든 데이터를 삭제하시겠습니까?')) return;
    try {
      await axios.delete(`/api/announcements/${id}`, {
        headers: { 'x-admin-password': adminPassword }
      });
      await fetchAnnouncements();
      if (selectedId === id) {
        setSelectedId(null);
        setDetail(null);
      }
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError('관리자 권한이 없거나 비밀번호가 틀렸습니다.');
        setIsAdmin(false);
      } else {
        setError('삭제에 실패했습니다.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setPendingFiles(e.target.files);
    setIsConfirmingUpload(true);
    setExpectedCount('');
  };

  const onFileUpload = async () => {
    if (!pendingFiles) return;
    
    setUploading(true);
    setActiveProvider(selectedProvider);
    setActiveModel(selectedModel);
    setIsConfirmingUpload(false);
    setParsingStatus('문서에서 텍스트를 추출하는 중...');
    setCurrentStep(1);
    setProgressCount(0);
    setProgressTotal(expectedCount ? parseInt(expectedCount) : 0);

    const jobId = Math.random().toString(36).substring(7);
    
    // Polling Progress
    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/status/${jobId}`);
        if (res.data.count > 0) setProgressCount(res.data.count);
        if (res.data.total > 0) setProgressTotal(res.data.total);
        if (res.data.model) setActiveModel(res.data.model);
        if (res.data.key_idx !== undefined) setActiveKeyIdx(res.data.key_idx);
        if (res.data.provider) setActiveProvider(res.data.provider);
        
        if (res.data.error) {
          setError(`분석 중 오류 발생: ${res.data.error}`);
          clearInterval(pollInterval);
          setUploading(false);
          setParsingStatus('');
          setCurrentStep(0);
          return;
        }

        if (res.data.result) {
          clearInterval(pollInterval);
          setPreviewData({
            title: res.data.result.announcement_title,
            desc: res.data.result.announcement_description,
            houses: res.data.result.houses
          });
          setUploading(false);
          setPendingFiles(null);
          setParsingStatus('');
          setCurrentStep(0);
          setProgressCount(0);
          setProgressTotal(0);
        } else if (res.data.partial_result && res.data.partial_result.length > 0) {
          // Show last found house as a hint
          const lastHouse = res.data.partial_result[res.data.partial_result.length - 1];
          setParsingStatus(`최근 발견: ${lastHouse.address.split(' ').slice(0, 2).join(' ')} (${res.data.count}건)`);
        }

        if (res.data.step && res.data.step.includes('QUOTA')) {
          setParsingStatus(`할당량 초과로 모델/키를 변경하여 분석 중...`);
        }
      } catch (e) {
        console.error("Status poll error", e);
      }
    }, 3000);
    
    const formData = new FormData();
    // Only upload the first file since the updated routes.py takes one "file"
    formData.append('file', pendingFiles[0]);
    if (userApiKey) {
      localStorage.setItem('gemini_api_key', userApiKey);
    }
    
    try {
      setTimeout(() => {
        setParsingStatus('AI가 단지별 상세 정보를 구조화하고 있습니다 (2~3분 소요)...');
      }, 1500);

      await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'x-job-id': jobId,
          'x-gemini-key': userApiKey,
          'x-provider': selectedProvider,
          'x-model': selectedModel || undefined,
          'x-admin-password': adminPassword
        }
      });
      
      setIsDrawerOpen(false);
    } catch (err) {
      console.error(err);
      setError('분석 시작 중 오류가 발생했습니다.');
      clearInterval(pollInterval);
      setUploading(false);
      setParsingStatus('');
      setCurrentStep(0);
    }
  };

  const onFinalSave = async () => {
    if (!previewData) return;
    setUploading(true);
    setParsingStatus('카카오 맵 API를 통해 좌표를 추출하는 중...');
    setCurrentStep(3);
    
    try {
      setTimeout(() => {
        setParsingStatus('인접 지하철역 도보 거리를 계산하고 있습니다...');
        setCurrentStep(4);
      }, 3000);

      await axios.post('/api/save', {
        announcement_title: previewData.title,
        announcement_description: previewData.desc,
        houses: previewData.houses.map(h => ({
        ...h,
        id: h.id || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2))
      }))
      }, {
        headers: { 'x-admin-password': adminPassword }
      });
      setPreviewData(null);
      await fetchAnnouncements();
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 401) {
        setError('관리자 권한이 없거나 비밀번호가 틀렸습니다.');
        setIsAdmin(false);
      } else {
        setError('최종 저장 중 오류가 발생했습니다.');
      }
    } finally {
      setUploading(false);
      setParsingStatus('');
      setCurrentStep(0);
    }
  };

  const updateProvider = (p: 'gemini' | 'openai') => {
    setSelectedProvider(p);
    localStorage.setItem('llm_provider', p);
    
    // Reset model to default for the provider to avoid "Gemini | gpt-4o" style mismatch
    const defaultModel = p === 'gemini' ? 'gemini-1.5-flash' : 'gpt-4o';
    setSelectedModel(defaultModel);
    localStorage.setItem('llm_model', defaultModel);
  };

  const updateModel = (m: string) => {
    setSelectedModel(m);
    localStorage.setItem('llm_model', m);
  };

  const filteredHouses = detail?.filter(h => 
    h.address.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f8fafc] font-sans text-slate-900">
      
      {/* 1. Nav Rail */}
      <nav className="w-16 lg:w-20 bg-slate-900 flex flex-col items-center py-6 gap-8 z-50 border-r border-slate-800 shrink-0">
        <div className="w-10 h-10 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Home className="w-6 h-6 text-white" />
        </div>
        
        <div className="flex flex-col gap-4">
          <button 
            onClick={() => { setIsDrawerOpen(true); setPreviewData(null); }}
            className={cn(
              "p-3 rounded-2xl transition-all relative group shadow-sm",
              isDrawerOpen ? "bg-white text-slate-900" : "text-slate-400 hover:text-white hover:bg-slate-800"
            )}
            title="공고 목록"
          >
            <Library className="w-6 h-6" />
          </button>

          <button 
            onClick={() => {
              if (!isAdmin) {
                const pass = window.prompt('관리자 비밀번호를 입력하세요:');
                if (pass) {
                  setAdminPassword(pass);
                  setIsAdmin(true);
                }
              } else {
                setIsAdmin(false);
                setAdminPassword('');
              }
            }}
            className={cn(
              "p-3 rounded-2xl transition-all relative group shadow-sm",
              isAdmin ? "bg-amber-400 text-slate-900" : "text-slate-400 hover:text-white hover:bg-slate-800"
            )}
            title={isAdmin ? "관리자 모드 (ON)" : "관리자 모드 (OFF)"}
          >
            <Layers className="w-6 h-6" />
          </button>
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
              <p className="text-sm font-bold opacity-60">왼쪽 메뉴에서 공고를 선택하거나<br/>새로운 공고를 추가해주세요.</p>
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
                  <div className="flex-1 min-w-0 pr-4">
                    <h3 className={cn(
                      "font-bold text-slate-800 transition-colors leading-tight truncate",
                      selectedHouseId === house.id ? "text-indigo-700" : "group-hover:text-indigo-600"
                    )}>{house.address.split(' ').slice(0, 3).join(' ')}</h3>
                    {house.unit_no && (
                      <span className="text-[10px] font-bold text-slate-400 bg-slate-100/50 px-1.5 py-0.5 rounded-md mt-1 inline-block">
                        {house.unit_no}
                      </span>
                    )}
                  </div>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full text-[9px] font-black shrink-0">{house.house_type}</span>
                
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-300 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-500 leading-snug break-all">{house.address}</p>
                      {house.nearest_station && (
                        <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                          <span className="text-[9px] font-black px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded flex items-center gap-0.5">
                            <Layers className="w-2.5 h-2.5" /> {house.nearest_station}역
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">도보 {house.walking_time_mins}분 ({house.distance_meters}m)</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between pt-1 border-t border-slate-50">
                    <div className="flex items-center gap-2">
                      <BadgeCent className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                      <p className="text-xs font-black text-indigo-600">
                        보증금 {house.deposit.toLocaleString()} / 월 {house.monthly_rent.toLocaleString()} <span className="text-[9px] text-slate-400 font-normal ml-0.5">(만원)</span>
                      </p>
                    </div>
                    {house.extra_info && Object.keys(house.extra_info).length > 0 && (
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedHouseId(expandedHouseId === house.id ? null : house.id);
                        }}
                        className="text-[10px] font-bold text-slate-400 hover:text-indigo-600 flex items-center gap-0.5 transition-colors"
                      >
                        {expandedHouseId === house.id ? '접기' : '더보기'}
                        <ChevronRight className={cn("w-3 h-3 transition-transform", expandedHouseId === house.id && "rotate-90")} />
                      </button>
                    )}
                  </div>

                  {/* Expandable Extra Info Section */}
                  {expandedHouseId === house.id && house.extra_info && (
                    <div className="mt-3 grid grid-cols-2 gap-2 p-3 bg-white/50 rounded-2xl border border-indigo-50 animate-in slide-in-from-top-2">
                      {Object.entries(house.extra_info).map(([key, value]) => (
                        <div key={key} className="flex flex-col gap-0.5">
                          <span className="text-[8px] font-black text-slate-400 uppercase tracking-tighter">{key}</span>
                          <span className="text-[10px] font-bold text-slate-700 truncate">{String(value) || '-'}</span>
                        </div>
                      ))}
                    </div>
                  )}
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

        <div className="absolute top-6 right-6 z-40 flex items-center gap-3 animate-in fade-in slide-in-from-right-4">
          <div className="relative">
              <button 
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                className={`p-2 rounded-xl border transition-all duration-200 flex items-center gap-2 ${
                  isSettingsOpen 
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-600' 
                    : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${selectedProvider === 'openai' ? 'bg-orange-500' : 'bg-emerald-500'}`} />
                <span className="text-xs font-bold uppercase tracking-wider">
                  {selectedProvider === 'openai' ? 'GPT-4O' : 'Gemini'}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${isSettingsOpen ? 'rotate-180' : ''}`} />
              </button>

              {isSettingsOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-2xl border border-slate-200 p-2 z-50 animate-in fade-in zoom-in-95 duration-200">
                  <div className="p-2 mb-1">
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400">LLM Provider</h4>
                  </div>
                  <div className="space-y-1">
                    <button 
                      onClick={() => { updateProvider('gemini'); setIsSettingsOpen(false); }}
                      className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-colors ${selectedProvider === 'gemini' ? 'bg-emerald-50 text-emerald-700 font-bold' : 'hover:bg-slate-50 text-slate-600'}`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span className="text-sm">Gemini (Default)</span>
                      </div>
                      {selectedProvider === 'gemini' && <Check className="w-4 h-4" />}
                    </button>
                    <button 
                      onClick={() => { updateProvider('openai'); setIsSettingsOpen(false); }}
                      className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-colors ${selectedProvider === 'openai' ? 'bg-orange-50 text-orange-700 font-bold' : 'hover:bg-slate-50 text-slate-600'}`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                        <span className="text-sm">OpenAI (GPT-4o)</span>
                      </div>
                      {selectedProvider === 'openai' && <Check className="w-4 h-4" />}
                    </button>
                  </div>

                  {selectedProvider === 'openai' && (
                    <>
                      <div className="h-px bg-slate-100 my-2" />
                      <div className="p-2 mb-1">
                        <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400">GPT Model</h4>
                      </div>
                      <div className="space-y-1">
                        {['gpt-4o', 'gpt-4o-mini'].map(m => (
                          <button 
                            key={m}
                            onClick={() => { updateModel(m); setIsSettingsOpen(false); }}
                            className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-colors ${selectedModel === m ? 'bg-orange-50 text-orange-700 font-bold' : 'hover:bg-slate-50 text-slate-600'}`}
                          >
                            <span className="text-sm uppercase tracking-tighter">{m}</span>
                            {selectedModel === m && <Check className="w-4 h-4" />}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

          <button
            onClick={() => setIsDrawerOpen(true)}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-all duration-300 shadow-lg shadow-indigo-200 active:scale-95"
          >
            <Upload className="w-4 h-4" />
            <span>새 공고 분석</span>
          </button>
        </div>

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

      {/* --- Preview & Edit Overlay (Admin only) --- */}
      {previewData && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4 lg:p-12 animate-in fade-in zoom-in-95">
          <div className="bg-white w-full max-w-6xl h-full rounded-[3rem] shadow-2xl flex flex-col overflow-hidden">
            <div className="p-8 border-b border-slate-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-4">
                <div className={cn(
                  "w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg",
                  previewData.houses.length > 0 ? "bg-indigo-50 text-indigo-600" : "bg-amber-50 text-amber-600"
                )}>
                  {previewData.houses.length > 0 ? <FileText className="w-6 h-6" /> : <AlertCircle className="w-6 h-6" />}
                </div>
                <div>
                  <h2 className="text-2xl font-black text-slate-800 tracking-tight">Data Preview & Edit</h2>
                  <p className="text-sm text-slate-400 mt-1 font-medium">
                    {previewData.houses.length > 0 
                      ? `저장하기 전에 데이터를 확인하고 수정하세요. 총 ${previewData.houses.length}건이 분석되었습니다.`
                      : '분석된 주택 정보가 없습니다. 파일 내용을 확인하거나 예상 개수를 입력해 보세요.'}
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={() => setPreviewData(null)}
                  className="px-6 py-3 bg-slate-100 text-slate-600 font-bold rounded-2xl hover:bg-slate-200"
                >
                  취소
                </button>
                <button 
                  onClick={onFinalSave}
                  disabled={uploading}
                  className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-700 shadow-lg flex items-center gap-2"
                >
                  {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
                  최종 저장 및 지도로 보내기
                </button>
                <button 
                  onClick={onGeocodeAll}
                  disabled={uploading || geocodingIndices.size > 0}
                  className="px-6 py-3 bg-emerald-600 text-white font-bold rounded-2xl hover:bg-emerald-700 shadow-lg flex items-center gap-2"
                >
                  {geocodingIndices.size > 0 ? <Loader2 className="w-5 h-5 animate-spin" /> : <MapPin className="w-5 h-5" />}
                  주소 좌표 확인 (Geocode)
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-8 pt-0">
              <table className="w-full text-left border-separate border-spacing-y-2">
                <thead>
                  <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest text-center border-b border-slate-100">
                    <th className="pb-4 pl-4 text-left">#</th>
                    <th className="pb-4 text-left w-16">자치구</th>
                    <th className="pb-4 text-left w-20">단지번호</th>
                    <th className="pb-4 text-left">주소</th>
                    <th className="pb-4">호수</th>
                    <th className="pb-4">면적</th>
                    <th className="pb-4">유형</th>
                    <th className="pb-4">승강기</th>
                    <th className="pb-4">위도/경도</th>
                    <th className="pb-4">인근역/거리</th>
                    <th className="pb-4">보증금(만)</th>
                    <th className="pb-4 pr-4">월세(만)</th>
                  </tr>
                </thead>
                <tbody className="space-y-4">
                  {previewData.houses.map((h, i) => (
                    <tr key={i} className="bg-slate-50 hover:bg-indigo-50 transition-colors group">
                      <td className="pl-4 py-3 rounded-l-2xl">
                        <input 
                          type="number"
                          className="bg-transparent border-none text-[10px] font-black text-slate-400 w-8 outline-none"
                          value={h.index || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].index = parseInt(e.target.value) || 0;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3">
                        <input 
                          className="bg-transparent border-none text-[10px] font-medium text-slate-600 focus:ring-1 focus:ring-indigo-300 rounded px-1 w-16 outline-none"
                          value={h.district || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].district = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3">
                        <input 
                          className="bg-transparent border-none text-[10px] text-slate-400 focus:ring-1 focus:ring-indigo-300 rounded px-1 w-20 outline-none"
                          value={h.complex_no || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].complex_no = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3">
                        <input 
                          className="bg-transparent border-none text-[10px] text-slate-500 w-full text-left outline-none italic font-medium"
                          value={h.address}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].address = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 text-center">
                        <input 
                          className="bg-transparent border-none text-[10px] font-bold text-slate-700 w-12 text-center outline-none"
                          value={h.unit_no || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].unit_no = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 text-center">
                        <input 
                          type="number"
                          step="0.01"
                          className="bg-transparent border-none text-[10px] font-bold text-indigo-600 w-12 text-center outline-none"
                          value={h.area || 0}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].area = parseFloat(e.target.value) || 0;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 text-center">
                        <input 
                          className="bg-transparent border-none text-[9px] font-black text-amber-600 w-12 text-center outline-none"
                          value={h.house_type || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].house_type = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 text-center">
                        <input 
                          className="bg-transparent border-none text-[10px] text-slate-400 w-10 text-center outline-none"
                          value={h.elevator || ''}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].elevator = e.target.value;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 text-center">
                        <div className="flex flex-col items-center gap-0.5">
                          {geocodingIndices.has(i) ? (
                            <Loader2 className="w-3 h-3 animate-spin text-slate-300" />
                          ) : h.lat && h.lng ? (
                            <>
                              <div className="text-[8px] font-mono text-slate-400">{h.lat?.toFixed(5)}</div>
                              <div className="text-[8px] font-mono text-slate-400">{h.lng?.toFixed(5)}</div>
                            </>
                          ) : (
                            <div className="w-2 h-2 rounded-full bg-slate-200" />
                          )}
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        <div className="flex flex-col items-center gap-0.5">
                          <span className="text-[9px] font-black text-emerald-600 truncate max-w-[60px]">{h.nearest_station || '-'}</span>
                          <span className="text-[8px] text-slate-400 font-bold">{h.distance_meters ? `${h.distance_meters}m` : ''}</span>
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        <input 
                          type="number"
                          step="0.1"
                          className="bg-transparent border-none text-xs font-bold text-indigo-600 w-14 text-center outline-none"
                          value={h.deposit}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].deposit = parseFloat(e.target.value) || 0;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                      <td className="py-3 pr-4 rounded-r-2xl text-center">
                        <input 
                          type="number"
                          step="0.1"
                          className="bg-transparent border-none text-xs font-bold text-indigo-600 w-14 text-center outline-none"
                          value={h.monthly_rent}
                          onChange={(e) => {
                            const newHouses = [...previewData.houses];
                            newHouses[i].monthly_rent = parseFloat(e.target.value) || 0;
                            setPreviewData({...previewData, houses: newHouses});
                          }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* --- Library Drawer Overhaul --- */}
      {isDrawerOpen && (
        <>
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-40 animate-in fade-in duration-300" onClick={() => setIsDrawerOpen(false)} />
          <div className="fixed top-0 bottom-0 left-16 lg:left-20 w-[400px] bg-white shadow-2xl z-50 animate-in slide-in-from-left duration-500 border-r border-slate-100 flex flex-col rounded-r-3xl overflow-hidden">
            <div className="p-8 border-b border-slate-100 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-2xl font-black text-slate-800 tracking-tight">Library</h2>
                <p className="text-sm text-slate-400 mt-1 font-medium italic">분석된 공고 내역입니다.</p>
              </div>
              <button onClick={() => setIsDrawerOpen(false)} className="p-3 hover:bg-slate-100 rounded-2xl transition-colors">
                <X className="w-6 h-6 text-slate-400" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
              {isAdmin && (
                <label className={cn(
                  "p-6 rounded-[2.5rem] border-2 border-dashed transition-all cursor-pointer group flex flex-col items-center justify-center gap-2",
                  uploading ? "bg-indigo-50 border-indigo-200 cursor-not-allowed" : "bg-slate-50 border-slate-200 hover:bg-white hover:border-indigo-400 hover:shadow-xl"
                )}>
                  {uploading ? <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" /> : <Plus className="w-8 h-8 text-slate-400 group-hover:text-indigo-600" />}
                  <div className="text-center">
                    <span className="block text-sm font-black text-slate-800">새로운 공고 추가하기</span>
                  </div>
                  <input type="file" multiple className="hidden" onChange={handleFileChange} disabled={uploading} />
                </label>
              )}

              {announcements.map((a) => (
                <div 
                  key={a.id}
                  onClick={() => loadDetail(a.id)}
                  className={cn(
                    "p-6 rounded-[2.5rem] border transition-all cursor-pointer group relative overflow-hidden",
                    selectedId === a.id ? "bg-indigo-50 border-indigo-200" : "bg-white border-slate-100 hover:border-indigo-100 hover:shadow-2xl hover:-translate-y-1"
                  )}
                >
                  <div className="flex justify-between items-start">
                    <span className="px-2 py-0.5 bg-indigo-600 text-white rounded-full text-[8px] font-black uppercase tracking-widest">
                      {a.house_count || 0} UNITS
                    </span>
                    {isAdmin && (
                      <button 
                        onClick={(e) => deleteAnnouncement(e, a.id)}
                        className="p-1 text-slate-300 hover:text-red-500 transition-colors"
                      >
                       <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  <h3 className={cn("text-lg font-black text-slate-800 leading-tight my-2 group-hover:text-indigo-600", selectedId === a.id && "text-indigo-700")}>{a.title}</h3>
                  <div className="flex items-center gap-2 text-slate-400 text-[10px] font-bold uppercase truncate"><FileText className="w-3.5 h-3.5" /> {a.filename}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 4. Upload Confirmation Modal */}
      {isConfirmingUpload && (
        <>
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[70] animate-in fade-in" onClick={() => setIsConfirmingUpload(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] bg-white shadow-2xl z-[80] p-8 rounded-[2.5rem] animate-in zoom-in-95 duration-300">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-3xl flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8" />
              </div>
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">분석 시작하기</h2>
              <p className="text-sm text-slate-400 mt-2 font-medium">선택하신 {pendingFiles?.length}개의 파일을 분석합니다.</p>
            </div>
            
            <div className="space-y-4">
              {!hasServerKey && (
                <div>
                  <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2 px-1">Gemini API Key (필수)</label>
                  <input type="password" placeholder="Key..." className="w-full px-5 py-3 bg-red-50/50 border border-red-100 rounded-2xl text-sm font-bold focus:ring-2 focus:ring-red-500 outline-none transition-all" value={userApiKey} onChange={(e) => setUserApiKey(e.target.value)} />
                </div>
              )}
              <div>
                <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2 px-1">예상 주택 개수 (선택)</label>
                <input type="number" placeholder="예: 261" className="w-full px-5 py-3 bg-slate-100 border-none rounded-2xl text-lg font-bold focus:ring-2 focus:ring-indigo-500 outline-none transition-all" value={expectedCount} onChange={(e) => setExpectedCount(e.target.value)} />
              </div>

              <div className="h-px bg-slate-100 my-2" />
              
              <div>
                <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2 px-1">LLM 공급자</label>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => updateProvider('gemini')}
                    className={`px-4 py-2.5 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${selectedProvider === 'gemini' ? 'bg-emerald-50 border-emerald-500 text-emerald-700 font-bold' : 'bg-white border-slate-100 text-slate-400 hover:border-slate-200'}`}
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-sm">Gemini</span>
                  </button>
                  <button 
                    onClick={() => updateProvider('openai')}
                    className={`px-4 py-2.5 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${selectedProvider === 'openai' ? 'bg-orange-50 border-orange-500 text-orange-700 font-bold' : 'bg-white border-slate-100 text-slate-400 hover:border-slate-200'}`}
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                    <span className="text-sm">OpenAI</span>
                  </button>
                </div>
              </div>

              {selectedProvider === 'openai' && (
                <div className="animate-in slide-in-from-top-2 duration-300">
                  <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2 px-1">GPT 모델 선택</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['gpt-4o', 'gpt-4o-mini'].map(m => (
                      <button 
                        key={m}
                        onClick={() => updateModel(m)}
                        className={`px-3 py-2 rounded-xl border-2 transition-all text-xs font-bold uppercase tracking-tighter ${selectedModel === m ? 'bg-orange-50 border-orange-500 text-orange-700' : 'bg-white border-slate-100 text-slate-400 hover:border-slate-200'}`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button onClick={() => setIsConfirmingUpload(false)} className="flex-1 px-5 py-3 bg-slate-100 text-slate-600 font-bold rounded-2xl">취소</button>
                <button onClick={onFileUpload} className="flex-1 px-5 py-3 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-700 shadow-lg">분석 시작</button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 5. Coffee Donation Floating UI */}
      <div className="fixed bottom-6 right-6 lg:bottom-10 lg:right-10 z-[100] flex flex-col items-end gap-3">
        {isCoffeeOpen && (
          <div className="bg-white p-4 shadow-2xl border border-slate-100 rounded-[2rem] animate-in slide-in-from-bottom-4 duration-300 flex flex-col items-center gap-3 w-48">
            <span className="text-sm font-black text-slate-800 text-center">개발자에게 커피 사주기</span>
            <a 
              href="https://qr.kakaopay.com/Ej88F1kMG" 
              target="_blank" 
              rel="noreferrer"
              className="group hover:scale-105 transition-transform"
            >
              <picture>
                <source media="(max-width: 640px)" srcSet="http://localhost:8000/static/images/btn_send_small.png" />
                <img 
                  src="http://localhost:8000/static/images/btn_send_regular.png" 
                  alt="카카오페이" 
                  className="h-10 block filter drop-shadow-[0_4px_6px_rgba(0,0,0,0.2)] rounded-xl"
                  onError={(e) => (e.currentTarget.style.display = 'none')}
                />
              </picture>
            </a>
          </div>
        )}
        <button 
          onClick={() => setIsCoffeeOpen(!isCoffeeOpen)}
          className={cn(
            "w-12 h-12 lg:w-14 lg:h-14 bg-white shadow-2xl border border-slate-100 rounded-full flex items-center justify-center text-2xl hover:scale-110 active:scale-95 transition-all outline-none",
            isCoffeeOpen && "bg-indigo-600 border-indigo-700 shadow-indigo-200"
          )}
        >
          {isCoffeeOpen ? <X className="w-6 h-6 text-white" /> : '☕'}
        </button>
      </div>

      {/* 6. Global Loading Overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[200] flex flex-col items-center justify-center animate-in fade-in duration-300 px-4">
          <div className="bg-white/80 p-8 lg:p-12 rounded-[3.5rem] shadow-2xl flex flex-col items-center gap-8 border border-white/50 max-w-2xl w-full">
            
            <div className="relative">
              <div className="w-20 h-20 border-4 border-indigo-100 border-t-indigo-600 rounded-full animate-spin" />
              <Loader2 className="w-8 h-8 text-indigo-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
            </div>

            <div className="w-full">
              <div className="flex justify-between relative">
                {/* Connector Line */}
                <div className="absolute top-5 left-0 w-full h-0.5 bg-slate-100 -z-10" />
                <div 
                  className="absolute top-5 left-0 h-0.5 bg-indigo-600 transition-all duration-1000 -z-10" 
                  style={{ width: `${Math.max(0, (currentStep - 1) * 33.33)}%` }}
                />

                {[
                  { id: 1, label: 'AI 분석', icon: FileText },
                  { id: 2, label: '개수 검증', icon: Search },
                  { id: 3, label: '위치 추출', icon: MapPin },
                  { id: 4, label: '거리 계산', icon: Layers },
                ].map((step) => {
                  const Icon = step.icon;
                  const isActive = currentStep === step.id;
                  const isCompleted = currentStep > step.id;
                  
                  return (
                    <div key={step.id} className="flex flex-col items-center gap-3 relative bg-white/0 px-2">
                       <div className={cn(
                        "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 border-2",
                        isActive ? "bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-200 scale-110" : 
                        isCompleted ? "bg-emerald-500 border-emerald-500 text-white" : 
                        "bg-white border-slate-200 text-slate-300"
                      )}>
                        {isCompleted ? <Plus className="w-5 h-5 rotate-45" /> : <Icon className="w-5 h-5" />}
                      </div>
                      <span className={cn(
                        "text-[10px] font-black uppercase tracking-tighter transition-colors",
                        isActive ? "text-indigo-600" : isCompleted ? "text-emerald-600" : "text-slate-400"
                      )}>
                        {step.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="text-center space-y-4">
              {progressTotal > 0 && (
                <div className="flex flex-col items-center gap-1 animate-in slide-in-from-bottom-2 duration-500">
                  <div className="text-[10px] font-bold text-slate-400 mb-0.5 flex items-center gap-1 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="uppercase tracking-tighter">
                      {activeProvider === 'openai' ? 'OpenAI' : 'Gemini'}
                    </span> 
                    <span className="mx-1 opacity-20">|</span>
                    <span className="uppercase tracking-tighter text-slate-500">{activeModel || 'FLASH'}</span>
                    {activeProvider === 'gemini' && activeKeyIdx >= 0 && (
                      <span className="ml-1 px-1.5 py-0.5 bg-indigo-100/50 text-indigo-600 rounded-md font-black text-[8px] border border-indigo-200/50">
                        KEY #{activeKeyIdx + 1}
                      </span>
                    )}
                    사용 중
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-black text-indigo-600 tracking-tighter">{progressCount}</span>
                    <span className="text-slate-300 font-bold">/</span>
                    <span className="text-xl font-bold text-slate-400">{progressTotal}</span>
                  </div>
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">건 추출 완료</span>
                </div>
              )}
              <p className="text-sm font-bold text-indigo-600 animate-pulse px-4 bg-indigo-50/50 py-2 rounded-2xl border border-indigo-100/50 min-w-[280px]">
                {parsingStatus || '잠시만 기다려주세요...'}
              </p>
            </div>
          </div>
        </div>
      )}

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
