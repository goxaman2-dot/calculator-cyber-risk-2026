import json, math, itertools
import numpy as np
from scipy.stats import spearmanr

d = json.load(open('data.json'))
KR = d['KR'] / 1000.0          # тыс. руб.
L = 3000.0                     # тыс. руб.
B_RUB = 300.0
NODES = ["2023", "2024", "2025", "окт 2026", "ноя 2026", "дек 2026"]
TH0 = dict(emax=0.85, ec50=0.30, h=1.5)
DA, LAM, YCAP = 0.12, 1 / 30, 1.5
THETA = dict(emax=(0.75, 0.95), ec50=(0.20, 0.40), h=(1.2, 1.8))     # интервальное множество
WIDE = dict(emax=(0.70, 0.95), ec50=(0.15, 0.50), h=(1.0, 2.5))      # диапазоны прогонов статьи

def eff(y, k, p):
    y = np.maximum(y, 0)
    return p['emax'] * k * y ** p['h'] / (p['ec50'] ** p['h'] + y ** p['h'])

def survival(t):
    """вероятность сохранить доступ до момента удара"""
    r0, g = t['r0'], t['g']
    if r0 >= 1 or t.get('det') is False:
        return 1.0
    rho = max(r0, 1 - LAM / g)
    if rho <= r0 + 1e-12:
        return 1.0
    tau = math.log((rho / (1 - rho)) * ((1 - r0) / r0)) / g
    return math.exp(-LAM * tau)

def A_of(t, mode):
    a = t['dp'] * t['rho']
    return a * survival(t) if mode == 'exp' else a

def ystar(A, k, p, da=DA):
    if A <= da:
        return 0.0
    r = 1 - da / A
    em = p['emax'] * k
    if r >= em:
        return math.inf
    y = p['ec50'] * (r / (em - r)) ** (1 / p['h'])
    return y if y <= YCAP else math.inf

def delta(A, k, p, da=DA):
    return p['emax'] * k - (1 - da / A)

def theta_grid(T, n=5):
    return [dict(emax=a, ec50=b, h=c) for a in np.linspace(*T['emax'], n) for b in np.linspace(*T['ec50'], n) for c in np.linspace(*T['h'], n)]

GRID = theta_grid(THETA)

def ystar_rob(A, k):
    v = [ystar(A, k, p) for p in GRID]
    fin = [x for x in v if math.isfinite(x)]
    if len(fin) == len(v):
        return max(v), 'robust'
    if fin:
        return math.inf, 'conditional'
    return math.inf, 'unreachable'

def rows(node, mode='cond'):
    out = []
    for t in d['nodes'][node]:
        A = A_of(t, mode)
        out.append(dict(n=t['n'], A=A, k=t['ek'], y0=t['y0'], x=t['x'], z=t['z']))
    return out

# ---------- точная оптимизация на сетке (динамическое программирование)
def dp_opt(R, B, p, steps=300):
    dlt = B / steps
    kmax = min(steps, int(YCAP / dlt))
    f = np.zeros(steps + 1)
    choice = []
    for t in R:
        ks = np.arange(0, kmax + 1)
        dr = t['A'] * (1 - eff(ks * dlt, t['k'], p))
        g = np.full(steps + 1, np.inf); arg = np.zeros(steps + 1, int)
        for b in range(steps + 1):
            kk = ks[ks <= b]
            v = f[b - kk] + dr[:len(kk)]
            j = int(np.argmin(v)); g[b] = v[j]; arg[b] = kk[j]
        choice.append(arg); f = g
    # восстановление
    y = [0] * len(R); b = steps
    for i in range(len(R) - 1, -1, -1):
        k = choice[i][b]; y[i] = k * dlt; b -= k
    return f[steps], y

