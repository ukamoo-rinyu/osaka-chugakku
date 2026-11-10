import json, re, csv, sys, unicodedata
from collections import defaultdict, OrderedDict

rows = json.load(open(sys.argv[1]))
for r in rows:
    for k in ('ku','chu','sho'):
        r[k] = unicodedata.normalize('NFKC', r[k])
    if r['sho'] == '浪なみは速や': r['sho'] = '浪速'
Z = '０１２３４５６７８９'
def z2h(s): return s.translate(str.maketrans(Z, '0123456789'))
def h2z(s): return s.translate(str.maketrans('0123456789', Z))
D = r'[0-9０-９]+'

def expand_chome(spec):
    """'１丁目～３丁目、５丁目' / '３～６丁目' -> [1,2,3,5]"""
    out = []
    s = z2h(spec).replace('丁目', '')
    for part in re.split(r'[、・,]', s):
        if not part: continue
        m = re.fullmatch(r'(\d+)[～~\-](\d+)', part)
        if m: out += list(range(int(m[1]), int(m[2]) + 1))
        elif part.isdigit(): out.append(int(part))
    return out

recs = []   # one per (school row, town, chome)
prev = None
last_idx = []
for r in rows:
    key = (r['ku'], r['chu'], r['sho'])
    if key != prev: town = None; chomes = None; loc_ku = r['ku'] + '区'
    prev = key
    lines_ = [l for l in r['text'].split('\n') if l.strip()]
    # 他区の学校へ行く旨の参照注記（「～は、○区○小、○中へ」）は割当ではないので除外
    if lines_ and re.search(r'区.*へ$', lines_[-1].replace(' ', '')):
        continue
    for raw in lines_:
        line = unicodedata.normalize('NFKC', raw).replace(' ', '').strip()
        if not line: continue
        # 他区の町を含む場合の区見出し（例: 浪 速 区）
        if re.fullmatch(r'.{1,3}区', line):
            loc_ku = line; continue
        # 注記行
        if re.search(r'学校区は|児童遊園', line) or line.lstrip('※')[0] in '([〔':
            if recs and recs[-1]['sho'] == r['sho']:
                recs[-1]['note'] += line
                if re.search(r'除|一部', line):
                    for i in last_idx:
                        recs[i]['partial'] = True; recs[i]['detail'] += line
            continue
        if line[0] in 'を、':   # 前行の続き
            if recs: recs[-1]['detail'] += line
            continue
        line = re.sub(r'^(上町)([A-ZＡ-Ｚ])', r'\1 \2', line)  # 上町A番 等
        star = line.startswith('※')
        line = line.lstrip('※')
        m = re.match(r'^(?P<town>[^0-9０-９（(〔 ]*) ?(?P<chome>(?:' + D + r'丁目|' + D + r'[～~])(?:[～~、・]?' + D + r'丁目)*)?(?P<rest>.*)$', line)
        t, c, rest = m['town'], m['chome'], m['rest']
        # '東５番' '浜６番' style: one-char prefix before 番 -> continuation
        if t and not c and len(t) == 1 and re.match(D + '番', rest):
            rest = t + rest; t = ''
        if t:
            town = t; chomes = expand_chome(c) if c else [None]
        elif c:
            chomes = expand_chome(c)
        # else: continuation of 番/号 under previous town/chome
        if town is None: print('NO TOWN', r['page'], raw); continue
        partial = bool(re.search(r'番|号|一部|除|但し|ただし', rest)) or (not t and not c)
        last_idx = list(range(len(recs), len(recs) + len(chomes)))
        for ch in chomes:
            recs.append(dict(page=r['page'], ku=r['ku'], loc=loc_ku, chu=r['chu'], sho=r['sho'],
                             town=town, chome=ch, partial=partial, star=star,
                             detail=line, note=''))

# aggregate per (town, chome) per school
agg = OrderedDict()
for x in recs:
    k = (x['ku'], x['chu'], x['sho'], x['loc'], x['town'], x['chome'])
    a = agg.setdefault(k, dict(partial=False, details=[], notes=[], pages=set(), star=False))
    a['partial'] |= x['partial']; a['star'] |= x['star']
    if x['partial'] or x['star']: a['details'].append(x['detail'])
    if x['note']: a['notes'].append(x['note'])
    a['pages'].add(x['page'])

# how many distinct 中学校 claim each 町丁目
by_area = defaultdict(set)
for (ku, chu, sho, loc, town, ch) in agg: by_area[(loc, town, ch)].add(chu)

def name(town, ch):
    return town + (str(ch) + '丁目' if ch else '')

out = []
for (ku, chu, sho, loc, town, ch), a in agg.items():
    n_chu = len(by_area[(loc, town, ch)])
    if n_chu == 1:
        status = '単独'
    else:
        status = '要分割' if a['partial'] else '重複（選択可など）'
    out.append(OrderedDict(
        区=ku + '区', 中学校=chu + '中学校', 小学校=sho + '小学校',
        町の所在区=loc, 町名=town, 丁目=ch or '', 町丁目名=name(town, ch),
        町丁目名_全角=h2z(name(town, ch)),
        範囲='一部' if a['partial'] else '全域',
        中学校数=n_chu, 判定=status,
        番地指定='／'.join(dict.fromkeys(a['details'])),
        備考='／'.join(dict.fromkeys(a['notes'])),
        PDFページ=','.join(map(str, sorted(a['pages'])))))

with open(sys.argv[2], 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

from collections import Counter
print('rows', len(out), 'areas', len(by_area))
print(Counter(o['判定'] for o in out))
print('中学校', len(set((o['区'], o['中学校']) for o in out)))
