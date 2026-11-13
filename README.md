# 每日持仓分析看板 — GitHub + Cloudflare 版

线上网址: https://daily-trading-dashboard.18790098690-eaf.workers.dev/

策略: 趋势跟踪, 按类型分, 打分 0-100, 不下单
现在持仓: 0 只, 只有理财资产 (持仓有变化时更新 `holdings.yaml` 的记录, 这里只看自选股)

今天的结论、分数、止损/目标都在 `index.html` 和 `data.json` 里, 打开页面就能看到,
不要以这个 README 里写的某一天数字为准, 它只在写的那天是对的。

## 文件说明 (都在仓库根目录)

- `index.html` — 网站页面, 由 `build_site.py` 生成, 不要手改, 改了下次生成会被覆盖
- `data.json` — 当日分析的原始数据 (分数、收盘、止损、目标、新闻、财报)
- `build_site.py` — 生成脚本, 透明可读: 读 `data.json` + `muse-export.html` 模板 → 生成 `index.html`
- `muse-export.html` — 版式模板, 就是 Muse 空间里那个看板的原版样式 (CSS / 卡片布局 / 筛选排序)
- `DEPLOY.md` — 部署和每天更新的步骤

## 怎么更新

见 `DEPLOY.md` 每天更新一节: 跑分析 → 换 `data.json` → `python3 build_site.py` → `git push`, Cloudflare 自动重新部署。
