import sys, sqlite3, os
import geopandas as gpd, pyogrio
from shapely.geometry import box
# 使い方: python 20_haikei_layers.py 出力.gpkg 校区.gpkg 街区.gpkg 基盤地図(水域).gpkg 道路縁.gpkg
OUT, SEAM, GAIKU, KIBAN, ROAD = sys.argv[1:6]
if os.path.exists(OUT): os.remove(OUT)

wards = gpd.read_file(SEAM, layer='区境界').to_crs(6674)
area = box(*wards.total_bounds).buffer(1500)
ll = tuple(gpd.GeoSeries([area], crs=6674).to_crs(6668).total_bounds)

def save(g, name):
    g = g.to_crs(6674); g.to_file(OUT, layer=name, driver='GPKG'); print(name, len(g), flush=True)

save(gpd.read_file(SEAM, layer='中学校区_区別'), '01_中学校区')
save(wards[['区', 'コード', 'geometry']], '02_区境界')
rd = pyogrio.read_dataframe(ROAD, bbox=ll, where="type='真幅道路'", columns=['type'])
save(rd, '03_道路縁')
save(gpd.read_file(GAIKU, layer='街区_ポリゴン')[['区', '町丁目', '番', 'geometry']], '04_街区')
wa = gpd.read_file(KIBAN, layer='水域', bbox=ll)[['type', 'geometry']]
save(wa, '05_水域')
save(wards[['区', 'geometry']], '06_地の色')
print('data done', flush=True)
