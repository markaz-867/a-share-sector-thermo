#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块位置温度计 —— HTML 报表生成
三视图：矩阵（找机会）/ 排行（排序比较）/ 表格（全字段）
新增维度：轮动速度（20/60 日位置变化）、组内排名、月度走势曲线
"""
import json, datetime

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
    """底部抬升度 = 3年位置 − 5年位置"""
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
        if ex is not None and ex > 20:
            return "高位强势", "#FF5B5B", "rgba(255,91,91,.20)"
        if ex is not None and ex < -10:
            return "高位走弱", "#FFA726", "rgba(255,167,38,.18)"
        return "偏高", "#FFA726", "rgba(255,167,38,.13)"
    if ex is not None and ex > 20:
        return "高位强势", "#FF5B5B", "rgba(255,91,91,.20)"
    if ex is not None and ex < -10:
        return "高位走弱", "#FF5B5B", "rgba(255,91,91,.18)"
    return "高位", "#FF5B5B", "rgba(255,91,91,.16)"


# 预计算状态，供前端筛选
ZONE_CNT = {}
for it in ITEMS:
    tag, tc, tb = zone_of(it)
    it["zone"] = tag
    it["zc"] = tc
    it["zb"] = tb
    ZONE_CNT[tag] = ZONE_CNT.get(tag, 0) + 1

# 筛选器顺序：按「冷 → 热」排列，未出现的状态不显示
ZONE_ORDER = ["阴跌寻底", "低位磨底", "低位企稳", "底部反转", "回暖中",
              "偏低", "中性", "偏高", "高位走弱", "高位强势", "高位"]


def col_pos(v):
    return "#1E88C9" if v <= 20 else "#4FA3D1" if v <= 40 else "#6f8bab" if v <= 60 else "#FFA726" if v <= 80 else "#FF5B5B"


def sgn(v, suf="%"):
    if v is None:
        return '<span class="dim">—</span>'
    c = "#FF5B5B" if v > 0 else "#1EC98B" if v < 0 else "#9ab3cc"
    return f'<span style="color:{c}">{v:+.1f}{suf}</span>'


def sgn_raw(v, suf=""):
    if v is None:
        return '<span class="dim">—</span>'
    c = "#FF5B5B" if v > 0 else "#1EC98B" if v < 0 else "#9ab3cc"
    return f'<span style="color:{c}">{v:+.1f}{suf}</span>'


# ---------------- 表格视图（分组折叠） ----------------
def table_rows(grp):
    rows = sorted([i for i in ITEMS if i["group"] == grp], key=lambda x: x["w5"]["pos"])
    out = []
    for it in rows:
        tag, tc, tb = zone_of(it)
        lift = lift_of(it)
        lc = "#FF5B5B" if lift > 5 else "#1EC98B" if lift < -5 else "#9ab3cc"
        bars = it["bars"]
        warn = ' <span class="warn">样本短</span>' if bars < 1100 else ""
        mom = it.get("mom") or {}
        rk = f'{it.get("rank","—")}<span class="dim">/{it.get("g_size","—")}</span>'
        out.append(f"""<tr onclick="showDetail('{it['code']}')">
