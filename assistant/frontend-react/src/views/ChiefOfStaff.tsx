import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Briefing', 'Plan', 'Tasks', 'Goals', 'Evening'] as const;
type Tab = typeof TABS[number];

export function ChiefOfStaff() {
  const [tab, setTab] = useState<Tab>('Briefing');
  return (
    <Page title="Chief of Staff" subtitle="proactive daily execution — briefing · plan · tasks · goals · review"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }>
      {tab === 'Briefing' && <Briefing />}
      {tab === 'Plan' && <Plan />}
      {tab === 'Tasks' && <Tasks />}
      {tab === 'Goals' && <Goals />}
      {tab === 'Evening' && <Evening />}
    </Page>
  );
}

function Briefing() {
  const b = useAsync(() => helios.sidecar.cosBriefingAuto(), []);
  const d = b.data;
  return b.loading ? <Loading /> : !d ? <EmptyState message="Chief of Staff offline — start the sidecar." /> : (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Confidence" accent value={d.confidence?.level ?? '—'} />
        <MetricCard label="Priorities" value={d.todays_priorities?.length ?? 0} />
        <MetricCard label="Risks" value={d.risks?.length ?? 0} />
        <MetricCard label="Deadlines" value={d.upcoming_deadlines?.length ?? 0} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Executive summary" actions={<Button size="sm" onClick={() => b.reload()}>refresh</Button>}>
          <p className="text-[13px] text-ivory/90 leading-relaxed mb-3">{d.executive_summary}</p>
          <div className="mono text-[10px] uppercase text-warmgray mb-1">Today's priorities</div>
          <ul className="flex flex-col gap-1 mb-3">
            {(d.todays_priorities ?? []).map((p: any, i: number) => (
              <li key={i} className="text-[12px] flex items-center gap-2">
                <span className={cls('w-1.5 h-1.5 rounded-full', p.overdue ? 'bg-helred' : 'bg-gold')} />
                <span className="flex-1">{p.title}</span>
                <span className="mono text-[10px] text-warmgray">{p.score}</span>
              </li>
            ))}
          </ul>
          <div className="mono text-[10px] uppercase text-warmgray mb-1">Recommended actions</div>
          <ul className="text-[12px] flex flex-col gap-1">
            {(d.recommended_actions ?? []).map((a: string, i: number) => <li key={i}>• {a}</li>)}
          </ul>
        </Panel>
        <div className="flex flex-col gap-3">
          <Panel title="Risks">
            {(d.risks ?? []).length ? <ul className="text-[12px] flex flex-col gap-1">
              {d.risks.map((r: string, i: number) => <li key={i} className="text-helred/90">• {r}</li>)}</ul>
              : <EmptyState message="No risks flagged." />}
          </Panel>
          <Panel title="Opportunities & energy">
            <ul className="text-[12px] flex flex-col gap-1">
              {(d.opportunities ?? []).map((o: string, i: number) => <li key={i} className="text-helgreen/90">• {o}</li>)}
              {(d.energy_allocation ?? []).map((e: string, i: number) => <li key={`e${i}`} className="text-warmgray">• {e}</li>)}
            </ul>
          </Panel>
        </div>
      </div>
    </>
  );
}

function Plan() {
  const p = useAsync(() => helios.sidecar.cosPlanAuto(), []);
  const d = p.data;
  return p.loading ? <Loading /> : !d ? <EmptyState message="Planner offline." /> : (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Day plan" subtitle={d.summary}>
        <div className="mono text-[10px] uppercase text-warmgray mb-1">Goal pacing</div>
        {(d.goal_recommendations ?? []).map((g: any, i: number) => (
          <div key={i} className="text-[12px] mb-2">
            <div className="flex items-center justify-between">
              <span>{g.goal}</span><StatusBadge status={g.urgency === 'high' ? 'offline' : 'ready'} label={g.status} />
            </div>
            <div className="text-warmgray text-[11px]">{g.days_remaining} days left · ~{g.required_pace_per_day} {g.unit}/day · {g.recommended_minutes_today}m today</div>
          </div>
        )) || <EmptyState message="No deadline-bearing goals." />}
      </Panel>
      <Panel title="Scheduled focus blocks">
        {(d.calendar_blocks ?? []).length ? (
          <ul className="text-[12px] flex flex-col gap-1.5">
            {d.calendar_blocks.map((b: any, i: number) => (
              <li key={i} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                <div className="flex justify-between"><span>{b.title}</span>
                  <span className="mono text-[10px] text-gold">{b.start?.slice(11)}–{b.end?.slice(11)}</span></div>
                <div className="text-[10px] text-warmgray">{b.reason}</div>
              </li>
            ))}
          </ul>
        ) : <EmptyState message="No free focus blocks (add calendar via the app)." />}
      </Panel>
    </div>
  );
}

