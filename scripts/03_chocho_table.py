import csv, sys
from collections import OrderedDict
r = list(csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')))
d = OrderedDict()
for x in r:
    k = (x['町の所在区'], x['町丁目名'])
    a = d.setdefault(k, dict(chu=OrderedDict(), sho=OrderedDict(), partial=False, det=[], pages=set()))
    a['chu'][x['中学校']] = 1; a['sho'][x['小学校']] = 1
    a['partial'] |= x['範囲'] == '一部'
    if x['番地指定']: a['det'].append(x['中学校'] + '：' + x['番地指定'])
    a['pages'] |= set(x['PDFページ'].split(','))
out = []
for (ku, nm), a in d.items():
    chus = list(a['chu'])
    if len(chus) == 1:   st, chu = '単独', chus[0]
    elif a['partial']:   st, chu = '要分割', ''
    else:                st, chu = '重複（どちらも可）', chus[0]
    out.append(OrderedDict(所在区=ku, 町丁目名=nm, 中学校=chu, 判定=st,
        候補中学校='・'.join(chus), 小学校='・'.join(a['sho']),
        番地指定='／'.join(a['det']), PDFページ=','.join(sorted(a['pages'], key=int))))
with open(sys.argv[2], 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(len(out), Counter(o['判定'] for o in out))
