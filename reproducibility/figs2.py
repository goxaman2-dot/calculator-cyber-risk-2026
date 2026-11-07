import json, math
src = open('figs.py').read()
exec(open('analysis.py').read().split('res = {}')[0])
exec(src.split('# ---------- Рис. 1')[0])
bars_src = src[src.index('def bars('):src.index('cats=[')]
exec(bars_src)
r = json.load(open('res.json'))
SUB = lambda s: f'<tspan baseline-shift="sub" font-size="10">{s}</tspan>'

# ---------- Рис. 1: относительная ошибка требуемых затрат при занижении Emax
W, H = 800, 440; l, rr_, t_, b_ = 80, 210, 30, 70; pw, ph = W - l - rr_, H - t_ - b_
X = lambda e: l + pw * e / 0.10; Y = lambda v: t_ + ph * (1 - (v - 1) / 0.6)   # отношение 1..1,6
b = ''
for v in [1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]:
    b += L(l, Y(v), l + pw, Y(v), "#e3e3e3", 1) + T(l - 8, Y(v) + 5, f"{v:g}".replace('.', ','), 14, "end")
for e in [0, 0.02, 0.04, 0.06, 0.08, 0.10]:
    b += L(X(e), t_ + ph, X(e), t_ + ph + 5) + T(X(e), t_ + ph + 22, f"{e:.2f}".replace('.', ','), 14)
b += L(l, t_ + ph, l + pw, t_ + ph) + L(l, t_, l, t_ + ph)
b += T(l + pw / 2, H - 12, 'ошибка оценки предельной эффективности мер: E' + SUB('max') + ' занижена на величину ε', 14)
b += f'<text transform="translate(22,{t_ + ph / 2}) rotate(-90)" font-size="14" text-anchor="middle">y*(ε) / y*(0)</text>'
R2 = {t['n']: t for t in rows(2)}
SEL = [("Ransomware / APT", "#2e7d4f"), ("Phishing / BEC", "#e0a030"), ("XSS / инъекции", "#1f5fa8"), ("Brute Force", "#a12b2b")]
labs = []
for name, c in SEL:
    t = R2[name]; y0 = ystar(t['A'], 1, TH0); dl = delta(t['A'], 1, TH0)
    pts = []; last = None
    for i in range(201):
        e = 0.10 * i / 200
        y = ystar(t['A'], 1, dict(TH0, emax=0.85 - e))
        if not math.isfinite(y): last = e; break
        pts.append(f"{X(e):.1f},{Y(y / y0):.1f}")
    b += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c}" stroke-width="2.4"/>'
    if last is not None:
        ex, ey = pts[-1].split(','); b += f'<circle cx="{ex}" cy="{ey}" r="4.5" fill="{c}"/>'
        labs.append((float(ey), f"{name}: δ = {dl:.2f}".replace('.', ','), c, f"превышен предел ȳ при ε ≈ {last:.3f}".replace('.', ','), float(ex)))
    else:
        yv = ystar(t['A'], 1, dict(TH0, emax=0.75)) / y0
        labs.append((Y(yv), f"{name}: δ = {dl:.2f}".replace('.', ','), c, None, X(0.10)))
bf = [x for x in labs if x[3]]; labs = [x for x in labs if not x[3]]
for yv, n, c, note, ex in bf:
    tx, ty = X(0.04), Y(1.46)
    b += L(ex + 4, yv - 3, tx - 4, ty + 8, c, 1) + T(tx, ty, n, 13, "start", fill=c) + T(tx, ty + 17, note, 12, "start", fill="#555")
labs.sort(); prev = None
for yv, n, c, note, ex in labs:
    p = max(yv, t_ + 10) if prev is None else max(yv, prev + 42); p = min(p, t_ + ph + 20); prev = p
    b += L(ex + 3, yv, X(0.10) + 16, p, c, 1) + T(X(0.10) + 20, p + 5, n, 13, "start", fill=c)
    if note: b += T(X(0.10) + 20, p + 21, note, 12, "start", fill="#555")
open('fig1.svg', 'w').write(svg(W, H, b))

