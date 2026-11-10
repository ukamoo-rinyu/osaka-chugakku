"""通学区域一覧（raw.json）を 町丁目・番 単位の指定に分解する"""
import json, re, sys, unicodedata
from collections import defaultdict

def nk(s): return unicodedata.normalize('NFKC', s).replace('[', '〔').replace(']', '〕')
def town_norm(s):
    s = nk(s).replace(' ', '').replace('ヶ', 'ケ').replace('ヵ', 'ケ').replace('曽', '曾')
    return s

def expand_chome(spec):
    out = []
    for part in re.split(r'[、・,]', spec.replace('丁目', '')):
        m = re.fullmatch(r'(\d+)~(\d+)', part)
        if m: out += list(range(int(m[1]), int(m[2]) + 1))
        elif part.isdigit(): out.append(int(part))
    return out

ITEM = re.compile(r'((?:東|西|南|北|中|浜)?[0-9A-Z]+)番(?:~((?:東|西|南|北|中|浜)?\d+)番)?(\([^)]*\)|の一部|\d+号(?:~\d+号)?)?')
def parse_items(text):
    """'1番~25番、26番(2号~5号)、7番の一部' -> {番: 'full'|'partial'}"""
    text = re.sub(r'((?:東|西|南|北|中|浜)?\d+)~(\d+)番', r'\1番~\2番', text)
    text = re.sub(r'([A-Z])番・([A-Z])番・([A-Z])番', r'\1番、\2番、\3番', text)
    res = {}
    for m in ITEM.finditer(text):
        suf = m[3] or ''
        partial = bool(suf) and bool(re.search(r'号|一部|除', suf))
        if m[2]:
            pre = re.match(r'\D*', m[1])[0]
            a_, b_ = int(m[1][len(pre):]), int(re.sub(r'\D', '', m[2]))
            nums = [f'{pre}{i}' for i in range(a_, b_ + 1)]
        else:
            nums = [m[1]]
        for n in nums:
            k = 'partial' if partial else 'full'
            if res.get(n) == 'full' and k == 'partial': k = 'full'
            res[n] = k
    return res

EXCL = re.compile(r'[〔(][^〔〕]*?除く[)〕]*|〔[^〕]*除く[^〕]*〕')
def split_excl(rest):
    """rest から除外指定を取り出す -> (残り, [除外テキスト])"""
    ex = []
    for m in list(re.finditer(r'〔[^〕]*〕', rest)) + list(re.finditer(r'\((?:[^()]|\([^()]*\))*\)', rest)):
        if '除' in m[0] and '市営住宅' not in m[0] and '番' in m[0]:
            ex.append(m[0])
    for e in ex: rest = rest.replace(e, '')
    return rest, ex

def logical_lines(text):
    """括弧が閉じるまで行をつなげる。除外の注記行は前の行につなげる"""
    out = []
    for raw in text.split('\n'):
        l = nk(raw).replace(' ', '').strip()
        if not l: continue
        if out:
            prev = out[-1]
            opened = prev.count('(') + prev.count('〔') - prev.count(')') - prev.count('〕')
            if (opened > 0 and re.match(r'^(?!\d+丁目)[\d、を東西南北中浜]', l)) or l[0] in 'を、' or (l.lstrip('※')[0] in '(〔' and '除' in l):
                out[-1] = prev + l; continue
        out.append(l)
    return out

def parse(rows):
    for r in rows:
        for k in ('ku', 'chu', 'sho'): r[k] = nk(r[k])
        if r['sho'] == '浪なみは速や': r['sho'] = '浪速'
    claims = []   # dict(ku_loc, town_chome, ban('*'=全域), kind, excl_full, excl_part, chu, sho, src)
    prev = None
    for r in rows:
        key = (r['ku'], r['chu'], r['sho'])
        if key != prev: town = None; chomes = None; loc = r['ku'] + '区'
        prev = key
        lines = logical_lines(r['text'])
        if lines and re.search(r'区.*へ$', lines[-1]): continue
        for line in lines:
            line = line.replace('※', '')
            if not line: continue
            if re.fullmatch(r'.{1,3}区', line): loc = line; continue
            if re.search(r'学校区は|児童遊園', line) or line[0] in '([〔': continue
            line = re.sub(r'^(上町)([A-Z])', r'\1 \2', line)
            m = re.match(r'^(?P<town>[^0-9(〔 ]*) ?(?P<chome>(?:\d+丁目|\d+~)(?:[~、・]?\d+丁目)*)?(?P<rest>.*)$', line)
            t, c, rest = m['town'], m['chome'], m['rest']
            if t and not c and len(t) == 1 and re.match(r'\d+番', rest):
                rest = t + rest; t = ''
            if t:
                town = town_norm(t); chomes = expand_chome(c) if c else [None]
            elif c:
                chomes = expand_chome(c)
            if town is None: continue
            rest, excls = split_excl(rest)
            inc = parse_items(rest)
            if not chomes: continue
            last = chomes[-1]
            for ch in chomes:
                use_inc = inc if (ch == last or not c) else {}
                tc = town + (f'{ch}丁目' if ch else '')
                ef, ep = set(), set()
                for e in excls:
                    cm = re.search(r'(\d+)丁目', e)
                    if cm and ch is not None and int(cm[1]) != ch: continue
                    for b, kind in parse_items(e).items():
                        (ep if kind == 'partial' else ef).add(b)
                base = dict(loc=loc, tc=tc, chu=r['chu'] + '中学校', sho=r['sho'] + '小学校', src=line, page=r['page'])
                if use_inc:
                    for b, kind in use_inc.items():
                        claims.append(dict(base, ban=b, kind=kind))
                elif re.search(r'一部', rest) and (ch == last or not c):
                    claims.append(dict(base, ban='*', kind='partial', ef=ef, ep=ep))
                else:
                    claims.append(dict(base, ban='*', kind='full', ef=ef, ep=ep))
    return claims

if __name__ == '__main__':
    rows = json.load(open(sys.argv[1]))
    cl = parse(rows)
    print(len(cl))
    from collections import Counter
    print(Counter((c['ban'] == '*', c['kind']) for c in cl))
