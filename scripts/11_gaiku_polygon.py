import sys, glob, re, unicodedata, time
import pandas as pd, geopandas as gpd, pyogrio
from shapely.ops import polygonize, unary_union
from shapely.geometry import box
ROOT = sys.argv[1]; RD = sys.argv[2]; KIBAN = sys.argv[3]; OUT = sys.argv[4]
WARDS = sys.argv[5].split(',') if len(sys.argv) > 5 else None
KAN = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
def k2n(s):
    if '十' in s:
        a, b = s.split('十'); return (KAN.get(a,1) if a else 1)*10 + (KAN.get(b,0) if b else 0)
    return KAN[s]
def chome(s):
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'([一二三四五六七八九十]+)丁目', lambda m: f'{k2n(m[1])}丁目', s)
dfs = []
for f in sorted(glob.glob(f'{ROOT}/**/*_20*.csv', recursive=True)):
    d = pd.read_csv(f, encoding='cp932', dtype=str); dfs.append(d)
pt = pd.concat(dfs)
pt = pt[(pt['代表フラグ'] == '1') & (pt['更新後履歴フラグ'] == '0')]
pt['区'] = pt['市区町村名'].str.replace('大阪市', '')
pt['町丁目'] = pt['大字・丁目名'].map(chome)
pt['番'] = pt['街区符号・地番']
pt = gpd.GeoDataFrame(pt[['区','町丁目','番','住居表示フラグ']], geometry=gpd.points_from_xy(pt['経度'].astype(float), pt['緯度'].astype(float)), crs=6668).to_crs(6674)
print('points', len(pt), flush=True)
wards = WARDS or sorted(pt['区'].unique())
allp, miss = [], []
for w in wards:
    t0 = time.time()
    p = pt[pt['区'] == w]
    bb = box(*p.total_bounds).buffer(400)
    bb_ll = gpd.GeoSeries([bb], crs=6674).to_crs(6668).total_bounds
    rd = pyogrio.read_dataframe(RD, bbox=tuple(bb_ll)).to_crs(6674)
    wl = pyogrio.read_dataframe(KIBAN, layer='水涯線', bbox=tuple(bb_ll)).to_crs(6674)
    def mkfaces(lines):
        f = gpd.GeoDataFrame(geometry=list(polygonize(unary_union(lines))), crs=6674)
        return f[(f.area > 30) & (f.area < 300000)]
    # 1回目: 一般道路の道路縁だけで面を作る
    f1 = mkfaces(list(rd[rd['type'] == '真幅道路'].geometry) + list(wl.geometry))
    j1 = gpd.sjoin(p, f1, how='left', predicate='within')
    rest = p[j1['index_right'].isna().groupby(level=0).any()]
    # 2回目: 面に入らなかった点は、庭園路等も含めた道路縁で作った面を使う
    f2 = mkfaces(list(rd.geometry) + list(wl.geometry))
    f2 = f2[~f2.intersects(unary_union(f1.loc[j1['index_right'].dropna().astype(int).unique()].geometry))]
    j2 = gpd.sjoin(rest, f2, how='left', predicate='within')
    f2.index = f2.index + 10**7; j2['index_right'] = j2['index_right'] + 10**7
    faces = pd.concat([f1, f2])
    j = pd.concat([j1.dropna(subset=['index_right']), j2])
    miss.append(j[j['index_right'].isna()].drop(columns='index_right'))
    j = j.dropna(subset=['index_right'])
    g = j.groupby('index_right').agg(町丁目=('町丁目', lambda s: '・'.join(dict.fromkeys(s))),
                                     番=('番', lambda s: ','.join(dict.fromkeys(s))), 点数=('番', 'size'))
    poly = faces.loc[g.index.astype(int)].copy()
    poly[['町丁目','番','点数']] = g.values
    poly['区'] = w
    poly['判定'] = ['OK' if n == 1 else '複数の番が1つの面' for n in poly['点数']]
    allp.append(poly)
    print(w, 'points', len(p), 'faces', len(faces), 'assigned', len(poly), 'multi', (poly['点数'] > 1).sum(), 'miss', len(miss[-1]), f'{time.time()-t0:.0f}s', flush=True)
res = gpd.GeoDataFrame(pd.concat(allp), crs=6674)[['区','町丁目','番','点数','判定','geometry']]
res['面積_m2'] = res.area.round(1)
res.to_file(OUT, layer='街区_ポリゴン', driver='GPKG')
pt[pt['区'].isin(wards)].to_file(OUT, layer='街区_代表点', driver='GPKG')
m = gpd.GeoDataFrame(pd.concat(miss), crs=6674)
if len(m): m.to_file(OUT, layer='面に入らなかった代表点', driver='GPKG')
print('done', len(res), flush=True)
