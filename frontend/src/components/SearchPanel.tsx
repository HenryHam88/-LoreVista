/**
 * SearchPanel – Phase 4 跨章节搜索
 * 可嵌入侧边栏或作为 Modal 使用。
 */
import { useEffect, useRef, useState } from 'react';
import { Search, X, BookOpenText, Loader2, FileText, MessageSquare, Image, Hash } from 'lucide-react';

interface SearchHit {
  type: 'title' | 'novel_content' | 'chat_message' | 'scenes' | 'image_prompt';
  snippet: string;
  context: string | null;
}

interface SearchResult {
  chapter_id: number;
  chapter_number: number;
  title: string;
  hits: SearchHit[];
}

interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}

interface Props {
  storyId: number;
  onSelectChapter?: (chapterId: number) => void;
  onClose?: () => void;
}

const BASE = '';

function apiHeaders(): HeadersInit {
  const token = (import.meta.env.VITE_API_TOKEN as string | undefined) || '';
  return token ? { 'X-API-Token': token } : {};
}

const HIT_TYPE_ICONS: Record<string, React.ReactNode> = {
  title: <Hash size={11} />,
  novel_content: <FileText size={11} />,
  chat_message: <MessageSquare size={11} />,
  scenes: <BookOpenText size={11} />,
  image_prompt: <Image size={11} />,
};

const HIT_TYPE_LABELS: Record<string, string> = {
  title: '标题',
  novel_content: '正文',
  chat_message: '对话',
  scenes: '分镜',
  image_prompt: '提示词',
};

function highlight(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const lower = text.toLowerCase();
  const qLower = query.toLowerCase();
  const idx = lower.indexOf(qLower);
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-amber-400/30 text-amber-200 rounded px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export default function SearchPanel({ storyId, onSelectChapter, onClose }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      setTotal(0);
      setSearched(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      doSearch(query.trim());
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, storyId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function doSearch(q: string) {
    setLoading(true);
    try {
      const res = await fetch(
        `${BASE}/api/stories/${storyId}/search?q=${encodeURIComponent(q)}`,
        { headers: apiHeaders() },
      );
      if (!res.ok) throw new Error(await res.text());
      const data: SearchResponse = await res.json();
      setResults(data.results);
      setTotal(data.total);
      setSearched(true);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 bg-gray-900 border border-gray-800
                        rounded-lg px-3 py-2 focus-within:border-violet-500 transition-colors">
          <Search size={14} className="text-gray-500 shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="搜索正文、对话、分镜…"
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none"
          />
          {query && (
            <button
              onClick={() => { setQuery(''); setResults([]); setSearched(false); }}
              className="text-gray-600 hover:text-gray-300 transition-colors"
            >
              <X size={13} />
            </button>
          )}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-12 text-gray-500">
            <Loader2 size={20} className="animate-spin" />
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-600">
            <Search size={28} className="mb-3 opacity-40" />
            <p className="text-sm">没有找到「{query}」相关内容</p>
          </div>
        )}

        {!loading && !searched && !query && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-700">
            <Search size={28} className="mb-3 opacity-30" />
            <p className="text-sm">输入关键词搜索</p>
            <p className="text-xs mt-1 text-gray-700">可搜索正文、对话、分镜、提示词</p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="p-3 space-y-2">
            <p className="text-xs text-gray-600 px-1">
              找到 <span className="text-amber-400">{total}</span> 条匹配，共 {results.length} 话
            </p>
            {results.map(result => (
              <div
                key={result.chapter_id}
                className="rounded-lg border border-gray-800 bg-gray-900/60 overflow-hidden"
              >
                {/* Chapter header */}
                <button
                  onClick={() => onSelectChapter?.(result.chapter_id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left
                             hover:bg-gray-800/50 transition-colors"
                >
                  <BookOpenText size={13} className="text-violet-400 shrink-0" />
                  <span className="text-sm font-medium text-gray-200">
                    第 {result.chapter_number} 话
                    {result.title && (
                      <span className="font-normal text-gray-400 ml-1">· {result.title}</span>
                    )}
                  </span>
                  <span className="ml-auto text-xs text-gray-600">
                    {result.hits.length} 处
                  </span>
                </button>

                {/* Hits */}
                <div className="divide-y divide-gray-800/50">
                  {result.hits.map((hit, i) => (
                    <button
                      key={i}
                      onClick={() => onSelectChapter?.(result.chapter_id)}
                      className="w-full flex items-start gap-2.5 px-3 py-2 text-left
                                 hover:bg-gray-800/40 transition-colors"
                    >
                      <span className="flex items-center gap-1 shrink-0 mt-0.5 text-[10px]
                                       text-gray-600 w-14">
                        {HIT_TYPE_ICONS[hit.type]}
                        {HIT_TYPE_LABELS[hit.type]}
                        {hit.context && <span className="text-gray-700">({hit.context})</span>}
                      </span>
                      <p className="flex-1 text-xs text-gray-400 leading-relaxed line-clamp-2">
                        {highlight(hit.snippet, query)}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
