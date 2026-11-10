import sys, os, glob, zipfile, io, re
import xml.etree.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
GML = '{http://www.opengis.net/gml/3.2}'
def coords(txt):
    v = txt.split(); return [(float(v[i+1]), float(v[i])) for i in range(0, len(v), 2)]  # lat lon -> x y
def parse(stream):
    rows = []
    for ev, el in ET.iterparse(stream, events=('end',)):
        tag = el.tag.split('}')[-1]
        if el.tag.startswith(GML) or tag in ('Dataset', 'description'): continue
        # feature = element with a fid child
        fid = el.find('{*}fid')
        if fid is None: continue
        attrs = {'種別': tag}
        geom = None
        for c in el:
            n = c.tag.split('}')[-1]
            if n in ('pos', 'loc', 'area'):
                p = c.find(f'.//{GML}pos')
                if n == 'pos' and p is not None: geom = Point(coords(p.text)[0]); continue
                if n == 'loc':
                    pts = []
                    for pl in c.iter(f'{GML}posList'): pts += coords(pl.text)
                    if len(pts) >= 2: geom = LineString(pts)
                if n == 'area':
                    ext = c.find(f'.//{GML}exterior'); rings = []
                    ints = [coords(' '.join(pl.text for pl in i.iter(f'{GML}posList'))) for i in c.iter(f'{GML}interior')]
                    ex = coords(' '.join(pl.text for pl in ext.iter(f'{GML}posList')))
                    geom = Polygon(ex, [r for r in ints if len(r) >= 4])
            elif len(c) == 0:
                attrs['fid_gsi' if n=='fid' else n] = c.text
            elif n in ('lfSpanFr', 'devDate'):
                tp = c.find(f'{GML}timePosition'); attrs[n] = tp.text if tp is not None else None
        attrs['geometry'] = geom
        rows.append(attrs); el.clear()
    return rows
NAMES = {'SBAPt':'街区_代表点','SBBdry':'街区_境界線','WA':'水域','WL':'水涯線','WStrA':'水部構造物_面',
         'WStrL':'水部構造物_線','RdEdg':'道路縁','RdCompt':'道路構成線','AdmBdry':'行政区画_境界線',
         'AdmPt':'行政区画_代表点','CommBdry':'町字_境界線','CommPt':'町字_代表点','RailCL':'軌道の中心線',
         'BldL':'建築物_外周線','BldA':'建築物'}
root, out = sys.argv[1], sys.argv[2]
seen, data = set(), {}
def handle(name, opener):
    m = re.match(r'FG-GML-(\d+)-([A-Za-z]+)-', os.path.basename(name))
    if not m: return
    key = (m[1], m[2])
    if key in seen: return
    seen.add(key)
    rows = parse(opener())
    for r in rows: r['メッシュ'] = m[1]
    data.setdefault(m[2], []).extend(rows)
    print(m[1], m[2], len(rows), flush=True)
for f in sorted(glob.glob(os.path.join(root, '**', '*.xml'), recursive=True)):
    handle(f, lambda f=f: open(f, 'rb'))
for z in sorted(glob.glob(os.path.join(root, '**', '*.zip'), recursive=True)):
    zf = zipfile.ZipFile(z)
    for n in zf.namelist():
        if n.endswith('.xml'): handle(n, lambda n=n, zf=zf: io.BytesIO(zf.read(n)))
        elif n.endswith('.zip'):
            inner = zipfile.ZipFile(io.BytesIO(zf.read(n)))
            for m_ in inner.namelist():
                if m_.endswith('.xml'): handle(m_, lambda m_=m_, inner=inner: io.BytesIO(inner.read(m_)))
if os.path.exists(out): os.remove(out)
for k, rows in data.items():
    g = gpd.GeoDataFrame(rows, geometry='geometry', crs='EPSG:6668')
    g = g[g.geometry.notna()]
    g.to_file(out, layer=NAMES.get(k, k), driver='GPKG')
    print('wrote', NAMES.get(k, k), len(g), flush=True)

# 街区ポリゴンを作る
from shapely.ops import polygonize, unary_union
if 'SBBdry' in data:
    ln = gpd.read_file(out, layer='街区_境界線').to_crs(6674)
    polys = gpd.GeoDataFrame(geometry=list(polygonize(unary_union(list(ln.geometry)))), crs=6674)
    polys = polys[polys.area > 20]
    if 'SBAPt' in data:
        pt = gpd.read_file(out, layer='街区_代表点').to_crs(6674)[['sbaNo', 'geometry']]
        polys = gpd.sjoin(polys, pt, how='left', predicate='contains').drop(columns='index_right')
        polys = polys.groupby(level=0).agg({'geometry': 'first', 'sbaNo': lambda s: ','.join(sorted(set(s.dropna()), key=lambda v: (len(v), v))) or None})
        polys = gpd.GeoDataFrame(polys, geometry='geometry', crs=6674)
    polys['面積_m2'] = polys.area.round(1)
    polys.to_crs(6668).to_file(out, layer='街区_ポリゴン', driver='GPKG')
    print('wrote 街区_ポリゴン', len(polys), 'うち番号なし', polys['sbaNo'].isna().sum() if 'sbaNo' in polys else '-')
