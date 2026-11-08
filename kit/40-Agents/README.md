# 40-Agents 配置区（配置即代码）

Super-agent 的全部运行配置放在这里，纳入版本管理，改动即审计。
**任何 Agent 不得自动修改本目录，改动需人工 PR 审批。**

```
40-Agents/
├── router/
│   ├── router.yaml       ✅ Router：人设、轻量模型、派单表、回复约束（群聊 ≤100 词）
│   └── filters.yaml      ✅ 事件快过滤规则（DROP / ALLOW / URGENT 三级）
├── workers/
│   ├── knowledge-worker.yaml   ✅ 知识整理与回写（10-Knowledge 唯一写入口）
│   ├── code-worker.yaml        ✅ 代码评审 / CI 分析
│   └── chat-worker.yaml        ✅ 群聊对话 / 调研（兜底 Worker）
├── 权限与同步规则.md     ✅ 权限矩阵 + 署名提交 + 分区写入
├── 接入授权-Grok-Maus.md ✅ 两个 bot 的 Deploy Key / PAT 授权步骤
├── 事件驱动机制.md       ✅ 快过滤→慢判断→直通全流程 + 路由表 + 场景走查
└── watchdog.yaml         ✅ 看门狗：心跳/队列积压/同步状态/回写审计 + 告警
```

配套运维脚本在 `90-System/`：`watchdog/watchdog.sh`（巡检自愈）、`sop/强制回写SOP.md`（完成定义与催办升级）。
