/**
 * StructuredStoryboard – Phase 2 storyboard editor.
 * Shows Page/Panel records with character chips + location chips.
 * Allows editing panel descriptions and chip assignments.
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Sparkles, RefreshCw, Loader2, Pencil, Check, X, Users, MapPin,
  ChevronDown, ChevronRight, Info,
} from 'lucide-react';
import {
  generateStructuredScenes,
  getStructuredPages,
  updatePanel,
  listCharacters,
  listLocations,
  type PageData,
  type PanelData,
  type CharacterData,
  type LocationData,
} from '../api';

interface Props {
  chapterId: number;
  storyId: number;
  hasMessages: boolean;
  /** Called when scenes are generated (so parent can refresh legacy scenes too) */
  onScenesGenerated?: () => void;
}

const ROLE_COLORS: Record<string, string> = {
  protagonist: 'bg-amber-800/50 text-amber-200 border-amber-700/50',
  supporting: 'bg-sky-800/50 text-sky-200 border-sky-700/50',
  antagonist: 'bg-red-800/50 text-red-200 border-red-700/50',
  background: 'bg-gray-700/50 text-gray-400 border-gray-600/50',
};

function CharChip({ char }: { char: CharacterData }) {
  const colorCls = ROLE_COLORS[char.role] || ROLE_COLORS.background;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] rounded-full border ${colorCls}`}
      title={char.description || char.name}
    >
      <Users size={9} />
      {char.name}
    </span>
  );
}

function LocChip({ loc, locations }: { loc: LocationData; locations: LocationData[] }) {
  const parent = locations.find(l => l.id === loc.parent_id);
  const label = parent ? `${parent.name}·${loc.name}` : loc.name;
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] rounded-full bg-teal-800/50 text-teal-200 border border-teal-700/50"
      title={loc.description || label}
    >
      <MapPin size={9} />
      {label}
    </span>
  );
}

interface PanelCardProps {
  panel: PanelData;
  pageId: number;
  chapterId: number;
  charMap: Map<number, CharacterData>;
  locMap: Map<number, LocationData>;
  allLocations: LocationData[];
  onUpdated: (updated: PanelData) => void;
}

function PanelCard({ panel, pageId, chapterId, charMap, locMap, allLocations, onUpdated }: PanelCardProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(panel.description || '');
  const [saving, setSaving] = useState(false);

  const charItems = (panel.character_ids || []).map(id => charMap.get(id)).filter(Boolean) as CharacterData[];
  const locItem = panel.location_id ? locMap.get(panel.location_id) : null;

  const camLabel = panel.camera_angle;

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updatePanel(chapterId, pageId, panel.id, { description: draft });
      onUpdated(updated);
      setEditing(false);
    } catch (err: any) {
      alert(`保存失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-2.5">
      {/* Panel header row */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="shrink-0 text-[10px] text-gray-500 font-mono w-5 text-center">
          {panel.panel_number}
        </span>
        {camLabel && (
          <span className="text-[10px] text-gray-600 px-1.5 py-0.5 rounded bg-gray-800">
            {camLabel}
          </span>
        )}
        {/* Character chips */}
        <div className="flex flex-wrap gap-1 flex-1 min-w-0">
          {charItems.map(char => <CharChip key={char.id} char={char} />)}
          {locItem && <LocChip loc={locItem} locations={allLocations} />}
          {charItems.length === 0 && !locItem && (
            <span className="text-[10px] text-gray-700 italic">无角色/场景链接</span>
          )}
        </div>
        <button
          onClick={() => { setDraft(panel.description || ''); setEditing(v => !v); }}
          className="shrink-0 p-1 rounded text-gray-600 hover:text-gray-300 hover:bg-gray-800 transition-colors"
          title="编辑此格描述"
        >
          <Pencil size={11} />
        </button>
      </div>

      {/* Description */}
      {editing ? (
        <div className="space-y-1">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-xs text-gray-200 resize-none outline-none focus:border-violet-500 leading-relaxed"
            rows={3}
            autoFocus
          />
          <div className="flex justify-end gap-1.5">
            <button onClick={() => setEditing(false)} className="px-2 py-1 text-xs rounded text-gray-500 hover:bg-gray-800">取消</button>
            <button onClick={handleSave} disabled={saving} className="px-2 py-1 text-xs rounded bg-violet-600 hover:bg-violet-500 text-white disabled:opacity-40 flex items-center gap-1">
              {saving ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
              保存
            </button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">
          {panel.description || <span className="italic text-gray-600">（无描述）</span>}
        </p>
      )}

      {/* Dialogue preview */}
      {panel.dialogue && (
        <p className="mt-1 text-[11px] text-violet-300/70 italic truncate">
          {panel.dialogue}
        </p>
      )}
    </div>
  );
}