def greedy(R, B, p, steps=300, K=40):
    dlt = B / steps; y = [0.0] * len(R); left = steps
    cur = [t['A'] * (1 - eff(0, t['k'], p)) for t in R]
    while left > 0:
        best, bk, bg = -1, 0, 1e-12
        for i, t in enumerate(R):
            for k in range(1, min(K, left) + 1):
                ny = y[i] + k * dlt
                if ny > YCAP: break
                g = (cur[i] - t['A'] * (1 - eff(ny, t['k'], p))) / k
                if g > bg: bg, best, bk = g, i, k
        if best < 0: break
        y[best] += bk * dlt; cur[best] = R[best]['A'] * (1 - eff(y[best], R[best]['k'], p)); left -= bk
    return sum(cur), y

def resid(R, y, p):
    return sum(t['A'] * (1 - eff(yy, t['k'], p)) for t, yy in zip(R, y))

def fact(R, B):
    s = sum(t['y0'] for t in R); return [t['y0'] * B / s for t in R]

def prop(R, B):
    s = sum(t['A'] for t in R); return [t['A'] * B / s for t in R]

def lex_dp(R, B, p, req, steps=300):
    """двухступенчатый критерий: максимум закрытых угроз (Dr <= Da при y >= req), затем минимум суммарного ущерба"""
    dlt = B / steps; kmax = min(steps, int(YCAP / dlt))
    BIG = 1000.0
    f = np.zeros(steps + 1); choice = []
    for t, rq in zip(R, req):
        ks = np.arange(0, kmax + 1)
        dr = t['A'] * (1 - eff(ks * dlt, t['k'], p))
        closed = (ks * dlt >= rq - 1e-9) & np.isfinite(rq) & (rq > 0)
        val = dr - BIG * closed          # закрытие весит больше любого ущерба
        g = np.full(steps + 1, np.inf); arg = np.zeros(steps + 1, int)
        for b in range(steps + 1):
            kk = ks[ks <= b]; v = f[b - kk] + val[:len(kk)]
            j = int(np.argmin(v)); g[b] = v[j]; arg[b] = kk[j]
        choice.append(arg); f = g
    y = [0] * len(R); b = steps
    for i in range(len(R) - 1, -1, -1):
        k = choice[i][b]; y[i] = k * dlt; b -= k
    return y

def pxd(R, B, p):
    req = [ystar(t['A'], t['k'], p) for t in R]
    idx = [i for i, r in enumerate(req) if math.isfinite(r) and r > 0]
    idx.sort(key=lambda i: req[i] / (R[i]['A'] - DA))
    y = [0.0] * len(R); rem = B
    for i in idx:
        if req[i] <= rem: y[i] = req[i]; rem -= req[i]
    if rem > 1e-9:
        # жадный остаток
        dlt = rem / 150; left = 150
        while left > 0:
            best, bk, bg = -1, 0, 1e-12
            for i, t in enumerate(R):
                for k in range(1, min(40, left) + 1):
                    ny = y[i] + k * dlt
                    if ny > YCAP: break
                    g = (t['A'] * (eff(ny, t['k'], p) - eff(y[i], t['k'], p))) / k
                    if g > bg: bg, best, bk = g, i, k
            if best < 0: break
            y[best] += bk * dlt; left -= bk
    return y

def over(R, y, p):
    return sum(1 for t, yy in zip(R, y) if t['A'] > DA and t['A'] * (1 - eff(yy, t['k'], p)) > DA * (1 + 1e-6))

res = {}
B = B_RUB / KR
# 1. две интерпретации отложенной атаки
interp = []
for n in range(6):
    rc, re_ = rows(n, 'cond'), rows(n, 'exp')
    def norm(R):
        ys = [ystar(t['A'], t['k'], TH0) for t in R]
        return sum(y for y in ys if math.isfinite(y)) * KR, sum(1 for y in ys if not math.isfinite(y)), sum(1 for t in R if t['A'] > DA)
    nc, rc_, ac = norm(rc); ne, re2, ae = norm(re_)
    rho_s = spearmanr([t['A'] for t in rc], [t['A'] for t in re_]).correlation
    surv = [survival(t) for t in d['nodes'][n]]
    interp.append(dict(node=NODES[n], Nc=nc, resc=rc_, abovec=ac, Ne=ne, rese=re2, abovee=ae, rho=rho_s, smin=min(surv), smean=float(np.mean(surv))))
