# -*- coding: utf-8 -*-
"""全量体检：结构 / 链接 / 锚点 / JS 语法 / 索引一致性 / 体积。只读。"""
import os, re, glob, json, gzip, base64, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
files = sorted(glob.glob('*.html'))
print('页面数', len(files))

# ---------- 1. 基础结构 ----------
def read(f):
    return open(f, encoding='utf-8').read()

report = {'pages': len(files), 'tables': 0, 'chars': 0}
ids = {}
bad = []
for f in files:
    s = read(f)
    report['tables'] += len(re.findall(r'<table\b', s, re.I))
    report['chars'] += len(re.sub(r'<[^>]+>', '', s))
    for m in re.finditer(r'\bid=["\']([^"\']+)["\']', s):
        ids.setdefault(m.group(1), []).append(f)
    # 结构平衡
    for tag in ('div', 'section', 'table', 'ul', 'ol', 'details'):
        o = len(re.findall(r'<' + tag + r'\b', s, re.I))
        c = len(re.findall(r'</' + tag + r'>', s, re.I))
        if o != c:
            bad.append((f, tag, o, c))
print('表格总数', report['tables'], '纯文本字符', report['chars'])
print('标签不平衡', len(bad), bad[:6])

# 重复 id（同页内）
dups = []
for f in files:
    s = read(f)
    seen = {}
    for m in re.finditer(r'\bid=["\']([^"\']+)["\']', s):
        seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    d = [k for k, v in seen.items() if v > 1]
    if d:
        dups.append((f, d[:5]))
print('同页重复 id', len(dups), dups[:4])

# ---------- 2. 链接与锚点 ----------
missing, badanchor, total_links = [], [], 0
for f in files:
    s = read(f)
    for m in re.finditer(r'href=["\']([^"\']+)["\']', s):
        h = m.group(1)
        if h.startswith(('http', 'mailto:', 'tel:', 'javascript:', 'data:')) or h == '#':
            continue
        total_links += 1
        path, _, frag = h.partition('#')
        path = urllib.parse.unquote(path)
        target = path or f
        if path and not os.path.exists(target):
            missing.append((f, h))
            continue
        if frag:
            ts = read(target)
            if ('id="' + frag + '"') not in ts and ("id='" + frag + "'") not in ts:
                badanchor.append((f, h))
print('站内链接', total_links, '缺失文件', len(missing), missing[:5], '锚点失效', len(badanchor), badanchor[:5])

# ---------- 3. 增强层完整性 ----------
from collections import Counter
cs = Counter()
for f in files:
    s = read(f)
    cs['css_start'] += s.count('<!-- PSYX:CSS:START -->')
    cs['css_end'] += s.count('<!-- PSYX:CSS:END -->')
    cs['ui_start'] += s.count('<!-- PSYX:UI:START -->')
    cs['ui_end'] += s.count('<!-- PSYX:UI:END -->')
    cs['data_page'] += s.count('data-psyx-page=')
print('增强层标记', dict(cs))

# 孤儿页（没有任何其他页面链接到它）
linked = set()
for f in files:
    for m in re.finditer(r'href=["\']([^"\'#]+\.html)', read(f)):
        linked.add(os.path.basename(urllib.parse.unquote(m.group(1))))
orphan = [f for f in files if f not in linked and f != 'index.html']
print('孤儿页', orphan)

# ---------- 4. 索引一致性 ----------
sys_path = os.path.join(ROOT, 'tools')
import sys
sys.path.insert(0, sys_path)
import importlib.util
spec = importlib.util.spec_from_file_location('be', os.path.join(sys_path, 'build_enhancements.py'))
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)

idx_fresh = be.build_index(be.pages())
emb = re.search(r'JSON\.parse\(await decompress\("([^"]+)"\)\)', read('index.html'))
emb_json = json.loads(gzip.decompress(base64.b64decode(emb.group(1))).decode('utf-8'))
print('索引条目', len(idx_fresh['e']), '与内嵌一致', idx_fresh == emb_json)

# ---------- 5. 体积 ----------
total = sum(os.path.getsize(f) for f in files)
print('总体积 MB', round(total / 1024 / 1024, 2), '最大页', max(files, key=lambda f: os.path.getsize(f)),
      round(max(os.path.getsize(f) for f in files) / 1024), 'KB')
