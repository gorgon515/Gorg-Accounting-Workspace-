// Browser half of the form-filler. Protocol (one JSON object per line):
//   stdout 1: {fields, captcha, title, url}      -> Python plans the answers
//   stdin  1: {fills:[{idx,value}], submit:bool}
//   stdout 2: {errors, submitted_clicked, final_url, text, screenshots}
// It never solves or bypasses CAPTCHA, logins or identity checks: it reports them and stops.
const { chromium } = require('playwright');
const readline = require('readline');
const [url, outDir, headful] = process.argv.slice(2);
const CAPTCHA = /recaptcha|hcaptcha|turnstile|captcha|verify (you are|you're) human|arkoselabs|datadome/i;

(async () => {
  const browser = await chromium.launch({ headless: !headful });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 1600 } })).newPage();
  const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1500);
    const info = await page.evaluate(() => {
      const vis = (el) => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return el.type === 'file' || (r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'); };
      const labelOf = (el) => {
        const t = (s) => (s || '').replace(/\s+/g, ' ').trim();
        if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return t(l.innerText); }
        if (el.getAttribute('aria-label')) return t(el.getAttribute('aria-label'));
        const lb = el.getAttribute('aria-labelledby'); if (lb && document.getElementById(lb)) return t(document.getElementById(lb).innerText);
        const wrap = el.closest('label'); if (wrap) return t(wrap.innerText);
        return t(el.placeholder || el.name || '');
      };
      const groupLabel = (el) => { const fs = el.closest('fieldset'); const lg = fs && fs.querySelector('legend');
        return lg ? lg.innerText.replace(/\s+/g, ' ').trim() : ''; };
      const fields = [], seen = new Set(); let idx = 0;
      for (const el of document.querySelectorAll('input, select, textarea')) {
        const type = (el.tagName === 'SELECT' ? 'select' : el.tagName === 'TEXTAREA' ? 'textarea' : (el.type || 'text')).toLowerCase();
        if (['hidden', 'submit', 'button', 'image', 'reset', 'search'].includes(type) || !vis(el) || el.disabled) continue;
        if (type === 'radio') {
          if (seen.has(el.name)) continue; seen.add(el.name);
          const opts = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)];
          opts.forEach((o, i) => o.setAttribute('data-cd', `${idx}-${i}`));
          fields.push({ idx: idx++, type, label: groupLabel(el) || labelOf(el), required: opts.some(o => o.required),
                        options: opts.map(labelOf) });
          continue;
        }
        el.setAttribute('data-cd', String(idx));
        fields.push({ idx: idx++, type, label: (type === 'checkbox' ? labelOf(el) : labelOf(el) || groupLabel(el)),
                      required: el.required || el.getAttribute('aria-required') === 'true',
                      options: type === 'select' ? [...el.options].map(o => o.text.trim()).filter(Boolean) : undefined,
                      accept: el.accept || undefined });
      }
      const frames = [...document.querySelectorAll('iframe')].map(f => f.src).join(' ');
      return { fields, frames, text: document.body.innerText.slice(0, 6000), title: document.title,
               password: !!document.querySelector('input[type=password]') };
    });
    out({ fields: info.fields, captcha: CAPTCHA.test(info.frames) || CAPTCHA.test(info.text), login: info.password,
          title: info.title, url: page.url(), text: info.text.slice(0, 3000) });

    const line = await new Promise((res) => { const rl = readline.createInterface({ input: process.stdin });
      rl.once('line', res); rl.once('close', () => res(null)); });
    if (line === null) { await browser.close(); return; }  // caller stopped (manual / error path)
    const plan = JSON.parse(line), errors = [];
    for (const f of plan.fills || []) {
      try {
        const field = info.fields.find(x => x.idx === f.idx);
        if (field.type === 'radio') {
          const i = field.options.findIndex(o => o.toLowerCase() === String(f.value).toLowerCase());
          if (i < 0) throw new Error('option not found'); await page.check(`[data-cd="${f.idx}-${i}"]`);
        } else if (field.type === 'file') await page.setInputFiles(`[data-cd="${f.idx}"]`, f.value);
        else if (field.type === 'select') await page.selectOption(`[data-cd="${f.idx}"]`, { label: String(f.value) });
        else if (field.type === 'checkbox') await page.setChecked(`[data-cd="${f.idx}"]`, !!f.value);
        else await page.fill(`[data-cd="${f.idx}"]`, String(f.value));
      } catch (e) { errors.push({ idx: f.idx, error: e.message.split('\n')[0] }); }
    }
    const shots = [`${outDir}/filled.png`];
    await page.screenshot({ path: shots[0], fullPage: true });
    let clicked = false;
    if (plan.submit && !errors.length) {
      const btn = page.locator('button[type=submit], input[type=submit]').first();
      if (await btn.count()) {
        await Promise.all([page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}), btn.click()]);
        await page.waitForTimeout(1500); clicked = true;
        shots.push(`${outDir}/after_submit.png`); await page.screenshot({ path: shots[1], fullPage: true });
      } else errors.push({ error: 'no submit button found' });
    }
    out({ errors, submitted_clicked: clicked, final_url: page.url(),
          text: (await page.evaluate(() => document.body.innerText)).slice(0, 3000), screenshots: shots });
  } catch (e) { out({ fatal: e.message.split('\n')[0] }); }
  await browser.close();
})();