res['interp'] = interp
# сводка вероятностей выживания по угрозам (дек 26)
res['surv'] = [(t['n'], round(survival(t), 3), round(t['rho'], 3)) for t in d['nodes'][5]]

# 2. greedy против точного оптимума
gap = []
for n in range(6):
    R = rows(n)
    Dg, _ = greedy(R, B, TH0); Dx, _ = dp_opt(R, B, TH0)
    Dx2, _ = dp_opt(R, B, TH0, steps=600)
    Df = resid(R, fact(R, B), TH0)
    gap.append(dict(node=NODES[n], greedy=Dg * L, exact=Dx * L, exact600=Dx2 * L, fact=Df * L, gap_pct=(Dg - Dx) / (Df - Dx) * 100))
res['gap'] = gap

# 3. запас достижимости, эластичность, надёжность
rng = np.random.default_rng(7)
def draw(T, n):
    return [dict(emax=rng.uniform(*T['emax']), ec50=rng.uniform(*T['ec50']), h=rng.uniform(*T['h'])) for _ in range(n)]
draws_in, draws_wide = draw(THETA, 400), draw(WIDE, 400)
rel = []
for n in [2, 5]:
    for t in rows(n):
        if t['A'] <= DA: continue
        dl = delta(t['A'], t['k'], TH0); ys = ystar(t['A'], t['k'], TH0)
        if not math.isfinite(ys):
            rel.append(dict(node=NODES[n], n=t['n'], delta=dl, ystar=None, p_in=None, p_wide=None, cls=ystar_rob(t['A'], t['k'])[1])); continue
        pin = np.mean([t['A'] * (1 - eff(ys, t['k'], q)) <= DA * (1 + 1e-6) for q in draws_in])
        pw = np.mean([t['A'] * (1 - eff(ys, t['k'], q)) <= DA * (1 + 1e-6) for q in draws_wide])
        # разброс требуемых затрат при ошибке на 0,05 в Emax
        lo = ystar(t['A'], t['k'], dict(TH0, emax=0.80))
        rel.append(dict(node=NODES[n], n=t['n'], delta=dl, ystar=ys * KR, y_em80=(lo * KR if math.isfinite(lo) else None), p_in=float(pin), p_wide=float(pw), cls=ystar_rob(t['A'], t['k'])[1], elast=-1 / (TH0['h'] * dl)))
res['rel'] = rel

# 4. классификация и устойчивый норматив по узлам и отраслям
cls = []
for n in range(6):
    R = rows(n); c = {'robust': 0, 'conditional': 0, 'unreachable': 0}; Nr = 0; Nnom = 0; unacc = 0; unacc_rob = 0
    for t in R:
        if t['A'] <= DA: continue
        yr, k = ystar_rob(t['A'], t['k']); c[k] += 1
        yn = ystar(t['A'], t['k'], TH0)
        if math.isfinite(yn): Nnom += yn * KR
        else: unacc += (t['A'] * (1 - eff(YCAP, t['k'], TH0)) - DA) * L
        if k == 'robust': Nr += yr * KR
        else: unacc_rob += max(0, (t['A'] * (1 - eff(YCAP, t['k'], TH0)) - DA)) * L
    # то же при k=1 для угроз ИИ-агентов (проверка H1 на независимость от допущения)
    res_k1 = sum(1 for t in R if t['A'] > DA and not math.isfinite(ystar(t['A'], 1.0, TH0)))
    cls.append(dict(node=NODES[n], above=sum(1 for t in R if t['A'] > DA), **c, Nnom=Nnom, Nrob=Nr, unacc=unacc, res_k1=res_k1,
                    res_nom=sum(1 for t in R if t['A'] > DA and not math.isfinite(ystar(t['A'], t['k'], TH0)))))
