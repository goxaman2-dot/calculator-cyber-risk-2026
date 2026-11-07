import math
F='font-family="Times New Roman, Liberation Serif, serif"'
def svg(w,h,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {F}><rect width="{w}" height="{h}" fill="#ffffff"/>{body}</svg>'
def T(x,y,s,size=15,anchor="middle",w="normal",fill="#111",style=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{w}" fill="{fill}" {style}>{s}</text>'
def L(x1,y1,x2,y2,c="#333",sw=1.2,dash=None,marker=False):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    m=' marker-end="url(#ar)"' if marker else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{sw}"{d}{m}/>'
AR='<defs><marker id="ar" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#333"/></marker></defs>'
def box(x,y,w,h,lines,fill="#f2f5f9",stroke="#4a5d73",size=14):
    o=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>'
    n=len(lines);y0=y+h/2-(n-1)*size*0.62+size*0.35
    for i,s in enumerate(lines):o+=T(x+w/2,y0+i*size*1.24,s,size)
    return o
# ---------- Рис. 1: схема модели
b=AR
b+=box(20,20,230,62,["Токсичность x","(БДУ ФСТЭК, индекс TDI)"])
b+=box(20,110,230,62,["Частота атак z","(PT, BI.ZONE, Solar 4RAYS)"])
b+=box(300,65,230,62,["Потенциал ущерба","D<tspan baseline-shift='sub' font-size='10'>p</tspan> = x(0,25 + 0,75z), ф. (1)"])
b+=box(20,210,230,62,["Время обнаружения MTTD,","λ = 1/MTTD"])
b+=box(300,210,230,62,["Зрелость атаки ρ","(отложенная атака), ф. (2)–(4)"])
b+=box(580,137,200,62,["Реализуемый ущерб","D<tspan baseline-shift='sub' font-size='10'>p</tspan>·ρ"],fill="#fff4e5",stroke="#b26b00")
b+=box(580,20,200,62,["Кривая «затраты — эффект»","E(y), ф. (5)"])
b+=box(580,300,200,62,["Требуемые затраты y*","и резистентность, ф. (7)–(8)"],fill="#fff4e5",stroke="#b26b00")
b+=box(300,300,230,62,["КиберНорма N","(норматив затрат), ф. (9)"],fill="#e8f3ec",stroke="#2e7d4f")
b+=box(300,395,230,62,["Правило PARETO-X·D:","сортировка + остаток, ф. (11)"],fill="#e8f3ec",stroke="#2e7d4f")
b+=box(20,395,230,62,["Смета мер защиты","в рублях (каталог, K<tspan baseline-shift='sub' font-size='10'>R</tspan>)"],fill="#e8f3ec",stroke="#2e7d4f")
b+=box(580,395,200,62,["Остаточный ущерб D<tspan baseline-shift='sub' font-size='10'>r</tspan>,","качество Q, ф. (6), (10)"])
b+=L(250,51,298,86,marker=True)+L(250,141,298,106,marker=True)
b+=L(250,241,298,241,marker=True)+L(530,96,578,155,marker=True)+L(530,241,578,180,marker=True)
b+=L(680,82,680,135,marker=True)+L(680,199,680,298,marker=True)
b+=L(578,331,532,331,marker=True)+L(580,345,532,410,marker=True)
b+=L(298,426,252,426,marker=True)+L(530,440,578,440,marker=True)
open("fig1.svg","w").write(svg(800,480,b))

# ---------- Рис. 2: остаточный ущерб от затрат
emax,ec,h,da,KR=0.85,0.30,1.5,0.12,84.5
def E(y,k=1):return emax*k*y**h/(ec**h+y**h) if y>0 else 0
W,H=800,470;l,r,t,bt=80,200,30,70;pw,ph=W-l-r,H-t-bt
X=lambda y:l+pw*y/1.5;Y=lambda d:t+ph*(1-d/0.8)
b=''
for d in [0,0.2,0.4,0.6,0.8]:
    b+=L(l,Y(d),l+pw,Y(d),"#e3e3e3",1)+T(l-8,Y(d)+5,f"{d:.1f}".replace(".",","),14,"end")
for y in [0,0.25,0.5,0.75,1,1.25,1.5]:
    b+=L(X(y),t+ph,X(y),t+ph+5,"#333",1)+T(X(y),t+ph+22,f"{y:g}".replace(".",","),14)
    b+=T(X(y),t+ph+40,f"{y*KR:.0f}",12,fill="#666")
b+=L(l,t+ph,l+pw,t+ph)+L(l,t,l,t+ph)
b+=T(l+pw/2,H-8,"затраты y, доли от средней стоимости полного набора мер (под осью — тыс. ₽/год)",14)
b+=f'<text transform="translate(22,{t+ph/2}) rotate(-90)" font-size="14" text-anchor="middle">остаточный ущерб D<tspan baseline-shift="sub" font-size="10">r</tspan>, доли от L</text>'
b+=L(l,Y(da),l+pw,Y(da),"#b26b00",1.6,"7 5")
TH=[("Deepfake-атаки",0.432,1,"#1f5fa8",None),("Phishing / BEC",0.231,1,"#2e7d4f",None),("LLM Jailbreaking",0.749,1,"#a12b2b","предел затрат"),("Заражение ИИ-агентов",0.386,0.6,"#6a3fa0","предел E")]
lab=[]
for n,dp,k,c,res in TH:
    pts=" ".join(f"{X(y):.1f},{Y(dp*(1-E(y,k))):.1f}" for y in [i*1.5/150 for i in range(151)])
    b+=f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.4"/>'
    lab.append((Y(dp*(1-E(1.5,k))),n,c,res))
    r_=1-da/dp
    if r_<emax*k:
        ys=ec*(r_/(emax*k-r_))**(1/h)
        if ys<=1.5:
            b+=f'<circle cx="{X(ys):.1f}" cy="{Y(da):.1f}" r="5" fill="{c}"/>'
            b+=L(X(ys),Y(da),X(ys),t+ph,c,1,"3 3")
            if n.startswith("Deep"):tx,ty=X(ys)+30,Y(da)-60
            else:tx,ty=X(0.46),Y(0.035)
            b+=L(X(ys),Y(da),tx,ty-4,c,1)+T(tx+4,ty,f"y* = {ys:.2f} ({ys*KR:.0f} тыс. ₽)".replace(".",","),13,"start",fill=c)
# подписи справа с выносками, без наложения
lab.sort();ly=[]
for yv,n,c,res in lab:
    p=max(yv,(ly[-1]+40) if ly else yv);ly.append(p)
    b+=L(X(1.5),yv,X(1.5)+14,p,c,1)
    b+=T(X(1.5)+18,p+5,n,14,"start",fill=c)
    if res:b+=T(X(1.5)+18,p+22,f"резистентна: {res}",12,"start",fill="#555")
b+=f'<text x="{X(0.02):.1f}" y="{Y(da)+20:.1f}" font-size="13" fill="#b26b00">D<tspan baseline-shift="sub" font-size="10">a</tspan> = 0,12</text>'
open("fig2.svg","w").write(svg(W,H,b))

# ---------- общий бар-чарт
def bars(fname,cats,series,colors,names,ymin,ymax,ticks,ylab,fmt,W=800,H=440,extra=None,legend_rows=1):
    l,r,t,bt=70,20,40,95;pw,ph=W-l-r,H-t-bt
    Y=lambda v:t+ph*(ymax-v)/(ymax-ymin)
    b=''
    for v in ticks:b+=L(l,Y(v),l+pw,Y(v),"#e3e3e3",1)+T(l-8,Y(v)+5,fmt(v),13,"end")
    b+=L(l,Y(0),l+pw,Y(0),"#333",1.2)+L(l,t,l,t+ph)
    gw=pw/len(cats);ns=len(series);bw=min(26 if ns>1 else 64,(gw-18)/ns)
    for gi,c in enumerate(cats):
        x0=l+gi*gw+(gw-bw*ns)/2
        for si,s in enumerate(series):
            v=s[gi];x=x0+si*bw;y1,y2=Y(max(v,0)),Y(min(v,0))
            b+=f'<rect x="{x+1:.1f}" y="{y1:.1f}" width="{bw-2:.1f}" height="{max(y2-y1,0.8):.1f}" fill="{colors[si]}"/>'
            ty=y1-4 if v>=0 else y2+13
            b+=T(x+bw/2,ty,fmt(v),11)
        b+=T(l+gi*gw+gw/2,t+ph+20,c,14)
    b+=f'<text transform="translate(18,{t+ph/2}) rotate(-90)" font-size="14" text-anchor="middle">{ylab}</text>'
    # легенда
    lx=l;ly=H-45
    per=math.ceil(len(names)/legend_rows)
    for i,n in enumerate(names):
        row=i//per;col=i%per;xx=l+col*(pw/per);yy=ly+row*22
        b+=f'<rect x="{xx:.1f}" y="{yy-11}" width="14" height="14" fill="{colors[i]}"/>'+T(xx+20,yy+1,n,13,"start")
    if extra:b+=extra(Y,l,pw,gw)
    open(fname,"w").write(svg(W,H,b))
cats=["2023","2024","2025","окт 2026","ноя 2026","дек 2026"]
f2=lambda v:(f"{v:.2f}").replace(".",",").replace("-","−")
bars("fig3.svg",cats,[[-0.11,0.06,0.12,0.13,0.16,0.18],[0.42,0.43,0.46,0.46,0.47,0.48],[0.83,0.84,0.85,0.82,0.82,0.82]],
     ["#9aa5b1","#e0a030","#1f5fa8"],["∝ TDI (только токсичность)",'∝ D<tspan baseline-shift="sub" font-size="10">p</tspan> (токсичность и частота)','∝ D<tspan baseline-shift="sub" font-size="10">p</tspan>·ρ (плюс зрелость атаки)'],-0.2,1.0,[-0.2,0,0.2,0.4,0.6,0.8,1.0],"индекс качества Q",f2,W=800,H=430,legend_rows=2)
fi=lambda v:str(int(v))
bars("fig4.svg",cats,[[3,6,6,9,9,10],[2,6,8,12,12,12],[2,4,7,12,12,12],[0,2,4,4,5,5],[0,1,2,4,5,5]],
     ["#9aa5b1","#e0a030","#7a4fb0","#1f5fa8","#2e7d4f"],["факт",'∝ D<tspan baseline-shift="sub" font-size="10">p</tspan>·ρ (Гордон — Лёб)','оптимум по ΣD<tspan baseline-shift="sub" font-size="10">r</tspan>',"PARETO-X·D","нижняя граница"],0,14,[0,2,4,6,8,10,12,14],'число угроз выше D<tspan baseline-shift="sub" font-size="10">a</tspan>',fi,W=800,H=430,legend_rows=2)
def ex5(Y,l,pw,gw):
    o=L(l,Y(300),l+pw,Y(300),"#a12b2b",1.8,"7 5")
    o+=L(l+112,Y(300),l+95,Y(300)-44,"#a12b2b",1)+T(l+12,Y(300)-50,"фактический бюджет 300 тыс. ₽",13,"start",fill="#a12b2b")
    res=[0,0,0,2,3,3]
    for i,rv in enumerate(res):
        v=[213,318,441,481,419,428][i]
        if rv:o+=T(l+i*gw+gw/2,Y(v)-22,f"резистентных: {rv}",12,fill="#a12b2b")
    return o
bars("fig5.svg",cats,[[213,318,441,481,419,428]],["#2e7d4f"],["норматив КиберНормы N, тыс. ₽/год"],0,600,[0,100,200,300,400,500,600],"тыс. ₽/год",fi,W=800,H=400,extra=ex5)
print("ok")
