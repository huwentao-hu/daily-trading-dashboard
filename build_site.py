#!/usr/bin/env python3
"""透明建站脚本 build_site.py — 不是黑盒.
用法: python3 build_site.py
读 data.json (每日分析的原始数据), 生成 index.html.

版式来源: muse-export.html — 就是 HU 在 Muse 空间里看到的
"每日持仓分析看板" 的原版导出文件, 同文件夹, CSS / 卡片布局 /
筛选 / 排序 / 打分理由展开, 全部 1:1 照搬, 没有改版式.
这个脚本只做三件事, 全部从 data.json 生成, 没有写死的数据:
  1. 股票卡片数据 STOCKS / 新闻 NEWS: 分数、收盘、止损、目标、
     仓位、MA/RSI/ATR、支撑阻力、打分理由、如果错了怎么办、数据源.
     财报只显示未来财报 (days_away >= 0), 7 天内标警告.
  2. 顶部总览 / 大盘面板 / 筛选按钮上的数量: 关注/观望/回避只数、
     7 天内财报只数、SPY/QQQ 分数、大盘结论, 每天跟着数据变.
     关注 0 只时, 页面顶部会显示"今天无操作"横幅.
  3. 去掉了模板里对 Google Fonts 的外部引用, 页面完全自包含,
     在 Cloudflare 上打开更快, 断网也能正常显示.
SpaceX 未上市, 手动关注, 不进自动分析 (模板里已有固定板块).
没有调用任何外部 API, 没有上传任何账号信息.
每次更新网站: 换 data.json -> 跑这个脚本 -> git push, Cloudflare 自动部署.
"""
import json, re, html
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
template = (ROOT / "muse-export.html").read_text(encoding="utf-8")
results = data["results"]
market = data.get("market", {})
now_bj = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

def cat(score):
    return "focus" if score >= 75 else "watch" if score >= 50 else "avoid"

def mtag(score):
    """大盘分数 -> (文字, 颜色class)."""
    if score >= 75:
        return "强势", "green"
    if score >= 50:
        return "观望偏多", "amber"
    if score >= 40:
        return "观望", "gray"
    return "偏弱", "red"

def esc(x):
    return html.escape(str(x))

focus = [r for r in results if r["score"] >= 75]
watch = [r for r in results if 50 <= r["score"] < 75]
avoid = [r for r in results if r["score"] < 50]
earn_soon = [r for r in results
             if isinstance((r.get("earnings") or {}).get("days_away"), int)
             and 0 <= r["earnings"]["days_away"] <= 7]
spy = market.get("SPY", {}).get("score", 0)
qqq = market.get("QQQ", {}).get("score", 0)
holdings = data.get("holdings_count", 0)

# ---- 1. 卡片数据 ----
stocks = []
news = {}
for r in results:
    earn = r.get("earnings") or {}
    days = earn.get("days_away")
    earn_date = earn.get("date", "") if isinstance(days, int) and days >= 0 else ""
    stocks.append({
        "ticker": r["ticker"], "name": r["name"], "score": r["score"],
        "action": r["action"].replace(" / ", "/"), "cat": cat(r["score"]),
        "price": r["close"], "cur": "₩" if r["currency"] == "KRW" else "$",
        "stop": r["stop_price"], "target": r["target_price"],
        "pos": f"{r['position_pct_max']}%",
        "chg": r.get("score_change") if isinstance(r.get("score_change"), int) else 0,
        "ma20": r["ma20"], "ma50": r["ma50"], "ma200": r["ma200"],
        "rsi": r["rsi"], "atr": r["atr"],
        "res": r["resistance_20d"], "sup": r["support_20d"],
        "earn": earn_date,
        "earnWarn": bool(isinstance(days, int) and 0 <= days <= 7),
        "reasons": r["reasons"], "wrong": r["if_wrong"],
        "src": r.get("source", data.get("source", "")),
    })
    news[r["ticker"]] = [{"t": n.get("title", ""), "d": n.get("date", "")}
                         for n in (r.get("news") or [])]