res['cls'] = cls
sect = []
for key, s in d['sect'].items():
    c = {'robust': 0, 'conditional': 0, 'unreachable': 0}; Nr = 0; Nn = 0; resn = 0
    for t in s['rows']:
        A = t['dp'] * t['rho']
        if A <= DA: continue
        yr, kk = ystar_rob(A, t['ek']); c[kk] += 1
        if kk == 'robust': Nr += yr * KR
        yn = ystar(A, t['ek'], TH0)
        if math.isfinite(yn): Nn += yn * KR
        else: resn += 1
    sect.append(dict(n=s['n'], Nnom=Nn, Nrob=Nr, resn=resn, **c))
res['sect'] = sect

# 5. правила: номинальное и устойчивое двухступенчатое против прочих, проверка при ошибке параметров
def evaluate(n, draws):
    R = rows(n)
    req_nom = [ystar(t['A'], t['k'], TH0) for t in R]
    req_rob = [ystar_rob(t['A'], t['k'])[0] for t in R]
    Dx, yopt = dp_opt(R, B, TH0)
    ys = dict(fact=fact(R, B), prop=prop(R, B), opt=yopt, pxd=pxd(R, B, TH0),
              lex=lex_dp(R, B, TH0, req_nom), rlex=lex_dp(R, B, TH0, req_rob))
    out = {}
    Df = resid(R, ys['fact'], TH0)
    for k, y in ys.items():
        D = resid(R, y, TH0)
        claimed = sum(1 for t, yy, rq in zip(R, y, req_rob if k == 'rlex' else req_nom) if math.isfinite(rq) and rq > 0 and yy >= rq - 1e-9)
        ov = [over(R, y, q) for q in draws]
        true_closed = [sum(1 for t, yy, rq in zip(R, y, req_rob if k == 'rlex' else req_nom) if math.isfinite(rq) and rq > 0 and yy >= rq - 1e-9 and t['A'] * (1 - eff(yy, t['k'], q)) <= DA * (1 + 1e-6)) for q in draws]
        out[k] = dict(D=D * L, Q=(Df - D) / (Df - Dx), over=over(R, y, TH0), claimed=claimed, over_mc=float(np.mean(ov)),
                      reliab=(float(np.mean(true_closed)) / claimed if claimed else None),
                      Dmc=float(np.mean([resid(R, y, q) for q in draws])) * L)
    return out
res['rules'] = {NODES[n]: dict(inside=evaluate(n, draws_in[:200]), wide=evaluate(n, draws_wide[:200])) for n in [2, 5]}

# 6. портфель мер: точный перебор 2^19 наборов
mids = list(d['MEAS']); cost = np.array([d['MEAS'][m]['c'] / 1000 for m in mids])
def portfolio(n):
    R = rows(n); M = np.zeros((len(mids), len(R)))
    for j, t in enumerate(R):
        for m in d['MAP'].get(t['n'], []): M[mids.index(m), j] = 1
    nS = 1 << len(mids)
    S = ((np.arange(nS)[:, None] >> np.arange(len(mids))) & 1).astype(np.float32)
    C = S @ cost
    Y = (S @ (M * cost[:, None])) / KR                    # затраты на угрозу без двойного счёта
    A = np.array([t['A'] for t in R]); k = np.array([t['k'] for t in R])
    def drm(p): return A * (1 - eff(np.minimum(Y, YCAP), k, p))
    reqn = np.array([ystar(t['A'], t['k'], TH0) for t in R]); reqr = np.array([ystar_rob(t['A'], t['k'])[0] for t in R])
    closable = np.isfinite(reqn) & (reqn > 0)
    closed_n = (Y >= reqn - 1e-9) & closable
    closed_r = (Y >= reqr - 1e-9) & np.isfinite(reqr) & (reqr > 0)
    Dn = drm(TH0).sum(1)
    out = dict(per_threat_norm=float(np.nansum(np.where(closable, reqn, 0)) * KR))
    full = closed_n.sum(1) == closable.sum()
    out['measure_norm'] = float(C[full].min()) if full.any() else None
    out['measure_norm_set'] = [d['MEAS'][mids[i]]['n'] for i in np.where(S[np.argmin(np.where(full, C, np.inf))] > 0)[0]] if full.any() else []
    within = C <= B_RUB + 1e-9
    for tag, cl in [('nom', closed_n), ('rob', closed_r)]:
        cnt = np.where(within, cl.sum(1), -1)
        best = cnt.max(); cand = np.where(cnt == best)[0]
        i = cand[np.argmin(Dn[cand])]
        out[tag] = dict(closed=int(best), cost=float(C[i]), D=float(Dn[i] * L), set=[d['MEAS'][mids[j]]['n'] for j in np.where(S[i] > 0)[0]],
                        over=int(((A > DA) & (drm(TH0)[i] > DA * (1 + 1e-6))).sum()))
    # оптимум по суммарному ущербу среди наборов
    i = np.argmin(np.where(within, Dn, np.inf)); out['minD'] = dict(cost=float(C[i]), D=float(Dn[i] * L), closed=int(closed_n[i].sum()))
    return out