# ---------- Рис. 2: классы достижимости по узлам
cats = ["2023", "2024", "2025", "окт 2026", "ноя 2026", "дек 2026"]
C = r['cls']
W, H = 800, 420; l, rr_, t_, b_ = 70, 20, 40, 95; pw, ph = W - l - rr_, H - t_ - b_
Y = lambda v: t_ + ph * (1 - v / 14); b = ''
for v in [0, 2, 4, 6, 8, 10, 12, 14]:
    b += L(l, Y(v), l + pw, Y(v), "#e3e3e3", 1) + T(l - 8, Y(v) + 5, str(v), 13, "end")
b += L(l, Y(0), l + pw, Y(0), "#333", 1.2) + L(l, t_, l, t_ + ph)
gw = pw / 6; bw = 54; cols = [("robust", "#2e7d4f"), ("conditional", "#e0a030"), ("unreachable", "#a12b2b")]
for i, c in enumerate(C):
    x = l + i * gw + (gw - bw) / 2; acc = 0
    for k, col in cols:
        v = c[k]
        if v:
            b += f'<rect x="{x:.1f}" y="{Y(acc + v):.1f}" width="{bw}" height="{Y(acc) - Y(acc + v):.1f}" fill="{col}"/>'
            b += T(x + bw / 2, (Y(acc) + Y(acc + v)) / 2 + 5, str(v), 13, fill="#fff")
        acc += v
    b += T(x + bw / 2, Y(acc) - 6, f"всего {acc}", 12)
    b += T(l + i * gw + gw / 2, t_ + ph + 20, cats[i], 14)
b += f'<text transform="translate(18,{t_ + ph / 2}) rotate(-90)" font-size="14" text-anchor="middle">угроз выше D{SUB("a")}</text>'
names = ["порог достижим при всех θ ∈ Θ", "порог достижим при части θ", "порог недостижим при всех θ"]
for i, (n, (k, col)) in enumerate(zip(names, cols)):
    xx = l + i * (pw / 3); b += f'<rect x="{xx:.1f}" y="{H - 56}" width="14" height="14" fill="{col}"/>' + T(xx + 20, H - 44, n, 13, "start")
open('fig2.svg', 'w').write(svg(W, H, b))

# ---------- Рис. 3: номинальный и устойчивый норматив
ex = r['extra']; f0 = lambda v: f"{v:.0f}"
bars("fig3.svg", ["2025", "дек 2026"],
     [[r['cls'][2]['Nnom'], r['cls'][5]['Nnom']], [ex['2025']['robust_nom'], ex['дек 2026']['robust_nom']], [ex['2025']['robust_rob'], ex['дек 2026']['robust_rob']]],
     ["#9aa5b1", "#e0a030", "#1f5fa8"],
     ["номинальный норматив, все достижимые угрозы", "номинальная стоимость устойчивого набора", "устойчивый норматив того же набора"], 0, 500, [0, 100, 200, 300, 400, 500], "тыс. руб. в год", f0, W=800, H=450, legend_rows=3)

# ---------- Рис. 4: компромисс правил (2025, параметры внутри Θ)
o = r['v3']['rules']['2025']
W, H = 800, 460; l, rr_, t_, b_ = 80, 30, 30, 70; pw, ph = W - l - rr_, H - t_ - b_
X = lambda v: l + pw * (v - 4800) / 2200; Y = lambda v: t_ + ph * (1 - (v - 3) / 6); b = ''
for v in [3, 4, 5, 6, 7, 8, 9]:
    b += L(l, Y(v), l + pw, Y(v), "#e3e3e3", 1) + T(l - 8, Y(v) + 5, str(v), 13, "end")
for v in [5000, 5500, 6000, 6500, 7000]:
    b += L(X(v), t_ + ph, X(v), t_ + ph + 5) + T(X(v), t_ + ph + 22, f"{v:,}".replace(',', ' '), 13)
