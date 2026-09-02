#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块位置温度计 —— HTML 报表生成"""
import json, datetime, sys

D = json.load(open("sector_data.json", encoding="utf-8"))
META, ITEMS = D["meta"], D["items"]
BENCH = META["bench"]
NOW = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

ORDER = ["中证一级行业", "细分行业指数", "AI·半导体·算力", "新能源", "医药",
         "消费", "金融地产", "资源周期", "军工·宽基"]
GROUPS = [g for g in ORDER if any(i["group"] == g for i in ITEMS)]
for i in ITEMS:
    if i["group"] not in GROUPS:
        GROUPS.append(i["group"])


def lift_of(it):
    """底部抬升度 = 3年位置 − 5年位置。
    正值越大：近3年的低点相对更高（未跌破5年前的极端低点）；
    负值：近3年仍在创新低。"""
    return round(it["w3"]["pos"] - it["w5"]["pos"], 1)


def zone_of(it):
    """状态标签：位置(便不便宜) × 趋势(在涨在跌) × 底部(低点抬不抬)"""
    p5 = it["w5"]["pos"]
    ex = it.get("excess1y")
    r1 = it.get("ret1y")
    lift = lift_of(it)
    bt = it.get("bottom") or {}
    rising = bt.get("rising")
    up = (ex is not None and ex > 0) or (r1 is not None and r1 > 0)

    if p5 <= 20:
        if up and rising:
            return "底部反转", "#1EC98B", "rgba(30,201,139,.20)"
        if up:
            return "低位企稳", "#5DCAA5", "rgba(93,202,165,.16)"
        if rising or lift > 15:
            return "低位磨底", "#4FA3D1", "rgba(79,163,209,.16)"
        return "阴跌寻底", "#8fa8c4", "rgba(143,168,196,.14)"
    if p5 <= 40:
        if up and lift > 10:
            return "回暖中", "#5DCAA5", "rgba(93,202,165,.14)"
        return "偏低", "#4FA3D1", "rgba(79,163,209,.13)"
    if p5 <= 60:
        return "中性", "#6f8bab", "rgba(111,139,171,.12)"
    if p5 <= 80:
        if ex is not None and ex < -10:
            return "高位走弱", "#FFA726", "rgba(255,167,38,.18)"
        return "偏高", "#FFA726", "rgba(255,167,38,.13)"
    if ex is not None and ex > 20:
        return "高位强势", "#FF5B5B", "rgba(255,91,91,.20)"
    if ex is not None and ex < -10:
        return "高位走弱", "#FF5B5B", "rgba(255,91,91,.18)"
    return "高位", "#FF5B5B", "rgba(255,91,91,.16)"


def col_pos(v):
    return "#1E88C9" if v <= 20 else "#4FA3D1" if v <= 40 else "#6f8bab" if v <= 60 else "#FFA726" if v <= 80 else "#FF5B5B"


def fmt(v, suf="%"):
    return "—" if v is None else f"{v:+.1f}{suf}" if suf == "%" and v != v else f"{v:.1f}{suf}"


def sgn(v, suf="%"):
    if v is None:
        return '<span class="dim">—</span>'
    c = "#FF5B5B" if v > 0 else "#1EC98B" if v < 0 else "#9ab3cc"
    return f'<span style="color:{c}">{v:+.1f}{suf}</span>'


# ---------------- 明细表 ----------------
def table_rows(grp):
    rows = sorted([i for i in ITEMS if i["group"] == grp], key=lambda x: x["w5"]["pos"])
    out = []
    for it in rows:
        tag, tc, tb = zone_of(it)
        lift = lift_of(it)
        lc = "#FF5B5B" if lift > 5 else "#1EC98B" if lift < -5 else "#9ab3cc"
        bt_s = (f'<b style="color:{lc}">{lift:+.0f}</b>'
                f'<div class="sub" style="font-size:10px">3年−5年</div>')
        bars = it["bars"]
        warn = ' <span class="warn">样本短</span>' if bars < 1100 else ""
        out.append(f"""<tr onclick="showDetail('{it['code']}')">
<td class="nm">{it['name']}{warn}<div class="sub">{it['code']} · {bars}根 · 起{it['start']}</div></td>
<td class="num">{it['last_close']:g}</td>
<td class="num"><b style="color:{col_pos(it['w3']['pos'])}">{it['w3']['pos']:.0f}</b><div class="bar"><i style="width:{it['w3']['pos']}%;background:{col_pos(it['w3']['pos'])}"></i></div></td>
<td class="num"><b style="color:{col_pos(it['w5']['pos'])}">{it['w5']['pos']:.0f}</b><div class="bar"><i style="width:{it['w5']['pos']}%;background:{col_pos(it['w5']['pos'])}"></i></div></td>
<td class="num">{sgn(it['w5']['dd_hi'])}</td>
<td class="num">{sgn(it['ret1y'])}</td>
<td class="num">{sgn(it['excess1y'])}</td>
<td class="num">{sgn(it['ytd'])}</td>
<td class="num" style="font-size:12px">{bt_s}</td>
<td><span class="tag" style="color:{tc};background:{tb}">{tag}</span></td>
</tr>""")
    return "\n".join(out)