<td class="nm">{it['name']}{warn}<div class="sub">{it['code']} · {bars}根 · 起{it['start']}</div></td>
<td class="num">{it['last_close']:g}</td>
<td class="num"><b style="color:{col_pos(it['w3']['pos'])}">{it['w3']['pos']:.0f}</b><div class="bar"><i style="width:{it['w3']['pos']}%;background:{col_pos(it['w3']['pos'])}"></i></div></td>
<td class="num"><b style="color:{col_pos(it['w5']['pos'])}">{it['w5']['pos']:.0f}</b><div class="bar"><i style="width:{it['w5']['pos']}%;background:{col_pos(it['w5']['pos'])}"></i></div></td>
<td class="num" style="font-size:12px">{rk}</td>
<td class="num" style="font-size:12px">{sgn_raw(mom.get('d20'))}</td>
<td class="num" style="font-size:12px">{sgn_raw(mom.get('d60'))}</td>
<td class="num">{sgn(it['w5']['dd_hi'])}</td>
<td class="num">{sgn(it['ret1y'])}</td>
<td class="num">{sgn(it['excess1y'])}</td>
<td class="num">{sgn(it['ytd'])}</td>
<td class="num" style="font-size:12px"><b style="color:{lc}">{lift:+.0f}</b></td>
<td><span class="tag" style="color:{tc};background:{tb}">{tag}</span></td>
</tr>""")
    return "\n".join(out)


def group_summary(grp):
    lst = [i for i in ITEMS if i["group"] == grp]
    if not lst:
        return ""
    p5 = sum(x["w5"]["pos"] for x in lst) / len(lst)
    ex = [x["excess1y"] for x in lst if x.get("excess1y") is not None]
    m20 = [x["mom"]["d20"] for x in lst if (x.get("mom") or {}).get("d20") is not None]
    sex = sum(ex) / len(ex) if ex else None
    sm20 = sum(m20) / len(m20) if m20 else None
    lo = min(lst, key=lambda x: x["w5"]["pos"])
    hi = max(lst, key=lambda x: x["w5"]["pos"])
    return (f'<span class="gs">均 <b style="color:{col_pos(p5)}">{p5:.0f}%</b></span>'
            f'<span class="gs">超额 {sgn(round(sex,1)) if sex is not None else "—"}</span>'
            f'<span class="gs">轮动 {sgn_raw(round(sm20,1)) if sm20 is not None else "—"}</span>'
            f'<span class="gs dim">最冷 {lo["name"]} {lo["w5"]["pos"]:.0f}% ｜ 最热 {hi["name"]} {hi["w5"]["pos"]:.0f}%</span>')


tables = "\n".join(f"""<div class="card grp">
<div class="gh" onclick="tog('g{GROUPS.index(g)}')">
<span class="ar" id="ar{GROUPS.index(g)}">▸</span>
<h2 style="margin:0">{g}<span class="cnt">{len([i for i in ITEMS if i['group']==g])} 个标的</span></h2>
<div class="gsum">{group_summary(g)}</div>
</div>
<div class="gbody" id="g{GROUPS.index(g)}" style="display:none">
<div class="tw"><table>
<thead><tr><th>标的</th><th>现价</th><th>3年位置</th><th>5年位置</th><th>组内</th><th>轮动20日</th><th>轮动60日</th><th>距5年高</th><th>近1年</th><th>超额1年</th><th>年初至今</th><th>抬升度</th><th>状态</th></tr></thead>
<tbody>{table_rows(g)}</tbody></table></div></div></div>""" for g in GROUPS)

CHIPS = "".join(
    f'<span class="chip" data-z="{z}">{z}<b>{ZONE_CNT[z]}</b></span>'
    for z in ZONE_ORDER if z in ZONE_CNT)

DATA_JS = json.dumps({i["code"]: i for i in ITEMS}, ensure_ascii=False)
BENCH_JS = json.dumps({k: BENCH.get(k) for k in ("w3", "w5", "ret1y")}, ensure_ascii=False)

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
.card{background:#102a43;border:1px solid #1c3a5e;border-radius:12px;padding:16px 18px 18px;margin-bottom:14px;box-shadow:0 4px 18px rgba(0,0,0,.25)}
h2{font-size:15px;margin:0 0 12px;color:#fff;font-weight:600}
.cnt{font-size:11px;color:#6f8bab;font-weight:400;margin-left:8px}
.ctl{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.cg{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.clab{font-size:11px;color:#5d7a99;margin-right:2px}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tab{background:#0c2238;border:1px solid #1c3a5e;color:#9ab3cc;border-radius:8px;padding:6px 13px;font-size:13px;cursor:pointer;white-space:nowrap}
.tab.on{background:#16395c;color:#fff;border-color:#2a5a8a}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{background:#0c2238;border:1px solid #1c3a5e;color:#9ab3cc;border-radius:20px;padding:4px 11px;font-size:12px;cursor:pointer;white-space:nowrap}
.chip b{color:#5d7a99;font-weight:400;margin-left:5px;font-size:11px}
.chip.on{background:#16395c;color:#fff;border-color:#2a5a8a}
.chip.on b{color:#9ab3cc}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#9ab3cc;margin:0 0 10px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
#chartBox,#mxBox{position:relative;width:100%}
.view{display:none}
.view.on{display:block}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:980px}
th{background:#16395c;color:#cfe0f2;font-weight:600;padding:9px 8px;text-align:right;white-space:nowrap;position:sticky;top:0;font-size:12px}
th:first-child,th:last-child{text-align:left}
td{padding:9px 8px;border-bottom:1px solid #17324e;text-align:right;white-space:nowrap}
td.nm{text-align:left;font-weight:500}
tr{cursor:pointer}
tr:hover td{background:#14304d}
.sub{font-size:11px;color:#6f8bab;font-weight:400;margin-top:2px}
.dim{color:#5d7a99}
.num{font-variant-numeric:tabular-nums}
.bar{height:4px;background:#0c2238;border-radius:2px;margin-top:4px;width:64px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:2px}
.tag{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.warn{background:rgba(255,193,7,.16);color:#ffd54f;font-size:10px;padding:1px 5px;border-radius:4px;margin-left:4px;font-weight:600}
.gh{display:flex;align-items:center;gap:10px;cursor:pointer;flex-wrap:wrap}
.gh:hover h2{color:#ffd54f}
.ar{color:#5d7a99;font-size:13px;transition:transform .15s;display:inline-block}
.ar.on{transform:rotate(90deg)}
.gsum{display:flex;gap:14px;flex-wrap:wrap;margin-left:auto;font-size:12px;color:#9ab3cc}
.gs b{font-variant-numeric:tabular-nums}
.gbody{padding-top:14px}
.mb-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}
.ov.on{display:flex}
.modal{background:#102a43;border:1px solid #1c3a5e;border-radius:12px;padding:0;width:min(760px,94vw);max-height:88vh;overflow:auto;box-shadow:0 10px 34px rgba(0,0,0,.5)}
.mh{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #1c3a5e;position:sticky;top:0;background:#102a43}
.mh h3{margin:0;font-size:16px;color:#fff}
.x{background:none;border:none;color:#8fa8c4;font-size:22px;cursor:pointer;line-height:1}
.mb{padding:14px 18px 20px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));gap:9px;margin-bottom:14px}
.kv div{background:#0c2238;border:1px solid #1c3a5e;border-radius:8px;padding:8px 10px}
.kv span{display:block;font-size:11px;color:#6f8bab}
.kv b{font-size:15px;color:#e6f0fa}
.foot{color:#5d7a99;font-size:11px;line-height:1.7;margin-top:22px;border-top:1px solid #1c3a5e;padding-top:12px}
.empty{color:#6f8bab;font-size:13px;padding:30px 0;text-align:center}
</style></head><body>
<div class="wrap">
<h1>A股板块位置温度计</h1>
<div class="meta">数据截至 <b style="color:#ffd54f">__END__</b> ｜ 页面生成 <b style="color:#ffd54f">__NOW__</b>（北京时间）｜ 数据源：腾讯行情（主）/ 新浪（备）｜ 共 __N__ 个标的，基准 __BENCH__</div>

<div class="card">
<div class="ctl">
  <div class="cg"><span class="clab">视图</span>
    <span class="tab on" data-v="mx">矩阵</span>
    <span class="tab" data-v="rk">排行</span>
    <span class="tab" data-v="tb">表格</span>
  </div>
  <div class="cg"><span class="clab">窗口</span>
    <span class="tab on" data-w="w5">近5年</span><span class="tab" data-w="w3">近3年</span>
  </div>
  <div class="cg"><span class="clab">类型</span>
    <span class="tab on" data-p="all">全部</span><span class="tab" data-p="idx">行业指数</span><span class="tab" data-p="etf">主题ETF</span>
  </div>
  <div class="cg" id="ycg"><span class="clab">纵轴</span>
    <span class="tab on" data-y="ex">近1年超额</span><span class="tab" data-y="m60">轮动60日</span><span class="tab" data-y="m20">轮动20日</span>
  </div>
</div>
<div class="ctl"><div class="cg"><span class="clab">状态筛选</span>
  <span class="chip on" data-z="">全部<b>__N__</b></span>__CHIPS__
</div></div>
<div class="legend" id="lg"></div>
<div id="nbar" class="sub" style="margin-bottom:8px"></div>

<div class="view on" id="v-mx">
  <div id="mxBox"><canvas id="mx" role="img" aria-label="板块位置与超额收益矩阵散点图">板块矩阵图</canvas></div>
  <div class="sub" style="margin-top:8px">点击任意圆点查看该板块的走势曲线、轮动速度与逐年低高点明细</div>
</div>

<div class="view" id="v-rk">
  <div id="chartBox"><canvas id="c" role="img" aria-label="板块位置百分位排行">板块位置排行图</canvas></div>
</div>

<div class="view" id="v-tb">
  <div class="cg" style="margin-bottom:12px">
    <span class="tab" onclick="togAll(true)">全部展开</span><span class="tab" onclick="togAll(false)">全部收起</span>
  </div>
  __TABLES__
</div>
</div>

<div class="foot">
<b style="color:#9ab3cc">口径说明</b><br>
· <b>位置%</b> =（现价 − 窗口内最低收盘）÷（窗口内最高收盘 − 最低收盘）×100。0% = 窗口最低点，100% = 窗口最高点。<br>
· <b>轮动速度</b> = 当前位置% − N 个交易日之前的位置%（均按当时可见的滚动窗口重算）。<b>正值 = 位置在往上爬，负值 = 在往下掉。</b>20 日看短期方向，60 日看中期趋势。两者同号 = 趋势稳定；20 日正、60 日负 = 短期反弹但中期仍下行（典型如煤炭：20日 +19.7、60日 −13.4）。<br>
· <b>组内排名</b> = 该标的在自己所属分组内按 5 年位置的排名（1 = 组内位置最高）。操作层面常比绝对位置更直接。<br>
· <b>抬升度</b> = 3年位置 − 5年位置。正值 = 近 3 年低点高于 5 年内极端低点（未破前低）；负值 = 近 3 年仍在创新低。<b>注意</b>：正值也可能只是"5年前那个坑太深"造成的统计现象（如医药 2022 年低点），必须结合「近 1 年超额」一起看才有效。<br>
· <b>超额1年</b> = 近 1 年自身涨跌幅 − 沪深300 同期涨跌幅。<br>
· <b>矩阵四象限</b>（纵轴=超额）：左上 <b style="color:#1EC98B">底部反转</b>（位置低且已跑赢，最稀缺）｜右上 <b style="color:#FF5B5B">高位强势</b>（位置高且仍在跑赢）｜左下 <b style="color:#8fa8c4">阴跌寻底</b>（位置低且继续跑输，慎抄底）｜右下 <b style="color:#FFA726">高位走弱</b>（位置高但已跑输，警惕回落）。<br>
· <b>关键提醒</b>：位置低 ≠ 该买。宽基指数有长期向上托底，板块没有——行业可能结构性衰退（如地产、白酒）。请结合「底部是否抬升 + 超额收益是否转正 + 轮动速度是否转正」三重确认，位置低但仍在下移的属下降趋势，不宜机械抄底。<br>
· ETF 采用不复权价格并对份额折算/分红跳空做了后向修正；行业指数为前复权。样本不足 1100 根（约 4.5 年）的标的已标注「样本短」，其 5 年位置参考价值有限。走势曲线为月度采样（每 21 个交易日取一点）。<br>
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
let W='w5', POOL='all', VIEW='mx', ZONE='', YAX='ex', CH=null, MX=null;
const YDEF={ex:{k:'excess1y',t:'近1年超额',u:'%',q:['底部反转','高位强势','阴跌寻底','高位走弱']},
            m60:{k:'d60',t:'轮动60日',u:'',q:['低位爬升','高位加速','低位下坠','高位回落']},
            m20:{k:'d20',t:'轮动20日',u:'',q:['低位反弹','高位冲高','低位探底','高位跳水']}};

function yv(d){const k=YDEF[YAX].k; return YAX==='ex'?d[k]:(d.mom?d.mom[k]:null);}
function rowsFor(){
  let a=Object.values(DATA);
  if(POOL==='idx') a=a.filter(x=>x.kind==='idx');
  if(POOL==='etf') a=a.filter(x=>x.kind==='etf');
  if(ZONE) a=a.filter(x=>x.zone===ZONE);
  return a;
}
const cp=v=>v<=20?'#1E88C9':v<=40?'#4FA3D1':v<=60?'#6f8bab':v<=80?'#FFA726':'#FF5B5B';
const zc=t=>{const m={'阴跌寻底':'#8fa8c4','低位磨底':'#4FA3D1','低位企稳':'#5DCAA5','底部反转':'#1EC98B',
  '回暖中':'#5DCAA5','偏低':'#4FA3D1','中性':'#6f8bab','偏高':'#FFA726','高位走弱':'#FF5B5B','高位强势':'#FF5B5B','高位':'#FF5B5B'};
  return m[t]||'#6f8bab';};

function drawLegend(){
  const q=YDEF[YAX].q;
  document.getElementById('lg').innerHTML=
   (VIEW==='mx'
     ? '<span><i style="background:#1EC98B"></i>'+q[0]+'（低+强）</span><span><i style="background:#FF5B5B"></i>'+q[1]+'（高+强）</span>'
       +'<span><i style="background:#8fa8c4"></i>'+q[2]+'（低+弱）</span><span><i style="background:#FFA726"></i>'+q[3]+'（高+弱）</span>'
       +'<span style="color:#ffd54f">十字虚线 = 位置50% / '+YDEF[YAX].t+' 0</span>'
     : '<span><i style="background:#1E88C9"></i>0-20% 冰点</span><span><i style="background:#4FA3D1"></i>20-40% 偏低</span>'
       +'<span><i style="background:#6f8bab"></i>40-60% 中性</span><span><i style="background:#FFA726"></i>60-80% 偏高</span>'
       +'<span><i style="background:#FF5B5B"></i>80%+ 高位</span><span style="color:#ffd54f">虚线 = 沪深300 基准位置</span>');
}

function drawMX(){
  const a=rowsFor().filter(x=>yv(x)!==null&&yv(x)!==undefined);
  document.getElementById('mxBox').style.height=Math.max(400,Math.min(620,window.innerHeight*0.72))+'px';
  if(MX){MX.destroy();MX=null;}
  if(!a.length){document.getElementById('nbar').textContent='当前筛选无数据';return;}
  const pts=a.map(d=>({x:d[W].pos,y:yv(d),code:d.code,name:d.name,zone:d.zone}));
  MX=new Chart(document.getElementById('mx'),{
    type:'scatter',
    data:{datasets:[{data:pts,pointRadius:6,pointHoverRadius:9,
      backgroundColor:pts.map(p=>zc(p.zone)),borderColor:'rgba(10,25,41,.9)',borderWidth:1}]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      onClick:(e,el)=>{if(el.length) showDetail(pts[el[0].index].code);},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{
        const p=pts[c.dataIndex],d=DATA[p.code];
        return [d.name+' · '+d.group,'位置 '+p.x.toFixed(1)+'%','超额1年 '+(d.excess1y??'—')+'%',
                '轮动20日 '+(d.mom&&d.mom.d20!=null?d.mom.d20:'—')+' ｜ 60日 '+(d.mom&&d.mom.d60!=null?d.mom.d60:'—'),
                '状态 '+p.zone,'点击查看明细'];}}}},
      scales:{x:{min:0,max:100,title:{display:true,text:'5年位置 %（0=最低 100=最高）',color:'#9ab3cc',font:{size:12}},
                 grid:{color:'rgba(255,255,255,.06)'},ticks:{color:'#6f8bab',font:{size:11},callback:v=>v+'%'}},
             y:{title:{display:true,text:YDEF[YAX].t+YDEF[YAX].u,color:'#9ab3cc',font:{size:12}},
                grid:{color:'rgba(255,255,255,.06)'},ticks:{color:'#6f8bab',font:{size:11}}}}},
    plugins:[{id:'quad',beforeDraw(ch){
      const {ctx,chartArea:ca,scales:{x,y}}=ch, xm=x.getPixelForValue(50), ym=y.getPixelForValue(0);
      ctx.save();
      ctx.fillStyle='rgba(30,201,139,.05)';ctx.fillRect(ca.left,ca.top,xm-ca.left,ym-ca.top);
      ctx.fillStyle='rgba(255,91,91,.05)';ctx.fillRect(xm,ca.top,ca.right-xm,ym-ca.top);
      ctx.fillStyle='rgba(143,168,196,.04)';ctx.fillRect(ca.left,ym,xm-ca.left,ca.bottom-ym);
      ctx.fillStyle='rgba(255,167,38,.05)';ctx.fillRect(xm,ym,ca.right-xm,ca.bottom-ym);
      ctx.strokeStyle='rgba(255,213,79,.45)';ctx.setLineDash([5,4]);ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(xm,ca.top);ctx.lineTo(xm,ca.bottom);ctx.stroke();
      ctx.beginPath();ctx.moveTo(ca.left,ym);ctx.lineTo(ca.right,ym);ctx.stroke();
      ctx.setLineDash([]);ctx.fillStyle='rgba(255,213,79,.75)';ctx.font='600 11px sans-serif';
      const q=YDEF[YAX].q;
      ctx.fillText(q[0],ca.left+8,ca.top+14);
      ctx.textAlign='right';ctx.fillText(q[1],ca.right-8,ca.top+14);
      ctx.fillText(q[3],ca.right-8,ca.bottom-8);ctx.textAlign='left';
      ctx.fillText(q[2],ca.left+8,ca.bottom-8);
      ctx.restore();}}]
  });
}

function drawRank(){
  const a=rowsFor().sort((x,y)=>x[W].pos-y[W].pos);
  const H=Math.max(320,a.length*24+56);
  document.getElementById('chartBox').style.height=H+'px';
  if(CH) CH.destroy();
  if(!a.length){CH=null;return;}
  CH=new Chart(document.getElementById('c'),{
    type:'bar',
    data:{labels:a.map(x=>x.name),datasets:[{data:a.map(x=>x[W].pos),
      backgroundColor:a.map(x=>cp(x[W].pos)),borderRadius:3,barPercentage:.74}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:false,
      onClick:(e,el)=>{if(el.length) showDetail(a[el[0].index].code);},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{
        const d=a[c.dataIndex],m=d.mom||{};
        return ['位置 '+c.parsed.x+'%','距窗高 '+d[W].dd_hi+'%','近1年 '+(d.ret1y??'—')+'%',
                '轮动20日 '+(m.d20??'—')+' ｜ 60日 '+(m.d60??'—'),'状态 '+d.zone,'点击查看明细'];}}}},
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

function render(){
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.id==='v-'+VIEW));
  document.getElementById('ycg').style.display=VIEW==='mx'?'':'none';
  const a=rowsFor();
  document.getElementById('nbar').textContent='当前显示 '+a.length+' 个标的'
    +(ZONE?'（状态：'+ZONE+'）':'')+' · 基准沪深300 位置 '+BENCH[W].pos+'%';
  drawLegend();
  // 容器刚由 display:none 转为可见时，Chart.js 量得到尺寸却不自动重绘，
  // 故延迟一帧绘制后再显式 resize 一次，否则图上只有坐标轴没有内容
  if(VIEW==='mx') setTimeout(()=>{drawMX(); setTimeout(()=>{if(MX)MX.resize();},120);},40);
  if(VIEW==='rk') setTimeout(()=>{drawRank(); setTimeout(()=>{if(CH)CH.resize();},120);},40);
}

document.querySelectorAll('.tab[data-v]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-v]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); VIEW=t.dataset.v; render();});
document.querySelectorAll('.tab[data-w]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-w]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); W=t.dataset.w; render();});
document.querySelectorAll('.tab[data-p]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-p]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); POOL=t.dataset.p; render();});
document.querySelectorAll('.tab[data-y]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab[data-y]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); YAX=t.dataset.y; render();});
document.querySelectorAll('.chip[data-z]').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.chip[data-z]').forEach(z=>z.classList.remove('on'));
  t.classList.add('on'); ZONE=t.dataset.z; render();});

function tog(id){
  const b=document.getElementById(id), a=document.getElementById('ar'+id.slice(1));
  const open=b.style.display!=='none';
  b.style.display=open?'none':'block'; a.classList.toggle('on',open);
}
function togAll(open){
  document.querySelectorAll('.gbody').forEach(b=>b.style.display=open?'block':'none');
  document.querySelectorAll('.ar').forEach(a=>a.classList.toggle('on',open));
}

function sparkSVG(d){
  const s=d.series; if(!s||!s.c||s.c.length<2) return '';
  const v=s.c.map(x=>x/100), W=680, H=190, PL=52, PR=54, PT=16, PB=26;
  const lo=Math.min.apply(null,v), hi=Math.max.apply(null,v);
  const wlo=d.w5.lo, whi=d.w5.hi;
  const ymin=Math.min(lo,wlo), ymax=Math.max(hi,whi), sp=(ymax-ymin)*0.06||1;
  const Y=t=>PT+(ymax+sp-t)/(ymax-ymin+2*sp)*(H-PT-PB);
  const X=i=>PL+i/(v.length-1)*(W-PL-PR);
  let p=''; v.forEach((c,i)=>{p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(c).toFixed(1)+' ';});
  const area=p+'L'+X(v.length-1).toFixed(1)+' '+(H-PB)+' L'+X(0).toFixed(1)+' '+(H-PB)+' Z';
  let g='';
  for(let t=0;t<=4;t++){const y=PT+t/4*(H-PT-PB);
    g+='<line x1="'+PL+'" y1="'+y+'" x2="'+(W-PR)+'" y2="'+y+'" stroke="rgba(255,255,255,.06)"/>';}
  [['5年高',whi,'#FF5B5B'],['5年低',wlo,'#1EC98B']].forEach(([lb,val,cc])=>{
    if(val<ymin||val>ymax) return;
    const y=Y(val);
    g+='<line x1="'+PL+'" y1="'+y.toFixed(1)+'" x2="'+(W-PR)+'" y2="'+y.toFixed(1)+'" stroke="'+cc+'" stroke-width="1" stroke-dasharray="4 4" opacity=".7"/>';
    g+='<text x="'+(W-PR+4)+'" y="'+(y+3.5).toFixed(1)+'" fill="'+cc+'" font-size="10">'+lb+'</text>';});
  const cx=X(v.length-1), cy=Y(v[v.length-1]);
  let out='<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="display:block">';
  out+='<defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">'
     +'<stop offset="0%" stop-color="#4FA3D1" stop-opacity=".28"/><stop offset="100%" stop-color="#4FA3D1" stop-opacity="0"/></linearGradient></defs>';
  out+=g+'<path d="'+area+'" fill="url(#g1)"/><path d="'+p+'" fill="none" stroke="#4FA3D1" stroke-width="1.8" stroke-linejoin="round"/>';
  out+='<circle cx="'+cx.toFixed(1)+'" cy="'+cy.toFixed(1)+'" r="4" fill="#ffd54f" stroke="#0a1929" stroke-width="1.5"/>';
  const n=s.d.length;
  [0,Math.floor(n/2),n-1].forEach(i=>{
    const xx=X(i), anc=i===0?'start':i===n-1?'end':'middle';
    out+='<text x="'+xx.toFixed(1)+'" y="'+(H-8)+'" fill="#6f8bab" font-size="10" text-anchor="'+anc+'">'+s.d[i]+'</text>';});
  out+='<text x="'+(PL-6)+'" y="'+(PT+8)+'" fill="#6f8bab" font-size="10" text-anchor="end">'+ymax.toFixed(2)+'</text>';
  out+='<text x="'+(PL-6)+'" y="'+(H-PB)+'" fill="#6f8bab" font-size="10" text-anchor="end">'+ymin.toFixed(2)+'</text>';
  out+='</svg>';
  return out;
}

function showDetail(code){
  const d=DATA[code]; if(!d) return;
  document.getElementById('mt').textContent=d.name+' ('+d.code+') · '+d.group;
  const m=d.mom||{}, y=d.yearly||[], lf=(d.w3.pos-d.w5.pos);
  let h='<div class="kv">';
  h+='<div><span>现价</span><b>'+d.last_close+'</b></div>';
  h+='<div><span>3年位置</span><b style="color:'+cp(d.w3.pos)+'">'+d.w3.pos+'%</b></div>';
  h+='<div><span>5年位置</span><b style="color:'+cp(d.w5.pos)+'">'+d.w5.pos+'%</b></div>';
  h+='<div><span>组内排名</span><b>'+(d.rank??'—')+'<span style="color:#5d7a99;font-size:12px">/'+d.g_size+'</span></b></div>';
  h+='<div><span>轮动20日</span><b style="color:'+(m.d20>0?'#FF5B5B':m.d20<0?'#1EC98B':'#9ab3cc')+'">'+(m.d20==null?'—':(m.d20>0?'+':'')+m.d20)+'</b></div>';
  h+='<div><span>轮动60日</span><b style="color:'+(m.d60>0?'#FF5B5B':m.d60<0?'#1EC98B':'#9ab3cc')+'">'+(m.d60==null?'—':(m.d60>0?'+':'')+m.d60)+'</b></div>';
  h+='<div><span>近1年</span><b style="color:'+(d.ret1y>0?'#FF5B5B':'#1EC98B')+'">'+(d.ret1y??'—')+'%</b></div>';
  h+='<div><span>超额1年</span><b style="color:'+(d.excess1y>0?'#FF5B5B':'#1EC98B')+'">'+(d.excess1y??'—')+'%</b></div>';
  h+='<div><span>抬升度</span><b style="color:'+(lf>5?'#FF5B5B':lf<-5?'#1EC98B':'#9ab3cc')+'">'+(lf>0?'+':'')+lf.toFixed(0)+'</b></div>';
  h+='<div><span>样本</span><b>'+d.bars+'根</b></div></div>';
  h+='<div style="display:flex;align-items:center;gap:10px;margin:0 0 10px">'
   + '<span class="tag" style="color:'+d.zc+';background:'+d.zb+'">'+d.zone+'</span>'
   + '<span class="sub" style="margin:0">数据起 '+d.start+' ｜ 5年窗口 '+d.w5.bars+'根（'+d.w5.start+' 起）｜ 低 '+d.w5.lo+'（'+d.w5.lo_date+'）｜ 高 '+d.w5.hi+'（'+d.w5.hi_date+'）</span></div>';
  h+='<div class="sub" style="margin:0 0 4px">5 年走势（月度采样 · 黄点=最新收盘 · 虚线=窗口高低）</div>';
  h+='<div style="background:#0c2238;border:1px solid #1c3a5e;border-radius:8px;padding:6px 4px 2px;margin-bottom:14px">'+sparkSVG(d)+'</div>';
  h+='<div class="sub" style="margin:0 0 6px">逐年低点 / 高点（收盘口径）</div>';
  h+='<table style="min-width:0"><thead><tr><th style="text-align:left">年份</th><th>最低收盘</th><th>出现日</th><th>最高收盘</th><th>出现日</th><th>年内振幅</th></tr></thead><tbody>';
  y.slice().reverse().forEach(v=>{
    const amp=((v.hi/v.lo-1)*100).toFixed(0);
    h+='<tr style="cursor:default"><td class="nm" style="cursor:default"><b>'+v.year+'</b></td><td class="num" style="color:#1EC98B">'+v.lo.toFixed(3)+'</td><td class="num dim">'+v.lo_d+'</td><td class="num" style="color:#FF5B5B">'+v.hi.toFixed(3)+'</td><td class="num dim">'+v.hi_d+'</td><td class="num">'+amp+'%</td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('mb').innerHTML=h;
  document.getElementById('ov').classList.add('on');
}
function closeD(){document.getElementById('ov').classList.remove('on');}
document.getElementById('ov').onclick=e=>{if(e.target.id==='ov')closeD();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeD();});
render();
</script></body></html>"""

HTML = (HTML.replace("__NOW__", NOW)
            .replace("__END__", ITEMS[0]["last_date"] if ITEMS else "—")
            .replace("__N__", str(len(ITEMS)))
            .replace("__BENCH__", BENCH["name"])
            .replace("__CHIPS__", CHIPS)
            .replace("__TABLES__", tables)
            .replace("__DATAJS__", DATA_JS)
            .replace("__BENCHJS__", BENCH_JS))

open("sector_report.html", "w", encoding="utf-8").write(HTML)
open("index.html", "w", encoding="utf-8").write(HTML)
print(f"生成完成：{len(ITEMS)} 个标的，{len(GROUPS)} 个分组，{len(HTML):,} 字节")
print("状态分布:", dict(sorted(ZONE_CNT.items(), key=lambda x: -x[1])))
