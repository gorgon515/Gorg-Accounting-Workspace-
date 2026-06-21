import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Market Ideas — TradingView community ideas, news, and economic calendar.
export function MarketIdeas() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Market Ideas." />;
  const [tab, setTab] = useState<'ideas' | 'news' | 'calendar'>('ideas');
  const [ideasMode, setIdeasMode] = useState<'hot' | 'picks'>('hot');
  const [newsMarket, setNewsMarket] = useState<string>('stock');
  const [selectedNews, setSelectedNews] = useState<any>(null);

  const hotIdeas = useAsync(() => helios.tradingview.hotIdeas(), []);
  const picks = useAsync(() => helios.tradingview.editorsPicks(), []);
  const news = useAsync(() => helios.tradingview.news({ market: newsMarket as any, limit: 30 }), [newsMarket]);
  const calendar = useAsync(() => helios.tradingview.calendar('US'), []);

  const ideasList: any[] = (ideasMode === 'hot' ? hotIdeas : picks).data ?? [];
  const newsList: any[] = Array.isArray(news.data) ? news.data : (news.data?.items ?? news.data?.news ?? []);
  const calendarList: any[] = Array.isArray(calendar.data) ? calendar.data : (calendar.data?.result ?? calendar.data?.events ?? []);

  const newsMarkets = ['stock', 'crypto', 'forex', 'futures', 'bond', 'etf', 'index', 'economic'];

  return (
    <Page title="Market Ideas" subtitle="TradingView · community ideas · news · economic calendar">
      <div className="grid gap-3">
        <div className="flex gap-1.5">
          {(['ideas', 'news', 'calendar'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={cls('px-3 py-1.5 rounded border text-[11px] mono capitalize',
                tab === t ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'ideas' && (
          <div className="grid gap-3">
            <div className="flex gap-1.5">
              {(['hot', 'picks'] as const).map((m) => (
                <button key={m} onClick={() => setIdeasMode(m)}
                  className={cls('px-2.5 py-1 rounded border text-[10px] mono',
                    ideasMode === m ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>
                  {m === 'hot' ? '🔥 Hot Ideas' : '✎ Editors Picks'}
                </button>
              ))}
            </div>
            <Panel title={ideasMode === 'hot' ? 'Hot Ideas' : "Editor's Picks"}
              subtitle="TradingView community">
              {(ideasMode === 'hot' ? hotIdeas : picks).loading ? <Loading /> : ideasList.length === 0 ? (
                <EmptyState message="No ideas available. Ensure TRADINGVIEW_RAPIDAPI_KEY is configured." />
              ) : (
                <div className="grid gap-2 max-h-[600px] overflow-y-auto scroll-thin">
                  {ideasList.map((idea: any, n: number) => (
                    <IdeaCard key={n} idea={idea} />
                  ))}
                </div>
              )}
            </Panel>
          </div>
        )}

        {tab === 'news' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <Panel title="News Feed" subtitle={newsMarket}
              actions={
                <div className="flex flex-wrap gap-1">
                  {newsMarkets.map((m) => (
                    <button key={m} onClick={() => setNewsMarket(m)}
                      className={cls('px-1.5 py-0.5 rounded border text-[9px] mono capitalize',
                        newsMarket === m ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>
                      {m}
                    </button>
                  ))}
                </div>
              }
              className="lg:col-span-1">
              {news.loading ? <Loading /> : newsList.length === 0 ? (
                <EmptyState message="No news available." />
              ) : (
                <div className="grid gap-1.5 max-h-[580px] overflow-y-auto scroll-thin">
                  {newsList.map((item: any, n: number) => (
                    <button key={n} onClick={() => setSelectedNews(item)}
                      className={cls('text-left px-2.5 py-2 rounded border hover:bg-ivory/5',
                        selectedNews === item ? 'border-gold/40 bg-gold/5' : 'border-hairline')}>
                      <p className="text-[11px] leading-snug line-clamp-2">
                        {item.title ?? item.headline ?? ''}
                      </p>
                      <p className="mono text-[9px] text-warmgray mt-1">
                        {item.source ?? item.provider ?? ''} · {fmtTime(item.published ?? item.published_at ?? item.date)}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </Panel>

            <Panel title={selectedNews?.title ?? 'Article'} subtitle={selectedNews?.source ?? 'select an article'}
              className="lg:col-span-2">
              {!selectedNews ? (
                <EmptyState message="Select an article on the left to read it." />
              ) : (
                <div className="grid gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedNews.symbols && (selectedNews.symbols as string[]).map((s: string) => (
                      <span key={s} className="mono text-[10px] text-gold bg-gold/10 rounded px-1.5 py-0.5">{s}</span>
                    ))}
                    <span className="mono text-[9px] text-warmgray ml-auto">
                      {fmtTime(selectedNews.published ?? selectedNews.published_at ?? selectedNews.date)}
                    </span>
                  </div>
                  <p className="text-[12px] text-warmgray leading-relaxed">
                    {selectedNews.description ?? selectedNews.summary ?? selectedNews.body ?? 'Full article not available — click the link below to read.'}
                  </p>
                  {selectedNews.url && (
                    <p className="mono text-[10px] text-gold/70 truncate">{selectedNews.url}</p>
                  )}
                </div>
              )}
            </Panel>
          </div>
        )}

        {tab === 'calendar' && (
          <Panel title="Economic Calendar" subtitle="US macro events">
            {calendar.loading ? <Loading /> : calendarList.length === 0 ? (
              <EmptyState message="No calendar events. Ensure TRADINGVIEW_RAPIDAPI_KEY is configured." />
            ) : (
              <div className="grid gap-1.5 max-h-[600px] overflow-y-auto scroll-thin">
                <div className="grid grid-cols-4 gap-2 px-2.5 py-1 mono text-[9px] uppercase text-warmgray">
                  <span>Date/Time</span><span>Event</span><span>Actual</span><span>Forecast / Prior</span>
                </div>
                {calendarList.map((ev: any, n: number) => {
                  const imp = ev.importance ?? ev.impact ?? '';
                  return (
                    <div key={n} className="grid grid-cols-4 gap-2 px-2.5 py-2 rounded border border-hairline text-[11px]">
                      <span className="mono text-[10px] text-warmgray">
                        {fmtTime(ev.date ?? ev.datetime ?? ev.time)}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className={cls('w-1.5 h-1.5 rounded-full flex-shrink-0', impColor(imp))} />
                        <span className="truncate">{ev.title ?? ev.name ?? ev.event ?? ''}</span>
                      </div>
                      <span className={cls('mono font-medium', ev.actual > ev.forecast ? 'text-helgreen' : ev.actual < ev.forecast ? 'text-helred' : '')}>
                        {ev.actual ?? '—'}
                      </span>
                      <span className="mono text-warmgray">
                        {ev.forecast != null ? `${ev.forecast} / ` : ''}{ev.previous ?? ev.prior ?? '—'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        )}
      </div>
    </Page>
  );
}

function IdeaCard({ idea }: { idea: any }) {
  const [open, setOpen] = useState(false);
  const dir = (idea.direction ?? idea.signal ?? idea.type ?? '').toUpperCase();
  return (
    <div className={cls('rounded border', open ? 'border-gold/30' : 'border-hairline')}>
      <button className="w-full text-left px-3 py-2.5 flex items-center gap-3" onClick={() => setOpen(!open)}>
        <span className={cls('mono text-[10px] w-12 font-bold', dir.includes('LONG') || dir.includes('BUY') ? 'text-helgreen' : dir.includes('SHORT') || dir.includes('SELL') ? 'text-helred' : 'text-warmgray')}>
          {dir || 'VIEW'}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[12px] truncate">{idea.title ?? idea.name ?? ''}</p>
          <p className="mono text-[9px] text-warmgray mt-0.5">
            {idea.symbol ?? idea.ticker ?? ''} · {idea.author ?? idea.username ?? ''} · {fmtTime(idea.published ?? idea.created_at ?? idea.date)}
          </p>
        </div>
        <span className="mono text-[9px] text-warmgray">{idea.likes ?? idea.views ?? ''}</span>
      </button>
      {open && (idea.description ?? idea.content ?? idea.body) && (
        <div className="px-3 pb-2.5 border-t border-hairline/40">
          <p className="text-[11px] text-ivory/70 mt-2 leading-relaxed line-clamp-6">
            {idea.description ?? idea.content ?? idea.body}
          </p>
        </div>
      )}
    </div>
  );
}

function impColor(imp: any): string {
  const s = String(imp ?? '').toUpperCase();
  if (s === 'HIGH' || s === '3' || s === 'CRITICAL') return 'bg-helred';
  if (s === 'MEDIUM' || s === '2') return 'bg-gold';
  return 'bg-warmgray';
}

function fmtTime(v: any): string {
  if (!v) return '—';
  try {
    const d = new Date(typeof v === 'number' ? v * 1000 : v);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return String(v); }
}
