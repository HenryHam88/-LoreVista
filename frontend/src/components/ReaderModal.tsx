/**
 * ReaderModal – Phase 3 全屏漫画阅读器
 * 支持：瀑布流模式（上下滚动）和翻页模式（左右切换）
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  X, ChevronLeft, ChevronRight, LayoutList, BookOpen,
  ZoomIn, ZoomOut, Maximize2,
} from 'lucide-react';
import { mangaImageUrl, mangaThumbUrl, type Chapter, type MangaImage } from '../api';

interface Props {
  chapter: Chapter;
  initialImageNumber?: number;
  onClose: () => void;
}

type ReadMode = 'scroll' | 'page';

export default function ReaderModal({ chapter, initialImageNumber = 1, onClose }: Props) {
  const images = [...(chapter.images ?? [])].sort((a, b) => a.image_number - b.image_number);
  const [mode, setMode] = useState<ReadMode>('scroll');
  const [pageIdx, setPageIdx] = useState(() => {
    const idx = images.findIndex(i => i.image_number === initialImageNumber);
    return idx >= 0 ? idx : 0;
  });
  const [zoom, setZoom] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (mode === 'page') {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          setPageIdx(p => Math.max(0, p - 1));
        }
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          setPageIdx(p => Math.min(images.length - 1, p + 1));
        }
      }
      if (e.key === '+' || e.key === '=') setZoom(z => Math.min(2, z + 0.1));
      if (e.key === '-') setZoom(z => Math.max(0.5, z - 0.1));
      if (e.key === '0') setZoom(1);
      if (e.key === 'f' || e.key === 'F') setMode(m => m === 'scroll' ? 'page' : 'scroll');
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mode, images.length, onClose]);

  // When switching to page mode, scroll to current page ref
  useEffect(() => {
    if (mode === 'page') {
      pageRefs.current[pageIdx]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [pageIdx, mode]);

  // In scroll mode, scroll to the initial image on first open
  useEffect(() => {
    if (mode === 'scroll') {
      const initialIdx = images.findIndex(i => i.image_number === initialImageNumber);
      if (initialIdx >= 0) {
        setTimeout(() => {
          pageRefs.current[initialIdx]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePrev = useCallback(() => setPageIdx(p => Math.max(0, p - 1)), []);
  const handleNext = useCallback(() => setPageIdx(p => Math.min(images.length - 1, p + 1)), [images.length]);

  const currentImg = images[pageIdx];
  const title = chapter.title?.trim()
    ? `第 ${chapter.chapter_number} 话 · ${chapter.title.trim()}`
    : `第 ${chapter.chapter_number} 话`;

  return (
    <div className="fixed inset-0 z-[100] bg-black flex flex-col" role="dialog" aria-modal="true">
      {/* ── Top bar ── */}
      <header className="shrink-0 flex items-center justify-between gap-3 px-4 py-2.5
                          bg-black/90 border-b border-white/10 backdrop-blur-sm">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="关闭（Esc）"
          >
            <X size={18} />
          </button>
          <span className="text-sm text-gray-300 truncate font-medium">{title}</span>
          {mode === 'page' && (
            <span className="text-xs text-gray-500 shrink-0">
              {pageIdx + 1} / {images.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {/* Mode toggle */}
          <div className="flex items-center gap-0.5 bg-white/10 rounded-lg p-0.5">
            <button
              onClick={() => setMode('scroll')}
              title="瀑布流（上下滚动）"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
                mode === 'scroll' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <LayoutList size={13} />
              <span className="hidden sm:inline">瀑布流</span>
            </button>
            <button
              onClick={() => setMode('page')}
              title="翻页模式"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
                mode === 'page' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <BookOpen size={13} />
              <span className="hidden sm:inline">翻页</span>
            </button>
          </div>

          {/* Zoom controls */}
          <button
            onClick={() => setZoom(z => Math.max(0.5, z - 0.15))}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="缩小（-）"
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-xs text-gray-500 w-10 text-center tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom(z => Math.min(2, z + 0.15))}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="放大（+）"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="重置缩放（0）"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </header>

      {/* ── Main area ── */}
      {mode === 'scroll' ? (
        /* Waterfall / infinite scroll */
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto overflow-x-hidden"
          style={{ backgroundColor: '#0a0a0a' }}
        >
          <div
            className="mx-auto transition-all duration-200"
            style={{ width: `${Math.round(zoom * 100)}%`, maxWidth: '900px', minWidth: '280px' }}
          >
            {images.map((img, idx) => (
              <div
                key={img.id}
                ref={el => { pageRefs.current[idx] = el; }}
                className="w-full"
              >
                <img
                  src={mangaThumbUrl(img.image_path, 1280)!}
                  alt={`第 ${img.image_number} 页`}
                  className="w-full block"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            ))}
            {/* Bottom padding */}
            <div className="h-16" />
          </div>
        </div>
      ) : (
        /* Paged / flip mode */
        <div className="flex-1 flex items-center justify-center relative overflow-hidden bg-[#0a0a0a]">
          {/* Prev button */}
          <button
            onClick={handlePrev}
            disabled={pageIdx === 0}
            className="absolute left-3 z-10 p-3 rounded-full bg-black/60 hover:bg-black/80
                       text-white disabled:opacity-20 disabled:cursor-not-allowed transition-all
                       hover:scale-110 active:scale-95"
            title="上一页（←）"
          >
            <ChevronLeft size={24} />
          </button>

          {/* Image */}
          {currentImg && (
            <div
              className="h-full flex items-center justify-center overflow-auto"
              style={{ width: `${Math.round(zoom * 100)}%`, maxWidth: '900px' }}
            >
              <img
                key={currentImg.id}
                src={mangaImageUrl(currentImg.image_path)}
                alt={`第 ${currentImg.image_number} 页`}
                className="max-h-full max-w-full object-contain block select-none
                           transition-opacity duration-200"
                draggable={false}
              />
            </div>
          )}

          {/* Next button */}
          <button
            onClick={handleNext}
            disabled={pageIdx === images.length - 1}
            className="absolute right-3 z-10 p-3 rounded-full bg-black/60 hover:bg-black/80
                       text-white disabled:opacity-20 disabled:cursor-not-allowed transition-all
                       hover:scale-110 active:scale-95"
            title="下一页（→）"
          >
            <ChevronRight size={24} />
          </button>

          {/* Page dots */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
            {images.map((_, i) => (
              <button
                key={i}
                onClick={() => setPageIdx(i)}
                className={`rounded-full transition-all ${
                  i === pageIdx
                    ? 'w-4 h-2 bg-violet-500'
                    : 'w-2 h-2 bg-white/30 hover:bg-white/60'
                }`}
                aria-label={`跳转到第 ${i + 1} 页`}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Bottom bar (scroll mode: thumbnail strip) ── */}
      {mode === 'scroll' && images.length > 1 && (
        <div className="shrink-0 border-t border-white/10 bg-black/90 px-3 py-2 overflow-x-auto">
          <div className="flex gap-2">
            {images.map((img, idx) => (
              <button
                key={img.id}
                onClick={() => {
                  pageRefs.current[idx]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                className="shrink-0 w-12 h-16 rounded overflow-hidden border border-white/10
                           hover:border-violet-500 transition-colors"
                title={`第 ${img.image_number} 页`}
              >
                <img
                  src={mangaThumbUrl(img.image_path, 320)!}
                  alt={`缩略图 ${img.image_number}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Bottom bar (page mode: chapter/page info) ── */}
      {mode === 'page' && (
        <div className="shrink-0 border-t border-white/10 bg-black/90 px-4 py-2 flex items-center
                        justify-between gap-4 text-xs text-gray-500">
          <span>{title}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={pageIdx === 0}
              className="px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 text-gray-300
                         disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
            >
              上一页
            </button>
            <span className="text-gray-400 tabular-nums">{pageIdx + 1} / {images.length}</span>
            <button
              onClick={handleNext}
              disabled={pageIdx === images.length - 1}
              className="px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 text-gray-300
                         disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
