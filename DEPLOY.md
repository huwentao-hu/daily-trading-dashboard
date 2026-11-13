# 部署步骤 — GitHub + Cloudflare (透明版)

这个文件夹就是整个网站, 没有隐藏文件, 没有后端, 没有数据库.
你可以在本地先打开 `index.html` 检查, 确认无误再上传.

## 已部署 (2026-11-13 HU 自己连的)

- **线上网址: https://daily-trading-dashboard.18790098690-eaf.workers.dev/**
- 仓库: `huwentao-hu/daily-trading-dashboard` (公开仓库, main 分支)
- 部署方式: Cloudflare Workers (HU 在 Cloudflare 里连的; 下面第三步写的 Pages 是另一种做法, 也能用, 但现在线上跑的是 Workers 这个)
- 每天 07:00 自动更新 (定时任务已设好, 见"每天更新网站"一节)

## 文件清单 (每个文件是干什么的)

| 文件 | 作用 | 你需要改吗 |
|---|---|---|
| `index.html` | 网站本身, 浏览器打开就是看板 | 不用手改, 由 `build_site.py` 生成 |
| `data.json` | 当日分析的原始数据 (14 只股票的评分/止损/目标/新闻/财报) | 每天更新时替换成新的 `daily_analysis_YYYY-MM-DD.json` |
| `build_site.py` | 把 `data.json` + `muse-export.html` 生成 `index.html` 的脚本, 200 行左右, 打开就能看懂 | 不用改, 除非你想改页面样式 |
| `muse-export.html` | 版式模板, 就是 Muse 空间里那个看板的原版样式; `build_site.py` 生成页面时要读它, **必须一起放在仓库里** | 不用改 |
| `daily_update.sh` | 每天自动更新的脚本: 跑分析 → 换 data.json → 生成网站 → 推 GitHub (07:00 定时任务跑的就是它) | 不用改 |
| `DEPLOY.md` | 本文件 | — |
| `README.md` | 网站说明 + 每天更新流程 | — |

**里面没有任何账号、密码、私钥、Token。** 老虎的配置文件绝对不要放进这个仓库。

## 第一步: 在 GitHub 建仓库 (5 分钟, 只做一次)

1. 打开 https://github.com/new
2. Repository name: 比如 `daily-trading-dashboard` (你想叫什么都行, 告诉我一声就行)
3. 选 **Public** 还是 **Private** 都可以:
   - Public: 别人能看到你的代码和持仓分析, 但 Cloudflare 部署最简单
   - Private: 别人看不到代码, Cloudflare 一样能部署 (需要授权 Cloudflare 读这个私有仓库)
   - 现在用的仓库是 **Public** 的 (建的时候就这么选了); 想改成 Private, 在仓库页面 Settings → Danger Zone → Change visibility 里改, 改完 Cloudflare 也要重新授权读这个仓库
4. 不要勾选 Add README / .gitignore / license, 空仓库就行
5. 点 Create repository, 记下仓库地址, 比如 `https://github.com/你的用户名/daily-trading-dashboard.git`

## 第二步: 把这个文件夹推到 GitHub (3 分钟, 只做一次)

在你电脑上, 打开终端, 进入这个文件夹:

```bash
cd daily-trading-dashboard   # 就是这个文件夹, 里面有 index.html 的那个
git init
git add index.html data.json build_site.py muse-export.html daily_update.sh README.md DEPLOY.md
git commit -m "每日持仓分析看板 2026-11-12"
git branch -M main
git remote add origin https://github.com/你的用户名/daily-trading-dashboard.git
git push -u origin main
```

如果提示要登录, 用 GitHub 账号登录就行, 不要把密码发给我。
如果你想让我帮你推, 先点下面那个 GitHub 连接, 授权后再告诉我仓库名, 我再推 — 但这一步你自己做也完全可以, 而且更透明。

## 第三步: 在 Cloudflare Pages 部署 (5 分钟, 只做一次)

