#!/usr/bin/env python3
"""透明建站脚本 build_site.py — 不是黑盒.
用法: python3 build_site.py
读 data.json (每日分析的原始数据), 生成 index.html.
data.json 是每天跑 daily_analysis.py 后得到的 reports/daily_analysis_YYYY-MM-DD.json,
直接复制过来就行. 每次更新网站, 就是: 换 data.json -> 跑这个脚本 -> git push.
没有其他隐藏步骤, 没有调用任何外部 API, 没有上传你的任何账号信息.
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
results = sorted(data["results"], key=lambda r: r["score"], reverse=True)
market = data.get("market", {})

def esc(x):
    return html.escape(str(x))

def card(r):
    ch = r.get("score_change")
    ch_s = f"较昨日 {ch:+d}" if isinstance(ch, int) else "较昨日 -"
    earn = r.get("earnings") or {}
    # 只显示未来财报; 过去的财报不要当成下次财报警告 (V3.1 的 bug 已修)
    earn_s = ""
    if earn and isinstance(earn.get("days_away"), int) and earn["days_away"] >= 0:
        warn = " ⚠️ 财报在 7 天内, 波动大" if earn["days_away"] <= 7 else ""
        earn_s = f"<p>下次财报: {earn['date']} ({earn['days_away']} 天后){warn}</p>"
    news = "".join(f"<li>{esc(n.get('date',''))} {esc(n.get('title',''))}</li>" for n in (r.get("news") or []))
    news_s = f"<p>新闻 (只供鉴别, 不改变评分):</p><ul>{news}</ul>" if news else "<p>新闻: 暂无</p>"
    reasons = "".join(f"<li>{esc(x)}</li>" for x in r["reasons"])
    cls = "watch" if r["score"] >= 75 else "hold" if r["score"] >= 55 else "avoid" if r["score"] < 25 else "wait"
    badge = "badge-green" if r["score"] >= 75 else "badge-amber" if r["score"] >= 55 else "badge-red" if r["score"] < 25 else "badge-grey"
    return f"""
    <details class="card {cls}" data-score="{r['score']}" data-action="{esc(r['action'])}">
      <summary>
        <span class="ticker">{r['ticker']} {esc(r['name'])}</span>
        <span class="score {badge}">{r['score']}分 {ch_s}</span>
        <span class="action">{esc(r['action'])}</span>
        <span class="meta">收盘 {r['close']} {r['currency']} &nbsp;|&nbsp; 止损 <b>{r['stop_price']}</b> &nbsp;|&nbsp; 目标 <b>{r['target_price']}</b> &nbsp;|&nbsp; 仓位上限 {r['position_pct_max']}%</span>
      </summary>
      <div class="grid"><span>MA20 {r['ma20']}</span><span>MA50 {r['ma50']}</span><span>MA200 {r['ma200']}</span><span>RSI {r['rsi']}</span><span>ATR {r['atr']}</span><span>阻力 {r['resistance_20d']}</span><span>支撑 {r['support_20d']}</span><span>数据源 {r.get('source','')}</span></div>
      <p>{esc(r['action_note'])}</p>
      <ul>{reasons}</ul>
      <p><i>如果错了怎么办: {esc(r['if_wrong'])}</i></p>
      {earn_s}{news_s}
    </details>"""

cards = "\n".join(card(r) for r in results)
watch = sum(1 for r in results if r["score"] >= 75)
wait = sum(1 for r in results if 40 <= r["score"] < 75)
avoid = sum(1 for r in results if r["score"] < 40)

spy_score = market.get("SPY", {}).get("score", "?")
qqq_score = market.get("QQQ", {}).get("score", "?")
html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日持仓分析 {data['date']}</title>
<style>
body{{font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:960px;margin:0 auto;padding:24px 16px 48px;line-height:1.6;color:#111827;background:#f8fafc}}
header{{background:#111827;color:#fff;border-radius:16px;padding:20px 24px;margin-bottom:16px}}
header h1{{margin:0;font-size:26px}} header p{{margin:6px 0 0;color:#d1d5db}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.stat{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;text-align:center}}
.stat b{{font-size:24px;display:block}} .stat span{{color:#6b7280;font-size:13px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-left:5px solid #9ca3af;border-radius:12px;padding:14px 16px;margin:12px 0}}
.card.watch{{border-left-color:#16a34a}} .card.hold{{border-left-color:#ca8a04}} .card.avoid{{border-left-color:#dc2626}}
.score{{color:#fff;padding:3px 10px;border-radius:999px;font-weight:700;white-space:nowrap}}
.badge-green{{background:#16a34a}} .badge-amber{{background:#ca8a04}} .badge-red{{background:#dc2626}} .badge-grey{{background:#6b7280}}
.ticker{{font-size:18px;font-weight:700}} .action{{font-weight:600}}
.meta{{display:block;color:#374151;margin-top:6px;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;background:#f9fafb;border-radius:8px;padding:10px;font-size:13px;margin:10px 0}}
button{{padding:7px 14px;margin:4px;border-radius:999px;border:1px solid #d1d5db;background:#fff;cursor:pointer}}
button.active{{background:#111827;color:#fff;border-color:#111827}}
input{{padding:8px 12px;width:240px;border:1px solid #d1d5db;border-radius:999px}}
h1{{font-size:24px}} summary{{cursor:pointer;list-style:none}} summary::-webkit-details-marker{{display:none}}
@media(max-width:640px){{.stats{{grid-template-columns:repeat(2,1fr)}} .grid{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body>
<header><h1>每日持仓分析 {data['date']}</h1>
<p>数据源: {esc(data['source'])} | 现在持仓: {data.get('holdings_count',0)} 只 | 策略: 趋势跟踪, 按类型分, 打分制 | 不下单</p>
<p>大盘: SPY {spy_score}分, QQQ {qqq_score}分 — 观望, 不是强势, 新开仓要谨慎。</p></header>
<div class="stats">
<div class="stat"><b>{watch}</b><span>关注 / 可分批</span></div>
<div class="stat"><b>{len(results)-watch-avoid}</b><span>观望 / 持有偏多</span></div>
<div class="stat"><b>{avoid}</b><span>回避</span></div>
<div class="stat"><b>14</b><span>自选股总数</span></div>
</div>
<p><b>关注只是可分批, 不是让你全仓买入。</b> SpaceX 未上市, 手动关注。海力士价格单位是韩元 KRW。</p>
<p>
<button data-filter="all" class="active" onclick="filterCards('all',this)">全部 {len(results)}</button>
<button data-filter="watch" onclick="filterCards('watch',this)">关注 {watch}</button>
<button data-filter="hold" onclick="filterCards('hold',this)">持有/观望偏多</button>
<button data-filter="wait" onclick="filterCards('wait',this)">观望</button>
<button data-filter="avoid" onclick="filterCards('avoid',this)">回避</button>
<input id="q" placeholder="搜索代码或名称, 如 AAPL / 苹果" oninput="searchCards(this.value)">
</p>
<div id="list">
{cards}
</div>
<h2>术语解释</h2>
<ul>
<li>MA20/50/200: 过去 20/50/200 天收盘价的平均线, 线向上 = 趋势向上。</li>
<li>ATR: 平均真实波幅, 衡量一只股票每天大概波动多少钱, 波动越大止损越宽。</li>
<li>RSI: 相对强弱, 0-100, 40-70 是健康区间, 70 以上偏热, 30 以下偏冷。</li>
<li>1.5R: 目标盈利是止损亏损的 1.5 倍。</li>
<li>止损是活的: 每天根据 ATR 重新算, 不是一个固定价。</li>
</ul>
<p>这是策略建议, 不是投资承诺; 趋势会变, 消息要鉴别, 止损是活的, 每天会变。不下单。</p>
<p>数据文件: data.json (和这个页面一起在仓库里, 每天更新它再跑 build_site.py 就行)。</p>
<script>
function filterCards(f, btn){{
  document.querySelectorAll('button[data-filter]').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#list .card').forEach(c=>{{
    c.style.display = (f==='all' || c.classList.contains(f)) ? '' : 'none';
  }});
}}
function searchCards(q){{
  q=q.trim().toLowerCase();
  document.querySelectorAll('#list .card').forEach(c=>{{
    c.style.display = c.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body></html>
"""
# 上面 f-string 里的 {{}} 是转义, 需要还原成 {} — 直接用变量替换更稳妥
(ROOT / "index.html").write_text(html_doc, encoding="utf-8")
print(f"已生成 index.html, {len(results)} 只, 日期 {data['date']}, 关注 {watch} 只")
