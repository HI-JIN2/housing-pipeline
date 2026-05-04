import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Database,
  FileText,
  KeyRound,
  Loader2,
  LogOut,
  RefreshCcw,
  Search,
  ShieldAlert,
  Trash2,
  UploadCloud,
} from 'lucide-react';
import type { House } from '../types';

const AdminPortal: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{title: string, desc: string, houses: House[]} | null>(null);
  
  // States for upload process
  const [pendingFiles, setPendingFiles] = useState<FileList | null>(null);
  const [isConfirmingUpload, setIsConfirmingUpload] = useState(false);
  const [parsingStatus, setParsingStatus] = useState('');

  type AnnouncementItem = {
    id: string;
    filename: string;
    title: string;
    description: string;
    house_count: number;
    created_at?: string;
  };

  const [stats, setStats] = useState<{ total_announcements: number; total_houses: number; latest?: { id: string; title: string } | null } | null>(null);
  const [items, setItems] = useState<AnnouncementItem[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const adminHeaders = useMemo(() => ({ 'x-admin-password': adminPassword }), [adminPassword]);

  const loadDashboard = async (opts?: { page?: number; q?: string }) => {
    const nextPage = opts?.page ?? page;
    const nextQ = opts?.q ?? q;
    const skip = (nextPage - 1) * pageSize;

    const [statsRes, listRes] = await Promise.all([
      axios.get('/api/admin/stats', { headers: adminHeaders }),
      axios.get('/api/admin/announcements', {
        headers: adminHeaders,
        params: { limit: pageSize, skip, q: nextQ || undefined },
      }),
    ]);

    setStats(statsRes.data);
    setItems(listRes.data.items);
    setTotal(listRes.data.total);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    if (!adminPassword) {
      setAuthError('비밀번호를 입력해주세요.');
      return;
    }
    try {
      await axios.get('/api/admin/auth/verify', { headers: adminHeaders });
      setIsAdminAuthenticated(true);
    } catch {
      setAuthError('비밀번호가 올바르지 않습니다.');
    }
  };

  useEffect(() => {
    if (!isAdminAuthenticated) return;
    void loadDashboard({ page: 1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdminAuthenticated]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setPendingFiles(e.target.files);
    setIsConfirmingUpload(true);
  };

  const onFileUpload = async () => {
    if (!pendingFiles) return;
    setUploading(true);
    setParsingStatus('요청 전송 중...');
    const jobId = Math.random().toString(36).substring(7);
    let pollingCancelled = false;
    let pollingTimer: number | undefined;

    const stopPolling = () => {
      pollingCancelled = true;
      if (pollingTimer !== undefined) {
        window.clearTimeout(pollingTimer);
      }
    };

    const pollStatus = async () => {
      if (pollingCancelled) return;
      try {
        const res = await axios.get(`/api/admin/status/${jobId}`, { headers: adminHeaders });

        // Show what the LLM is doing right now (server-side status)
        const msg: string | undefined = res.data.message;
        const step: string | undefined = res.data.step;
        const count: number | undefined = res.data.count;
        const totalCount: number | undefined = res.data.total;
        const err: string | undefined = res.data.error;
        if (err) {
          setParsingStatus(`오류: ${err}`);
        } else if (msg) {
          const progress = totalCount ? ` (${count ?? 0}/${totalCount})` : (count !== undefined ? ` (${count})` : '');
          setParsingStatus(`${msg}${progress}`);
        } else if (step) {
          const progress = totalCount ? ` (${count ?? 0}/${totalCount})` : (count !== undefined ? ` (${count})` : '');
          setParsingStatus(`${step}${progress}`);
        }
        
        if (res.data.result) {
          stopPolling();
          setPreviewData({
            title: res.data.result.announcement_title,
            desc: res.data.result.announcement_description,
            houses: res.data.result.houses
          });
          setUploading(false);
        }
      } catch (e) {
        console.error(e);
      } finally {
        if (!pollingCancelled) {
          pollingTimer = window.setTimeout(() => {
            void pollStatus();
          }, 2000);
        }
      }
    };

    const formData = new FormData();
    formData.append('file', pendingFiles[0]);
    
    try {
      await axios.post('/api/admin/upload', formData, {
        headers: {
          'x-job-id': jobId,
          'x-admin-password': adminPassword,
        }
      });
      setParsingStatus('문서 텍스트 추출 완료. LLM 분석을 시작했습니다...');
      void pollStatus();
    } catch {
      console.error('Upload failed');
      stopPolling();
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
        headers: adminHeaders
      });
      setPreviewData(null);
      await loadDashboard({ page: 1 });
    } catch {
      console.error('Save failed');
    } finally {
      setUploading(false);
    }
  };

  const deleteAnnouncement = async (id: string) => {
    if (!window.confirm('정말 삭제하시겠습니까? (Mongo + Postgres 데이터가 함께 정리됩니다)')) return;
    try {
      await axios.delete(`/api/admin/announcements/${id}`, { headers: adminHeaders });
      const maxPage = Math.max(1, Math.ceil((total - 1) / pageSize));
      const nextPage = Math.min(page, maxPage);
      setPage(nextPage);
      await loadDashboard({ page: nextPage });
    } catch {
      console.error('Delete failed');
    }
  };

  const logout = () => {
    setIsAdminAuthenticated(false);
    setAdminPassword('');
    setAuthError(null);
    setStats(null);
    setItems([]);
    setTotal(0);
    setQ('');
    setPage(1);
  };

  if (!isAdminAuthenticated) {
    return (
      <div className="min-h-screen w-screen bg-[#0b1220] text-slate-100 flex items-center justify-center px-4">
        <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl overflow-hidden">
          <div className="p-8 border-b border-white/10">
            <div className="w-12 h-12 rounded-2xl bg-emerald-400/20 text-emerald-300 flex items-center justify-center mb-4">
              <Database className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-black tracking-tight">Admin Dashboard</h1>
            <p className="text-sm text-slate-300/80 font-medium mt-1">/admin 은 관리자 전용입니다. 서버에서 비밀번호를 검증합니다.</p>
          </div>

          <form onSubmit={handleLogin} className="p-8 space-y-4">
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-300/70 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                placeholder="ADMIN PASSWORD"
                className="w-full pl-11 pr-4 py-4 rounded-2xl bg-white/10 border border-white/10 focus:ring-2 focus:ring-emerald-400/60 outline-none font-bold"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
              />
            </div>

            {authError && (
              <div className="flex items-start gap-2 rounded-2xl bg-red-500/10 border border-red-400/20 px-4 py-3 text-sm text-red-200">
                <ShieldAlert className="w-4 h-4 mt-0.5" />
                <span className="font-bold">{authError}</span>
              </div>
            )}

            <button className="w-full py-4 rounded-2xl bg-emerald-500 text-emerald-950 font-black hover:bg-emerald-400 transition-all">
              서버 검증 후 입장
            </button>

            <a href="/" className="block text-center text-sm text-slate-300/80 font-bold hover:text-white">
              사용자 화면으로 돌아가기
            </a>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-screen bg-[#0b1220] text-slate-100 flex overflow-hidden">
      <aside className="w-[280px] shrink-0 border-r border-white/10 bg-white/5 backdrop-blur-xl p-6 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-400/20 text-emerald-300 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-black tracking-tight">공고zip</div>
              <div className="text-xs text-slate-300/70 font-bold">Admin DB Console</div>
            </div>
          </div>
          <button onClick={logout} className="p-2 rounded-xl hover:bg-white/10" title="로그아웃">
            <LogOut className="w-4 h-4 text-slate-200" />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs text-slate-300/70 font-black uppercase tracking-widest">Announcements</div>
            <div className="text-2xl font-black mt-1">{stats ? stats.total_announcements.toLocaleString() : '-'}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs text-slate-300/70 font-black uppercase tracking-widest">Total Houses</div>
            <div className="text-2xl font-black mt-1">{stats ? stats.total_houses.toLocaleString() : '-'}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs text-slate-300/70 font-black uppercase tracking-widest">Latest</div>
            <div className="text-sm font-black mt-2 overflow-hidden text-ellipsis whitespace-nowrap">{stats?.latest?.title || '-'}</div>
          </div>
        </div>

        <label className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl bg-emerald-500 text-emerald-950 font-black hover:bg-emerald-400 transition-all cursor-pointer">
          <UploadCloud className="w-5 h-5" /> 새 공고 업로드
          <input type="file" className="hidden" onChange={handleFileChange} />
        </label>

        <a href="/" className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-white/10 hover:bg-white/5 font-black text-slate-200">
          사용자 화면
        </a>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="p-6 border-b border-white/10 bg-white/5 backdrop-blur-xl flex items-center justify-between gap-4 shrink-0">
          <div>
            <h2 className="text-2xl font-black tracking-tight">데이터베이스 관리</h2>
            <p className="text-sm text-slate-300/70 font-bold">Mongo(원본/파싱) + Postgres(보강) 데이터를 관리합니다.</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadDashboard({ page: 1 })}
              className="px-4 py-2 rounded-2xl border border-white/10 hover:bg-white/5 font-black flex items-center gap-2"
              title="새로고침"
            >
              <RefreshCcw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </header>

        <div className="p-6 flex items-center gap-3 shrink-0">
          <div className="relative flex-1 max-w-2xl">
            <Search className="w-4 h-4 text-slate-300/70 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setPage(1);
                  void loadDashboard({ page: 1, q });
                }
              }}
              placeholder="제목/설명/파일명 검색 (Enter)"
              className="w-full pl-11 pr-4 py-3 rounded-2xl bg-white/5 border border-white/10 outline-none focus:ring-2 focus:ring-emerald-400/50 font-bold"
            />
          </div>
          <button
            onClick={() => {
              setPage(1);
              void loadDashboard({ page: 1, q });
            }}
            className="px-4 py-3 rounded-2xl border border-white/10 hover:bg-white/5 font-black"
          >
            검색
          </button>
        </div>

        <div className="flex-1 overflow-auto px-6 pb-6">
          <div className="rounded-3xl border border-white/10 bg-black/20 overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
              <div className="text-sm font-black">Announcements</div>
              <div className="text-xs text-slate-300/70 font-bold">Total: {total.toLocaleString()}</div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="text-xs text-slate-300/70 font-black uppercase tracking-widest">
                  <tr className="border-b border-white/10">
                    <th className="px-6 py-4">Title</th>
                    <th className="px-6 py-4">File</th>
                    <th className="px-6 py-4">Houses</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {items.map((a) => (
                    <tr key={a.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-black">{a.title}</div>
                        {a.description ? (
                          <div className="text-xs text-slate-300/70 font-bold mt-1 overflow-hidden text-ellipsis whitespace-nowrap">{a.description}</div>
                        ) : null}
                      </td>
                      <td className="px-6 py-4 text-slate-200/90 font-bold">
                        <span className="inline-flex items-center gap-2">
                          <FileText className="w-4 h-4 text-slate-300/70" />
                          {a.filename}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-white/5 border border-white/10 font-black">
                          {a.house_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => deleteAnnouncement(a.id)}
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-2xl bg-red-500/10 border border-red-400/20 text-red-200 font-black hover:bg-red-500/15"
                        >
                          <Trash2 className="w-4 h-4" /> Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-6 py-16 text-center text-slate-300/70 font-black">
                        검색 결과가 없습니다.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
              <div className="text-xs text-slate-300/70 font-bold">
                Page {page} / {Math.max(1, Math.ceil(total / pageSize))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const next = Math.max(1, page - 1);
                    setPage(next);
                    void loadDashboard({ page: next });
                  }}
                  disabled={page <= 1}
                  className="px-4 py-2 rounded-2xl border border-white/10 hover:bg-white/5 font-black disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  onClick={() => {
                    const maxPage = Math.max(1, Math.ceil(total / pageSize));
                    const next = Math.min(maxPage, page + 1);
                    setPage(next);
                    void loadDashboard({ page: next });
                  }}
                  disabled={page >= Math.ceil(total / pageSize)}
                  className="px-4 py-2 rounded-2xl border border-white/10 hover:bg-white/5 font-black disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Preview Overlay */}
      {previewData && (
        <div className="fixed inset-0 bg-slate-900/60 z-[100] flex items-center justify-center p-8 animate-in fade-in duration-300">
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
               <div className="flex-1 overflow-auto p-10 custom-scrollbar">
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
                       {previewData.houses.slice(0, 300).map((h, i) => (
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
                <UploadCloud className="w-10 h-10" />
              </div>
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">분석 시작</h2>
              <p className="text-sm text-slate-400 mt-2 mb-8">서버 `.env`에 설정된 Gemini 키로 공고 내용을 파싱합니다.</p>

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
