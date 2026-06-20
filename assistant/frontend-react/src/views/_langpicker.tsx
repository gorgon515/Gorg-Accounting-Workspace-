import { useEffect, useState } from 'react';
import { helios } from '../ipc/client';
import { cls } from '../lib/format';

const KEY = 'helios.academy.language';

// Shared, persisted target-language selection across the Language Academy views.
export function useAcademyLanguage(): [string, (c: string) => void, any[]] {
  const [langs, setLangs] = useState<any[]>([]);
  const [lang, setLang] = useState<string>(() => localStorage.getItem(KEY) || 'spanish');
  useEffect(() => {
    helios.languageAcademy.languages()
      .then((l: any) => { const arr = Array.isArray(l) ? l : (l?.languages ?? []); setLangs(arr); })
      .catch(() => setLangs([]));
  }, []);
  const set = (c: string) => { setLang(c); localStorage.setItem(KEY, c); };
  return [lang, set, langs];
}

export function LanguagePicker({ lang, set, langs }: { lang: string; set: (c: string) => void; langs: any[] }) {
  const list = langs.length ? langs : FALLBACK;
  return (
    <div className="flex flex-wrap gap-1 justify-end">
      {list.map((l: any) => (
        <button key={l.code} onClick={() => set(l.code)}
          className={cls('px-2 py-1 rounded border text-[11px] transition-colors',
            l.code === lang ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
          {l.flag} {l.name}
        </button>
      ))}
    </div>
  );
}

const FALLBACK = [
  { code: 'russian', name: 'Russian', flag: '🇷🇺' }, { code: 'spanish', name: 'Spanish', flag: '🇪🇸' },
  { code: 'french', name: 'French', flag: '🇫🇷' }, { code: 'german', name: 'German', flag: '🇩🇪' },
  { code: 'italian', name: 'Italian', flag: '🇮🇹' }, { code: 'japanese', name: 'Japanese', flag: '🇯🇵' },
  { code: 'mandarin', name: 'Mandarin', flag: '🇨🇳' },
];

export const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
