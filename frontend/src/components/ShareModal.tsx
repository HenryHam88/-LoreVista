/**
 * ShareModal – Phase 4 公开分享只读链接
 */
import { useEffect, useState } from 'react';
import { X, Link2, Copy, Check, Trash2, Loader2, ExternalLink } from 'lucide-react';

interface Props {
  storyId: number;
  storyTitle: string;
  onClose: () => void;
}

const BASE = '';

function apiHeaders(json = false): HeadersInit {
  const token = (import.meta.env.VITE_API_TOKEN as string | undefined) || '';
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { 'X-API-Token': token } : {}),
  };
}

export default function ShareModal({ storyId, storyTitle, onClose }: Props) {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [copying, setCopying] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  useEffect(() => {
    // Load existing token
    fetch(`${BASE}/api/stories/${storyId}/share-token`, {
      method: 'POST',
      headers: apiHeaders(),
    })
      .then(r => r.json())
      .then(data => { if (data.token) setToken(data.token); })
      .catch(() => {});
  }, [storyId]);

  const shareUrl = token
    ? `${window.location.origin}/#/share/${token}`
    : '';

  async function handleCreate() {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BASE}/api/stories/${storyId}/share-token`, {
        method: 'POST',
        headers: apiHeaders(),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setToken(data.token);
    } catch (err: any) {
      setError(err.message || '创建失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleRevoke() {
    if (!confirm('确定吊销分享链接？任何拥有该链接的人将无法访问。')) return;
    setLoading(true);
    try {
      await fetch(`${BASE}/api/stories/${storyId}/share-token`, {
        method: 'DELETE',
        headers: apiHeaders(),
      });
      setToken('');
    } catch (err: any) {
      setError(err.message || '吊销失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopying(true);
      setTimeout(() => setCopying(false), 2000);
    } catch {
      // fallback
      const el = document.createElement('textarea');
      el.value = shareUrl;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopying(true);
      setTimeout(() => setCopying(false), 2000);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-100 flex items-center gap-2">
            <Link2 size={15} className="text-sky-400" />
            分享「{storyTitle}」
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="px-5 py-5 space-y-4">
          <p className="text-xs text-gray-500 leading-relaxed">
            生成一个只读公开链接，任何人都可以通过这个链接浏览你的漫画作品，无需登录。
          </p>

          {error && (
            <div className="px-3 py-2 rounded-lg bg-red-900/30 border border-red-800 text-red-300 text-xs">
              {error}
            </div>
          )}

          {token ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={shareUrl}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs
                             text-gray-300 outline-none font-mono truncate"
                />
                <button
                  onClick={handleCopy}
                  className="shrink-0 flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg
                             bg-sky-700 hover:bg-sky-600 text-white transition-colors"
                  title="复制链接"
                >
                  {copying ? <Check size={13} /> : <Copy size={13} />}
                  {copying ? '已复制' : '复制'}
                </button>
              </div>
              <a
                href={shareUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300"
              >
                <ExternalLink size={12} />
                在新标签页预览
              </a>
            </div>
          ) : (
            <button
              onClick={handleCreate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium
                         rounded-lg bg-sky-600 hover:bg-sky-500 text-white
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Link2 size={15} />}
              {loading ? '生成中…' : '生成分享链接'}
            </button>
          )}

          {token && (
            <div className="pt-1 border-t border-gray-800">
              <button
                onClick={handleRevoke}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300
                           disabled:opacity-40 transition-colors"
              >
                <Trash2 size={12} />
                吊销链接（所有人将失去访问权限）
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
