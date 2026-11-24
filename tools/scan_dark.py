# -*- coding: utf-8 -*-
"""暗色主题体检：扫描所有"亮背景/低对比"元素，输出选择器与计算色值。"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

JS = r'''() => {
  const lum = (c) => {
    const m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (!m) return null;
    if (m[4] !== undefined && parseFloat(m[4]) < 0.4) return null; // 透明
    return (0.2126*+m[1] + 0.7152*+m[2] + 0.0722*+m[3]) / 255;
  };
  const sel = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.className && typeof el.className === 'string') {
      const cls = el.className.trim().split(/\s+/).slice(0, 3).join('.');
      if (cls) s += '.' + cls;
    }
    return s;
  };
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 60 || r.height < 18) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const bl = lum(cs.backgroundColor);
    const fl = lum(cs.color);
    if (bl === null) continue;
    if (bl > 0.55 || (fl !== null && Math.abs(bl - fl) < 0.28)) {
      out.push({sel: sel(el), bg: cs.backgroundColor, fg: cs.color, bgL: +bl.toFixed(2),
                area: Math.round(r.width * r.height), depth: (()=>{let d=0,p=el;while(p=p.parentElement)d++;return d;})()});
    }
  }
  // 去掉被祖先完全覆盖的重复项：按 area 降序保留
  out.sort((a, b) => b.area - a.area);
  const seen = new Set(), keep = [];
  for (const o of out) { if (seen.has(o.sel)) continue; seen.add(o.sel); keep.push(o); }
  return keep.slice(0, 40);
}'''

pages = sys.argv[1:] or ['精神病学_第一章_绪论_学习指南.html',
                         '精神病学_第六章_精神分裂症及其他原发性精神病性障碍_学习指南.html',
                         'psychotropic-drugs.html', 'clinical-workflow.html', 'index.html', 'textbook-guide.html']

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    for fn in pages:
        pg = b.new_page(viewport={'width': 1440, 'height': 940})
        pg.goto((ROOT / fn).as_uri())
        pg.wait_for_timeout(400)
        pg.evaluate("document.documentElement.setAttribute('data-psyx-theme','dark')")
        pg.wait_for_timeout(300)
        res = pg.evaluate(JS)
        print('=' * 20, fn, '->', len(res), 'hits')
        for o in res:
            print('  %-52s bg=%-22s fg=%-20s L=%.2f area=%d' % (o['sel'][:52], o['bg'], o['fg'], o['bgL'], o['area']))
        pg.close()
    b.close()
