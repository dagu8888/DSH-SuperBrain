#!/usr/bin/env bash
# 看门狗巡检脚本：git 同步状态 + Inbox 积压（Worker 心跳/队列检查依赖数据库，见 watchdog.yaml）
# 用法: bash 90-System/watchdog/watchdog.sh    建议 cron 每 10 分钟
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

NOW=$(date +%s)
ALERT=0
NOTE=""

# 1. 与云端差距（需要已配置 origin 且有凭据；无凭据时跳过不报错）
BEHIND=0; UNPUSHED=0
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin -q 2>/dev/null || NOTE="fetch失败(检查凭据)"
  BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
  UNPUSHED=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
fi

# 2. 自动愈合：落后就拉，有未推就推
if [ "$BEHIND" -gt 0 ]; then
  git pull --rebase --autostash -q 2>/dev/null && NOTE="$NOTE auto_pull_ok" || { ALERT=1; NOTE="$NOTE REBASE_CONFLICT需人工"; }
fi
if [ "$UNPUSHED" -gt 0 ]; then
  git push -q 2>/dev/null && NOTE="$NOTE auto_push_ok" || NOTE="$NOTE push失败(检查凭据)"
fi

# 3. 同步停滞：最后一次提交距今 > 24h
LAST_COMMIT_AGE_H=$(( (NOW - $(git log -1 --format=%ct 2>/dev/null || echo $NOW)) / 3600 ))
[ "$LAST_COMMIT_AGE_H" -gt 24 ] && { ALERT=1; NOTE="$NOTE 同步停滞${LAST_COMMIT_AGE_H}h"; }

# 4. Inbox 积压（不含 README）
INBOX_N=$(find 00-Inbox -name '*.md' ! -name 'README.md' 2>/dev/null | wc -l)
[ "$INBOX_N" -ge 10 ] && { ALERT=1; NOTE="$NOTE Inbox积压${INBOX_N}篇→触发整理"; }

# 5. 留痕（只追加）
mkdir -p 50-Events
printf '{"ts":"%s","behind":%s,"unpushed":%s,"stale_h":%s,"inbox":%s,"alert":%s,"note":"%s"}\n' \
  "$(date -Iseconds)" "$BEHIND" "$UNPUSHED" "$LAST_COMMIT_AGE_H" "$INBOX_N" "$ALERT" "$(echo $NOTE | tr '"' "'")" \
  >> "50-Events/watchdog-$(date +%F).jsonl"

if [ "$ALERT" -eq 1 ]; then echo "WATCHDOG_ALERT:$NOTE"; exit 1; fi
echo "WATCHDOG_OK$NOTE"
