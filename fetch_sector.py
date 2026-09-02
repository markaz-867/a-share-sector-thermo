#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块位置温度计 —— 数据抓取与指标计算
标的池：中证/国证行业指数（长历史） + 主题 ETF（细分覆盖）
数据源：腾讯（主） / 新浪（备）。东财在 GitHub Actions 云 IP 被封，故不作为主源。

输出 sector_data.json
"""
import json, subprocess, sys, time, datetime

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# (分组, 代码, 名称, 类型)  类型 idx=指数(用前复权) / etf=ETF(用不复权,近5年更长)
POOL = [
    # ---------- A. 中证全指一级行业（2011 起，15 年） ----------
    ("中证一级行业", "000986", "全指能源",   "idx"),
    ("中证一级行业", "000987", "全指材料",   "idx"),
    ("中证一级行业", "000988", "全指工业",   "idx"),
    ("中证一级行业", "000989", "全指可选",   "idx"),
    ("中证一级行业", "000990", "全指消费",   "idx"),
    ("中证一级行业", "000991", "全指信息",   "idx"),
    ("中证一级行业", "000992", "全指医药",   "idx"),
    ("中证一级行业", "000993", "全指金融",   "idx"),
    ("中证一级行业", "000994", "全指公用",   "idx"),
    ("中证一级行业", "000995", "全指电信",   "idx"),
    # ---------- B. 细分行业/主题指数（深证 399xxx，2015 起） ----------
    ("细分行业指数", "399975", "证券公司",   "idx"),
    ("细分行业指数", "399986", "中证银行",   "idx"),
    ("细分行业指数", "399997", "中证白酒",   "idx"),
    ("细分行业指数", "399989", "中证医疗",   "idx"),
    ("细分行业指数", "399808", "中证新能",   "idx"),
    ("细分行业指数", "399965", "800地产",    "idx"),
    ("细分行业指数", "399998", "中证煤炭",   "idx"),
    ("细分行业指数", "399441", "生物医药",   "idx"),
    ("细分行业指数", "399395", "国证有色",   "idx"),
    ("细分行业指数", "399707", "中证畜牧",   "idx"),
    # ---------- C. 主题 ETF：AI / 半导体 / 算力 ----------
    ("AI·半导体·算力", "512760", "芯片ETF",       "etf"),
    ("AI·半导体·算力", "512480", "半导体ETF",     "etf"),
    ("AI·半导体·算力", "588200", "科创芯片ETF",   "etf"),
    ("AI·半导体·算力", "159819", "人工智能ETF",   "etf"),
    ("AI·半导体·算力", "516510", "云计算ETF",     "etf"),
    ("AI·半导体·算力", "515400", "大数据ETF",     "etf"),
    ("AI·半导体·算力", "515880", "通信ETF",       "etf"),
    ("AI·半导体·算力", "159583", "通信设备ETF",   "etf"),
    ("AI·半导体·算力", "562500", "机器人ETF",     "etf"),
    ("AI·半导体·算力", "516010", "游戏ETF",       "etf"),
    ("AI·半导体·算力", "515000", "科技ETF",       "etf"),
    ("AI·半导体·算力", "159998", "计算机ETF",     "etf"),
    ("AI·半导体·算力", "159851", "金融科技ETF",   "etf"),
    # ---------- D. 主题 ETF：新能源 ----------
    ("新能源", "515790", "光伏ETF",     "etf"),
    ("新能源", "516160", "新能源ETF",   "etf"),
    ("新能源", "159755", "电池ETF",     "etf"),
    ("新能源", "515030", "新能源车ETF", "etf"),
    # ---------- E. 主题 ETF：医药 ----------
    ("医药", "512010", "医药ETF",       "etf"),
    ("医药", "512170", "医疗ETF",       "etf"),
    ("医药", "159992", "创新药ETF",     "etf"),
    ("医药", "513120", "港股创新药ETF", "etf"),
    # ---------- F. 主题 ETF：消费 ----------
    ("消费", "159928", "消费ETF", "etf"),
    ("消费", "512690", "酒ETF",   "etf"),
    ("消费", "159865", "养殖ETF", "etf"),
    # ---------- G. 主题 ETF：金融地产 ----------
    ("金融地产", "512880", "证券ETF",   "etf"),
    ("金融地产", "512800", "银行ETF",   "etf"),
    ("金融地产", "512200", "房地产ETF", "etf"),
    # ---------- H. 主题 ETF：资源周期 ----------
    ("资源周期", "515220", "煤炭ETF",     "etf"),
    ("资源周期", "512400", "有色金属ETF", "etf"),
    ("资源周期", "518880", "黄金ETF",     "etf"),
    ("资源周期", "159611", "电力ETF",     "etf"),
    ("资源周期", "516150", "稀土ETF",     "etf"),
    # ---------- I. 主题 ETF：军工 / 宽基 ----------
    ("军工·宽基", "512660", "军工ETF",     "etf"),
    ("军工·宽基", "510300", "沪深300ETF",  "etf"),
    ("军工·宽基", "510500", "中证500ETF",  "etf"),
    ("军工·宽基", "512100", "中证1000ETF", "etf"),
]

BENCH = ("000300", "沪深300")   # 基准

N_DAYS = 1300        # 请求根数（约 5.2 年）
W3, W5 = 730, 1250   # 近3年 / 近5年窗口（交易日）
Y1 = 251             # 近1年


def sym_of(code):
    """5/6 开头 → 沪市 ETF；000xxx 中证指数 → 沪市行情；其余（399/1xx）→ 深市"""
    return ("sh" if (code[0] in "56" or code.startswith("000")) else "sz") + code


def curl(url, timeout=30):
    try:
        r = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", UA, url],
                           capture_output=True, text=True)
        return r.stdout
    except Exception:
        return ""


def fetch_tx(sym, n=N_DAYS, fq="qfq"):
    """腾讯日 K。fq='qfq' 前复权（指数用）；fq='' 不复权（ETF 用，长度更长）"""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,,,{n},{fq}"
    try:
        d = json.loads(curl(url))
    except Exception:
        return None
    dd = d.get("data")
    if not isinstance(dd, dict):
        return None
    node = dd.get(sym) or {}
    k = node.get("qfqday") or node.get("day") or []
    return k or None


def fetch_sina(sym, n=N_DAYS):
    """新浪备用源"""
    url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           f"CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}")
    t = curl(url).strip()
    if not t or t == "null":
        return None
    try:
        d = json.loads(t)
    except Exception:
        return None
    # 统一为 [date, open, close, high, low, volume]
    return [[x["day"], x["open"], x["close"], x["high"], x["low"], x["volume"]] for x in d]


def get_klines(code, kind):
    sym = sym_of(code)
    fq = "qfq" if kind == "idx" else ""
    k = fetch_tx(sym, N_DAYS, fq)
    src = "tx"
    if not k or len(k) < 200:
        k = fetch_sina(sym, N_DAYS)
        src = "sina"
    if not k or len(k) < 200:
        return None, None
    # 腾讯返回 [date, open, close, high, low, volume]
    rows = []
    for x in k:
        try:
            rows.append((x[0], float(x[2])))   # date, close
        except Exception:
            continue
    rows = [r for r in rows if r[1] and r[1] > 0]
    rows.sort(key=lambda r: r[0])
    return rows, src


def fix_dividend(closes, bench_closes, dates):
    """ETF 不复权数据的分红跳空修正（后向调整 = 前复权）
    判定：单日跌幅 > 10%，且同期基准跌幅 < 3% → 视为除息"""
    out = list(closes)
    bmap = dict(zip(dates, bench_closes)) if bench_closes else {}
    n = 0
    for i in range(1, len(out)):
        r = out[i] / out[i - 1] - 1
        if r > -0.10:
            continue
        rb = None
        if bmap:
            b0, b1 = bmap.get(dates[i - 1]), bmap.get(dates[i])
            if b0 and b1:
                rb = b1 / b0 - 1
        if rb is None or rb > -0.03:
            f = out[i] / out[i - 1]
            for j in range(i):
                out[j] *= f
            n += 1
    return out, n


def pct_pos(cur, lo, hi):
    if hi <= lo:
        return 50.0
    return (cur - lo) / (hi - lo) * 100


def window_stats(dates, closes, w):
    seg = closes[-w:] if len(closes) > w else closes
    dseg = dates[-w:] if len(dates) > w else dates
    if len(seg) < 30:
        return None
    cur = closes[-1]
    lo, hi = min(seg), max(seg)
    return {
        "pos": round(pct_pos(cur, lo, hi), 1),
        "lo": round(lo, 4), "hi": round(hi, 4),
        "lo_date": dseg[seg.index(lo)], "hi_date": dseg[seg.index(hi)],
        "dd_hi": round((cur / hi - 1) * 100, 1),
        "up_lo": round((cur / lo - 1) * 100, 1),
        "start": dseg[0], "bars": len(seg),
    }


def yearly_extremes(dates, closes):
    """逐年低点/高点（收盘口径）"""
    y = {}
    for d, c in zip(dates, closes):
        yr = d[:4]
        if yr not in y:
            y[yr] = {"lo": c, "lo_d": d, "hi": c, "hi_d": d}
        else:
            if c < y[yr]["lo"]:
                y[yr]["lo"], y[yr]["lo_d"] = c, d
            if c > y[yr]["hi"]:
                y[yr]["hi"], y[yr]["hi_d"] = c, d
    return [{"year": k, **v} for k, v in sorted(y.items())]


def bottom_trend(dates, closes):
    """底部是否抬升：今年最低 vs 去年最低"""
    y = {}
    for d, c in zip(dates, closes):
        yr = d[:4]
        y[yr] = min(y.get(yr, 1e18), c)
    years = sorted(y)
    if len(years) < 2:
        return None
    cur_y, prev_y = years[-1], years[-2]
    # 当年数据不足 60 个交易日时不参与判定
    cnt_cur = sum(1 for d in dates if d[:4] == cur_y)
    if cnt_cur < 60:
        cur_y, prev_y = years[-2], years[-3] if len(years) >= 3 else years[-2]
    if prev_y == cur_y:
        return None
    return {"cur_year": cur_y, "prev_year": prev_y,
            "cur_low": round(y[cur_y], 4), "prev_low": round(y[prev_y], 4),
            "rising": y[cur_y] > y[prev_y]}


def main():
    t0 = time.time()
    # 基准
    bench_rows, bench_src = get_klines(BENCH[0], "idx")
    if not bench_rows:
        print("基准抓取失败", file=sys.stderr)
        return 1
    b_dates = [r[0] for r in bench_rows]
    b_closes = [r[1] for r in bench_rows]
    b_map = dict(bench_rows)
    print(f"基准 沪深300: {len(bench_rows)}根 {b_dates[0]} → {b_dates[-1]} ({bench_src})")

    items, failed = [], []
    for grp, code, name, kind in POOL:
        rows, src = get_klines(code, kind)
        if not rows:
            failed.append((grp, code, name))
            print(f"  ✗ {name}({code})")
            continue
        dates = [r[0] for r in rows]
        closes = [r[1] for r in rows]
        ndiv = 0
        if kind == "etf":
            closes, ndiv = fix_dividend(closes, b_closes, dates)

        cur = closes[-1]
        w3 = window_stats(dates, closes, W3)
        w5 = window_stats(dates, closes, W5)
        if not w3 or not w5:
            failed.append((grp, code, name))
            continue

        # 近 1 年涨跌幅（自身）
        ret1y = round((cur / closes[-1 - Y1] - 1) * 100, 1) if len(closes) > Y1 else None
        # 相对沪深300 超额（近 1 年，按日期对齐）
        excess = None
        if len(dates) > Y1:
            d0 = dates[-1 - Y1]
            b0 = b_map.get(d0)
            if b0:
                b1 = b_closes[-1]
                excess = round(((cur / closes[-1 - Y1]) - (b1 / b0)) * 100, 1)

        # 年初至今
        ytd = None
        cy = dates[-1][:4]
        idx0 = next((i for i, d in enumerate(dates) if d[:4] == cy), None)
        if idx0 is not None and idx0 < len(closes) - 1:
            ytd = round((cur / closes[idx0] - 1) * 100, 1)

        items.append({
            "group": grp, "code": code, "name": name, "kind": kind,
            "src": src, "div_adj": ndiv,
            "last_date": dates[-1], "last_close": round(cur, 4),
            "bars": len(closes), "start": dates[0],
            "w3": w3, "w5": w5,
            "ret1y": ret1y, "excess1y": excess, "ytd": ytd,
            "bottom": bottom_trend(dates, closes),
            "yearly": yearly_extremes(dates, closes),
        })
        print(f"  ✓ {name:<14}({code}) {len(closes):>5}根 {dates[0]}→{dates[-1]} "
              f"3年{w3['pos']:>5.1f}% 5年{w5['pos']:>5.1f}% [{src}]")

    out = {
        "meta": {
            "gen_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
            "bench": {"code": BENCH[0], "name": BENCH[1], "bars": len(bench_rows),
                      "start": b_dates[0], "end": b_dates[-1],
                      "w3": window_stats(b_dates, b_closes, W3),
                      "w5": window_stats(b_dates, b_closes, W5),
                      "ret1y": round((b_closes[-1] / b_closes[-1 - Y1] - 1) * 100, 1)},
            "total": len(items), "failed": failed,
            "windows": {"w3": W3, "w5": W5},
        },
        "items": items,
    }
    json.dump(out, open("sector_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n完成 {len(items)}/{len(POOL)}，失败 {len(failed)}，耗时 {time.time()-t0:.0f}s")
    if failed:
        print("失败:", failed)
    return 0 if items else 1


if __name__ == "__main__":
    sys.exit(main())
