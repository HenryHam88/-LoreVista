/**
 * AssetLibrary – Phase 1 right-side panel: 人物库 / 场景库
 * Displays character cards and location cards for the current story.
 */
import { useEffect, useState } from 'react';
import {
  Plus,
  Trash2,
  Users,
  MapPin,
  ChevronRight,
  X,
  Check,
  Pencil,
  Loader2,
  Shirt,
} from 'lucide-react';
import {
  listCharacters,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  listLocations,
  createLocation,
  updateLocation,
  deleteLocation,
  migrateCharacterProfiles,
  type CharacterData,
  type LocationData,
} from '../api';

type Tab = 'characters' | 'locations';

const ROLE_LABELS: Record<string, string> = {
  protagonist: '主角',
  supporting: '配角',
  antagonist: '反派',
  background: '路人',
};

const ROLE_COLORS: Record<string, string> = {
  protagonist: 'bg-amber-500/20 text-amber-300 border-amber-600/50',
  supporting: 'bg-sky-500/20 text-sky-300 border-sky-600/50',
  antagonist: 'bg-red-500/20 text-red-300 border-red-600/50',
  background: 'bg-gray-500/20 text-gray-400 border-gray-600/50',
};

interface Props {
  storyId: number | null;
}

export default function AssetLibrary({ storyId }: Props) {
  const [tab, setTab] = useState<Tab>('characters');
  const [characters, setCharacters] = useState<CharacterData[]>([]);
  const [locations, setLocations] = useState<LocationData[]>([]);
  const [loading, setLoading] = useState(false);

  // Character form
  const [showCharForm, setShowCharForm] = useState(false);
  const [charName, setCharName] = useState('');
  const [charRole, setCharRole] = useState('supporting');
  const [charDesc, setCharDesc] = useState('');
  const [charSaving, setCharSaving] = useState(false);

  // Character edit
  const [editingCharId, setEditingCharId] = useState<number | null>(null);
  const [editCharName, setEditCharName] = useState('');
  const [editCharRole, setEditCharRole] = useState('');
  const [editCharDesc, setEditCharDesc] = useState('');

  // Location form
  const [showLocForm, setShowLocForm] = useState(false);
  const [locName, setLocName] = useState('');
  const [locParentId, setLocParentId] = useState<number | null>(null);
  const [locDesc, setLocDesc] = useState('');
  const [locSaving, setLocSaving] = useState(false);

  // Location edit
  const [editingLocId, setEditingLocId] = useState<number | null>(null);
  const [editLocName, setEditLocName] = useState('');
  const [editLocDesc, setEditLocDesc] = useState('');

  // Migration
  const [migrating, setMigrating] = useState(false);
  // Load data when storyId or tab changes
  useEffect(() => {
    if (!storyId) {
      setCharacters([]);
      setLocations([]);
      return;
    }
    setLoading(true);
    if (tab === 'characters') {
      listCharacters(storyId)
        .then(setCharacters)
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      listLocations(storyId)
        .then(setLocations)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [storyId, tab]);

  // ─── Character handlers ───────────────────────────────

  const handleCreateChar = async () => {
    if (!storyId || !charName.trim()) return;
    setCharSaving(true);
    try {
      const created = await createCharacter(storyId, {
        name: charName.trim(),
        role: charRole,
        description: charDesc.trim() || undefined,
      });
      setCharacters((prev) => [...prev, created]);
      setCharName('');
      setCharRole('supporting');
      setCharDesc('');
      setShowCharForm(false);
    } catch (err: any) {
      alert(`创建失败: ${err.message}`);
    } finally {
      setCharSaving(false);
    }
  };

  const handleDeleteChar = async (id: number) => {
    if (!storyId) return;
    if (!confirm('确定删除此角色？关联的造型也会一并删除。')) return;
    try {
      await deleteCharacter(storyId, id);
      setCharacters((prev) => prev.filter((c) => c.id !== id));
    } catch (err: any) {
      alert(`删除失败: ${err.message}`);
    }
  };

  const startEditChar = (char: CharacterData) => {
    setEditingCharId(char.id);
    setEditCharName(char.name);
    setEditCharRole(char.role);
    setEditCharDesc(char.description || '');
  };

  const cancelEditChar = () => {
    setEditingCharId(null);
  };

  const commitEditChar = async () => {
    if (!storyId || editingCharId === null) return;
    try {
      const updated = await updateCharacter(storyId, editingCharId, {
        name: editCharName.trim() || undefined,
        role: editCharRole || undefined,
        description: editCharDesc.trim(),
      });
      setCharacters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err: any) {
      alert(`更新失败: ${err.message}`);
    } finally {
      setEditingCharId(null);
    }
  };

  // ─── Location handlers ────────────────────────────────

  const handleCreateLoc = async () => {
    if (!storyId || !locName.trim()) return;
    setLocSaving(true);
    try {
      const created = await createLocation(storyId, {
        name: locName.trim(),
        parent_id: locParentId,
        description: locDesc.trim() || undefined,
      });
      setLocations((prev) => [...prev, created]);
      setLocName('');
      setLocParentId(null);
      setLocDesc('');
      setShowLocForm(false);
    } catch (err: any) {
      alert(`创建失败: ${err.message}`);
    } finally {
      setLocSaving(false);
    }
  };

  const handleDeleteLoc = async (id: number) => {
    if (!storyId) return;
    if (!confirm('确定删除此场景？子场景也会一并删除。')) return;
    try {
      await deleteLocation(storyId, id);
      setLocations((prev) => prev.filter((l) => l.id !== id));
    } catch (err: any) {
      alert(`删除失败: ${err.message}`);
    }
  };

  const startEditLoc = (loc: LocationData) => {
    setEditingLocId(loc.id);
    setEditLocName(loc.name);
    setEditLocDesc(loc.description || '');
  };

  const cancelEditLoc = () => {
    setEditingLocId(null);
  };

  const commitEditLoc = async () => {
    if (!storyId || editingLocId === null) return;
    try {
      const updated = await updateLocation(storyId, editingLocId, {
        name: editLocName.trim() || undefined,
        description: editLocDesc.trim(),
      });
      setLocations((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch (err: any) {
      alert(`更新失败: ${err.message}`);
    } finally {
      setEditingLocId(null);
    }
  };

  // Build breadcrumb for a location
  const getBreadcrumb = (loc: LocationData): string => {
    if (!loc.parent_id) return loc.name;
    const parent = locations.find((l) => l.id === loc.parent_id);
    if (!parent) return loc.name;
    return `${parent.name} › ${loc.name}`;
  };

  if (!storyId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm">
        请先选择一个故事
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Header with tabs */}
      <div className="px-4 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-1 bg-gray-900 rounded-lg p-1 border border-gray-800">
          <button
            onClick={() => setTab('characters')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex-1 justify-center ${
              tab === 'characters'
                ? 'bg-violet-600 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Users size={13} />
            人物库
          </button>
          <button
            onClick={() => setTab('locations')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex-1 justify-center ${
              tab === 'locations'
                ? 'bg-violet-600 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <MapPin size={13} />
            场景库
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-gray-500">
            <Loader2 size={20} className="animate-spin" />
          </div>
        ) : tab === 'characters' ? (
          <>
            {/* Character list */}
            {characters.length === 0 && !showCharForm && (
              <div className="text-center py-10 text-gray-600 text-sm">
                <Users size={32} className="mx-auto mb-3 opacity-40" />
                <p>还没有角色</p>
                <p className="text-xs text-gray-700 mt-1">点击下方 + 创建第一个角色</p>
                {/* Migration button */}
                <button
                  onClick={async () => {
                    if (!storyId) return;
                    setMigrating(true);
                    try {
                      const migrated = await migrateCharacterProfiles(storyId);
                      setCharacters(migrated);
                    } catch (err: any) {
                      if (err.message?.includes('No character profiles')) {
                        alert('没有找到旧的角色设定文本可以迁移');
                      } else if (err.message?.includes('already has structured')) {
                        alert('已经有结构化角色数据了');
                      } else {
                        alert(`迁移失败: ${err.message}`);
                      }
                    } finally {
                      setMigrating(false);
                    }
                  }}
                  disabled={migrating}
                  className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                             bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-700/50
                             transition-colors disabled:opacity-40"
                >
                  {migrating ? (
                    <><Loader2 size={12} className="animate-spin" />迁移中…</>
                  ) : (
                    '从旧角色设定一键迁移'
                  )}
                </button>
              </div>
            )}
            <div className="space-y-2">
              {characters.map((char) =>
                editingCharId === char.id ? (
                  <div key={char.id} className="rounded-lg border border-violet-700/50 bg-gray-900 p-3 space-y-2">
                    <input
                      value={editCharName}
                      onChange={(e) => setEditCharName(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-violet-500"
                      placeholder="角色名"
                    />
                    <select
                      value={editCharRole}
                      onChange={(e) => setEditCharRole(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 outline-none"
                    >
                      <option value="protagonist">主角</option>
                      <option value="supporting">配角</option>
                      <option value="antagonist">反派</option>
                      <option value="background">路人</option>
                    </select>
                    <textarea
                      value={editCharDesc}
                      onChange={(e) => setEditCharDesc(e.target.value)}
                      rows={2}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 resize-none outline-none focus:border-violet-500"
                      placeholder="角色描述/备注（可选）"
                    />
                    <div className="flex justify-end gap-2">
                      <button onClick={cancelEditChar} className="px-2 py-1 text-xs text-gray-400 hover:text-white">
                        <X size={13} />
                      </button>
                      <button onClick={commitEditChar} className="px-2 py-1 text-xs text-emerald-400 hover:text-emerald-300">
                        <Check size={13} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    key={char.id}
                    className="group rounded-lg border border-gray-800 bg-gray-900/70 p-3 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      {/* Avatar placeholder */}
                      <div className="w-10 h-10 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0 text-gray-500 text-sm font-bold">
                        {char.name.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-100 truncate">{char.name}</span>
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                              ROLE_COLORS[char.role] || ROLE_COLORS.background
                            }`}
                          >
                            {ROLE_LABELS[char.role] || char.role}
                          </span>
                        </div>
                        {char.description && (
                          <p className="mt-1 text-xs text-gray-500 line-clamp-2">{char.description}</p>
                        )}
                        {char.outfits && char.outfits.length > 0 && (
                          <div className="mt-1.5 flex items-center gap-1 text-[10px] text-gray-600">
                            <Shirt size={10} />
                            <span>{char.outfits.length} 套造型</span>
                          </div>
                        )}
                      </div>
                      {/* Actions */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        <button
                          onClick={() => startEditChar(char)}
                          className="p-1.5 rounded text-gray-500 hover:text-violet-400 hover:bg-gray-800"
                          title="编辑"
                        >
                          <Pencil size={12} />
                        </button>
                        <button
                          onClick={() => handleDeleteChar(char.id)}
                          className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-gray-800"
                          title="删除"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                ),
              )}
            </div>

            {/* New character form */}
            {showCharForm && (
              <div className="mt-3 rounded-lg border border-violet-700/50 bg-gray-900 p-3 space-y-2">
                <input
                  value={charName}
                  onChange={(e) => setCharName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-violet-500"
                  placeholder="角色名称"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateChar()}
                />
                <select
                  value={charRole}
                  onChange={(e) => setCharRole(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 outline-none"
                >
                  <option value="protagonist">主角</option>
                  <option value="supporting">配角</option>
                  <option value="antagonist">反派</option>
                  <option value="background">路人</option>
                </select>
                <textarea
                  value={charDesc}
                  onChange={(e) => setCharDesc(e.target.value)}
                  rows={2}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 resize-none outline-none focus:border-violet-500"
                  placeholder="角色描述/备注（可选）"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowCharForm(false)}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white rounded"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreateChar}
                    disabled={!charName.trim() || charSaving}
                    className="px-3 py-1.5 text-xs font-medium bg-violet-600 hover:bg-violet-500 text-white rounded disabled:opacity-40"
                  >
                    {charSaving ? '创建中…' : '创建'}
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Location list */}
            {locations.length === 0 && !showLocForm && (
              <div className="text-center py-10 text-gray-600 text-sm">
                <MapPin size={32} className="mx-auto mb-3 opacity-40" />
                <p>还没有场景</p>
                <p className="text-xs text-gray-700 mt-1">点击下方 + 创建第一个场景</p>
              </div>
            )}
            <div className="space-y-2">
              {locations.map((loc) =>
                editingLocId === loc.id ? (
                  <div key={loc.id} className="rounded-lg border border-violet-700/50 bg-gray-900 p-3 space-y-2">
                    <input
                      value={editLocName}
                      onChange={(e) => setEditLocName(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-violet-500"
                      placeholder="场景名称"
                    />
                    <textarea
                      value={editLocDesc}
                      onChange={(e) => setEditLocDesc(e.target.value)}
                      rows={2}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 resize-none outline-none focus:border-violet-500"
                      placeholder="场景描述（可选）"
                    />
                    <div className="flex justify-end gap-2">
                      <button onClick={cancelEditLoc} className="px-2 py-1 text-xs text-gray-400 hover:text-white">
                        <X size={13} />
                      </button>
                      <button onClick={commitEditLoc} className="px-2 py-1 text-xs text-emerald-400 hover:text-emerald-300">
                        <Check size={13} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    key={loc.id}
                    className="group rounded-lg border border-gray-800 bg-gray-900/70 p-3 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      {/* Location icon */}
                      <div className="w-10 h-10 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0 text-gray-500">
                        <MapPin size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          {loc.parent_id && (
                            <span className="text-[10px] text-gray-600 flex items-center gap-0.5">
                              {locations.find((p) => p.id === loc.parent_id)?.name || '?'}
                              <ChevronRight size={9} />
                            </span>
                          )}
                          <span className="text-sm font-medium text-gray-100 truncate">{loc.name}</span>
                        </div>
                        {loc.description && (
                          <p className="mt-1 text-xs text-gray-500 line-clamp-2">{loc.description}</p>
                        )}
                      </div>
                      {/* Actions */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        <button
                          onClick={() => startEditLoc(loc)}
                          className="p-1.5 rounded text-gray-500 hover:text-violet-400 hover:bg-gray-800"
                          title="编辑"
                        >
                          <Pencil size={12} />
                        </button>
                        <button
                          onClick={() => handleDeleteLoc(loc.id)}
                          className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-gray-800"
                          title="删除"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                ),
              )}
            </div>

            {/* New location form */}
            {showLocForm && (
              <div className="mt-3 rounded-lg border border-violet-700/50 bg-gray-900 p-3 space-y-2">
                <input
                  value={locName}
                  onChange={(e) => setLocName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-violet-500"
                  placeholder="场景名称"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateLoc()}
                />
                {locations.length > 0 && (
                  <select
                    value={locParentId ?? ''}
                    onChange={(e) => setLocParentId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 outline-none"
                  >
                    <option value="">无父场景（顶级）</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {getBreadcrumb(l)}
                      </option>
                    ))}
                  </select>
                )}
                <textarea
                  value={locDesc}
                  onChange={(e) => setLocDesc(e.target.value)}
                  rows={2}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 resize-none outline-none focus:border-violet-500"
                  placeholder="场景描述（可选）"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowLocForm(false)}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white rounded"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreateLoc}
                    disabled={!locName.trim() || locSaving}
                    className="px-3 py-1.5 text-xs font-medium bg-violet-600 hover:bg-violet-500 text-white rounded disabled:opacity-40"
                  >
                    {locSaving ? '创建中…' : '创建'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Bottom add button */}
      <div className="px-4 py-3 border-t border-gray-800 shrink-0">
        <button
          onClick={() => {
            if (tab === 'characters') setShowCharForm(true);
            else setShowLocForm(true);
          }}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg
                     bg-gray-900 hover:bg-gray-800 text-gray-300 border border-gray-800 hover:border-gray-700 transition-colors"
        >
          <Plus size={14} />
          {tab === 'characters' ? '添加角色' : '添加场景'}
        </button>
      </div>
    </div>
  );
}