export default function StructuredStoryboard({ chapterId, storyId, hasMessages, onScenesGenerated }: Props) {
  const [pages, setPages] = useState<PageData[]>([]);
  const [charMap, setCharMap] = useState<Map<number, CharacterData>>(new Map());
  const [locMap, setLocMap] = useState<Map<number, LocationData>>(new Map());
  const [allLocations, setAllLocations] = useState<LocationData[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [expandedPages, setExpandedPages] = useState<Set<number>>(new Set());

  // Load characters + locations for chip resolution
  useEffect(() => {
    listCharacters(storyId).then(chars => {
      setCharMap(new Map(chars.map(c => [c.id, c])));
    }).catch(() => {});
    listLocations(storyId).then(locs => {
      setAllLocations(locs);
      setLocMap(new Map(locs.map(l => [l.id, l])));
    }).catch(() => {});
  }, [storyId]);

  // Load existing pages
  useEffect(() => {
    setLoading(true);
    getStructuredPages(chapterId)
      .then(ps => {
        setPages(ps);
        if (ps.length > 0) {
          setExpandedPages(new Set(ps.slice(0, 3).map(p => p.id)));
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [chapterId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setErrorMsg('');
    try {
      const newPages = await generateStructuredScenes(chapterId);
      setPages(newPages);
      setExpandedPages(new Set(newPages.slice(0, 3).map(p => p.id)));
      onScenesGenerated?.();
    } catch (err: any) {
      setErrorMsg(err.message || '生成失败');
    } finally {
      setGenerating(false);
    }
  };

  const togglePage = (pageId: number) => {
    setExpandedPages(prev => {
      const next = new Set(prev);
      if (next.has(pageId)) next.delete(pageId);
      else next.add(pageId);
      return next;
    });
  };

  const handlePanelUpdated = useCallback((pageId: number, updated: PanelData) => {
    setPages(prev => prev.map(pg =>
      pg.id !== pageId ? pg : {
        ...pg,
        panels: pg.panels.map(p => p.id === updated.id ? updated : p),
      }
    ));
  }, []);

  const totalPanels = pages.reduce((s, p) => s + p.panels.length, 0);

  return (
    <div className="space-y-3">
      {/* Header + Generate button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            结构化分镜
          </h3>
          {pages.length > 0 && (
            <span className="text-[10px] text-gray-600">
              {pages.length} 页 · {totalPanels} 格
            </span>
          )}
          {/* Legend */}
          <span
            className="hidden md:inline text-[10px] text-gray-700 cursor-help"
            title="每格显示出场角色芯片（颜色=角色类型）和场景芯片。点击铅笔图标可编辑格子描述。"
          >
            <Info size={11} />
          </span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !hasMessages}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md
                     bg-violet-600 hover:bg-violet-500 text-white
                     disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={!hasMessages ? '请先在左侧进行对话' : ''}
        >
          {generating ? (
            <><Loader2 size={12} className="animate-spin" /> 生成中…</>
          ) : (
            <><RefreshCw size={12} /> {pages.length > 0 ? '重新生成' : '生成结构化分镜'}</>
          )}
        </button>
      </div>

      {/* Error */}
      {errorMsg && (
        <div className="text-xs text-red-400 bg-red-900/20 rounded p-2">⚠ {errorMsg}</div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center gap-2 text-xs text-gray-500 py-4 justify-center">
          <Loader2 size={14} className="animate-spin" />
          加载分镜…
        </div>
      )}

      {/* Empty state */}
      {!loading && pages.length === 0 && (
        <div className="text-xs text-gray-600 py-6 text-center leading-relaxed">
          点击「生成结构化分镜」，AI 将输出每格的<br />
          角色引用、场景引用、台词、动作描述。
        </div>
      )}

      {/* Pages list */}
      {!loading && pages.map(page => {
        const isOpen = expandedPages.has(page.id);
        return (
          <div key={page.id} className="rounded-lg border border-gray-800 bg-gray-900/30 overflow-hidden">
            {/* Page header */}
            <button
              onClick={() => togglePage(page.id)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-800/40 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-300">第 {page.page_number} 页</span>
                <span className="text-gray-600">{page.panels.length} 格</span>
                {/* Quick chip preview for closed pages */}
                {!isOpen && page.panels.length > 0 && (
                  <div className="flex gap-1 flex-wrap max-w-[200px]">
                    {Array.from(new Set(
                      page.panels.flatMap(p => p.character_ids || [])
                    )).slice(0, 3).map(cid => {
                      const c = charMap.get(cid);
                      return c ? (
                        <span key={cid} className="text-[10px] text-gray-500">{c.name}</span>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
              {isOpen ? <ChevronDown size={13} className="text-gray-600" /> : <ChevronRight size={13} className="text-gray-600" />}
            </button>

            {/* Panels */}
            {isOpen && (
              <div className="px-2 pb-2 space-y-2">
                {page.panels.map(panel => (
                  <PanelCard
                    key={panel.id}
                    panel={panel}
                    pageId={page.id}
                    chapterId={chapterId}
                    charMap={charMap}
                    locMap={locMap}
                    allLocations={allLocations}
                    onUpdated={(updated) => handlePanelUpdated(page.id, updated)}
                  />
                ))}
                {page.panels.length === 0 && (
                  <p className="text-xs text-gray-600 py-2 text-center">此页暂无格子数据</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
