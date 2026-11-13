# 每日持仓分析看板 — GitHub + Cloudflare 版

数据日期: 2026-11-12 (最后一个完整交易日)
现在持仓: 0 只, 只有理财资产
策略: 趋势跟踪, 按类型分, 打分 0-100, 不下单

## 今天的结论

- 关注 / 可分批 (3 只): AAPL 90 分, AMZN 90 分, AMD 85 分
- 持有 / 观望偏多: MSFT 70 分 (昨天 80 分, 跌出关注线), AVGO 60 分
- 观望: TSM 50 分
- 回避: GOOGL、INTC、NVDA、META、BABA 等
- 大盘: SPY 40 分, QQQ 40 分, 观望

详细数据在 `data.json`, 页面在 `index.html`。

## 怎么更新

见 `DEPLOY.md` 每天更新一节: 换 `data.json` → `python3 build_site.py` → `git push`。