1. 打开 https://dash.cloudflare.com/ , 登录 Cloudflare (没有账号先注册一个, 免费)
2. 左侧点 **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
3. 选 **GitHub**, 授权 Cloudflare 读取你刚才那个仓库 (只授权这一个仓库就行)
4. 选仓库 `daily-trading-dashboard`, 点 Begin setup
5. 设置 (照着填, 不要改别的):
   - Production branch: `main`
   - Framework preset: **None**
   - Build command: **留空** (不要填, 因为 index.html 已经生成好了, 不需要构建)
   - Build output directory: **留空 / 填 `.`** (就是仓库根目录)
   - Root directory: 留空
6. 点 **Save and Deploy**
7. 等 1 分钟左右, Cloudflare 会给你一个网址, 比如:
   `https://daily-trading-dashboard-xxx.pages.dev`
   打开就是你的网站了。

## 第四步: (可选) 绑自己的域名

1. 在 Cloudflare Pages 项目里点 **Custom domains** → **Set up a custom domain**
2. 输入你的域名, 按提示在域名那里加一条 CNAME 记录就行
3. 不绑域名也能用, 上面那个 `*.pages.dev` 的网址就是正式网址

## 每天更新网站

**现在是自动的, 不用手动做下面这些:** 每天 07:00 定时任务自动跑 `daily_update.sh`
(跑分析 → 换 data.json → 生成网站 → 推 GitHub, Cloudflare 约 1 分钟后自动更新),
跑完会在聊天里发一条晨报。下面是手动做法, 只在自动任务出问题时备用。

网站不会自己更新, 因为数据是每天收盘后才有的。流程是:

```bash
# 1. 在交易系统里跑今天的分析 (在我这里, 或在你自己电脑上)
# 注意: 必须用项目里的 .venv, 系统自带的 python3 没有装 yfinance/tigeropen,
# 直接跑会报 No module named 'yfinance'
cd quant-trading-system
.venv/bin/python daily_analysis.py --source tiger
# 得到 reports/daily_analysis_2026-11-13.json

# 2. 把新的数据文件复制成 data.json, 重新生成网站
# build_site.py 会读 data.json + muse-export.html (版式模板) 生成 index.html,
# 总览/大盘/筛选数字都是跟着 data.json 动态算的, 不用手改页面
cp reports/daily_analysis_2026-11-13.json github-cloudflare-dashboard/data.json
cd github-cloudflare-dashboard
python3 build_site.py
# 检查一下 index.html, 确认日期和分数对了

# 3. 推到 GitHub, Cloudflare 会自动重新部署 (约 1 分钟)
git add data.json index.html build_site.py
git commit -m "每日分析 2026-11-13"
git push
```

推完等 1 分钟, 打开你的 `*.pages.dev` 网址, 就是新的了。不用再去 Cloudflare 点任何东西。

## 如果部署失败, 先看这里

- Cloudflare 显示 Build failed, 但 Build command 是空的: 检查是不是误填了构建命令, 删掉, 重新部署。
- 打开网站是 404: 检查 Build output directory 是不是根目录, index.html 是不是在仓库根目录 (不是在子文件夹里)。
- 打开网站是旧数据: 检查 git push 有没有成功, Cloudflare Pages 的 Deployments 里最新一次是不是成功 (Success), 失败的话点进去看日志, 把日志发给我。
- GitHub 推不上去: 先确认仓库地址和分支名是不是 `main`, 再确认你登录的是哪个 GitHub 账号。

## 安全提醒

- 这个仓库里只有公开的股票分析, 没有你的持仓金额、没有券商账号、没有老虎私钥和 Token。
- 以后你告诉我交易记录, 我只会记在 `quant-trading-system/` 里, **不会**自动放进这个网站仓库, 除非你明确说要放。
- 如果你以后想让网站需要密码才能看, Cloudflare Pages 免费版做不到, 要用 Cloudflare Access, 到时再单独加。