res['portfolio'] = {NODES[n]: portfolio(n) for n in [2, 5]}

# 7. чувствительность норматива к Da (2025)
res['da'] = []
for da in [0.08, 0.10, 0.12, 0.15, 0.20]:
    R = rows(2); ys = [ystar(t['A'], t['k'], TH0, da) for t in R]
    res['da'].append(dict(da=da, N=sum(y for y in ys if math.isfinite(y)) * KR, res=sum(1 for y in ys if not math.isfinite(y))))

# 8. эмпирика 2024 только по наблюдаемым классам
z24 = {x['n']: x['z'] for x in d['z24']}
obs = [(k, v['s']) for k, v in d['EMP24'].items() if not v.get('e') and k in z24]
allc = [(k, v['s']) for k, v in d['EMP24'].items() if k in z24]
r1 = spearmanr([z24[k] for k, _ in obs], [s for _, s in obs]); r2 = spearmanr([z24[k] for k, _ in allc], [s for _, s in allc])
res['emp'] = dict(n_obs=len(obs), rho_obs=r1.correlation, p_obs=r1.pvalue, n_all=len(allc), rho_all=r2.correlation, p_all=r2.pvalue, obs=[k for k, _ in obs])
json.dump(res, open('res.json', 'w'), ensure_ascii=False, indent=1, default=float)
print("ok")

# ---- дополнения
extra = {}
for n in [2, 5]:
    R = rows(n); prem_nom = 0; prem_rob = 0; unp = []
    for t in R:
        if t['A'] <= DA: continue
        yr, kk = ystar_rob(t['A'], t['k']); yn = ystar(t['A'], t['k'], TH0)
        if kk == 'robust': prem_nom += yn * KR; prem_rob += yr * KR
        full = sum(d['MEAS'][m]['c'] for m in d['MAP'].get(t['n'], [])) / 1000 / KR
        if math.isfinite(yn) and full < yn: unp.append((t['n'], round(full * KR, 1), round(yn * KR, 1)))
    extra[NODES[n]] = dict(robust_nom=prem_nom, robust_rob=prem_rob, premium=prem_rob / prem_nom - 1, unpurchasable=unp)