tables = "\n".join(f"""<div class="card">
<h2>{g}<span class="cnt">{len([i for i in ITEMS if i['group']==g])} 个标的</span></h2>
<div class="tw"><table>
<thead><tr><th>标的</th><th>现价</th><th>3年位置</th><th>5年位置</th><th>距5年高</th><th>近1年</th><th>超额1年</th><th>年初至今</th><th>抬升度</th><th>状态</th></tr></thead>
<tbody>{table_rows(g)}</tbody></table></div></div>""" for g in GROUPS)

DATA_JS = json.dumps({i["code"]: i for i in ITEMS}, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta name="build-time" content="__NOW__">
<title>A股板块位置温度计</title>
<style>
body{margin:0;background:#0a1929;color:#e6f0fa;font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding:18px 18px 60px}
h1{font-size:22px;margin:0 0 6px;color:#fff}
.meta{color:#6f8bab;font-size:12px;margin-bottom:16px}
.card{background:#102a43;border:1px solid #1c3a5e;border-radius:12px;padding:16px 18px 18px;margin-bottom:18px;box-shadow:0 4px 18px rgba(0,0,0,.25)}
h2{font-size:15px;margin:0 0 12px;color:#fff;font-weight:600}
.cnt{font-size:11px;color:#6f8bab;font-weight:400;margin-left:8px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.tab{background:#0c2238;border:1px solid #1c3a5e;color:#9ab3cc;border-radius:8px;padding:6px 13px;font-size:13px;cursor:pointer}
.tab.on{background:#16395c;color:#fff;border-color:#2a5a8a}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#9ab3cc;margin:0 0 10px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
#chartBox{position:relative;width:100%}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:900px}
th{background:#16395c;color:#cfe0f2;font-weight:600;padding:9px 8px;text-align:right;white-space:nowrap;position:sticky;top:0;font-size:12px}
th:first-child,th:last-child{text-align:left}
td{padding:9px 8px;border-bottom:1px solid #17324e;text-align:right;white-space:nowrap}
td.nm{text-align:left;font-weight:500;cursor:pointer}
td.nm:hover{color:#ffd54f}
tr{cursor:pointer}
tr:hover td{background:#14304d}
.sub{font-size:11px;color:#6f8bab;font-weight:400;margin-top:2px}
.dim{color:#5d7a99}
.num{font-variant-numeric:tabular-nums}
.bar{height:4px;background:#0c2238;border-radius:2px;margin-top:4px;width:64px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:2px}
.tag{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.warn{background:rgba(255,193,7,.16);color:#ffd54f;font-size:10px;padding:1px 5px;border-radius:4px;margin-left:4px;font-weight:600}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}
.ov.on{display:flex}
.modal{background:#102a43;border:1px solid #1c3a5e;border-radius:12px;padding:0;width:min(720px,94vw);max-height:86vh;overflow:auto;box-shadow:0 10px 34px rgba(0,0,0,.5)}
.mh{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #1c3a5e;position:sticky;top:0;background:#102a43}
.mh h3{margin:0;font-size:16px;color:#fff}
.x{background:none;border:none;color:#8fa8c4;font-size:22px;cursor:pointer;line-height:1}
.mb{padding:14px 18px 20px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:14px}
.kv div{background:#0c2238;border:1px solid #1c3a5e;border-radius:8px;padding:9px 11px}
.kv span{display:block;font-size:11px;color:#6f8bab}
.kv b{font-size:15px;color:#e6f0fa}
.foot{color:#5d7a99;font-size:11px;line-height:1.7;margin-top:22px;border-top:1px solid #1c3a5e;padding-top:12px}
</style></head><body>
<div class="wrap">
<h1>A股板块位置温度计</h1>
<div class="meta">数据截至 <b style="color:#ffd54f">__END__</b> ｜ 页面生成 <b style="color:#ffd54f">__NOW__</b>（北京时间）｜ 数据源：腾讯行情（主）/ 新浪（备）｜ 共 __N__ 个标的，基准 __BENCH__</div>

<div class="card">
<h2>位置排行<span class="cnt">按近 __WDEF__ 年区间百分位排序 · 点击任意条形查看逐年明细</span></h2>
<div class="tabs">
<span class="tab on" data-w="w5">近5年</span><span class="tab" data-w="w3">近3年</span>
<span class="tab" data-p="all" style="margin-left:14px">全部</span>__PTABS__
</div>
<div class="legend">
<span><i style="background:#1E88C9"></i>0-20% 冰点</span><span><i style="background:#4FA3D1"></i>20-40% 偏低</span>
<span><i style="background:#6f8bab"></i>40-60% 中性</span><span><i style="background:#FFA726"></i>60-80% 偏高</span>
<span><i style="background:#FF5B5B"></i>80%+ 高位</span>
<span style="color:#ffd54f">虚线 = 沪深300 基准位置</span>
</div>
<div id="chartBox"><canvas id="c" role="img" aria-label="板块位置百分位排行">板块位置排行图</canvas></div>
</div>

__TABLES__

<div class="foot">
<b style="color:#9ab3cc">口径说明</b><br>
· <b>位置%</b> =（现价 − 窗口内最低收盘）÷（窗口内最高收盘 − 最低收盘）×100。0% = 窗口最低点，100% = 窗口最高点。<br>
· <b>抬升度</b> = 3年位置 − 5年位置。正值 = 近 3 年低点高于 5 年内极端低点（未破前低）；负值 = 近 3 年仍在创新低。<b>注意</b>：正值也可能只是"5年前那个坑太深"造成的统计现象（如医药 2022 年低点），必须结合「近 1 年超额」一起看才有效。<br>
· <b>超额1年</b> = 近 1 年自身涨跌幅 − 沪深300 同期涨跌幅。<br>
· <b>关键提醒</b>：位置低 ≠ 该买。宽基指数有长期向上托底，板块没有——行业可能结构性衰退（如地产、白酒）。请结合「底部是否抬升 + 超额收益是否转正」判断，位置低但仍在下移的属下降趋势，不宜机械抄底。<br>
· ETF 采用不复权价格并对份额折算/分红跳空做了后向修正；行业指数为前复权。样本不足 1100 根（约 4.5 年）的标的已标注「样本短」，其 5 年位置参考价值有限。<br>
· 本表仅为公开行情数据的量化整理，不构成任何投资建议。市场有风险，决策需谨慎。
</div>
</div>

<div class="ov" id="ov"><div class="modal">
<div class="mh"><h3 id="mt"></h3><button class="x" onclick="closeD()">×</button></div>
<div class="mb" id="mb"></div></div></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const DATA=__DATAJS__;
const BENCH=__BENCHJS__;
let W='w5', POOL='all', CH=null;

function rowsFor(){
  let a=Object.values(DATA);
  if(POOL==='idx') a=a.filter(x=>x.kind==='idx');
  if(POOL==='etf') a=a.filter(x=>x.kind==='etf');
  a.sort((x,y)=>x[W].pos-y[W].pos);
  return a;
}
const cp=v=>v<=20?'#1E88C9':v<=40?'#4FA3D1':v<=60?'#6f8bab':v<=80?'#FFA726':'#FF5B5B';

function draw(){
  const a=rowsFor(), H=Math.max(320,a.length*24+56);
  document.getElementById('chartBox').style.height=H+'px';
  if(CH) CH.destroy();
  CH=new Chart(document.getElementById('c'),{
    type:'bar',
    data:{labels:a.map(x=>x.name),datasets:[{data:a.map(x=>x[W].pos),
      backgroundColor:a.map(x=>cp(x[W].pos)),borderRadius:3,barPercentage:.74}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      onClick:(e,el)=>{if(el.length) showDetail(a[el[0].index].code);},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{
        const d=rowsFor()[c.dataIndex];
        return ['位置 '+c.parsed.x+'%','距窗高 '+d[W].dd_hi+'%','距窗低 +'+d[W].up_lo+'%','近1年 '+(d.ret1y??'—')+'%','点击查看逐年明细'];}}}},
      scales:{x:{min:0,max:100,grid:{color:'rgba(255,255,255,.06)'},ticks:{color:'#6f8bab',font:{size:11},callback:v=>v+'%'}},
              y:{grid:{display:false},ticks:{color:'#cfe0f2',font:{size:12},autoSkip:false}}}},
    plugins:[{id:'bl',afterDraw(ch){
      const bv=BENCH[W]?BENCH[W].pos:null; if(bv==null) return;
      const {ctx,chartArea:ca,scales:{x}}=ch, px=x.getPixelForValue(bv);
      ctx.save();ctx.strokeStyle='#ffd54f';ctx.setLineDash([5,4]);ctx.lineWidth=1.5;
      ctx.beginPath();ctx.moveTo(px,ca.top);ctx.lineTo(px,ca.bottom);ctx.stroke();
      ctx.setLineDash([]);ctx.fillStyle='#ffd54f';ctx.font='600 11px sans-serif';
      ctx.fillText('沪深300 '+bv+'%',px+4,ca.top+12);ctx.restore();}}]
  });
}
document.querySelectorAll('.tab[data-w]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-w]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); W=t.dataset.w; draw();
  document.querySelector('.cnt').textContent='按近 '+(W==='w5'?'5':'3')+' 年区间百分位排序 · 点击任意条形查看逐年明细';
});
document.querySelectorAll('.tab[data-p]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-p]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); POOL=t.dataset.p; draw();
});

function showDetail(code){
  const d=DATA[code]; if(!d) return;
  document.getElementById('mt').textContent=d.name+' ('+d.code+') · '+d.group;
  const y=d.yearly||[];
  let h='<div class="kv">';
  h+='<div><span>现价</span><b>'+d.last_close+'</b></div>';
  h+='<div><span>3年位置</span><b style="color:'+cp(d.w3.pos)+'">'+d.w3.pos+'%</b></div>';
  h+='<div><span>5年位置</span><b style="color:'+cp(d.w5.pos)+'">'+d.w5.pos+'%</b></div>';
  h+='<div><span>距5年高</span><b style="color:#1EC98B">'+d.w5.dd_hi+'%</b></div>';
  h+='<div><span>距5年低</span><b style="color:#FF5B5B">+'+d.w5.up_lo+'%</b></div>';
  h+='<div><span>近1年</span><b style="color:'+(d.ret1y>0?'#FF5B5B':'#1EC98B')+'">'+(d.ret1y??'—')+'%</b></div>';
  h+='<div><span>超额1年</span><b style="color:'+(d.excess1y>0?'#FF5B5B':'#1EC98B')+'">'+(d.excess1y??'—')+'%</b></div>';
  const lf=(d.w3.pos-d.w5.pos);
  h+='<div><span>抬升度(3y−5y)</span><b style="color:'+(lf>5?'#FF5B5B':lf<-5?'#1EC98B':'#9ab3cc')+'">'+(lf>0?'+':'')+lf.toFixed(0)+'</b></div>';
  h+='<div><span>样本</span><b>'+d.bars+'根</b></div></div>';
  h+='<div class="sub" style="margin-bottom:10px">数据起 '+d.start+' ｜ 5年窗口 '+d.w5.bars+'根（'+d.w5.start+' 起）｜ 窗口最低 '+d.w5.lo+'（'+d.w5.lo_date+'）｜ 窗口最高 '+d.w5.hi+'（'+d.w5.hi_date+'）</div>';
  h+='<table style="min-width:0"><thead><tr><th style="text-align:left">年份</th><th>最低收盘</th><th>出现日</th><th>最高收盘</th><th>出现日</th><th>年内振幅</th></tr></thead><tbody>';
  y.slice().reverse().forEach(v=>{
    const amp=((v.hi/v.lo-1)*100).toFixed(0);
    h+='<tr><td class="nm" style="cursor:default"><b>'+v.year+'</b></td><td class="num" style="color:#1EC98B">'+v.lo.toFixed(3)+'</td><td class="num dim">'+v.lo_d+'</td><td class="num" style="color:#FF5B5B">'+v.hi.toFixed(3)+'</td><td class="num dim">'+v.hi_d+'</td><td class="num">'+amp+'%</td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('mb').innerHTML=h;
  document.getElementById('ov').classList.add('on');
}
function closeD(){document.getElementById('ov').classList.remove('on');}
document.getElementById('ov').onclick=e=>{if(e.target.id==='ov')closeD();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeD();});
draw();
</script></body></html>"""

PTABS = ('<span class="tab" data-p="idx">行业指数</span>'
         '<span class="tab" data-p="etf">主题ETF</span>')
BENCH_JS = json.dumps({k: BENCH.get(k) for k in ("w3", "w5", "ret1y")}, ensure_ascii=False)

HTML = (HTML.replace("__NOW__", NOW)
            .replace("__END__", ITEMS[0]["last_date"] if ITEMS else "—")
            .replace("__N__", str(len(ITEMS)))
            .replace("__BENCH__", BENCH["name"])
            .replace("__WDEF__", "5")
            .replace("__PTABS__", PTABS)
            .replace("__TABLES__", tables)
            .replace("__DATAJS__", DATA_JS)
            .replace("__BENCHJS__", BENCH_JS))

open("sector_report.html", "w", encoding="utf-8").write(HTML)
open("index.html", "w", encoding="utf-8").write(HTML)
print(f"生成完成：{len(ITEMS)} 个标的，{len(GROUPS)} 个分组，{len(HTML):,} 字节")
