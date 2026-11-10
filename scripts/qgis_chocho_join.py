# -*- coding: utf-8 -*-
"""
大阪市 中学校区ポリゴン作成スクリプト（QGIS Pythonコンソール用）

使い方
  1. e-Stat の「国勢調査 小地域（町丁・字等）境界データ」大阪市分を QGIS に読み込む
  2. そのレイヤを「レイヤパネル」で選択した状態にする
  3. 下の CSV_PATH / OUT_DIR を自分のパソコンの場所に書き換える
  4. QGIS メニュー［プラグイン］→［Pythonコンソール］→ エディタを開いて
     このファイルを開き、▶（実行）を押す

できるもの（OUT_DIR に保存）
  chocho_joined.gpkg  … 町丁目ごとに中学校名を付けたレイヤ（判定=要分割 は手で分割する）
  chugakku.gpkg       … 中学校名でまとめた（ディゾルブした）中学校区ポリゴン
  unmatched.csv       … 名前が一致しなかった町丁目（表記ゆれ確認用）
"""
import csv, os, re, unicodedata
from qgis.core import (QgsProject, QgsVectorLayer, QgsField, QgsFeature,
                       QgsVectorFileWriter)
from qgis.PyQt.QtCore import QVariant
import processing

# ===== ここを書き換える =====
CSV_PATH = r"C:\work\chocho.csv"          # 町丁目→中学校 対応表
OUT_DIR  = r"C:\work\chugakku_out"        # 出力先フォルダ
CITY_FIELD = "CITY_NAME"   # 区名の列（e-Stat: 例「大阪市北区」）
TOWN_FIELD = "S_NAME"      # 町丁目名の列（e-Stat: 例「天満４丁目」）
# ============================

KANJI = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
def kanji2num(s):
    if s.isdigit(): return s
    n = 0
    if '十' in s:
        a, b = s.split('十')
        n = (KANJI.get(a, 1) if a else 1) * 10 + (KANJI.get(b, 0) if b else 0)
    else:
        n = KANJI.get(s, 0)
    return str(n)

def norm(s):
    """表記ゆれを吸収したキー（全角半角・空白・ヶ/ケ・曽/曾・漢数字丁目）"""
    if s is None: return ''
    s = unicodedata.normalize('NFKC', str(s)).replace(' ', '').replace('　', '')
    s = s.replace('ヶ', 'ケ').replace('ヵ', 'ケ').replace('曽', '曾')
    s = re.sub(r'([一二三四五六七八九十]+)丁目', lambda m: kanji2num(m.group(1)) + '丁目', s)
    return s

def ward(s):
    s = norm(s)
    return s.replace('大阪府', '').replace('大阪市', '')

# --- 対応表を読む ---
table = {}
with open(CSV_PATH, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        table[(ward(r['所在区']), norm(r['町丁目名']))] = r

src = iface.activeLayer()
if src is None:
    raise Exception('町丁目レイヤを選択してから実行してください')
os.makedirs(OUT_DIR, exist_ok=True)

# --- 町丁目レイヤに中学校名を付ける ---
crs = src.crs().authid()
lyr = QgsVectorLayer(f"MultiPolygon?crs={crs}", "町丁目_中学校", "memory")
pr = lyr.dataProvider()
pr.addAttributes(src.fields().toList() + [
    QgsField('中学校', QVariant.String), QgsField('判定', QVariant.String),
    QgsField('候補中学校', QVariant.String), QgsField('小学校', QVariant.String),
    QgsField('番地指定', QVariant.String), QgsField('PDFページ', QVariant.String)])
lyr.updateFields()

used, unmatched = set(), []
for ft in src.getFeatures():
    k = (ward(ft[CITY_FIELD]), norm(ft[TOWN_FIELD]))
    r = table.get(k)
    nf = QgsFeature(lyr.fields()); nf.setGeometry(ft.geometry())
    vals = list(ft.attributes())
    if r:
        used.add(k)
        vals += [r['中学校'] or None, r['判定'], r['候補中学校'], r['小学校'], r['番地指定'], r['PDFページ']]
    else:
        # 水面・名前なし等は「対象外」、それ以外は不一致として記録
        st = '対象外（名称なし）' if not norm(ft[TOWN_FIELD]) else '不一致（地図側のみ）'
        if st.startswith('不一致'): unmatched.append(('地図側のみ',) + k)
        vals += [None, st, None, None, None, None]
    nf.setAttributes(vals); pr.addFeature(nf)
lyr.updateExtents()

for k in table:
    if k not in used: unmatched.append(('表側のみ',) + k)

# --- 保存 ---
p1 = os.path.join(OUT_DIR, 'chocho_joined.gpkg')
opt = QgsVectorFileWriter.SaveVectorOptions(); opt.driverName = 'GPKG'
QgsVectorFileWriter.writeAsVectorFormatV3(lyr, p1, QgsProject.instance().transformContext(), opt)
QgsProject.instance().addMapLayer(QgsVectorLayer(p1, '町丁目_中学校', 'ogr'))

p2 = os.path.join(OUT_DIR, 'chugakku.gpkg')
processing.run('native:dissolve', {
    'INPUT': p1, 'FIELD': ['中学校'], 'OUTPUT': p2})
QgsProject.instance().addMapLayer(QgsVectorLayer(p2, '中学校区（仮）', 'ogr'))

with open(os.path.join(OUT_DIR, 'unmatched.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['どちらにだけあるか', '区', '町丁目名']); w.writerows(unmatched)

print(f'完了：表 {len(table)} 件中 {len(used)} 件が一致、不一致 {len(unmatched)} 件 → unmatched.csv を確認')