stocks_js = "const STOCKS=" + json.dumps(stocks, ensure_ascii=False) + ";"
news_js = "const NEWS=" + json.dumps(news, ensure_ascii=False) + ";"

out = template
# 去掉 Google Fonts 外部引用, 页面完全自包含
out = re.sub(r'<link rel="preconnect"[^>]*>\s*', "", out)
out = re.sub(r'<link href="https://fonts\.googleapis[^>]*>\s*', "", out)

out = re.sub(r"const STOCKS=\[.*?\];\nconst NEWS=", stocks_js + "\nconst NEWS=",
             out, count=1, flags=re.S)
out = re.sub(r"const NEWS=\{.*?\};\nfunction esc",
             news_js + "\nfunction esc", out, count=1, flags=re.S)
# 卡片上显示每只的数据源 (tiger / yfinance), 模板渲染函数里加一行
out = out.replace(
    "      ${newsHtml}\n      <button class=\"details-btn\"",
    "      ${newsHtml}\n      <div style=\"font-size:12px;color:var(--muted);margin-top:8px\">数据源: ${esc(s.src||'')}</div>\n      <button class=\"details-btn\"",
    1)
assert "数据源: ${esc(s.src" in out, "卡片数据源行插入失败"
assert '"ticker": "AAPL"' in out, "STOCKS 替换失败"
assert '"Jensen Huang vs. Steve Jobs' in out, "NEWS 替换失败"

# ---- 2. 顶部总览 / 大盘面板 / 筛选数量, 全部动态 ----
def sub(pattern, repl, name):
    global out
    new, n = re.subn(pattern, repl, out, count=1, flags=re.S)
    assert n == 1, f"动态替换失败: {name}"
    out = new

sub(r'<div class="date">[^<]*</div>',
    f'<div class="date">数据日期 · {esc(data["date"])}（最后一个完整交易日） · 美股收盘后分析</div>',
    "日期")
sub(r'当前持仓 <b>\d+ 只</b>',
    f'当前持仓 <b>{holdings} 只</b>', "持仓数")
sub(r'<span class="badge">持仓 \d+ 只 · [^<]*</span>',
    f'<span class="badge">持仓 {holdings} 只 · {"空仓观察" if holdings == 0 else "持有中"}</span>',
    "持仓徽章")
if earn_soon:
    sub(r'<span class="badge warn">[^<]*</span>',
        f'<span class="badge warn">⚠ {len(earn_soon)} 只 7 天内财报</span>', "财报徽章")
else:
    sub(r'<span class="badge warn">[^<]*</span>',
        '<span class="badge">7 天内无财报</span>', "财报徽章")

spy_w, spy_c = mtag(spy)
qqq_w, qqq_c = mtag(qqq)
mkt_word = "观望" if min(spy, qqq) >= 40 else "偏弱"
sub(r'<div class="conclusion">.*?</div>',
    f'<div class="conclusion">关注 <span>{len(focus)} 只可分批</span>，其余观望或回避。<br>'
    f'大盘同为 {spy} / {qqq} 分{mkt_word}，新开仓保持谨慎。</div>', "总览结论")

kpi_html = (
    '<div class="kpis">\n'
    f'        <div class="kpi green"><b>{len(focus)}</b><span>关注 / 可分批<br>{esc(" · ".join(r["ticker"] for r in focus)) or "无"}</span></div>\n'
    f'        <div class="kpi amber"><b>{len(watch)}</b><span>观望偏多 / 观望<br>{esc(" · ".join(r["ticker"] for r in watch)) or "无"}</span></div>\n'
    f'        <div class="kpi red"><b>{len(avoid)}</b><span>偏弱 / 回避<br>{esc(avoid[0]["ticker"] + " 起共 " + str(len(avoid)) + " 只") if avoid else "无"}</span></div>\n'
    f'        <div class="kpi"><b>{len(results)}</b><span>自动分析总数<br>+ SpaceX 手动关注</span></div>\n'
    '      </div>')
sub(r'<div class="kpis">.*?</div>\n      <p style="font-size:13px;color:var\(--muted\);margin:12px 0 0">',
    kpi_html + '\n      <p style="font-size:13px;color:var(--muted);margin:12px 0 0">', "KPI")

