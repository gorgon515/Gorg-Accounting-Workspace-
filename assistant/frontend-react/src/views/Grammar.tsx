import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage, LEVELS } from './_langpicker';

// Grammar Academy — rules by level plus a live mistake checker.
export function Grammar() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Grammar." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const [level, setLevel] = useState<string | undefined>(undefined);
  const rules = useAsync(() => helios.languageAcademy.grammar(lang, level), [lang, level]);
  const [openId, setOpenId] = useState<string | null>(null);

  const list: any[] = Array.isArray(rules.data) ? rules.data : (rules.data?.rules ?? []);
  const open = list.find((r) => r.id === openId);

  return (
    <Page title="Grammar Academy" subtitle="rules · examples · mistake detection"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <GrammarChecker lang={lang} />

        <Panel title="Level">
          <div className="flex gap-1.5">
            <button onClick={() => setLevel(undefined)}
              className={cls('px-3 py-1.5 rounded border text-[11px] mono',
                !level ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>all</button>
            {LEVELS.map((lv) => (
              <button key={lv} onClick={() => setLevel(lv)}
                className={cls('px-3 py-1.5 rounded border text-[11px] mono',
                  level === lv ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>{lv}</button>
            ))}
          </div>
        </Panel>

        <Panel title="Rules" subtitle={`${list.length} · ${lang}`}>
          {rules.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No grammar rules for this selection." />
          ) : (
            <div className="grid gap-1.5">
              {list.map((r: any) => (
                <div key={r.id}>
                  <div className="flex items-center gap-2 px-2.5 py-2 rounded border border-hairline cursor-pointer hover:bg-ivory/5"
                    onClick={() => setOpenId(openId === r.id ? null : r.id)}>
                    <span className="mono text-[10px] text-gold w-8">{r.level}</span>
                    <span className="text-[12px] flex-1">{r.title}</span>
                    <span className="mono text-[10px] text-warmgray">{(r.common_mistakes ?? []).length} pitfalls</span>
                  </div>
                  {openId === r.id && open && (
                    <div className="ml-8 mb-1 px-3 py-2 rounded border border-hairline/60 bg-obsidian/40">
                      <p className="text-[12px] text-ivory/80 mb-2">{open.explanation}</p>
                      {(open.examples ?? []).map((e: any, n: number) => (
                        <p key={n} className="mono text-[11px] text-warmgray">› {typeof e === 'string' ? e : e.text ?? ''}</p>
                      ))}
                      {(open.common_mistakes ?? []).length > 0 && (
                        <div className="mt-2 pt-2 border-t border-hairline grid gap-1">
                          {open.common_mistakes.map((m: any, n: number) => (
                            <div key={n} className="text-[11px]">
                              <span className="text-helred line-through">{m.wrong}</span>
                              <span className="text-warmgray mx-1.5">→</span>
                              <span className="text-helgreen">{m.right}</span>
                              {m.note && <span className="text-warmgray"> — {m.note}</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function GrammarChecker({ lang }: { lang: string }) {
  const [text, setText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function check() {
    if (!text.trim()) return;
    setBusy(true);
    try { setResult(await helios.languageAcademy.grammarCheck({ language: lang, text })); }
    finally { setBusy(false); }
  }

  const found: any[] = result?.found ?? [];

  return (
    <Panel title="Mistake Checker" subtitle="paste a sentence — common errors are flagged">
      <div className="flex gap-2">
        <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
          placeholder={`Write a sentence in ${lang}…`} value={text}
          onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && check()} />
        <Button size="sm" variant="gold" onClick={check} disabled={busy}>{busy ? '…' : 'Check'}</Button>
      </div>
      {result && (
        <div className="mt-3">
          {found.length === 0 ? (
            <p className="text-[12px] text-helgreen">✓ No common mistakes detected{result.score != null ? ` · score ${result.score}` : ''}.</p>
          ) : (
            <div className="grid gap-1.5">
              {found.map((f: any, n: number) => (
                <div key={n} className="text-[12px] px-2 py-1.5 rounded border border-helred/30 bg-helred/5">
                  <span className="text-helred line-through">{f.wrong}</span>
                  <span className="text-warmgray mx-1.5">→</span>
                  <span className="text-helgreen">{f.right}</span>
                  {f.note && <span className="text-warmgray"> — {f.note}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
