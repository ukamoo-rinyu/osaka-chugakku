F = "font-family=\"'Meiryo','Yu Gothic','Noto Sans JP','Noto Sans CJK JP',sans-serif\""
o = []
a = o.append
W, H = 590, 322
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
a('''<defs>
 <pattern id="dotB" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/><circle cx="2" cy="2" r="0.9" fill="#222"/></pattern>
 <pattern id="dotW" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#b8262b"/><circle cx="2" cy="2" r="0.9" fill="#fff"/></pattern>
</defs>''')
a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="#fff" stroke="#333" stroke-width="1.5"/>')
def t(x, y, s, size=12, anchor="start", weight="normal", fill="#222"):
    a(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" {F}>{s}</text>')
def box_label(x, y, w, s):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="20" fill="#fff" stroke="#333" stroke-width="1.2"/>')
    t(x + w/2, y + 15, s, 12, "middle", "bold")

t(12, 20, "凡例", 13, weight="bold")
# ---- 一般施設 ----
box_label(14, 28, 72, "一般施設")
x = [14, 36, 92, 154, 216, 290]       # 列境界
y = [58, 80, 102, 154, 206, 258, 310]  # 行境界
G = "#c8c8c8"
a(f'<rect x="{x[0]}" y="{y[0]}" width="{x[5]-x[0]}" height="{y[2]-y[0]}" fill="{G}"/>')
a(f'<rect x="{x[0]}" y="{y[2]}" width="{x[2]-x[0]}" height="{y[6]-y[2]}" fill="{G}"/>')
a(f'<rect x="{x[2]}" y="{y[2]}" width="{x[5]-x[2]}" height="{y[6]-y[2]}" fill="#fff"/>')
L = 'stroke="#555" stroke-width="1"'
for yy in y[2:]: a(f'<line x1="{x[1]}" y1="{yy}" x2="{x[5]}" y2="{yy}" {L}/>')
a(f'<line x1="{x[2]}" y1="{y[1]}" x2="{x[5]}" y2="{y[1]}" {L}/>')
a(f'<line x1="{x[0]}" y1="{y[0]}" x2="{x[5]}" y2="{y[0]}" {L}/>')
a(f'<line x1="{x[0]}" y1="{y[6]}" x2="{x[5]}" y2="{y[6]}" {L}/>')
for i in (0, 5): a(f'<line x1="{x[i]}" y1="{y[0]}" x2="{x[i]}" y2="{y[6]}" {L}/>')
a(f'<line x1="{x[1]}" y1="{y[2]}" x2="{x[1]}" y2="{y[6]}" {L}/>')
for i in (2, 3, 4): a(f'<line x1="{x[i]}" y1="{y[0] if i == 2 else y[1]}" x2="{x[i]}" y2="{y[6]}" {L}/>')
t((x[2]+x[5])/2, y[0]+16, "延床面積（㎡）", 12, "middle")
for i, s in enumerate(["～499", "500～1,999", "2,000～"]):
    t((x[2+i]+x[3+i])/2, y[1]+16, s, 11, "middle")
for i, s in enumerate(["～19", "20～39", "40～49", "50～"]):
    t((x[1]+x[2])/2, (y[2+i]+y[3+i])/2+5, s, 12, "middle")
# 縦書きラベル
cx = (x[0]+x[1])/2; yy = y[2] + 18
for ch in "築年数":
    t(cx, yy, ch, 13, "middle"); yy += 16
yy += 2
for ch in "（令和5年度を基準）":
    if ch in "（）":
        a(f'<text x="{cx}" y="{yy-3}" font-size="9" text-anchor="middle" fill="#222" transform="rotate(90 {cx} {yy-6})" {F}>{ch}</text>')
    else:
        t(cx, yy, ch, 9, "middle")
    yy += 11
# 記号
fills = ["#fff", "url(#dotB)", "url(#dotW)", "#d83a35"]
radii = [7, 10, 15]
for r_, f in enumerate(fills):
    for c_, rad in enumerate(radii):
        a(f'<circle cx="{(x[2+c_]+x[3+c_])/2}" cy="{(y[2+r_]+y[3+r_])/2}" r="{rad}" fill="{f}" stroke="#111" stroke-width="2.4"/>')

# ---- 学校施設・賃借施設 ----
box_label(304, 28, 76, "学校施設")
t(318, 74, "文", 17, "middle", "bold")
t(334, 73, "小中学校", 13)
a('<circle cx="318" cy="112" r="11" fill="#fff" stroke="#111" stroke-width="2.4"/>')
t(318, 118, "文", 13, "middle", "bold")
t(334, 117, "高等学校", 13)
box_label(304, 152, 76, "賃借施設")
a('<rect x="333" y="182" width="14" height="14" fill="#fff" stroke="#111" stroke-width="1.8"/>')

# ---- 参考 ----
a(f'<line x1="395" y1="8" x2="395" y2="{H-8}" stroke="#333" stroke-width="1.2"/>')
t(404, 22, "（参考）", 12, weight="bold")
rows = [44, 84, 124, 160, 198, 238]
X1, X2, TX = 406, 448, 454
# JR線
a(f'<line x1="{X1}" y1="{rows[0]}" x2="{X2}" y2="{rows[0]}" stroke="#222" stroke-width="7"/>')
a(f'<line x1="{X1+2}" y1="{rows[0]}" x2="{X2-2}" y2="{rows[0]}" stroke="#fff" stroke-width="3" stroke-dasharray="8 5"/>')
t(TX, rows[0]+5, "：JR線", 13)
# 大阪メトロ
a(f'<line x1="{X1}" y1="{rows[1]}" x2="{X2}" y2="{rows[1]}" stroke="#6a72c8" stroke-width="2" stroke-dasharray="6 4"/>')
t(TX, rows[1]+5, "：大阪メトロ", 13)
t(TX+8, rows[1]+21, "(Osaka Metro)", 12)
# 私鉄
a(f'<line x1="{X1}" y1="{rows[2]+6}" x2="{X2}" y2="{rows[2]+6}" stroke="#7a80b8" stroke-width="1.6"/>')
t(TX, rows[2]+11, "：私鉄", 13)
# 国道
yy = rows[3]+6
a(f'<line x1="{X1}" y1="{yy}" x2="{X2}" y2="{yy}" stroke="#777" stroke-width="5"/>')
a(f'<path d="M{(X1+X2)/2-8},{yy-7} h16 v5 l-8,9 l-8,-9 z" fill="#222" stroke="#fff" stroke-width="0.8"/>')
t(TX, yy+5, "：国道", 13)
# 高速道路
a(f'<line x1="{X1}" y1="{rows[4]}" x2="{X2}" y2="{rows[4]}" stroke="#e8613a" stroke-width="5"/>')
t(TX, rows[4]+5, "：高速道路", 13)
# 中学校区
a(f'<rect x="{X1+3}" y="{rows[5]-8}" width="{X2-X1-6}" height="16" fill="#fff" stroke="#5a3a22" stroke-width="5"/>')
t(TX, rows[5]+5, "：中学校区", 13)
a('</svg>')
open('legend.svg', 'w', encoding='utf-8').write('\n'.join(o))
