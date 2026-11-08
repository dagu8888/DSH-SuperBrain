#!/usr/bin/env bash
# 超级大脑同步脚本：本地工作副本 ⇄ 云端唯一信息源
# 用法: bash 90-System/sync/sync.sh "可选提交说明"
# 署名: AGENT_NAME=grok bash 90-System/sync/sync.sh
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1
AGENT="${AGENT_NAME:-unknown-agent}"
MSG="${1:-sync: $(date '+%Y-%m-%d %H:%M:%S') by ${AGENT}}"

git add -A

# 场景一：尚未配置云端仓库 → 仅本地提交，明确提示待同步
if ! git remote get-url origin >/dev/null 2>&1; then
  if git diff --cached --quiet; then
    echo "NO_CHANGES"
  else
    git -c user.name="${AGENT}" -c user.email="${AGENT}@super-brain.local" commit -m "$MSG"
    echo "NO_REMOTE: 已本地提交。配置云端仓库后再运行本脚本会自动推送。"
  fi
  exit 0
fi

# 场景二：已配置云端 → 先拉（rebase+autostash），再推
git pull --rebase --autostash || { echo "PULL_FAILED: 存在冲突，请人工处理后重试"; exit 1; }

if git diff --cached --quiet && [ -z "$(git log origin/$(git branch --show-current)..HEAD 2>/dev/null)" ]; then
  echo "NO_CHANGES"
  exit 0
fi

git diff --cached --quiet || git -c user.name="${AGENT}" -c user.email="${AGENT}@super-brain.local" commit -m "$MSG"
git push && echo "SYNC_OK" || { echo "PUSH_FAILED"; exit 1; }
