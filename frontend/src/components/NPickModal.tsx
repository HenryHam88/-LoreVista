/**
 * NPickModal – Phase 4 N选1出图
 * 为一个格子生成 4 张候选图，用户点击选一张确认。
 */
import { useEffect, useState } from 'react';
import { Loader2, X, Check, RefreshCw, Sparkles } from 'lucide-react';
import { mangaThumbUrl } from '../api';

export interface NPickCandidate {
  id: number;
  chapter_id: number;
  image_number: number;
  image_path: string;
  prompt: string | null;
  is_selected: boolean;
  created_at: string;
}

interface Props {
  chapterId: number;
  imageNumber: number;
  scenePrompt: string;
  onConfirm: (candidate: NPickCandidate) => void;
  onClose: () => void;
}

const BASE = '';

function apiHeaders(json = false): HeadersInit {
  const keys = {
    deepseekApiKey: localStorage.getItem('lorevista.deepseekApiKey') || '',
    imageApiKey: localStorage.getItem('lorevista.imageApiKey') || '',
  };
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(keys.deepseekApiKey ? { 'X-DeepSeek-API-Key': keys.deepseekApiKey } : {}),
    ...(keys.imageApiKey ? { 'X-Image-API-Key': keys.imageApiKey } : {}),
  };
}

export default function NPickModal({ chapterId, imageNumber, scenePrompt, onConfirm, onClose }: Props) {
  const [candidates, setCandidates] = useState<NPickCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState<number | null>(null);
  const [error, setError] = useState('');

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  // Load existing candidates, or generate fresh ones
  useEffect(() => {
    loadOrGenerate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadOrGenerate() {
    setLoading(true);
    setError('');
    try {
      // Check for existing candidates
      const listRes = await fetch(
        `${BASE}/api/chapters/${chapterId}/npick/${imageNumber}`,
        { headers: apiHeaders() },
      );
      if (listRes.ok) {
        const existing: NPickCandidate[] = await listRes.json();
        if (existing.length > 0) {
          setCandidates(existing);
          setLoading(false);
          return;
        }
      }
      // Generate fresh
      await generate();
    } catch (err: any) {
      setError(err.message || '加载失败');
      setLoading(false);
    }
  }

  async function generate() {
    setLoading(true);
    setError('');
    setCandidates([]);
    try {
      const res = await fetch(
        `${BASE}/api/chapters/${chapterId}/npick/${imageNumber}`,
        { method: 'POST', headers: apiHeaders() },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      const data: NPickCandidate[] = await res.json();
      setCandidates(data);
    } catch (err: any) {
      setError(err.message || '生成失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(cand: NPickCandidate) {
    setConfirming(cand.id);
    try {
      const res = await fetch(
        `${BASE}/api/chapters/${chapterId}/npick/${imageNumber}/confirm/${cand.id}`,
        { method: 'POST', headers: apiHeaders() },
      );
      if (!res.ok) throw new Error(await res.text());
      onConfirm(cand);
    } catch (err: any) {
      setError(err.message || '确认失败');
    } finally {
      setConfirming(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-4xl shadow-2xl flex flex-col max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-gray-100 flex items-center gap-2">
              <Sparkles size={15} className="text-amber-400" />
              N选1出图 — 第 {imageNumber} 格
            </h3>
            <p className="mt-0.5 text-xs text-gray-500 line-clamp-1 max-w-lg">{scenePrompt}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-gray-400">
              <Loader2 size={36} className="animate-spin text-amber-400" />
              <div className="text-center">
                <p className="text-sm font-medium">正在生成 4 张候选图…</p>
                <p className="text-xs text-gray-600 mt-1">并行出图，预计 30-60 秒</p>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-900/30 border border-red-800 text-red-300 text-sm">
              ⚠ {error}
            </div>
          )}

          {!loading && candidates.length > 0 && (
            <>
              <p className="text-xs text-gray-500 mb-4">
                点击任意一张图片确认选择。其余候选图将被删除。
              </p>
              <div className="grid grid-cols-2 gap-4">
                {candidates.map((cand, idx) => (
                  <div
                    key={cand.id}
                    className="group relative rounded-xl overflow-hidden border border-gray-700
                               hover:border-amber-500 transition-all cursor-pointer"
                    onClick={() => !confirming && handleConfirm(cand)}
                  >
                    <img
                      src={mangaThumbUrl(cand.image_path, 720)!}
                      alt={`候选 ${idx + 1}`}
                      className={`w-full block ${confirming === cand.id ? 'opacity-50' : ''}`}
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors
                                    flex items-center justify-center">
                      {confirming === cand.id ? (
                        <Loader2 size={32} className="animate-spin text-white" />
                      ) : (
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity
                                        flex items-center gap-2 px-4 py-2 rounded-full
                                        bg-amber-500 text-gray-950 text-sm font-semibold">
                          <Check size={16} />
                          选这张
                        </div>
                      )}
                    </div>
                    <div className="absolute top-2 left-2 w-6 h-6 rounded-full bg-black/70
                                    flex items-center justify-center text-xs text-white font-mono">
                      {idx + 1}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {!loading && candidates.length === 0 && !error && (
            <div className="text-center py-12 text-gray-600">
              <Sparkles size={32} className="mx-auto mb-3 opacity-40" />
              <p className="text-sm">点击下方按钮生成候选图</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 flex items-center justify-between gap-3 px-5 py-3 border-t border-gray-800">
          <button
            onClick={generate}
            disabled={loading || !!confirming}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg
                       bg-gray-800 hover:bg-gray-700 text-gray-300
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={13} />
            重新生成 4 张
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800
                       rounded-lg transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
