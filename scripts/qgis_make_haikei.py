# -*- coding: utf-8 -*-
"""
大阪市 区別地図の背景をつくる（QGIS Pythonコンソール用）

使い方
  QGIS を新しいプロジェクトで開く →［プラグイン］→［Pythonコンソール］→ エディタを表示
  → このファイルを開いて ▶ 実行
  対象の区はプロジェクト変数 target_ku で切り替え（［プロジェクト］→［プロパティ］→［変数］）
  アトラスで出力するときは自動で @atlas_pagename が使われる
"""
import os
from qgis.core import (QgsProject, QgsVectorLayer, QgsFillSymbol, QgsLineSymbol,
                       QgsSingleSymbolRenderer, QgsRuleBasedRenderer, QgsPalLayerSettings,
                       QgsTextFormat, QgsTextBufferSettings, QgsRuleBasedLabeling,
                       QgsExpressionContextUtils, QgsCoordinateReferenceSystem)
from qgis.PyQt.QtGui import QColor, QFont

# ===== ファイルの場所（必要なら書き換え） =====
DL = r"C:\Users\YOURNAME\Downloads"   # 自分の環境に合わせて変更
ROAD   = DL + r"\FGD_RdEdg\osaka_rdedg.gpkg|layername=road_edge"
KIBAN  = DL + r"\20261110220207140-001\kiban_osaka.gpkg"
GAIKU  = DL + r"\街区レベル\gaiku_osaka.gpkg|layername=街区_ポリゴン"
SEAM   = DL + r"\街区レベル\chugakku_seamless.gpkg"
# あれば使う（国土数値情報など。無ければ空のままでOK）
RAIL    = ""   # 鉄道 N02 の RailroadSection（例: r"C:\...\N02-23_RailroadSection.shp"）
HIGHWAY = ""   # 高速道路 N06 など
PARK    = ""   # 公園ポリゴン（PLATEAU の土地利用、OSM など）
SAVE_AS = DL + r"\街区レベル\haikei_osaka.qgz"
TARGET  = "北区"
# ============================================

P = QgsProject.instance()
P.setCrs(QgsCoordinateReferenceSystem("EPSG:6674"))  # 平面直角座標系 第VI系
QgsExpressionContextUtils.setProjectVariable(P, "target_ku", TARGET)
KU = "coalesce(@atlas_pagename, @target_ku)"
root = P.layerTreeRoot()
grp = root.insertGroup(0, "背景地図")

def add(uri, name, provider="ogr"):
    lyr = QgsVectorLayer(uri, name, provider)
    if not lyr.isValid():
        print("読み込めませんでした:", name, uri); return None
    P.addMapLayer(lyr, False); grp.addLayer(lyr)   # 追加順に下へ積む
    return lyr

def fill(color, outline="transparent", width="0"):
    return QgsFillSymbol.createSimple({"color": color, "outline_color": outline,
                                       "outline_width": width, "outline_width_unit": "MM",
                                       "outline_style": "no" if outline == "transparent" else "solid"})

def line(color, width, style="solid", cap="round"):
    return QgsLineSymbol.createSimple({"line_color": color, "line_width": str(width),
                                       "line_width_unit": "MM", "line_style": style, "capstyle": cap})

def rules(lyr, items):
    """items: [(ラベル, 式, シンボル)]"""
    r = QgsRuleBasedRenderer.Rule(None)
    for label, expr, sym in items:
        r.appendChild(QgsRuleBasedRenderer.Rule(sym, 0, 0, expr, label))
    lyr.setRenderer(QgsRuleBasedRenderer(r))

def labels(lyr, field_expr, size, color, expr=None, bold=False):
    s = QgsPalLayerSettings()
    s.fieldName = field_expr; s.isExpression = True
    f = QgsTextFormat(); fn = QFont("Meiryo"); fn.setBold(bold); f.setFont(fn)
    f.setSize(size); f.setColor(QColor(color))
    b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(1); b.setColor(QColor("white")); f.setBuffer(b)
    s.setFormat(f)
    root_rule = QgsRuleBasedLabeling.Rule(None)
    root_rule.appendChild(QgsRuleBasedLabeling.Rule(s, 0, 0, expr or "TRUE"))
    lyr.setLabeling(QgsRuleBasedLabeling(root_rule)); lyr.setLabelsEnabled(True)

# ---- 上から順に追加（あとで追加したものほど下） ----
# 1 中学校区の線（対象区だけ）
ku_line = add(SEAM + "|layername=中学校区_区別", "中学校区")
if ku_line:
    sym = fill("transparent", "#5a3a22", "1.4")
    rules(ku_line, [("中学校区", f'"区" = {KU}', sym)])
    labels(ku_line, "replace(\"中学校\", '中学校', '')", 11, "#5a3a22", f'"区" = {KU}', True)

# 2 鉄道・高速道路（あれば）
if RAIL:
    rl = add(RAIL, "鉄道")
    if rl:
        jr = line("#222222", 1.2); jr.appendSymbolLayer(line("#ffffff", 0.5, "dash").symbolLayer(0).clone())
        rules(rl, [("JR線", '"N02_002" IN (\'1\',\'2\')', jr),
                   ("大阪メトロ", '"N02_002" = \'3\'', line("#6a72c8", 0.5, "dash")),
                   ("私鉄", '"N02_002" IN (\'4\',\'5\')', line("#7a80b8", 0.4))])
if HIGHWAY:
    hw = add(HIGHWAY, "高速道路")
    if hw: hw.setRenderer(QgsSingleSymbolRenderer(line("#e8613a", 1.0)))

# 3 区境界の線と区名（対象区以外は灰色の文字）
wb = add(SEAM + "|layername=区境界", "区境界")
if wb:
    wb.setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#8c8c8c", "0.4")))
    labels(wb, '"区"', 13, "#8a8a8a", f'"区" <> {KU}', True)

# 4 道路縁（重いので 1/30,000 より詳しい縮尺でだけ表示）
rd = add(ROAD, "道路縁")
if rd:
    rules(rd, [("道路縁", "\"type\" = '真幅道路'", line("#c4bda8", 0.12, cap="flat"))])
    rd.setScaleBasedVisibility(True); rd.setMinimumScale(30000)

# 5 街区（線だけ。広域表示ではこちらが道路の代わりになる）
gk = add(GAIKU, "街区")
if gk: gk.setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#cfc8b2", "0.12")))

# 6 公園（あれば）
if PARK:
    pk = add(PARK, "公園")
    if pk: pk.setRenderer(QgsSingleSymbolRenderer(fill("#a8d08d")))

# 7 水域
wa = add(KIBAN + "|layername=水域", "水域")
if wa: wa.setRenderer(QgsSingleSymbolRenderer(fill("#a9cde3", "#7fb0cf", "0.15")))

# 8 地の色：対象区は白、それ以外はベージュ
base = add(SEAM + "|layername=区境界", "地の色")
if base:
    rules(base, [("対象区", f'"区" = {KU}', fill("#ffffff")),
                 ("その他の区", "ELSE", fill("#f3efdc"))])

# 対象区に表示範囲を合わせる
if base:
    from qgis.utils import iface
    base.selectByExpression(f'"区" = \'{TARGET}\'')
    iface.mapCanvas().zoomToSelected(base); base.removeSelection()

P.write(SAVE_AS)
print("背景地図を作成しました →", SAVE_AS)
