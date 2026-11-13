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
    # V3.3: 仓位建议双币种 (人民币 + 美元一起显示)
    sug = r.get("suggest_cny") or {}
    if sug.get("shares"):
        suggest_txt = (f"可买 {sug['shares']} 股 · 约 ¥{sug['amount_cny']:,} / "
                       f"${sug['amount_usd']:,.2f}")
    elif sug:
        suggest_txt = "按 1% 风险买不到 1 股，止损距离太宽，等回调"
    else:
        suggest_txt = ""
    stocks.append({
        "ticker": r["ticker"], "name": r["name"], "score": r["score"],
        "action": r["action"].replace(" / ", "/"), "cat": cat(r["score"]),
        "held": bool(r.get("is_holding")), "suggest": suggest_txt,
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
# V3.3: 卡片上显示仓位建议 (双币种), 只有高分未持仓的才有 suggest
out = out.replace(
    "      ${srHtml}${maHtml}${earnHtml}",
    """      ${srHtml}${maHtml}${earnHtml}${s.suggest?`<div style="margin-top:10px;font-size:13px;background:var(--surface2);border-radius:10px;padding:8px">💰 仓位建议：${esc(s.suggest)}</div>`:''}""",
    1)
assert "仓位建议：" in out, "卡片仓位建议行插入失败"
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

# V3.2: 有持仓时, 在总览上方加一张"我的持仓"表 (成本/现价/浮盈亏/止损/建议).
# 没持仓时什么都不加, 页面和原来一模一样.
holdings = data.get("holdings", [])
if holdings:
    # V3.3: 美元持仓的成本/现价/浮盈亏同时显示人民币 (用当天汇率 fx_usdcny 换算)
    fx = data.get("fx_usdcny") or 0
    rows = ""
    for h in holdings:
        cur = "₩" if h.get("currency") == "KRW" else "$"
        pnl_color = "var(--green)" if h["pnl"] >= 0 else "var(--red)"
        if h.get("currency") == "USD" and fx:
            cost_txt = f"${h['entry_price']}（¥{h['entry_price'] * fx:,.0f}）"
            close_txt = f"${h['close']}（¥{h['close'] * fx:,.0f}）"
            pnl_txt = f"{h['pnl']:+.2f} ({h['pnl_pct']:+.2f}%)（¥{h['pnl'] * fx:+,.0f}）"
        else:
            cost_txt = f"{cur}{h['entry_price']}"
            close_txt = f"{cur}{h['close']}"
            pnl_txt = f"{cur}{h['pnl']:+.2f} ({h['pnl_pct']:+.2f}%)"
        rows += (
            f'<tr><td style="padding:6px 8px"><b>{esc(h["ticker"])}</b> {esc(h["name"])}</td>'
            f'<td style="padding:6px 8px">{h["shares"]} 股</td>'
            f'<td style="padding:6px 8px">{cost_txt}</td>'
            f'<td style="padding:6px 8px">{close_txt}</td>'
            f'<td style="padding:6px 8px;color:{pnl_color}">{pnl_txt}</td>'
            f'<td style="padding:6px 8px;color:var(--red)">{cur}{h["stop_price"]}</td>'
            f'<td style="padding:6px 8px">{esc(h["action"])}</td></tr>')
    panel = (
        '<div class="panel" style="margin-top:14px">'
        f'<h2>我的持仓 · {len(holdings)} 只</h2>'
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<tr style="color:var(--muted);text-align:left">'
        '<th style="padding:6px 8px">代码</th><th style="padding:6px 8px">股数</th>'
        '<th style="padding:6px 8px">成本</th><th style="padding:6px 8px">现价</th>'
        '<th style="padding:6px 8px">浮盈亏</th><th style="padding:6px 8px">止损</th>'
        '<th style="padding:6px 8px">建议</th></tr>'
        f'{rows}</table>'
        '<p style="font-size:13px;color:var(--muted);margin:12px 0 0">'
        '止损是活的，每天按 ATR 重算；跌破止损按计划离场。'
        '持仓卡片上也有“已持有”标记。</p></div>\n  <div class="market">')
    out = out.replace('  <div class="market">', panel, 1)
    # 持仓卡片上加"已持有"标记
    out = out.replace(
        '<span class="tag ${tagClass(s.cat)}" style="margin-top:6px">${s.action}</span>',
        '<span class="tag ${tagClass(s.cat)}" style="margin-top:6px">${s.action}</span>'
        '${s.held?\'<span class="tag green" style="margin-top:6px;margin-left:6px">已持有</span>\':\'\'}',
        1)
    assert "已持有</span>" in out, "持仓标记插入失败"

# V3.3: 网页上手动改自选股的面板.
# 注意: 这个网站是静态页面, 没有后端, 网页自己改不了 GitHub 上的数据.
# 所以面板的做法是: 在网页上填好 -> 存在你自己的浏览器里 (localStorage, 不上传) ->
# 生成一段发给 Muse 的话 -> 你复制发给我, 我加进系统, 第二天早上 7 点的分析就带上它.
# 加进去了, 下次打开页面时面板会自动把那条从待发送里去掉 (因为已经在 STOCKS 里了).
# 面板是固定内容, 不用插值, 所以用普通字符串 (不是 f-string, 里面有 JS 的 ${}).
MANAGE_PANEL = r'''
  <section class="panel" id="manage-panel" style="margin-top:14px">
    <h2>管理自选股 · 在网页上改</h2>
    <p style="font-size:13px;color:var(--muted);margin:0 0 12px">在这里填好，点“加入待发送”，再点复制，把那段话发给我，我加进系统。第二天早上 7 点的分析就会带上它；加进去了，这里会自动消失。</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">
      <label style="font-size:12px;color:var(--muted)">代码<br><input id="mg-ticker" class="search" style="flex:none;min-width:110px" placeholder="如 JPM" autocomplete="off"></label>
      <label style="font-size:12px;color:var(--muted)">名称<br><input id="mg-name" class="search" style="flex:none;min-width:110px" placeholder="如 摩根大通"></label>
      <label style="font-size:12px;color:var(--muted)">类型<br><select id="mg-type" class="select"><option value="mega">大盘科技</option><option value="chip">芯片</option><option value="china_adr">中概</option><option value="other">其他</option></select></label>
      <button class="chip" id="mg-add-btn" type="button">＋ 加入待发送</button>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end;margin-top:10px">
      <label style="font-size:12px;color:var(--muted)">删除一只<br><select id="mg-remove" class="select"></select></label>
      <button class="chip" id="mg-remove-btn" type="button">－ 加入待发送</button>
    </div>
    <div id="mg-msg" style="font-size:13px;margin-top:10px"></div>
    <div id="mg-pending" style="margin-top:10px"></div>
    <div id="mg-send" style="display:none;margin-top:10px">
      <div style="font-size:13px;font-weight:700;margin-bottom:6px">发给我的话（点复制，粘贴到聊天里发我）：</div>
      <textarea id="mg-text" readonly rows="3" style="width:100%;border:1px solid var(--line);border-radius:10px;background:var(--surface2);padding:10px;font-size:13px"></textarea>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
        <button class="chip" id="mg-copy-btn" type="button">复制</button>
        <button class="chip" id="mg-clear-btn" type="button">清空待发送</button>
      </div>
    </div>
    <p style="font-size:12px;color:var(--muted);margin:12px 0 0">你的请求只存在你自己的浏览器里，不会上传到任何地方。删的时候，如果那只还在持仓里，得先卖掉再删。未上市的公司（如 SpaceX）加不进自动分析，在聊天里告诉我，我记到手动关注里。</p>
  </section>
  <script>
  (function(){
    var KEY='dq_pending_watchlist_v1';
    function load(){ try{ return JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ return []; } }
    function save(list){ try{ localStorage.setItem(KEY, JSON.stringify(list)); }catch(e){} }
    function tickers(){ return (typeof STOCKS!=='undefined'?STOCKS:[]).map(function(s){return s.ticker;}); }
    function esc(s){ return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
    function prune(list){
      var cur=tickers();
      return list.filter(function(it){
        if(it.op==='add') return cur.indexOf(it.ticker)===-1;
        return cur.indexOf(it.ticker)!==-1;
      });
    }
    function msg(text, ok){
      var el=document.getElementById('mg-msg');
      el.textContent=text||'';
      el.style.color=ok?'var(--green)':'var(--red)';
    }
    function render(){
      var list=prune(load()); save(list);
      var sel=document.getElementById('mg-remove');
      var curSel=sel.value;
      sel.innerHTML=tickers().map(function(t){return '<option value="'+esc(t)+'">'+esc(t)+'</option>';}).join('');
      if(curSel) sel.value=curSel;
      var box=document.getElementById('mg-pending');
      if(!list.length){
        box.innerHTML='<div style="font-size:13px;color:var(--muted)">待发送是空的。</div>';
        document.getElementById('mg-send').style.display='none';
        return;
      }
      var typeName={mega:'大盘科技',chip:'芯片',china_adr:'中概',other:'其他'};
      box.innerHTML=list.map(function(it,i){
        var label=it.op==='add'?('加：'+it.ticker+' '+it.name+'（'+(typeName[it.type]||it.type)+'）'):('删：'+it.ticker);
        return '<div style="display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:13px;padding:6px 0;border-top:1px dashed var(--line)"><span>'+esc(label)+'</span><button class="chip" type="button" data-i="'+i+'" onclick="mgDel(this)">删除</button></div>';
      }).join('');
      var lines=['请帮我改自选股：'].concat(list.map(function(it){
        return it.op==='add'?('加：'+it.ticker+' '+it.name+'（'+(typeName[it.type]||it.type)+'）'):('删：'+it.ticker);
      }));
      document.getElementById('mg-text').value=lines.join('\n');
      document.getElementById('mg-send').style.display='block';
    }
    window.mgDel=function(btn){
      var list=load(); list.splice(Number(btn.getAttribute('data-i')),1); save(list); render();
      if(!load().length){ document.getElementById('mg-msg').textContent=''; }
    };
    function init(){
      render();
      document.getElementById('mg-add-btn').addEventListener('click',function(){
        var t=document.getElementById('mg-ticker').value.trim().toUpperCase();
        var name=document.getElementById('mg-name').value.trim()||t;
        var type=document.getElementById('mg-type').value;
        if(!/^[A-Z0-9.\-]{1,12}$/.test(t)){ msg('代码格式不对：只支持字母、数字、点和短横线，如 JPM、000660.KS'); return; }
        var list=load();
        if(tickers().indexOf(t)!==-1){ msg('这只已经在自选里了，不用重复加。', true); return; }
        if(list.some(function(it){return it.ticker===t;})){ msg('这只已经在待发送里了。', true); return; }
        list.push({op:'add',ticker:t,name:name,type:type}); save(list);
        document.getElementById('mg-ticker').value=''; document.getElementById('mg-name').value='';
        msg('已加入待发送：加 '+t+' '+name+'。点下面的复制发给我。', true); render();
      });
      document.getElementById('mg-remove-btn').addEventListener('click',function(){
        var t=document.getElementById('mg-remove').value;
        if(!t){ msg('自选里没有可删的股票。'); return; }
        var list=load();
        if(list.some(function(it){return it.ticker===t;})){ msg('这只已经在待发送里了。', true); return; }
        list.push({op:'remove',ticker:t,name:'',type:''}); save(list);
        msg('已加入待发送：删 '+t+'。点下面的复制发给我。', true); render();
      });
      document.getElementById('mg-copy-btn').addEventListener('click',function(){
        var ta=document.getElementById('mg-text');
        function done(){ msg('已复制，去聊天里粘贴发我就行。', true); }
        if(navigator.clipboard&&navigator.clipboard.writeText){
          navigator.clipboard.writeText(ta.value).then(done,function(){ ta.select(); document.execCommand('copy'); done(); });
        }else{ ta.select(); document.execCommand('copy'); done(); }
      });
      document.getElementById('mg-clear-btn').addEventListener('click',function(){
        save([]); msg('已清空。', true); render();
      });
    }
    if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded',init); } else { init(); }
  })();
  </script>'''

out = out.replace('  <div class="controls">', MANAGE_PANEL + '\n  <div class="controls">', 1)
assert 'id="manage-panel"' in out, "管理自选股面板插入失败"

# 页脚加生成时间, 打开页面就知道数据是哪天几点生成的
sub(r'价格为 \d{4}-\d{2}-\d{2} 收盘数据',
    f'价格为 {esc(data["date"])} 收盘数据', "页脚收盘日期")
sub(r'单只仓位上限 20%，本页已按评分给出每只上限。',
    f'单只仓位上限 20%，本页已按评分给出每只上限。<br>'
    f'<b>页面生成时间：</b>{now_bj}（北京时间）· 数据日期 {esc(data["date"])} · 数据源 {esc(data.get("source", ""))}。<br>'
    f'<b>回测提示：</b>2023-10~2026-11 回测, 趋势跟踪跑输买入持有 (269 笔交易, 胜率约 46%)。'
    f'本系统价值在风险控制与纪律, 不在跑赢大盘。',
    "页脚时间")

(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"已生成 index.html, {len(results)} 只, 日期 {data['date']}, "
      f"关注 {len(focus)} 只 / 观望 {len(watch)} 只 / 回避 {len(avoid)} 只, "
      f"7天内财报 {len(earn_soon)} 只 ({', '.join(r['ticker'] for r in earn_soon)}), "
      f"大盘 SPY {spy} / QQQ {qqq}, 生成时间 {now_bj} 北京时间")