# минимальная стоимость набора мер, закрывающего все достижимые набором угрозы (без ограничения бюджета)
def mnorm(n):
    R = rows(n); M = np.zeros((len(mids), len(R)))
    for j, t in enumerate(R):
        for m in d['MAP'].get(t['n'], []): M[mids.index(m), j] = 1
    nS = 1 << len(mids); S = ((np.arange(nS)[:, None] >> np.arange(len(mids))) & 1).astype(np.float32)
    C = S @ cost; Y = (S @ (M * cost[:, None])) / KR
    reqn = np.array([ystar(t['A'], t['k'], TH0) for t in R]); ok = np.isfinite(reqn) & (reqn > 0)
    cl = (Y >= reqn - 1e-9) & ok; mx = cl.sum(1).max()
    i = np.argmin(np.where(cl.sum(1) == mx, C, np.inf))
    # стоимость тех же угроз по суммированию y*
    sel = cl[i]
    return dict(maxclosed=int(mx), closable=int(ok.sum()), cost=float(C[i]), per_threat_same=float(reqn[sel].sum() * KR))
for n in [2, 5]: extra[NODES[n]]['mnorm'] = mnorm(n)
res['extra'] = extra
json.dump(res, open('res.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(extra, ensure_ascii=False, indent=1, default=float))

# ======================= версия 3: правки по рецензии =======================
def pxd_grid(R, B, p, steps=300, K=40):
    """PARETO-X·D на той же сетке, что и точные решения: пороги округлены вверх до узла сетки"""
    dlt = B / steps
    req = [ystar(t['A'], t['k'], p) for t in R]
    idx = [i for i, r in enumerate(req) if math.isfinite(r) and r > 0]
    idx.sort(key=lambda i: req[i] / (R[i]['A'] - DA))
    k = [0] * len(R); left = steps
    for i in idx:
        need = math.ceil(req[i] / dlt - 1e-9)
        if need <= left: k[i] = need; left -= need
    while left > 0:
        best, bk, bg = -1, 0, 1e-12
        for i, t in enumerate(R):
            for kk in range(1, min(K, left) + 1):
                ny = (k[i] + kk) * dlt
                if ny > YCAP: break
                g = t['A'] * (eff(ny, t['k'], p) - eff(k[i] * dlt, t['k'], p)) / kk
                if g > bg: bg, best, bk = g, i, kk
        if best < 0: break
        k[best] += bk; left -= bk
    return [kk * dlt for kk in k]

rng3 = np.random.default_rng(2026)
def inside(q): return all(THETA[x][0] <= q[x] <= THETA[x][1] for x in THETA)
def draws_inside(n): return [dict(emax=rng3.uniform(*THETA['emax']), ec50=rng3.uniform(*THETA['ec50']), h=rng3.uniform(*THETA['h'])) for _ in range(n)]
def draws_outside(n):
    out = []
    while len(out) < n:
        q = dict(emax=rng3.uniform(*WIDE['emax']), ec50=rng3.uniform(*WIDE['ec50']), h=rng3.uniform(*WIDE['h']))
        if not inside(q): out.append(q)
    return out
DIN, DOUT = draws_inside(2000), draws_outside(2000)

def boot(ok, nb=1000):
    if ok.size == 0: return None
    bs = [ok[rng3.integers(0, len(ok), len(ok))].mean() for _ in range(nb)]
    return [float(ok.mean()), *map(float, np.percentile(bs, [2.5, 97.5]))]

v3 = {'grid_cmp': [], 'rules': {}}
for n in range(6):
    R = rows(n); req = [ystar(t['A'], t['k'], TH0) for t in R]
    yp = pxd_grid(R, B, TH0); yl = lex_dp(R, B, TH0, req)
    v3['grid_cmp'].append(dict(node=NODES[n], pxd_over=over(R, yp, TH0), pxd_D=resid(R, yp, TH0) * L, lex_over=over(R, yl, TH0), lex_D=resid(R, yl, TH0) * L))
for n in [2, 5]:
    R = rows(n)
    req_nom = [ystar(t['A'], t['k'], TH0) for t in R]; req_rob = [ystar_rob(t['A'], t['k'])[0] for t in R]
    Dx, yopt = dp_opt(R, B, TH0)
    ys = dict(fact=fact(R, B), prop=prop(R, B), opt=yopt, pxd=pxd_grid(R, B, TH0), lex=lex_dp(R, B, TH0, req_nom), rlex=lex_dp(R, B, TH0, req_rob))
    Df = resid(R, ys['fact'], TH0); out = {}
    for kname, y in ys.items():
        rq = req_rob if kname == 'rlex' else req_nom
        cl = [i for i, (yy, r_) in enumerate(zip(y, rq)) if math.isfinite(r_) and r_ > 0 and yy >= r_ - 1e-9]
        o = dict(D=resid(R, y, TH0) * L, Q=(Df - resid(R, y, TH0)) / (Df - Dx), over=over(R, y, TH0), claimed=len(cl))
        for tag, dr in [('in', DIN), ('out', DOUT)]:
            ok = np.array([[R[i]['A'] * (1 - eff(y[i], R[i]['k'], q)) <= DA * (1 + 1e-6) for i in cl] for q in dr]) if cl else np.zeros((len(dr), 0))
            o['rel_' + tag] = boot(ok.flatten() if False else ok.mean(1)) if cl else None   # доля по сценариям, затем среднее
            o['all_' + tag] = float(ok.all(1).mean()) if cl else None
            o['over_' + tag] = float(np.mean([over(R, y, q) for q in dr]))
        out[kname] = o
    v3['rules'][NODES[n]] = out
# таблица 3 с разделением причин
t3 = []
for t in rows(2):
    if t['A'] <= DA: continue
    dl = delta(t['A'], t['k'], TH0); ys_ = ystar(t['A'], t['k'], TH0)
    dl80 = delta(t['A'], t['k'], dict(TH0, emax=0.80)); r_ = 1 - DA / t['A']
    raw80 = TH0['ec50'] * (r_ / dl80) ** (1 / TH0['h']) if dl80 > 0 else math.inf
    t3.append(dict(n=t['n'], A=t['A'], delta=dl, ystar=ys_ * KR, semi=-1 / (TH0['h'] * dl), el_d=-1 / TH0['h'], el_em=-t['k'] * TH0['emax'] / (TH0['h'] * dl),
                   y80=raw80 * KR, y80_cap=raw80 > YCAP, delta80=dl80, cls=ystar_rob(t['A'], t['k'])[1],
                   p_in=float(np.mean([t['A'] * (1 - eff(ys_, t['k'], q)) <= DA * (1 + 1e-6) for q in DIN]))))
v3['t3'] = t3
# перечень классов
first = {}
for n in range(6):
    for t in d['nodes'][n]: first.setdefault(t['n'], NODES[n])
cls_list = []
for t in d['nodes'][5]:
    e = d['EMP24'].get(t['n'])
    typ = 'экспертная (новый класс)' if e is None else ('экспертная' if e.get('e') else 'наблюдаемая')
    cls_list.append(dict(n=t['n'], first=first[t['n']], typ=typ, k=t['ek']))
v3['classes'] = cls_list
# причины недостижимости в Θ для узлов 2026
causes = []
for n in [3, 4, 5]:
    for t in rows(n):
        if t['A'] <= DA: continue
        dmin = delta(t['A'], t['k'], dict(TH0, emax=THETA['emax'][0])); dmax = delta(t['A'], t['k'], dict(TH0, emax=THETA['emax'][1]))
        c = ystar_rob(t['A'], t['k'])[1]
        if c != 'robust': causes.append(dict(node=NODES[n], n=t['n'], cls=c, dmin=dmin, dmax=dmax))
v3['causes'] = causes
res['v3'] = v3
json.dump(res, open('res.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(v3['grid_cmp'], ensure_ascii=False))
for nn, o in v3['rules'].items():
    for k_, x in o.items(): print(nn, k_, {a: (round(b, 3) if isinstance(b, float) else ([round(c, 3) for c in b] if isinstance(b, list) else b)) for a, b in x.items()})
for x in t3: print({a: (round(b, 3) if isinstance(b, float) else b) for a, b in x.items()})
for x in cls_list: print(x)
for x in causes: print({a: (round(b, 3) if isinstance(b, float) else b) for a, b in x.items()})
