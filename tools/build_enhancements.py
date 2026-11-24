#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精神病学学习站增强层构建脚本（可重复运行，幂等）。

生成内容：
  1. 跨 29 页的全文检索索引（gzip + base64 内嵌，保持单文件、零网络依赖）
  2. localStorage 学习状态（阅读进度 / 自测成绩 / 速记卡翻阅 / 书签 / 最近访问）
  3. 亮/暗主题切换与统一设计令牌
  4. 总目录「继续学习」面板

用法：python tools/build_enhancements.py
"""
import os, re, json, gzip, base64, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_START = '<!-- PSYX:CSS:START -->'
CSS_END = '<!-- PSYX:CSS:END -->'
UI_START = '<!-- PSYX:UI:START -->'
UI_END = '<!-- PSYX:UI:END -->'

EXTRA_PAGE = 'clinical-workflow.html'
CHAPTER_ORDER = []
CHUNK_CAP = 3  # 每节最多切 3 段，控制内嵌索引体积

def pages():
    fs = [f for f in os.listdir(ROOT) if f.endswith('.html')]
    fs.sort()
    return fs

def strip_tags(s):
    s = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = (s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<')
          .replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'"))
    return re.sub(r'\s+', ' ', s).strip()

def family_of(fn):
    if fn == 'index.html': return 'index'
    if fn == EXTRA_PAGE: return 'clinical'
    if fn == 'psychotropic-drugs.html': return 'drugs'
    if fn.startswith('沈渔邨'): return 'symptom'
    s = open(os.path.join(ROOT, fn), encoding='utf-8').read()
    m = re.search(r':root\s*\{([\s\S]{0,700}?)\}', s)
    head = m.group(1) if m else ''
    return 'chapterA' if '--symptom' in head else 'chapterB'

def build_index(files):
    names, titles, entries = [], [], []
    for fn in files:
        s = open(os.path.join(ROOT, fn), encoding='utf-8').read()
        # 去掉增强层与脚本样式，保证重复构建时索引稳定（幂等）
        s = re.sub(re.escape(CSS_START) + r'[\s\S]*?' + re.escape(CSS_END), ' ', s)
        s = re.sub(re.escape(UI_START) + r'[\s\S]*?' + re.escape(UI_END), ' ', s)
        s = re.sub(r'<script\b[\s\S]*?</script>', ' ', s, flags=re.I)
        s = re.sub(r'<style\b[\s\S]*?</style>', ' ', s, flags=re.I)
        fi = len(names)
        names.append(fn)
        mt = re.search(r'<title[^>]*>([\s\S]*?)</title>', s, re.I | re.S)
        titles.append(strip_tags(mt.group(1)) if mt else fn)
        if fn == 'index.html':
            continue
        parts = re.split(r'(?=<section\b)', s, flags=re.I)
        for part in parts:
            mo = re.match(r'<section\b([^>]*)>', part, re.I)
            if not mo:
                continue
            am = re.search(r'\bid=["\']([^"\']+)["\']', mo.group(1))
            anchor = am.group(1) if am else ''
            hm = re.search(r'<h[23][^>]*>([\s\S]*?)</h[23]>', part, re.I)
            title = strip_tags(hm.group(1)) if hm else ''
            if not title:
                continue
            cells = []
            for tr in re.findall(r'<tr\b[^>]*>([\s\S]*?)</tr>', part, re.I)[:12]:
                td = re.search(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', tr, re.I)
                if td:
                    v = strip_tags(td.group(1))[:40]
                    if v: cells.append(v)
            # 全文分段：按句子切成 ~240 字的块，使正文深部内容也能被检索命中
            body = strip_tags(part)
            if cells:
                body += ' ' + ' / '.join(cells)
            chunks, cur = [], ''
            for sent in re.split(r'(?<=[。！？；!?])', body):
                if cur and len(cur) + len(sent) > 200:
                    chunks.append(cur)
                    cur = sent
                else:
                    cur += sent
                if len(chunks) >= CHUNK_CAP:
                    break
            if cur.strip() and len(chunks) < CHUNK_CAP:
                chunks.append(cur)
            chunks = [c.strip() for c in chunks if c.strip()] or [title]
            for c in chunks:
                entries.append([fi, anchor, title[:70], c[:300]])
    return {'n': names, 't': titles, 'e': entries}

CSS = r'''
:root{--psyx-ui-bg:#ffffff;--psyx-ui-fg:#152033;--psyx-ui-muted:#64748b;--psyx-ui-line:#dbe3ee;--psyx-ui-accent:#0f6e56;--psyx-ui-soft:#e8f3ef;--psyx-ui-danger:#b42318}
html[data-psyx-theme="dark"]{--psyx-ui-bg:#171f2c;--psyx-ui-fg:#e7edf7;--psyx-ui-muted:#9aabc0;--psyx-ui-line:#2d3a4e;--psyx-ui-accent:#5ee0b0;--psyx-ui-soft:#1d2b37;--psyx-ui-danger:#fda29b}
.psyx-fab{position:fixed;right:18px;bottom:18px;z-index:9000;display:flex;flex-direction:column;gap:8px;font-family:inherit}
.psyx-fab button{width:46px;height:46px;border-radius:14px;border:1px solid var(--psyx-ui-line);background:var(--psyx-ui-bg);color:var(--psyx-ui-accent);font-size:19px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(15,23,42,.13)}
.psyx-fab button:hover{border-color:var(--psyx-ui-accent)}
.psyx-fab .psyx-mini{font-size:11px;font-weight:600;letter-spacing:.02em}
.psyx-modal{position:fixed;inset:0;z-index:9500;display:none;align-items:flex-start;justify-content:center;padding:11vh 16px 24px;background:rgba(9,16,28,.52)}
.psyx-modal.open{display:flex}
.psyx-panel{width:min(680px,100%);max-height:78vh;overflow:auto;background:var(--psyx-ui-bg);color:var(--psyx-ui-fg);border:1px solid var(--psyx-ui-line);border-radius:16px;padding:18px 20px;font-family:inherit;font-size:14px;line-height:1.6}
.psyx-panel h2{font-size:16px;font-weight:600;margin:0 0 12px;color:var(--psyx-ui-fg)}
.psyx-panel input{width:100%;padding:12px 14px;border:1px solid var(--psyx-ui-line);border-radius:10px;background:transparent;color:var(--psyx-ui-fg);font-size:15px;font-family:inherit}
.psyx-panel input:focus{outline:2px solid var(--psyx-ui-accent);outline-offset:1px}
.psyx-meta{display:flex;justify-content:space-between;gap:12px;color:var(--psyx-ui-muted);font-size:12px;margin:10px 2px 6px}
.psyx-hits{display:flex;flex-direction:column;gap:6px}
.psyx-hit{text-align:left;border:1px solid var(--psyx-ui-line);border-radius:10px;background:transparent;color:var(--psyx-ui-fg);padding:10px 12px;cursor:pointer;font-family:inherit}
.psyx-hit:hover,.psyx-hit.is-active{border-color:var(--psyx-ui-accent);background:var(--psyx-ui-soft)}
.psyx-hit b{display:block;font-size:13px;font-weight:600}
.psyx-hit small{display:block;color:var(--psyx-ui-muted);font-size:12px;margin-top:2px}
.psyx-hit mark{background:#fde68a;color:#3b2f00;padding:0 1px}
.psyx-stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:8px 0 14px}
.psyx-stat{background:var(--psyx-ui-soft);border-radius:10px;padding:10px 12px}
.psyx-stat span{display:block;color:var(--psyx-ui-muted);font-size:12px}
.psyx-stat b{font-size:18px;font-weight:600;color:var(--psyx-ui-fg)}
.psyx-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.psyx-links a,.psyx-close{display:inline-block;border:1px solid var(--psyx-ui-line);border-radius:8px;padding:7px 11px;color:var(--psyx-ui-accent);text-decoration:none;background:transparent;font-size:13px;cursor:pointer;font-family:inherit}
.psyx-links a:hover{border-color:var(--psyx-ui-accent)}
.psyx-flag{outline:3px solid #f59e0b!important;outline-offset:3px;border-radius:4px;transition:outline-color 1.4s}
#psyx-continue{background:var(--psyx-ui-soft);border:1px solid var(--psyx-ui-line);border-radius:14px;padding:16px 20px;margin:0 0 24px;color:var(--psyx-ui-fg)}
#psyx-continue h2{font-size:15px;font-weight:600;margin:0 0 8px}
#psyx-continue p{margin:4px 0;color:var(--psyx-ui-muted);font-size:13px}
#psyx-continue a{color:var(--psyx-ui-accent);font-weight:600}
@media(max-width:600px){.psyx-fab{right:12px;bottom:12px}.psyx-fab button{width:42px;height:42px;border-radius:12px}.psyx-panel{padding:14px;max-height:82vh}}
@media print{.psyx-fab,.psyx-modal{display:none!important}#psyx-continue{display:none!important}}
html[data-psyx-theme="dark"] body,
html[data-psyx-theme="dark"] .page,
html[data-psyx-theme="dark"] main,
html[data-psyx-theme="dark"] .content{background:#0d1119!important;color:#dfe6f1!important}
html[data-psyx-theme="dark"] .sidebar,
html[data-psyx-theme="dark"] .topbar,
html[data-psyx-theme="dark"] .hero,
html[data-psyx-theme="dark"] .cover,
html[data-psyx-theme="dark"] header,
html[data-psyx-theme="dark"] .masthead{background:#141c28!important;color:#e6edf7!important;background-image:none!important}
html[data-psyx-theme="dark"] .card,
html[data-psyx-theme="dark"] .module,
html[data-psyx-theme="dark"] .callout,
html[data-psyx-theme="dark"] .note,
html[data-psyx-theme="dark"] .quiz-block,
html[data-psyx-theme="dark"] .quiz-item,
html[data-psyx-theme="dark"] .flashcard,
html[data-psyx-theme="dark"] .case,
html[data-psyx-theme="dark"] .table-wrap,
html[data-psyx-theme="dark"] section,
html[data-psyx-theme="dark"] .panel,
html[data-psyx-theme="dark"] .box,
html[data-psyx-theme="dark"] .quote,
html[data-psyx-theme="dark"] details,
html[data-psyx-theme="dark"] .pills span,
html[data-psyx-theme="dark"] .badge,
html[data-psyx-theme="dark"] tbody tr:hover,
html[data-psyx-theme="dark"] .tab-panel{background:#161e2b!important;color:#dbe3ee!important;border-color:#2a3648!important;box-shadow:none!important}
html[data-psyx-theme="dark"] th{background:#1c2635!important;color:#dbe3ee!important}
html[data-psyx-theme="dark"] tbody tr:hover td{background:#1a2434!important}
html[data-psyx-theme="dark"] .badge,
html[data-psyx-theme="dark"] .pills span{color:#86efac!important;border-color:#2f6b52!important}
html[data-psyx-theme="dark"] .badge.fix{color:#fdba74!important;border-color:#7c4a1d!important}
html[data-psyx-theme="dark"] td.num{color:#5eead4!important}
html[data-psyx-theme="dark"] h1,html[data-psyx-theme="dark"] h2,html[data-psyx-theme="dark"] h3,html[data-psyx-theme="dark"] h4,
html[data-psyx-theme="dark"] p,html[data-psyx-theme="dark"] li,html[data-psyx-theme="dark"] td,html[data-psyx-theme="dark"] th,
html[data-psyx-theme="dark"] strong,html[data-psyx-theme="dark"] b,html[data-psyx-theme="dark"] span,html[data-psyx-theme="dark"] small,
html[data-psyx-theme="dark"] div,html[data-psyx-theme="dark"] em,html[data-psyx-theme="dark"] i,html[data-psyx-theme="dark"] figcaption,
html[data-psyx-theme="dark"] dt,html[data-psyx-theme="dark"] dd,html[data-psyx-theme="dark"] blockquote,html[data-psyx-theme="dark"] label,
html[data-psyx-theme="dark"] cite,html[data-psyx-theme="dark"] time,html[data-psyx-theme="dark"] code,html[data-psyx-theme="dark"] caption,
html[data-psyx-theme="dark"] legend,html[data-psyx-theme="dark"] mark,html[data-psyx-theme="dark"] sup,html[data-psyx-theme="dark"] sub{color:#dbe3ee!important}
html[data-psyx-theme="dark"] a{color:#7dd3fc!important}
html[data-psyx-theme="dark"] table,html[data-psyx-theme="dark"] th,html[data-psyx-theme="dark"] td{border-color:#2a3648!important}
html[data-psyx-theme="dark"] input,html[data-psyx-theme="dark"] button{background:#1c2635!important;color:#dbe3ee!important;border-color:#2a3648!important}
html[data-psyx-theme="dark"] .psyx-fab button,
html[data-psyx-theme="dark"] .psyx-links a,
html[data-psyx-theme="dark"] .psyx-close{background:var(--psyx-ui-bg)!important;color:var(--psyx-ui-accent)!important;border-color:var(--psyx-ui-line)!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] body,
html[data-psyx-page="symptom"][data-psyx-theme="light"] main,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .chapter{background:#f4f6fb!important;color:#152033!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] .sidebar,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .hero,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .card,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .chapter,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .sym,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .tablewrap{background:#ffffff!important;color:#152033!important;border-color:#dbe3ee!important;background-image:none!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] h1,html[data-psyx-page="symptom"][data-psyx-theme="light"] h2,
html[data-psyx-page="symptom"][data-psyx-theme="light"] h3,html[data-psyx-page="symptom"][data-psyx-theme="light"] p,
html[data-psyx-page="symptom"][data-psyx-theme="light"] td,html[data-psyx-page="symptom"][data-psyx-theme="light"] li,
html[data-psyx-page="symptom"][data-psyx-theme="light"] span,html[data-psyx-page="symptom"][data-psyx-theme="light"] b{color:#152033!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] .sidebar,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .sidebar *{color:#152033!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] .sidebar a{color:#0f6e56!important}
html[data-psyx-page="symptom"][data-psyx-theme="light"] .body-glow,
html[data-psyx-page="symptom"][data-psyx-theme="light"] .hero-bg{display:none!important}

/* ---- 暗色：组件表面补全（A/B 两族章节页 + 药物页 + 工具页，共 80+ 类） ---- */
/* 1) 中性白卡 → 深面板 */
html[data-psyx-theme="dark"] :is(.quiz-q,.fc-front,.flashcard-face,.sec-lead,.case-card,.route-card,.km-card,.m-formula,.stat-card,.m-type,.class-card,figure.diagram,figure.chart-figure,div.q,article.q,.mini-card,.termfix,.check,.step,.tablewrap,.table-wrap,.sym,.split,.chapter-end,.disclaimer,.hero-quote,.lev,.lv,span.lv,.lv1,.lv2,.lv3,.lv4,table,span.chap){background:#161e2b!important;border-color:#2a3648!important;box-shadow:none!important}
html[data-psyx-theme="dark"] :is(.sec-lead,.disclaimer,.hero-quote,span.lv,.lev){background:#141c28!important}
/* 2) 中性浅灰卡 → 更深一档 */
html[data-psyx-theme="dark"] :is(.mini,.opt,summary,.fact,.case-questions,ol.case-questions,.kv,span.ts,span.tone,.cp-disabled,span.bar-track,kbd){background:#121a26!important;border-color:#2a3648!important;color:#c3cfe0!important}
html[data-psyx-theme="dark"] tbody tr{background:#161e2b!important}
html[data-psyx-theme="dark"] tbody tr:nth-child(even){background:#131b27!important}
html[data-psyx-theme="dark"] td,html[data-psyx-theme="dark"] tbody td{background:transparent!important}
/* 3) 彩色浅底 → 深色同调（保留语义色差） */
html[data-psyx-theme="dark"] :is(.scene,.exam-alert){background:#2a2117!important;border-color:#4a3a22!important}
html[data-psyx-theme="dark"] .memory-card{background:#211d33!important;border-color:#3a3358!important}
html[data-psyx-theme="dark"] :is(.fc-back,.flashcard-back){background:#0f2830!important;border-color:#1d4a56!important;color:#cbe9f2!important}
html[data-psyx-theme="dark"] .quiz-score{background:#0f2431!important;border-color:#1d4257!important;color:#dbe3ee!important}
html[data-psyx-theme="dark"] :is(a.toc.active,.toc .active,.toc a.active){background:#123246!important;color:#7dd3fc!important}
html[data-psyx-theme="dark"] .toc span{background:#123246!important;color:#7dd3fc!important;border-color:#1d4257!important}
html[data-psyx-theme="dark"] .stat span{background:#123246!important;color:#7dd3fc!important;border-color:#1d4257!important}
html[data-psyx-theme="dark"] :is(.case-meta,.exam-meta,.m-meta,.card-meta,.case-tags) span{background:#2b2414!important;color:#fcd34d!important;border-color:#5c4a1d!important}
html[data-psyx-theme="dark"] a.active{background:#12323a!important;color:#7dd3fc!important}
html[data-psyx-theme="dark"] :is(a.cp-prev,a.cp-next,a.skip){background:#161e2b!important;border-color:#2a3648!important;color:#7dd3fc!important}
html[data-psyx-theme="dark"] .module-index,html[data-psyx-theme="dark"] span.module-index{background:#b45309!important;color:#fff!important}
/* 4) 徽标 / 标签：深底 + 语义文字色 */
html[data-psyx-theme="dark"] :is(span.ctag,.tag.risk,.tag.tag-core){background:#331b1e!important;color:#fca5a5!important;border-color:#5c2b30!important}
html[data-psyx-theme="dark"] :is(span.qtype,.tag.memory,span.tag.tag-memory,.card-tag.memory){background:#291d33!important;color:#d8b4fe!important;border-color:#463060!important}
html[data-psyx-theme="dark"] :is(span.answer-key,.tag.treat,.tag.tag-master,.card-tag.treatment){background:#12291d!important;color:#86efac!important;border-color:#2f6b52!important}
html[data-psyx-theme="dark"] :is(span.q-type,.tag.data){background:#2f1a26!important;color:#f9a8d4!important;border-color:#542a3d!important}
html[data-psyx-theme="dark"] :is(span.diff,.tag.tag-know,.card-tag.diagnosis){background:#2b2414!important;color:#fcd34d!important;border-color:#5c4a1d!important}
html[data-psyx-theme="dark"] :is(.tag.concept,.tag.tag-understand,.card-tag.concept,span.qn){background:#17253c!important;color:#93c5fd!important;border-color:#2b4368!important}
html[data-psyx-theme="dark"] .tag.diag{background:#2c2113!important;color:#fdba74!important;border-color:#5c4423!important}
html[data-psyx-theme="dark"] .tag:not(.hot):not(.cold),html[data-psyx-theme="dark"] span.tag{background:#1a2330!important;color:#cbd5e1!important;border-color:#2a3648!important}
html[data-psyx-theme="dark"] .tag.hot{background:#16291f!important;color:#86efac!important}
html[data-psyx-theme="dark"] .tag.cold{background:#2a2118!important;color:#fdba74!important}
/* 5) 高饱和实底徽标：压深底色保证对比度 */
html[data-psyx-theme="dark"] :is(.idx,.lab,span.idx,span.lab){background:#0369a1!important;color:#e0f2fe!important}
html[data-psyx-theme="dark"] :is(.qno,span.qno){background:#9d174d!important;color:#fce7f3!important}
html[data-psyx-theme="dark"] :is(.n,span.n){background:#075985!important;color:#e0f2fe!important;border-color:#0369a1!important}
'''

UI = r'''
<div class="psyx-fab" aria-label="学习工具">
  <button id="psyx-search-btn" type="button" title="全站检索 (Ctrl+K)" aria-label="全站检索">⌕</button>
  <button id="psyx-panel-btn" type="button" title="学习面板" aria-label="学习面板">▤</button>
  <button id="psyx-theme-btn" type="button" title="切换主题" aria-label="切换主题">◐</button>
</div>
<div class="psyx-modal" id="psyx-modal" role="dialog" aria-modal="true" aria-labelledby="psyx-modal-title">
  <div class="psyx-panel">
    <h2 id="psyx-modal-title">全站检索</h2>
    <input id="psyx-q" type="search" placeholder="搜索症状、药物、诊断标准、鉴别要点…（Ctrl+K 打开，Esc 关闭）" autocomplete="off">
    <div class="psyx-meta"><span id="psyx-count">输入关键词开始检索</span><span>↑↓ 选择 · Enter 跳转</span></div>
    <div class="psyx-hits" id="psyx-hits"></div>
    <div class="psyx-links"><button type="button" class="psyx-close" id="psyx-close">关闭</button></div>
  </div>
</div>
<div class="psyx-modal" id="psyx-pmodal" role="dialog" aria-modal="true" aria-labelledby="psyx-ptitle">
  <div class="psyx-panel">
    <h2 id="psyx-ptitle">学习面板</h2>
    <div class="psyx-stats">
      <div class="psyx-stat"><span>本页阅读</span><b id="psyx-s-progress">0%</b></div>
      <div class="psyx-stat"><span>自测成绩</span><b id="psyx-s-quiz">—</b></div>
      <div class="psyx-stat"><span>速记卡翻阅</span><b id="psyx-s-cards">0</b></div>
      <div class="psyx-stat"><span>已收藏章节</span><b id="psyx-s-books">0</b></div>
    </div>
    <div class="psyx-links">
      <button type="button" class="psyx-close" id="psyx-bookmark">收藏本页</button>
      <a href="clinical-workflow.html">临床工具箱</a>
      <a href="textbook-guide.html">教材对照</a>
      <a href="index.html">总目录 / 继续学习</a>
      <button type="button" class="psyx-close" id="psyx-pclose">关闭</button>
    </div>
    <p id="psyx-books-list" style="margin-top:12px;font-size:13px;color:var(--psyx-ui-muted)"></p>
    <h2 style="margin-top:18px">知识联动</h2>
    <div class="psyx-links" id="psyx-related"></div>
  </div>
</div>
'''

JS = r'''
(async function(){
'use strict';
var IDX = __INDEX__;
var FILE = __FILE__;
var ORDER = __ORDER__;
var LS = {
 get:function(k,d){try{var v=localStorage.getItem('psyx:'+k);return v==null?d:JSON.parse(v)}catch(e){return d}},
 set:function(k,v){try{localStorage.setItem('psyx:'+k,JSON.stringify(v))}catch(e){}}
};
function $(s){return document.querySelector(s)}
function esc(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function mark(s,terms){var out=esc(s);terms.forEach(function(t){if(!t)return;var re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi');out=out.replace(re,'<mark>$1</mark>')});return out}
function toast(msg){var b=$('#psyx-bookmark');if(b)b.textContent=msg;setTimeout(function(){if(b)b.textContent=isBookmarked()?'取消收藏':'收藏本页'},1800)}
function isBookmarked(){var a=LS.get('bookmarks',[]);return a.indexOf(FILE)>=0}

var theme=LS.get('theme',null);
if(theme==='dark'||theme==='light')document.documentElement.setAttribute('data-psyx-theme',theme);
else if(document.documentElement.getAttribute('data-psyx-page')==='symptom')document.documentElement.setAttribute('data-psyx-theme','dark');
$('#psyx-theme-btn').addEventListener('click',function(){
 var cur=document.documentElement.getAttribute('data-psyx-theme')||'light';
 var next=cur==='dark'?'light':'dark';
 document.documentElement.setAttribute('data-psyx-theme',next);LS.set('theme',next);
 this.textContent=next==='dark'?'☀':'◐';
});

function openM(id){$(id).classList.add('open');setTimeout(function(){var i=$('#psyx-q');if(i)i.focus()},30)}
function closeM(){document.querySelectorAll('.psyx-modal').forEach(function(m){m.classList.remove('open')})}
$('#psyx-search-btn').addEventListener('click',function(){openM('#psyx-modal')});
$('#psyx-panel-btn').addEventListener('click',function(){refreshPanel();openM('#psyx-pmodal')});
$('#psyx-close').addEventListener('click',closeM);
$('#psyx-pclose').addEventListener('click',closeM);
document.querySelectorAll('.psyx-modal').forEach(function(m){m.addEventListener('mousedown',function(e){if(e.target===m)closeM()})});
document.addEventListener('keydown',function(e){
 var typing=/^(INPUT|TEXTAREA)$/.test((e.target.tagName||''));
 if((e.ctrlKey||e.metaKey)&&String(e.key).toLowerCase()==='k'){e.preventDefault();closeM();openM('#psyx-modal')}
 else if(e.key==='Escape'){closeM()}
});

var hits=[],active=-1;
function search(q){
 var terms=q.toLowerCase().split(/\s+/).filter(Boolean);if(!terms.length)return[];
 var out=[],me=IDX.n.indexOf(FILE);
 for(var i=0;i<IDX.e.length;i++){
  var e=IDX.e[i],title=e[2],text=e[3],blob=(title+' '+text).toLowerCase();
  if(!terms.every(function(t){return blob.indexOf(t)>=0}))continue;
  var inTitle=terms.every(function(t){return title.toLowerCase().indexOf(t)>=0});
  // 排序权重：本节标题命中 < 本页正文命中 < 他页标题命中 < 他页正文命中
  var rank=(inTitle?0:2)+(e[0]===me?0:1);
  out.push({e:e,rank:rank,i:i});
 }
 out.sort(function(a,b){return a.rank-b.rank||a.i-b.i});
 var seen={},keep=[];
 for(var j=0;j<out.length;j++){var key=out[j].e[0]+'|'+out[j].e[1];if(seen[key])continue;seen[key]=1;keep.push(out[j])}
 return keep.slice(0,20);
}
function snip(text,terms){
 var low=text.toLowerCase(),p=-1;
 terms.forEach(function(t){var k=low.indexOf(t);if(k>=0&&(p<0||k<p))p=k});
 if(p<0)return text.slice(0,110);
 var a=Math.max(0,p-42),b=Math.min(text.length,a+120);
 return (a>0?'…':'')+text.slice(a,b)+(b<text.length?'…':'');
}
function render(q){
 hits=search(q);active=-1;
 var terms=q.toLowerCase().split(/\s+/).filter(Boolean);
 $('#psyx-count').textContent=hits.length?hits.length+' 条结果（最多 20 条）':'没有找到匹配内容';
 var box=$('#psyx-hits');box.innerHTML='';
 hits.forEach(function(h,i){
  var e=h.e,page=IDX.t[e[0]]||IDX.n[e[0]];
  var b=document.createElement('button');b.type='button';b.className='psyx-hit';
  b.innerHTML='<b>'+mark(e[2],terms)+'</b><small>'+esc(page)+' · '+mark(snip(e[3],terms),terms)+'</small>';
  b.addEventListener('click',function(){go(e)});
  box.appendChild(b);
 });
}
var qt;
$('#psyx-q').addEventListener('input',function(){var v=this.value;clearTimeout(qt);qt=setTimeout(function(){render(v)},80)});
$('#psyx-q').addEventListener('keydown',function(e){
 var list=document.querySelectorAll('.psyx-hit');
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){
  e.preventDefault();if(!list.length)return;
  active+=(e.key==='ArrowDown'?1:-1);if(active<0)active=list.length-1;if(active>=list.length)active=0;
  list.forEach(function(b,i){b.classList.toggle('is-active',i===active)});
  list[active].scrollIntoView({block:'nearest'});
 }else if(e.key==='Enter'&&active>=0&&hits[active]){e.preventDefault();go(hits[active].e)}
});
function go(e){
 var file=IDX.n[e[0]],url=file+(e[1]?'#'+e[1]:'');
 closeM();
 if(file===FILE){if(e[1]){var t=document.getElementById(e[1]);if(t){t.scrollIntoView({behavior:'smooth',block:'start'});flash(t)}}}
 else location.href=url;
}
function flash(el){el.classList.add('psyx-flag');setTimeout(function(){el.style.outlineColor='transparent';setTimeout(function(){el.classList.remove('psyx-flag');el.style.outlineColor=''},1500)},700)}
if(location.hash){var el=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(el)setTimeout(function(){el.scrollIntoView({block:'start'});flash(el)},120)}

var progress=LS.get('progress',{}),cards=LS.get('cards',{}),books=LS.get('bookmarks',[]),last=LS.get('last',{});
if(FILE!=='index.html'){last={file:FILE,ts:Date.now()};LS.set('last',last)}
function paintProgress(){
 var h=document.documentElement,max=h.scrollHeight-h.clientHeight;
 if(max<=0)return;
 var pct=Math.min(100,Math.round((window.scrollY||h.scrollTop||0)/max*100));
 progress[FILE]=pct;LS.set('progress',progress);
}
var tick=false;
window.addEventListener('scroll',function(){
 if(tick)return;tick=true;requestAnimationFrame(function(){tick=false;paintProgress()});
},{passive:true});
setTimeout(paintProgress,300);
setTimeout(paintProgress,1200);

function quizScore(){
 var n=document.querySelector('.quiz-score .qs-num');
 if(n){var m=n.textContent.match(/(\d+)\s*\/\s*(\d+)/);if(m)return m[1]+' / '+m[2]}
 var r=document.querySelector('#quizResult');
 if(r&&r.textContent){var m2=r.textContent.match(/得分\s*(\d+)\s*\/\s*(\d+)/);if(m2)return m2[1]+' / '+m2[2]}
 return '—';
}
var lastQuiz=quizScore();
function watchQuiz(){
 var cur=quizScore();
 if(cur!==lastQuiz){lastQuiz=cur;if(cur!=='—'){var q=LS.get('quiz',{});q[FILE]=cur;LS.set('quiz',q)}}
 setTimeout(watchQuiz,1200);
}
watchQuiz();
document.addEventListener('click',function(e){
 var c=e.target.closest?e.target.closest('.flashcard'):null;
 if(!c)return;
 var list=Array.prototype.slice.call(document.querySelectorAll('.flashcard'));
 var i=list.indexOf(c);if(i<0)return;
 var a=cards[FILE]||[];if(a.indexOf(i)<0){a.push(i);cards[FILE]=a;LS.set('cards',cards)}
},true);

function related(){
 var box=$('#psyx-related');if(!box)return;
 var i=ORDER.indexOf(FILE),h='';
 if(i>=0){
  if(i>0)h+='<a href="'+esc(ORDER[i-1])+'">← '+esc((IDX.t[IDX.n.indexOf(ORDER[i-1])]||'上一章').replace(/^精神病学\s*/,''))+'</a>';
  if(i<ORDER.length-1)h+='<a href="'+esc(ORDER[i+1])+'">'+esc((IDX.t[IDX.n.indexOf(ORDER[i+1])]||'下一章').replace(/^精神病学\s*/,''))+' →</a>';
 }
 h+='<a href="clinical-workflow.html#scales">量表速查</a><a href="clinical-workflow.html#evidence">证据来源说明</a>';
 box.innerHTML=h;
}
function refreshPanel(){
 related();
 $('#psyx-s-progress').textContent=(progress[FILE]||0)+'%';
 $('#psyx-s-quiz').textContent=quizScore();
 $('#psyx-s-cards').textContent=(cards[FILE]||[]).length;
 $('#psyx-s-books').textContent=books.length;
 $('#psyx-bookmark').textContent=isBookmarked()?'取消收藏':'收藏本页';
 var names=books.map(function(f){return IDX.t[IDX.n.indexOf(f)]||f});
 $('#psyx-books-list').textContent=names.length?'已收藏：'+names.join('、'):'尚未收藏章节';
}
$('#psyx-bookmark').addEventListener('click',function(){
 var i=books.indexOf(FILE);
 if(i>=0){books.splice(i,1);toast('已取消收藏')}else{books.push(FILE);toast('已收藏本页')}
 LS.set('bookmarks',books);refreshPanel();
});
refreshPanel();

if(FILE==='index.html'){
 var box=document.createElement('div');box.id='psyx-continue';
 var main=document.querySelector('.page')||document.body;
 main.insertBefore(box,main.firstChild);
 var prog=LS.get('progress',{}),qz=LS.get('quiz',{}),bk=LS.get('bookmarks',[]);
 var visited=Object.keys(prog).filter(function(k){return prog[k]>0}).length;
 var lf=IDX.t[IDX.n.indexOf(last.file)]||last.file;
 box.innerHTML='<h2>继续学习</h2>'+
  (last.file?'<p>上次阅读：<a href="'+esc(last.file)+'">'+esc(lf||last.file)+'</a> · 完成度 '+(prog[last.file]||0)+'%</p>':'<p>还没有阅读记录，从下方任意章节开始。</p>')+
  '<p>已读 '+visited+' / '+(IDX.n.length-1)+' 页 · 已收藏 '+bk.length+' 页 · 自测记录 '+Object.keys(qz).length+' 条</p>'+
  '<p><a href="clinical-workflow.html">打开临床工具箱 →</a></p>';
}
})();
'''

def clean(s):
    s = re.sub(re.escape(CSS_START) + r'[\s\S]*?' + re.escape(CSS_END) + r'\n?', '', s)
    s = re.sub(re.escape(UI_START) + r'[\s\S]*?' + re.escape(UI_END) + r'\n?', '', s)
    return s

def real_close(s, close_tag, guard_tags):
    """定位真正结束 <head>/<body> 的闭合标签。

    页面自带的 CSS 注释里出现过字面量 </head>（apply-refactor.ps1 的说明文字），
    若直接取首个匹配，注入块会落进 <style> 原始文本内部，导致该样式表被提前截断、
    整表失效。这里跳过所有位于未闭合 <style>/<script> 内部的伪闭合标签。
    """
    low = s.lower()
    start = 0
    while True:
        i = low.find(close_tag, start)
        if i < 0:
            return -1
        inside_raw_text = False
        for op in guard_tags:
            j = low.rfind(op, 0, i)
            if j >= 0 and low.rfind('</' + op[1:], 0, i) < j:
                inside_raw_text = True
                break
        if not inside_raw_text:
            return i
        start = i + 1

def inject(fn, index_b64, family, title):
    path = os.path.join(ROOT, fn)
    s = open(path, encoding='utf-8').read()
    s = clean(s)
    def fix(m):
        attrs = re.sub(r'\s+data-psyx-(?:page|title)="[^"]*"', '', m.group(1))
        return '<html' + attrs + ' data-psyx-page="' + family + '" data-psyx-title="' + html.escape(title, quote=True) + '">'
    s = re.sub(r'<html\b([^>]*)>', fix, s, count=1, flags=re.I)
    js = (JS.replace('__INDEX__', 'JSON.parse(await decompress("' + index_b64 + '"))')
            .replace('__FILE__', json.dumps(fn))
            .replace('__ORDER__', json.dumps(CHAPTER_ORDER, ensure_ascii=False)))
    decompress_helper = r'''function decompress(b64){
 try{
  var bin=atob(b64),arr=new Uint8Array(bin.length);
  for(var i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
  var stream=new Blob([arr]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).text();
 }catch(e){return '{"n":[],"t":[],"e":[]}'}
}
'''
    js = decompress_helper + js
    css_block = CSS_START + '\n<style>\n' + CSS + '\n</style>\n' + CSS_END + '\n'
    ui_block = UI_START + '\n' + UI + '\n<script>\n' + js + '\n</script>\n' + UI_END + '\n'
    hi = real_close(s, '</head>', ('<style', '<script'))
    if hi >= 0:
        s = s[:hi] + css_block + s[hi:]
    else:
        s = css_block + s
    bi = real_close(s, '</body>', ('<style', '<script'))
    if bi >= 0:
        s = s[:bi] + ui_block + s[bi:]
    else:
        s += ui_block
    open(path, 'w', encoding='utf-8').write(s)
    return len(s)

def main():
    global CHAPTER_ORDER
    files = pages()
    if EXTRA_PAGE not in files:
        raise SystemExit('缺少 ' + EXTRA_PAGE + '，请先生成临床工具页')
    idx_html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    CHAPTER_ORDER = re.findall(r'href="(精神病学_第[^"]+\.html)"', idx_html)
    idx = build_index(files)
    raw = json.dumps(idx, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    b64 = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode('ascii')
    print('索引条目', len(idx['e']), '原始', round(len(raw)/1024), 'KB → gzip+base64', round(len(b64)/1024), 'KB')
    total = 0
    for fn in files:
        fam = family_of(fn)
        mt = re.search(r'<title[^>]*>([\s\S]*?)</title>', open(os.path.join(ROOT, fn), encoding='utf-8').read(), re.I | re.S)
        title = strip_tags(mt.group(1)) if mt else fn
        total += inject(fn, b64, fam, title)
    print('注入完成', len(files), '页，总字节', round(total/1024/1024, 2), 'MB')

if __name__ == '__main__':
    main()
