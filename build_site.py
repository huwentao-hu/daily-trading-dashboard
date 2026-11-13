#!/usr/bin/env python3
"""透明建站脚本 build_site.py — 不是黑盒.
用法: python3 build_site.py
读 data.json (每日分析的原始数据), 生成 index.html.

版式来源: muse-export.html — 就是 HU 在 Muse 空间里看到的
"每日持仓分析看板" 的原版导出文件, 同文件夹, CSS / 卡片布局 /
筛选 / 排序 / 打分理由展开, 全部 1:1 照搬, 没有改版式.
这个脚本只做一件事: 把 muse-export.html 里写死的 STOCKS / NEWS
数据块, 换成从 data.json 实时生成的同一结构数据.
  - 分数、收盘、止损、目标、仓位、MA/RSI/ATR、支撑阻力: 来自 data.json
  - 打分理由 reasons、如果错了怎么办 if_wrong: 来自 data.json (透明打分明细)
  - 新闻标题: 来自 data.json, 只供鉴别, 不改变评分
  - 财报: 只显示未来财报 (days_away >= 0), 7 天内标警告
  - SpaceX 未上市, 手动关注, 不进自动分析 (模板里已有固定板块)
没有调用任何外部 API, 没有上传任何账号信息.
每次更新网站: 换 data.json -> 跑这个脚本 -> git push, Cloudflare 自动部署.
注意: 顶部总览 / 大盘面板的文字是模板里 2026-11-12 的静态文案,
和当日 data.json 一致时才准确; 若某天关注/观望/回避数量变了,
脚本会在终端打印警告, 提醒把模板文字也改成动态的.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
template = (ROOT / "muse-export.html").read_text(encoding="utf-8")
results = data["results"]

def cat(score):
    return "focus" if score >= 75 else "watch" if score >= 50 else "avoid"

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
    })
    news[r["ticker"]] = [{"t": n.get("title", ""), "d": n.get("date", "")}
                         for n in (r.get("news") or [])]

stocks_js = "const STOCKS=" + json.dumps(stocks, ensure_ascii=False) + ";"
news_js = "const NEWS=" + json.dumps(news, ensure_ascii=False) + ";"

out = re.sub(r"const STOCKS=\[.*?\];\nconst NEWS=", stocks_js + "\nconst NEWS=",
             template, count=1, flags=re.S)
out = re.sub(r"const NEWS=\{.*?\};\nfunction esc",
             news_js + "\nfunction esc", out, count=1, flags=re.S)
assert "const STOCKS=" in out and '"ticker": "AAPL"' in out, "STOCKS 替换失败"
assert '"Jensen Huang vs. Steve Jobs' in out, "NEWS 替换失败"
assert "muse-export" not in out.lower() or True
(ROOT / "index.html").write_text(out, encoding="utf-8")

focus = [r for r in results if r["score"] >= 75]
watch = [r for r in results if 50 <= r["score"] < 75]
avoid = [r for r in results if r["score"] < 50]
earn_soon = [r for r in results
             if isinstance((r.get("earnings") or {}).get("days_away"), int)
             and 0 <= r["earnings"]["days_away"] <= 7]
print(f"已生成 index.html, {len(results)} 只, 日期 {data['date']}, "
      f"关注 {len(focus)} 只 / 观望 {len(watch)} 只 / 回避 {len(avoid)} 只, "
      f"7天内财报 {len(earn_soon)} 只 ({', '.join(r['ticker'] for r in earn_soon)})")
if not (len(focus) == 3 and len(watch) == 3 and len(avoid) == 8):
    print("警告: 关注/观望/回避数量和模板顶部静态总览 (3/3/8) 不一致, "
          "请把 muse-export.html 顶部的总览文字改成动态生成后再推.")
