/**
 * ExtractPanel – 🪄 自动抽取人物/场景
 * Phase 2: One-click extraction of characters and locations from novel text.
 */
import { useState } from 'react';
import { Sparkles, Users, MapPin, Check, X, Loader2, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import {
  extractCharacters,
  extractLocations,
  type ExtractionResult,
  type CharacterData,
  type LocationData,
} from '../api';

interface Props {
  storyId: number;
  /** Called after extraction so parent can refresh character/location lists */
  onExtracted?: () => void;
}

type ExtractionState = 'idle' | 'loading' | 'done' | 'error';

interface TabResult {
  state: ExtractionState;
  result: ExtractionResult | null;
  error: string;
}

const emptyTab = (): TabResult => ({ state: 'idle', result: null, error: '' });

export default function ExtractPanel({ storyId, onExtracted }: Props) {
  const [charTab, setCharTab] = useState<TabResult>(emptyTab());
  const [locTab, setLocTab] = useState<TabResult>(emptyTab());
  const [activeTab, setActiveTab] = useState<'characters' | 'locations'>('characters');
  const [expanded, setExpanded] = useState(true);

  const handleExtractChars = async () => {
    setCharTab({ state: 'loading', result: null, error: '' });
    try {
      const result = await extractCharacters(storyId);
      setCharTab({ state: 'done', result, error: '' });
      onExtracted?.();
    } catch (err: any) {
      setCharTab({ state: 'error', result: null, error: err.message || '提取失败' });
    }
  };

  const handleExtractLocs = async () => {
    setLocTab({ state: 'loading', result: null, error: '' });
    try {
      const result = await extractLocations(storyId);
      setLocTab({ state: 'done', result, error: '' });
      onExtracted?.();
    } catch (err: any) {
      setLocTab({ state: 'error', result: null, error: err.message || '提取失败' });
    }
  };

  const tab = activeTab === 'characters' ? charTab : locTab;

  return (
    <div className="rounded-lg border border-amber-700/40 bg-amber-900/10 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-semibold text-amber-300 hover:bg-amber-900/20 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Sparkles size={13} className="text-amber-400" />
          🪄 自动抽取人物 / 场景
          <span className="text-[10px] font-normal text-amber-600">（半自动，点击触发）</span>
        </span>
        {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
      </button>

      {expanded && (
        <div className="px-3 pb-3">
          {/* Sub-tab bar */}
          <div className="flex gap-1 mb-3">
            <button
              onClick={() => setActiveTab('characters')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded-md transition-colors ${
                activeTab === 'characters'
                  ? 'bg-amber-700/40 text-amber-200'
                  : 'text-amber-500 hover:text-amber-300'
              }`}
            >
              <Users size={11} /> 人物
              {charTab.result && (
                <span className="ml-1 px-1 py-0.5 text-[10px] rounded bg-emerald-700/50 text-emerald-300">
                  +{charTab.result.created.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('locations')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded-md transition-colors ${
                activeTab === 'locations'
                  ? 'bg-amber-700/40 text-amber-200'
                  : 'text-amber-500 hover:text-amber-300'
              }`}
            >
              <MapPin size={11} /> 场景
              {locTab.result && (
                <span className="ml-1 px-1 py-0.5 text-[10px] rounded bg-emerald-700/50 text-emerald-300">
                  +{locTab.result.created.length}
                </span>
              )}
            </button>
          </div>

          {/* Action button */}
          <button
            onClick={activeTab === 'characters' ? handleExtractChars : handleExtractLocs}
            disabled={tab.state === 'loading'}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md
                       bg-amber-600 hover:bg-amber-500 text-gray-950 disabled:opacity-50 transition-colors mb-3"
          >
            {tab.state === 'loading' ? (
              <><Loader2 size={12} className="animate-spin" /> AI 分析中…</>
            ) : (
              <>
                <Sparkles size={12} />
                {activeTab === 'characters' ? '🪄 从小说正文抽取人物' : '🪄 从小说正文抽取场景'}
              </>
            )}
          </button>

          {/* Results */}
          {tab.state === 'error' && (
            <div className="text-xs text-red-400 bg-red-900/20 rounded p-2 mb-2">
              ⚠ {tab.error}
            </div>
          )}

          {tab.state === 'done' && tab.result && (
            <div className="space-y-2">
              {/* Created */}
              {tab.result.created.length > 0 && (
                <div>
                  <p className="text-[10px] text-emerald-400 font-medium mb-1 flex items-center gap-1">
                    <Check size={10} /> 新建 {tab.result.created.length} 个
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {tab.result.created.map((item) => (
                      <span
                        key={item.id}
                        className="px-2 py-0.5 text-[11px] rounded-full bg-emerald-900/40 text-emerald-300 border border-emerald-700/50"
                      >
                        {item.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Merged */}
              {tab.result.merged.length > 0 && (
                <div>
                  <p className="text-[10px] text-blue-400 font-medium mb-1 flex items-center gap-1">
                    <RefreshCw size={10} /> 合并 {tab.result.merged.length} 个
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {tab.result.merged.map((item) => (
                      <span
                        key={item.id}
                        className="px-2 py-0.5 text-[11px] rounded-full bg-blue-900/40 text-blue-300 border border-blue-700/50"
                        title={`匹配自：${item.matched_from}`}
                      >
                        {item.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Skipped */}
              {tab.result.skipped.length > 0 && (
                <div>
                  <p className="text-[10px] text-gray-500 font-medium mb-1 flex items-center gap-1">
                    <X size={10} /> 跳过 {tab.result.skipped.length} 个
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {tab.result.skipped.map((item, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-[11px] rounded-full bg-gray-800 text-gray-500 border border-gray-700"
                        title={item.reason}
                      >
                        {item.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {tab.result.created.length === 0 && tab.result.merged.length === 0 && (
                <p className="text-xs text-gray-500">未发现新{activeTab === 'characters' ? '人物' : '场景'}，已有的已合并。</p>
              )}
            </div>
          )}

          {tab.state === 'idle' && (
            <p className="text-[11px] text-amber-700 leading-relaxed">
              AI 会分析所有章节的小说正文，自动识别
              {activeTab === 'characters' ? '出场角色、外貌特征、身份' : '场景地点、环境描述'}，
              并与已有{activeTab === 'characters' ? '人物库' : '场景库'}进行模糊匹配合并。
            </p>
          )}
        </div>
      )}
    </div>
  );
}
