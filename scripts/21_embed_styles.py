import sqlite3, sys
from xml.sax.saxutils import quoteattr
OUT = sys.argv[1]
KU = 'coalesce(@atlas_pagename, @target_ku, "区")'   # 変数がなければ全区を対象として表示

def rgb(h, a=255):
    h = h.lstrip('#'); return f'{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a}'
def opt(d):
    return '<Option type="Map">' + ''.join(f'<Option name="{k}" type="QString" value={quoteattr(str(v))}/>' for k, v in d.items()) + '</Option>'
def fill_sym(name, color=None, outline=None, width=0.0):
    d = {'color': rgb(color) if color else '0,0,0,0', 'style': 'solid' if color else 'no',
         'outline_color': rgb(outline) if outline else '0,0,0,0', 'outline_style': 'solid' if outline else 'no',
         'outline_width': width, 'outline_width_unit': 'MM', 'joinstyle': 'round'}
    return f'<symbol type="fill" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0"><layer class="SimpleFill" enabled="1" locked="0" pass="0">{opt(d)}</layer></symbol>'
def line_sym(name, color, width, cap='round'):
    d = {'line_color': rgb(color), 'line_width': width, 'line_width_unit': 'MM', 'line_style': 'solid',
         'capstyle': cap, 'joinstyle': 'round'}
    return f'<symbol type="line" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0"><layer class="SimpleLine" enabled="1" locked="0" pass="0">{opt(d)}</layer></symbol>'
def single(sym):
    return f'<renderer-v2 type="singleSymbol" symbollevels="0" enableorderby="0" forceraster="0"><symbols>{sym}</symbols></renderer-v2>'
def rules(items):
    r = ''.join(f'<rule key="r{i}" symbol="{i}" filter={quoteattr(f)} label={quoteattr(l)}/>' for i, (l, f, _) in enumerate(items))
    s = ''.join(sym for _, _, sym in items)
    return f'<renderer-v2 type="RuleRenderer" symbollevels="0" enableorderby="0" forceraster="0"><rules key="root">{r}</rules><symbols>{s}</symbols></renderer-v2>'
def label(expr, size, color, filt, bold=True):
    st = (f'<settings calloutType="simple"><text-style fontFamily="Meiryo" namedStyle="{"Bold" if bold else "Regular"}" fontWeight="{75 if bold else 50}" '
          f'fontSize="{size}" fontSizeUnit="Point" textColor="{rgb(color)}" isExpression="1" fieldName={quoteattr(expr)} textOpacity="1" multilineHeight="1">'
          f'<text-buffer bufferDraw="1" bufferSize="1" bufferSizeUnits="MM" bufferColor="255,255,255,255" bufferOpacity="0.9" bufferJoinStyle="128"/></text-style>'
          f'<text-format wrapChar="" multilineAlign="1"/><placement placement="1" centroidInside="1" centroidWhole="0" fitInPolygonOnly="0"/>'
          f'<rendering obstacle="1" drawLabels="1" fontLimitPixelSize="0" limitNumLabels="0" mergeLines="0" upsidedownLabels="0" displayAll="0"/></settings>')
    return f'<labeling type="rule-based"><rules key="root"><rule key="l0" filter={quoteattr(filt)}>{st}</rule></rules></labeling>'
def qml(body, labels='', scale=None):
    sc = f'hasScaleBasedVisibilityFlag="1" minScale="{scale}" maxScale="0"' if scale else 'hasScaleBasedVisibilityFlag="0"'
    return (f"<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'><qgis version=\"3.34.0\" styleCategories=\"Symbology|Labeling|Rendering\" "
            f"labelsEnabled=\"{1 if labels else 0}\" {sc}>{body}{labels}<blendMode>0</blendMode><layerOpacity>1</layerOpacity></qgis>")

T = f'"区" = {KU}'
S = {
 '01_中学校区': qml(rules([('中学校区（対象区）', T, fill_sym('0', None, '#5a3a22', 1.4))]),
                   label("replace(\"中学校\", '中学校', '')", 11, '#5a3a22', T)),
 '02_区境界': qml(single(fill_sym('0', None, '#8c8c8c', 0.4)),
                  label('"区"', 13, '#8a8a8a', f'"区" <> {KU}')),
 '03_道路縁': qml(single(line_sym('0', '#c4bda8', 0.12, 'flat')), scale=30000),
 '04_街区': qml(single(fill_sym('0', None, '#cfc8b2', 0.12))),
 '05_水域': qml(single(fill_sym('0', '#a9cde3', '#7fb0cf', 0.15))),
 '06_地の色': qml(rules([('対象区', T, fill_sym('0', '#ffffff')), ('その他の区', 'ELSE', fill_sym('1', '#f3efdc'))])),
}
con = sqlite3.connect(OUT)
con.execute('''CREATE TABLE IF NOT EXISTS layer_styles (id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT(256),
 f_table_schema TEXT(256), f_table_name TEXT(256), f_geometry_column TEXT(256), styleName TEXT(30), styleQML TEXT,
 styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT(30), ui TEXT(30), update_time DATETIME DEFAULT CURRENT_TIMESTAMP)''')
geomcol = dict(con.execute('select table_name, column_name from gpkg_geometry_columns'))
con.execute('delete from layer_styles')
for t, q in S.items():
    con.execute('insert into layer_styles (f_table_catalog,f_table_schema,f_table_name,f_geometry_column,styleName,styleQML,styleSLD,useAsDefault,description,owner) values (?,?,?,?,?,?,?,?,?,?)',
                ('', '', t, geomcol[t], t, q, '', 1, '区別地図の背景用', ''))
# QGIS がスタイル表を認識できるよう gpkg_contents に登録
con.execute("insert or ignore into gpkg_contents (table_name, data_type, identifier) values ('layer_styles','attributes','layer_styles')")
con.commit()
print(con.execute('select f_table_name, useAsDefault, length(styleQML) from layer_styles').fetchall())
import xml.dom.minidom
for t, q in S.items(): xml.dom.minidom.parseString(q.split("'SYSTEM'>", 1)[1])
print('QML ok')
