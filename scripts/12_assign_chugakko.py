import json, os, sys, re, unicodedata
from collections import defaultdict
import pandas as pd, geopandas as gpd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_parse import parse, town_norm

RAW, GPKG, OUT, CSV = sys.argv[1:5]
claims = parse(json.load(open(RAW)))
pt = gpd.read_file(GPKG, layer='街区_代表点')
poly = gpd.read_file(GPKG, layer='街区_ポリゴン')
pt['tc'] = pt['町丁目'].map(town_norm)

bans = defaultdict(set)
for r in pt.itertuples(): bans[(r.区, r.tc)].add(r.番)

by_tc = defaultdict(list)
for c in claims: by_tc[(c['loc'], c['tc'])].append(c)

# 番ごとの割当
assign = {}   # (区, tc, 番) -> {chu: kind}
for (loc, tc), cl in by_tc.items():
    for c in cl:
        targets = []
        if c['ban'] == '*':
            for b in bans.get((loc, tc), []):
                if b in c['ef']: continue
                targets.append((b, 'partial' if (b in c['ep'] or c['kind'] == 'partial') else 'full'))
        else:
            targets.append((c['ban'], c['kind']))
        for b, k in targets:
            d = assign.setdefault((loc, tc, b), {})
            if d.get(c['chu']) != 'full': d[c['chu']] = k

def judge(d):
    if not d: return None, '指定なし', ''
    chus = list(d)
    if len(chus) == 1: return chus[0], ('OK' if d[chus[0]] == 'full' else 'OK（他校指定なし）'), chus[0]
    full = [c for c in chus if d[c] == 'full']
    if len(full) == 1: return full[0], 'OK（一部は他校）', '・'.join(chus)
    if not full: return None, '号単位で分割', '・'.join(chus)
    return full[0], '重複（選択可など）', '・'.join(chus)

# 代表点に結果を付ける
res = [judge(assign.get((r.区, r.tc, r.番), {})) for r in pt.itertuples()]
pt['中学校'] = [x[0] for x in res]; pt['判定'] = [x[1] for x in res]; pt['候補'] = [x[2] for x in res]

# 街区ポリゴンへ: 中に入っている点の結果をまとめる
j = gpd.sjoin(pt[['区', '町丁目', '番', '中学校', '判定', '候補', 'geometry']], poly[['geometry']], predicate='within')
def agg(g):
    chus = list(dict.fromkeys(g['中学校'].dropna()))
    js = set(g['判定'])
    if len(chus) == 1 and not js & {'号単位で分割', '指定なし'}: st, chu = 'OK', chus[0]
    elif len(chus) == 1: st, chu = '要確認（' + '・'.join(sorted(js - {'OK'})) + '）', chus[0]
    elif len(chus) > 1: st, chu = '要確認（1つの面に複数の中学校）', None
    elif '号単位で分割' in js: st, chu = '号単位で分割', None
    else: st, chu = '指定なし', None
    return pd.Series({'中学校': chu, '判定': st, '候補': '・'.join(dict.fromkeys(x for x in g['候補'] if x)),
                      '区': '・'.join(dict.fromkeys(g['区'])), '町丁目': '・'.join(dict.fromkeys(g['町丁目'])),
                      '番': ','.join(dict.fromkeys(g['番']))})
a = j.groupby('index_right').apply(agg)
out = poly[['geometry', '面積_m2']].join(a, how='inner')
out = gpd.GeoDataFrame(out, geometry='geometry', crs=poly.crs)[['区', '町丁目', '番', '中学校', '判定', '候補', '面積_m2', 'geometry']]

# 中学校区（街区を中学校ごとにまとめ、道路のすき間を埋める）
ok = out[out['中学校'].notna()].copy()
ok['geometry'] = ok.buffer(12, join_style=2)
ku = ok.dissolve(by='中学校', as_index=False)
ku['geometry'] = ku.buffer(-12, join_style=2).buffer(0)
ku = ku[['中学校', 'geometry']]
ku['面積_ha'] = (ku.area / 10000).round(1)

out.to_file(OUT, layer='街区_中学校', driver='GPKG')
ku.to_file(OUT, layer='中学校区_街区から作成', driver='GPKG')
pt.drop(columns='tc').to_file(OUT, layer='街区代表点_中学校', driver='GPKG')

# 表（町丁目・番 -> 中学校）
tab = pt.drop(columns=['geometry', 'tc']).sort_values(['区', '町丁目', '番'], key=lambda s: s.map(lambda v: (len(v), v)) if s.name == '番' else s)
tab.to_csv(CSV, index=False, encoding='utf-8-sig')

# PDFにあるがデータにない町丁目
pdf_tc = set(by_tc); pt_tc = set(bans)
miss = sorted(pdf_tc - pt_tc)
print('点', len(pt), pt['判定'].value_counts().to_dict())
print('面', len(out), out['判定'].value_counts().to_dict())
print('中学校区', len(ku))
print('PDFにあって位置参照にない町丁目', len(miss), miss[:40])
