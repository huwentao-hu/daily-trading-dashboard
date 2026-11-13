#!/bin/bash
# 每日自动更新 — 跑分析 -> 换 data.json -> 生成网站 -> 推 GitHub
# 用法: bash daily_update.sh [--dry-run]
#   不带参数: 全流程, 最后推 GitHub (推的时候 GitHub 可能会弹一次确认, 在手机上点一下就行)
#   --dry-run: 只到生成网站为止, 不推, 用来测试
# 依赖: 项目里的 .venv (系统 python3 没有 yfinance/tigeropen, 不能直接用)
# 日志: ~/workspace/goals/personal-quant-trading-system/hidden_files/daily_update_YYYY-MM-DD.log
set -u
QT=/home/hatch/workspace/quant-trading-system
SITE=/home/hatch/workspace/github-cloudflare-dashboard
LOGDIR=/home/hatch/workspace/goals/personal-quant-trading-system/hidden_files
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1
mkdir -p "$LOGDIR"
LOG="$LOGDIR/daily_update_$(date +%F).log"
exec > >(tee -a "$LOG") 2>&1
echo "=== 每日更新开始 $(date '+%F %T') 北京时间, dry-run=$DRY_RUN ==="

cd "$QT" || exit 1
# 先备份已有的最新日报: 重跑同一天会重新拉数据, yfinance 偶尔会修正
# 历史收盘价/财报日 (2026-11-13 实测: 海力士 11-12 收盘被修正 1313000->1264000,
# NVDA 财报日 11-17 又变回 11-18), 已发布过的版本以备份为准, 不被重跑覆盖.
PREV=$(ls -t reports/daily_analysis_20*.json 2>/dev/null | head -1 || true)
[ -n "$PREV" ] && cp "$PREV" "$LOGDIR/backup_$(basename "$PREV")" && echo "已备份 $PREV"
echo "[1/5] 跑每日分析 (Tiger 优先)..."
if ! .venv/bin/python daily_analysis.py --source tiger; then
  echo "Tiger 跑失败, 改用 yfinance 兜底 (会在页面上注明数据源)..."
  .venv/bin/python daily_analysis.py --source yfinance || { echo "FAIL: yfinance 也失败了"; exit 1; }
fi

NEWEST=$(ls -t reports/daily_analysis_20*.json | head -1)
[ -n "$NEWEST" ] || { echo "FAIL: 没找到日报 json"; exit 1; }
NEW_DATE=$(.venv/bin/python -c "import json; print(json.load(open('$NEWEST'))['date'])")
OLD_DATE=$(python3 -c "import json; print(json.load(open('$SITE/data.json'))['date'])" 2>/dev/null || echo none)
echo "[2/5] 最新日报: $NEWEST (数据日期 $NEW_DATE), 网站当前数据日期: $OLD_DATE"
if [ "$NEW_DATE" = "$OLD_DATE" ]; then
  echo "SKIP: 没有新的交易日数据 (周末/节假日), 不用更新, 直接结束."
  echo "注意: 本次重跑已用备份恢复已发布的 $NEW_DATE 日报 (防止数据源修正覆盖已验证版本)."
  cp "$SITE/data.json" "reports/daily_analysis_${NEW_DATE}.json"
  echo "=== 每日更新结束 (无新数据) $(date '+%F %T') ==="
  exit 0
fi

echo "[3/5] 换 data.json..."
cp "$NEWEST" "$SITE/data.json"
cd "$SITE" || exit 1
echo "[4/5] 生成网站..."
python3 build_site.py || { echo "FAIL: build_site.py 失败"; exit 1; }
grep -q "$NEW_DATE" index.html || { echo "FAIL: index.html 里没有新日期 $NEW_DATE"; exit 1; }

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY-RUN: 到此为止, 不推 GitHub."
  echo "=== 每日更新结束 (dry-run) $(date '+%F %T') ==="
  exit 0
fi

echo "[5/5] 推 GitHub..."
printf 'index.html\0data.json\0' > /tmp/daily-dashboard-push.txt
/opt/hatch/bin/github push-files --owner huwentao-hu --repo daily-trading-dashboard \
  --branch main --message "每日分析 $NEW_DATE" \
  --source-dir "$SITE" --paths-file /tmp/daily-dashboard-push.txt \
  || { echo "FAIL: push 失败"; exit 1; }
echo "=== 每日更新成功: 数据日期 $NEW_DATE, $(date '+%F %T') ==="