b += L(l, t_ + ph, l + pw, t_ + ph) + L(l, t_, l, t_ + ph)
b += T(l + pw / 2, H - 12, 'суммарный остаточный ущерб при номинальных параметрах, тыс. руб.', 14)
b += f'<text transform="translate(22,{t_ + ph / 2}) rotate(-90)" font-size="14" text-anchor="middle">угроз выше D{SUB("a")} в среднем при ошибке параметров</text>'
NM = dict(fact="факт", prop="пропорция лимитов Г — Л", opt="минимум ущерба (точный)", pxd="PARETO-X·D (сортировка)", lex="двухступенчатое, номинальное", rlex="двухступенчатое, устойчивое")
OFF = dict(fact=(10, 34, "start"), prop=(20, 30, "start"), opt=(20, -22, "start"), pxd=(24, 30, "start"), lex=(24, 34, "start"), rlex=(-20, 30, "end"))
for k, v in o.items():
    x, y = X(v['D']), Y(v['over_in']); dx, dy, an = OFF[k]
    col = "#1f5fa8" if k == 'rlex' else "#a12b2b" if k in ('pxd', 'lex') else "#555"
    b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{col}"/>' + L(x, y, x + dx, y + dy, col, 1)
    b += T(x + dx + (4 if an == 'start' else -4), y + dy + (5 if dy > 0 else 0), f"{NM[k]}: {v['over_in']:.1f}".replace('.', ','), 13, an, fill=col)
open('fig4.svg', 'w').write(svg(W, H, b))

# ---------- Рис. 5: надёжность закрытий с 95 % интервалами
V = r['v3']['rules']
cats = [("2025", "in", "2025: внутри Θ"), ("2025", "out", "2025: строго вне Θ"), ("дек 2026", "in", "дек 2026: внутри Θ"), ("дек 2026", "out", "дек 2026: строго вне Θ")]
ser = [("pxd", "#e0a030", "PARETO-X·D (на той же сетке)"), ("lex", "#a12b2b", "двухступенчатое, номинальное"), ("rlex", "#1f5fa8", "двухступенчатое, устойчивое")]
W, H = 800, 440; l, rr_, t_, b_ = 70, 20, 40, 100; pw, ph = W - l - rr_, H - t_ - b_
Y = lambda v: t_ + ph * (1 - v); b = ''
for v in [0, .2, .4, .6, .8, 1]:
    b += L(l, Y(v), l + pw, Y(v), "#e3e3e3", 1) + T(l - 8, Y(v) + 5, f"{v:.1f}".replace('.', ','), 13, "end")
b += L(l, Y(0.9), l + pw, Y(0.9), "#555", 1.2, "6 4") + T(l + pw - 4, Y(0.9) - 6, "порог гипотезы H2 = 0,9", 12, "end", fill="#555")
b += L(l, Y(0), l + pw, Y(0), "#333", 1.2) + L(l, t_, l, t_ + ph)
gw = pw / 4; bw = 40
for gi, (node, tag, lab) in enumerate(cats):
    x0 = l + gi * gw + (gw - bw * 3) / 2
    for si, (k, col, _) in enumerate(ser):
        m, lo, hi = V[node][k]['rel_' + tag]; x = x0 + si * bw
        b += f'<rect x="{x + 2:.1f}" y="{Y(m):.1f}" width="{bw - 4}" height="{Y(0) - Y(m):.1f}" fill="{col}"/>'
        b += L(x + bw / 2, Y(lo), x + bw / 2, Y(hi), "#111", 1.4) + L(x + bw / 2 - 5, Y(lo), x + bw / 2 + 5, Y(lo), "#111", 1.2) + L(x + bw / 2 - 5, Y(hi), x + bw / 2 + 5, Y(hi), "#111", 1.2)
        ty = Y(hi) - 6 if not (k == 'rlex' and tag == 'out') else Y(m) + 16
        b += T(x + bw / 2, ty, f"{m:.2f}".replace('.', ','), 11, fill="#fff" if (k == 'rlex' and tag == 'out') else "#111")
    b += T(l + gi * gw + gw / 2, t_ + ph + 20, lab, 13)
b += f'<text transform="translate(18,{t_ + ph / 2}) rotate(-90)" font-size="13" text-anchor="middle">доля подтвердившихся закрытий</text>'
for i, (k, col, n) in enumerate(ser):
    xx = l + (i % 2) * (pw / 2); yy = H - 50 + (i // 2) * 22
    b += f'<rect x="{xx:.1f}" y="{yy - 11}" width="14" height="14" fill="{col}"/>' + T(xx + 20, yy + 1, n, 13, "start")
open('fig5.svg', 'w').write(svg(W, H, b))
print("figs ok")
