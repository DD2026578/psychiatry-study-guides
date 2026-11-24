# -*- coding: utf-8 -*-
"""医学事实一致性扫描：抽取数字类断言，按主题聚类比较跨页/页内是否自相矛盾。"""
import os, re, glob, json
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = sorted(glob.glob('*.html'))

def plain(f):
    s = open(f, encoding='utf-8').read()
    s = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'[ \t]+', ' ', s)

TEXT = {f: plain(f) for f in FILES}

# ---------- 1. 患病率 / 流行病学数字 ----------
EPI = re.compile(r'(终生患病率|终身患病率|12\s*个月患病率|12月患病率|时点患病率|年患病率|患病率|发病率|构成比)[^。；\n]{0,28}?(\d+(?:\.\d+)?\s*[%％])')
epi = defaultdict(list)
for f, t in TEXT.items():
    for m in EPI.finditer(t):
        epi[m.group(1).replace(' ', '')].append((f, m.group(2), t[max(0, m.start() - 40):m.end() + 10].strip()))
print('=' * 30, '患病率类断言')
for k, v in epi.items():
    vals = sorted(set(x[1] for x in v))
    print('[%s] %d 处, 取值 %s' % (k, len(v), vals))
    if len(vals) > 1:
        for f, val, ctx in v:
            print('    %-40s %-8s %s' % (f[:40], val, ctx[:80]))

# ---------- 2. 药物剂量跨页比对 ----------
DRUGS = ['氯丙嗪', '氟哌啶醇', '奥氮平', '喹硫平', '利培酮', '帕利哌酮', '阿立哌唑', '齐拉西酮',
         '氨磺必利', '氯氮平', '舒必利', '布南色林', '鲁拉西酮', '氟西汀', '舍曲林', '帕罗西汀',
         '艾司西酞普兰', '西酞普兰', '氟伏沙明', '文拉法辛', '度洛西汀', '米氮平', '安非他酮',
         '曲唑酮', '碳酸锂', '丙戊酸', '卡马西平', '拉莫三嗪', '地西泮', '劳拉西泮', '氯硝西泮',
         '阿普唑仑', '唑吡坦', '苯海索', '美沙酮', '丁丙诺啡']
DOSE = re.compile(r'(\d+(?:\.\d+)?(?:\s*[–\-~—至]\s*\d+(?:\.\d+)?)?)\s*(mg|g|μg|µg|mL|ml)\s*(?:/\s*(d|日|天|kg|次))?')
dose_map = defaultdict(lambda: defaultdict(list))
for f, t in TEXT.items():
    for d in DRUGS:
        for m in re.finditer(re.escape(d), t):
            seg = t[m.end():m.end() + 70]
            dm = DOSE.search(seg)
            if dm and not re.search(r'[（(]\s*$', seg[:5]):
                dose_map[d][dm.group(1).replace(' ', '') + ' ' + dm.group(2) + ('/' + dm.group(3) if dm.group(3) else '')].append(f)
print('\n' + '=' * 30, '同名药物剂量取值分布（≥2 种取值才列出）')
for d, vals in dose_map.items():
    if len(vals) > 1:
        print('[%s]' % d)
        for v, fs in sorted(vals.items(), key=lambda x: -len(x[1]))[:6]:
            print('    %-22s x%-2d %s' % (v, len(fs), fs[0][:34]))

# ---------- 3. 量表分值范围与界值 ----------
SCALES = ['PANSS', 'YMRS', 'MADRS', 'HAMD', 'HAMA', 'MADRS', 'MMSE', 'MoCA', 'GAD-7', 'PHQ-9',
          'HAMA', 'CGI', 'PSQI', 'AIS', 'YBOCS', 'C-SSRS', 'ADOS', 'ABC', 'CARS']
print('\n' + '=' * 30, '量表分值/界值断言')
for sc in sorted(set(SCALES)):
    hits = []
    for f, t in TEXT.items():
        for m in re.finditer(re.escape(sc), t):
            seg = t[m.end():m.end() + 60]
            if re.search(r'\d', seg):
                hits.append((f, seg.strip()[:60]))
    uniq = sorted(set(h[1][:40] for h in hits))
    if len(uniq) >= 1:
        print('[%s] %d 处 / %d 种表述' % (sc, len(hits), len(uniq)))
        for u in uniq[:5]:
            print('    ', u)

# ---------- 4. 时间阈值类 ----------
TIME = re.compile(r'(病程|持续|至少|不少于|超过|达到)[^。；\n]{0,18}?(\d+\s*(?:个)?(?:小时|天|周|个月|月|年))')
print('\n' + '=' * 30, '时间阈值（按主题词聚类，仅列多取值）')
tm = defaultdict(set)
for f, t in TEXT.items():
    for m in TIME.finditer(t):
        tm[m.group(1)].add((m.group(2).replace(' ', ''), f))
for k, v in tm.items():
    vals = sorted(set(x[0] for x in v))
    if len(vals) > 1:
        print('[%s] %s' % (k, vals[:10]))
