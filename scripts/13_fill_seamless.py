"""街区ごとの中学校を、区境界の中ですき間なく広げて校区ポリゴンにする（ボロノイ分割）"""
import sys, numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely.geometry import MultiPoint

BLK, WARDS, OUT = sys.argv[1:4]
blk = gpd.read_file(BLK, layer='街区_中学校')
blk = blk[blk['中学校'].notna()].to_crs(6674)
wards = gpd.read_file(WARDS).to_crs(6674)
if len(sys.argv) > 4: wards = wards[wards['区'].isin(sys.argv[4].split(','))]
STEP = 15
GS = 0.01  # 座標を1cm単位に丸めて計算を安定させる  # 境界上に点を置く間隔(m)

def seeds(gdf):
    pts, lab = [], []
    for geom, chu in zip(gdf.geometry, gdf['中学校']):
        g = geom.simplify(1)
        for ring in ([g.exterior] if g.geom_type == 'Polygon' else [p.exterior for p in g.geoms]):
            n = max(4, int(ring.length / STEP))
            ps = shapely.line_interpolate_point(ring, np.linspace(0, ring.length, n, endpoint=False))
            pts.extend(ps); lab.extend([chu] * n)
    return pts, lab

out = []
for w in wards.itertuples():
    W = w.geometry
    sub = blk[blk['区'].str.contains(w.区, regex=False)]
    pts, lab = seeds(sub)
    xy = np.round(shapely.get_coordinates(np.array(pts)), 2)
    _, keep = np.unique(xy, axis=0, return_index=True); keep.sort()
    pts = list(shapely.points(xy[keep])); lab = [lab[i] for i in keep]
    mp = MultiPoint(pts)
    cells = shapely.voronoi_polygons(mp, extend_to=W.buffer(2000), ordered=True)
    cells = np.array(cells.geoms); lab = np.array(lab)
    # ボロノイの面はすき間も重なりもないので、高速な coverage_union でまとめる
    def uni(g):
        try: return shapely.coverage_union_all(g)
        except Exception:
            try: return shapely.union_all(g, grid_size=0.01)
            except Exception: return shapely.union_all(shapely.buffer(g, 0.01))
    rows = [{'中学校': c, 'geometry': uni(cells[lab == c])} for c in np.unique(lab)]
    d = gpd.GeoDataFrame(rows, crs=6674)
    d['geometry'] = shapely.intersection(d.geometry.values, W)
    d = d[~d.is_empty]
    # 小さな飛び地（2,000㎡未満）は、接している相手の校区に吸収
    e = d.explode(index_parts=False).reset_index(drop=True)
    small = e[e.area < 2000]; big = e[e.area >= 2000].copy()
    for s in small.itertuples():
        nb = big[big.touches(s.geometry) | big.intersects(s.geometry.buffer(0.5))]
        if len(nb):
            k = nb.geometry.apply(lambda g: g.intersection(s.geometry.buffer(0.5)).length).idxmax()
            big.at[k, 'geometry'] = shapely.union(big.at[k, 'geometry'], s.geometry).buffer(0)
        else:
            big = pd.concat([big, gpd.GeoDataFrame([{'中学校': s.中学校, 'geometry': s.geometry}], crs=6674)])
    d = big.dissolve(by='中学校', as_index=False)
    d['区'] = w.区
    out.append(d)
    print(w.区, len(d), '校区', flush=True)

res = gpd.GeoDataFrame(pd.concat(out), crs=6674)
res['geometry'] = res.buffer(0)
res['面積_ha'] = (res.area / 10000).round(1)
res = res[['区', '中学校', '面積_ha', 'geometry']].sort_values(['区', '中学校'])
res.to_file(OUT, layer='中学校区_区別', driver='GPKG')
whole = res.dissolve(by='中学校', as_index=False)[['中学校', 'geometry']]
whole['面積_ha'] = (whole.area / 10000).round(1)
whole.to_file(OUT, layer='中学校区_全体', driver='GPKG')
wards[['区', 'コード', 'geometry']].to_file(OUT, layer='区境界', driver='GPKG')
print('区別', len(res), '全体', len(whole))