if min(spy, qqq) < 40:
    mkt_note = "大盘低于 40 分，仓位减半，不追高。"
elif min(spy, qqq) == 40:
    mkt_note = "大盘低于 40 分时仓位减半——今天正好卡在 40 分，不追高。"
else:
    mkt_note = "大盘在 40 分以上，但仍不是强势，分批为主，不追高。"
sub(r'结论口径：评分 ≥75 关注，50–74 观望偏多/观望，&lt;40 偏弱或回避。大盘低于 40 分时仓位减半——今天正好卡在 40 分，不追高。',
    f'结论口径：评分 ≥75 关注，50–74 观望偏多/观望，&lt;40 偏弱或回避。{mkt_note}',
    "结论口径")

for label, code, score in [("SPY 标普500", "SPY", spy), ("QQQ 纳指100", "QQQ", qqq)]:
    w, c = mtag(score)
    sub(rf'{re.escape(label)}</span><strong>\d+ 分</strong><span class="tag \w+">[^<]*</span><div class="progress"><i style="width:\d+%"></i></div>',
        f'{label}</span><strong>{score} 分</strong><span class="tag {c}">{w}</span><div class="progress"><i style="width:{score}%"></i></div>',
        f"{code} 分数")
if earn_soon:
    earn_txt = "、".join(
        f'{r["ticker"]} {r["earnings"]["date"][5:]}（{r["earnings"]["days_away"]}天后）'
        for r in earn_soon)
    sub(r'大盘不强，个股再强也只适合分批。财报临近：<b style="color:var\(--orange\)">[^<]*</b>，财报前不新开这两只。',
        f'大盘不强，个股再强也只适合分批。财报临近：<b style="color:var(--orange)">{esc(earn_txt)}</b>，财报前不新开这几只。',
        "财报提示")
else:
    sub(r'大盘不强，个股再强也只适合分批。财报临近：<b style="color:var\(--orange\)">[^<]*</b>，财报前不新开这两只。',
        '大盘不强，个股再强也只适合分批。7 天内没有财报。', "财报提示")

sub(r'>全部 \d+<', f'>全部 {len(results)}<', "筛选-全部")
sub(r'>关注 / 可分批 \d+<', f'>关注 / 可分批 {len(focus)}<', "筛选-关注")
sub(r'>观望类 \d+<', f'>观望类 {len(watch)}<', "筛选-观望")
sub(r'>回避 / 偏弱 \d+<', f'>回避 / 偏弱 {len(avoid)}<', "筛选-回避")
sub(r'>7天内财报 \d+<', f'>7天内财报 {len(earn_soon)}<', "筛选-财报")

# 关注 0 只 = 今天无操作, 顶部加横幅
if not focus:
    banner = ('<div class="panel" style="margin-top:14px;border-color:var(--amber);background:var(--amber-bg)">'
              '<b>今天无操作</b> — 没有达到关注线的股票，不新开仓，只等趋势走出来。'
              '</div>\n  <div class="market">')
    out = out.replace('  <div class="market">', banner, 1)

# 页脚加生成时间, 打开页面就知道数据是哪天几点生成的
sub(r'价格为 \d{4}-\d{2}-\d{2} 收盘数据',
    f'价格为 {esc(data["date"])} 收盘数据', "页脚收盘日期")
sub(r'单只仓位上限 20%，本页已按评分给出每只上限。',
    f'单只仓位上限 20%，本页已按评分给出每只上限。<br>'
    f'<b>页面生成时间：</b>{now_bj}（北京时间）· 数据日期 {esc(data["date"])} · 数据源 {esc(data.get("source", ""))}。',
    "页脚时间")

(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"已生成 index.html, {len(results)} 只, 日期 {data['date']}, "
      f"关注 {len(focus)} 只 / 观望 {len(watch)} 只 / 回避 {len(avoid)} 只, "
      f"7天内财报 {len(earn_soon)} 只 ({', '.join(r['ticker'] for r in earn_soon)}), "
      f"大盘 SPY {spy} / QQQ {qqq}, 生成时间 {now_bj} 北京时间")