function Tasks() {
  const list = useAsync(() => helios.sidecar.listTasks('open'), []);
  const [title, setTitle] = useState(''); const [pri, setPri] = useState('3'); const [due, setDue] = useState('');
  async function add() {
    if (!title.trim()) return;
    try { await helios.sidecar.createTask({ title, priority: Number(pri), due: due || null }); setTitle(''); setDue(''); list.reload(); } catch {}
  }
  const tasks = list.data?.tasks ?? [];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Open tasks" subtitle={list.data?.stats ? `${list.data.stats.overdue} overdue · ${list.data.stats.blocked} blocked` : ''}>
        {list.loading ? <Loading /> : !tasks.length ? <EmptyState message="No open tasks." /> : (
          <ul className="flex flex-col gap-1.5">
            {tasks.map((t: any) => (
              <li key={t.id} className="flex items-center gap-2 rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                <button onClick={async () => { await helios.sidecar.completeTask(t.id); list.reload(); }}
                  className="w-5 h-5 rounded-full border border-hairline text-helgreen text-[10px]">✓</button>
                <span className="mono text-[9px] uppercase text-gold w-16 truncate">{t.category}</span>
                <span className="flex-1 text-[12px]">{t.title}</span>
                {t.due && <span className="mono text-[10px] text-warmgray">{t.due.slice(0, 10)}</span>}
                <span className="mono text-[10px] text-warmgray">P{t.priority}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Add task" subtitle="task intelligence: scoring · dependencies · recurrence">
        <div className="flex flex-col gap-2">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Task title"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
          <div className="flex gap-2">
            <select value={pri} onChange={(e) => setPri(e.target.value)}
              className="bg-obsidian/60 border border-hairline rounded-lg px-2 py-2 text-[12px]">
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>P{n}</option>)}
            </select>
            <input value={due} onChange={(e) => setDue(e.target.value)} placeholder="due YYYY-MM-DD"
              className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
            <Button variant="gold" onClick={add}>Add</Button>
          </div>
        </div>
      </Panel>
    </div>
  );
}

function Goals() {
  const dash = useAsync(() => helios.sidecar.goalsDashboard(), []);
  const [title, setTitle] = useState(''); const [deadline, setDeadline] = useState('');
  async function add() {
    if (!title.trim()) return;
    try { await helios.sidecar.createGoal({ title, deadline: deadline || null }); setTitle(''); setDeadline(''); dash.reload(); } catch {}
  }
  const goals = dash.data?.goals ?? [];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Goals" subtitle={dash.data ? `${dash.data.behind} behind pace` : ''}>
        {dash.loading ? <Loading /> : !goals.length ? <EmptyState message="No goals yet." /> : (
          <ul className="flex flex-col gap-2">
            {goals.map((g: any) => (
              <li key={g.id} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px]">{g.title}</span>
                  <StatusBadge status={g.forecast.status === 'behind' || g.forecast.status === 'overdue' ? 'offline' : 'ready'} label={g.forecast.status} />
                </div>
                <div className="h-1.5 rounded bg-obsidian my-1.5 overflow-hidden">
                  <div className="h-full bg-gold" style={{ width: `${g.forecast.percent_complete}%` }} />
                </div>
                <div className="text-[10px] text-warmgray">{(g.recommendations || [])[0]}</div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Add goal">
        <div className="flex flex-col gap-2">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Goal (e.g. Pass CPA FAR)"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
          <div className="flex gap-2">
            <input value={deadline} onChange={(e) => setDeadline(e.target.value)} placeholder="deadline YYYY-MM-DD"
              className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
            <Button variant="gold" onClick={add}>Add</Button>
          </div>
          <p className="text-[10px] text-warmgray/70">Deadline goals get pacing forecasts and drive the day plan.</p>
        </div>
      </Panel>
    </div>
  );
}

function Evening() {
  const r = useAsync(() => helios.sidecar.cosEveningReview({}), []);
  const d = r.data;
  return r.loading ? <Loading /> : !d ? <EmptyState message="Review offline." /> : (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Today" subtitle={d.productivity_score != null ? `productivity ${d.productivity_score}%` : ''}>
        <div className="mono text-[10px] uppercase text-warmgray mb-1">Completed ({d.completed_work?.length ?? 0})</div>
        <ul className="text-[12px] mb-3">{(d.completed_work ?? []).map((t: any, i: number) => <li key={i}>✓ {t.title}</li>)}</ul>
        <div className="mono text-[10px] uppercase text-warmgray mb-1">Missed ({d.missed_tasks?.length ?? 0})</div>
        <ul className="text-[12px]">{(d.missed_tasks ?? []).map((t: any, i: number) => <li key={i} className="text-helred/90">• {t.title}</li>)}</ul>
      </Panel>
      <Panel title="Tomorrow & reflection">
        <div className="mono text-[10px] uppercase text-warmgray mb-1">Top tasks tomorrow</div>
        <ul className="text-[12px] mb-3">{(d.tomorrow_preparation?.top_tasks ?? []).map((t: any, i: number) => <li key={i}>• {t.title}</li>)}</ul>
        <ul className="text-[12px] text-warmgray flex flex-col gap-1">
          {(d.reflection_notes ?? []).map((n: string, i: number) => <li key={i}>{n}</li>)}
        </ul>
      </Panel>
    </div>
  );
}
