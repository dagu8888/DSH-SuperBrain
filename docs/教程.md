# 如何让你单机DSH开启Obsidian双联云记忆Super-Agent架构保姆级教程

> 适用人群：非技术背景、Windows 用户、有多个本地项目（如 D:\DSH 下的 grok-bot、mausbot），想用 Obsidian + 云服务器搭建"永不丢记忆、多 Agent 协同"的个人系统。
> 本教程是 2026-11-08 一天之内真实走完的全程记录，所有命令、价格、坑都是实测。

---

## 〇、最终你会得到什么

```
你的 Windows 电脑                     阿里云·香港服务器
┌──────────────────┐                 ┌─────────────────────┐
│ Obsidian          │                │ super-brain 仓库      │
│  ↕ 编辑笔记        │   Git 同步      │  ↕ 每30分钟自动推拉    │
│ super-brain 仓库   │ ◄════════════► │ Router + 3 Worker    │
│ (grok/maus 机器人) │   GitHub 私仓   │ 看门狗 每10分钟巡检    │
└──────────────────┘   双向桥梁       │ DeepSeek 自动整理     │
                                      └─────────────────────┘
```

- **双联云记忆**：Obsidian 里写笔记 ⇄ GitHub 私有仓库（唯一信息源）⇄ 云服务器，三处永远一致。
- **Super-Agent 架构**：总台 Router 派活，3 个 Worker（聊天/代码/知识）干活，看门狗 7×24 盯着。
- **全自动整理**：往 `00-Inbox` 丢一篇笔记，1~2 分钟内 AI 自动分类归档进知识库。

**总成本**：服务器 ¥50.71/月（香港 2核2G）+ DeepSeek API 约几分钱/百篇 + GitHub 私仓免费。

---

## 一、起点（你可能也是这样）

- Windows 一台，`D:\DSH` 下躺着几个本地项目（grok-bot、mausbot……）
- 笔记散落在各处，AI 聊天记录无法沉淀，换台电脑就"失忆"
- 多个 AI 助手各干各的，没有统一记忆和分工

**目标**：一个云端知识库做"唯一信息源"，所有 AI 都读写它，配一套规矩防止乱写。

---

## 二、架构设计（半小时，值得想清楚再动手）

### 2.1 知识库目录（数字前缀 = 流转顺序）

```
super-brain/
├── 00-Inbox/       收集箱：任何笔记先丢这里，等待整理
├── 10-Knowledge/   知识库：Concepts(概念) / Decisions(决策) / Playbooks(方法)
├── 20-Skills/      可复用技能
├── 30-Reviews/     复盘报告
├── 40-Agents/      Agent 配置（Router/Worker/看门狗 全在这里定义）
├── 50-Events/      事件留痕（只追加，谁干了什么一查便知）
├── 60-Outputs/     成果输出
├── 70-Assets/      图片附件等
├── 80-Templates/   模板
└── 90-System/      系统脚本：sync.sh / watchdog.sh / runtime/
```

### 2.2 角色分工（写在 40-Agents/ 里的"宪法"）

| 角色 | 职责 | 红线 |
|---|---|---|
| Router 总台 | 只接待、派活、回话 | 绝不亲自执行耗时任务 |
| knowledge-worker | 整理 Inbox → 归档 10-Knowledge | 不动别人目录 |
| chat-worker / code-worker | 待接入对话/代码任务 | 同上 |
| 看门狗 Watchdog | 每 10 分钟巡检，能自愈就自愈 | 冲突只报警不硬来 |

**三条铁律**（所有 Agent 签字遵守）：
1. **云端仓库是唯一信息源**，干活前先 `git pull`，干完必须 `git push`（强制回写）
2. **留痕**：一切动作写 `50-Events/`，只追加不修改
3. **各管各的目录**，越界即违规

---

## 三、Step 1：建 GitHub 私有仓库（唯一信息源）

1. GitHub 注册/登录 → New Repository → 名字 `super-brain` → **Private** → 创建
2. 生成访问令牌（PAT）：Settings → Developer settings → Personal access tokens → Generate new token (classic) → 勾 `repo` 全部权限 → 复制保存（只显示一次！）
3. 本地克隆（Windows 装 Git for Windows 后）：

```bash
cd C:\Users\你的用户名
git clone https://你的用户名:你的PAT@github.com/你的用户名/super-brain.git
```

> 坑：PAT 写在 remote 里图方便，但等于明文存电脑上。教程末尾有安全加固。

---

## 四、Step 2：Obsidian 双联

1. Obsidian → 打开仓库文件夹 `C:\Users\你的用户名\super-brain` 作为仓库（Vault）
2. 从此：**Obsidian 里写笔记 = 改仓库文件**，配合同步脚本自动上云
3. 建议安装 Obsidian Git 插件（或让本地 Agent 定时跑 sync.sh），实现"写即同步"

---

## 五、Step 3：两个核心脚本（90-System/）

### sync.sh —— 同步（本地 ⇄ 云端）

逻辑一句话：`git add -A` → `git pull --rebase --autostash` → 提交 → `git push`。
输出 `SYNC_OK` 即成功；冲突时输出 `PULL_FAILED` 停下喊人，不乱来。

### watchdog.sh —— 看门狗巡检

- 落后云端 → 自动 `git pull` 自愈；有未推提交 → 自动 `git push`
- 超过 24 小时无推送 → 告警"同步停滞"
- `00-Inbox` 积压 ≥ 10 篇 → 告警触发整理
- 每轮结果追加写入 `50-Events/watchdog-日期.jsonl`，输出 `WATCHDOG_OK` / `WATCHDOG_ALERT`

---

## 六、Step 4：买云服务器（手把手·阿里云）

> 目标配置：**轻量应用服务器 · 中国香港 · 2核2G · Ubuntu 24.04 · 1个月先试**

1. 打开 https://www.aliyun.com/product/swas → 立即购买 → 扫码登录
2. **地域选"中国香港"**（免备案、国内访问快；注意：控制台默认可能显示"青岛"，务必手动改）
3. 规格：通用型 → **2 vCPU / 2 GiB / 40 GiB**（海外约 ¥56/月）
4. 镜像：系统镜像 → **Ubuntu 24.04**
5. 时长：**先买 1 个月试用**（¥56，满意再续年付约 ¥624 可用券）
6. 勾选协议 → 立即购买 → 收银台付款（本单实付 ¥50.71，余额抵扣 ¥5.29）
7. 付款后进控制台 → 左上角**切换到"中国香港"地域**才能看到实例
8. 实例 → 更多操作 → **设置密码 → 选"在线设置"（免重启立即生效）**

> 坑①：买错地域/时长没法直接改，未支付订单放着会自动取消，重新选配即可。
> 坑②：默认地域是杭州，付完款在列表里看不到实例别慌，切地域。
> 坑③：一个账号看到的"询价中"不用管，点进去就是正常价。

**记下三样东西**：公网 IP（如 8.218.x.x）、root 密码、实例 ID。

---

## 七、Step 5：服务器部署（SSH 三连）

Windows 可用 PowerShell 自带 `ssh`，或用阿里云的"远程连接"网页终端：

```bash
ssh root@你的IP

# 1. 装环境（Ubuntu 24.04 自带 python3.12 和 cron）
apt-get update && apt-get install -y git

# 2. 克隆仓库到服务器
cd /root && git clone https://你的用户名:你的PAT@github.com/你的用户名/super-brain.git
cd super-brain && git config user.name "hk-server" && git config user.email "server@local"

# 3. 定时任务：10分钟巡检 + 30分钟同步
crontab -e
# 加入两行：
*/10 * * * * cd /root/super-brain && bash 90-System/watchdog/watchdog.sh >> /var/log/watchdog.log 2>&1
*/30 * * * * cd /root/super-brain && AGENT_NAME=hk-server bash 90-System/sync/sync.sh >> /var/log/sync.log 2>&1

# 4. 首跑验证
bash 90-System/watchdog/watchdog.sh   # 应输出 WATCHDOG_OK
```

到这一步：**云记忆已通**——服务器每 30 分钟和 GitHub 双向同步，本地经同一仓库联动。

---

## 八、Step 6：Super-Agent 运行时上线（7×24）

`90-System/runtime/runtime.py`（约 150 行，纯标准库 Python）：

- **Router 线程**：每 60 秒扫描 `00-Inbox`，发现新 `.md` 就写入 SQLite 任务队列
- **3 个 Worker 线程**：每 5 秒抢单 + 每轮写心跳（heartbeats 表）
- **留痕**：派单/认领/完成全程写 `50-Events/runtime-日期.jsonl`

用 systemd 托管（开机自启 + 崩溃自愈）：

```bash
cp 90-System/runtime/super-brain.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now super-brain
systemctl status super-brain   # 看到 active (running) 即成功
```

> 实测踩过的坑：SQLite 写入后**必须立刻 commit**，否则长事务锁库，其他线程心跳全被堵死（血泪教训，代码里已修）。

---

## 九、Step 7：接 DeepSeek，开启全自动整理

1. 到 https://platform.deepseek.com 充值（10 元够用很久）→ 创建 API Key
2. 在服务器写配置（**此文件不进 Git**，已 gitignore）：

```bash
cat > /root/super-brain/90-System/runtime/llm.json <<'EOF'
{"api_key": "sk-你的Key", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"}
EOF
chmod 600 /root/super-brain/90-System/runtime/llm.json
systemctl restart super-brain
```

3. 工作原理：knowledge-worker 抢到"整理任务"后，把笔记发给 DeepSeek，要求返回 JSON `{分类, 标题, 摘要, 整理后正文}` → 写入 `10-Knowledge/Concepts|Decisions|Playbooks/` → 删除 Inbox 原件 → 留痕。
4. **失败兜底**：API 出错时任务标 failed，原文件原地不动，绝不丢笔记。

实测效果：丢进 3 篇杂乱接入笔记，2 分钟内全部分类正确、标题规范、带摘要归档。

---

## 十、安全清单（强烈建议逐项打勾）

- [ ] **换 SSH 密码**：`ssh root@IP` 后执行 `passwd`（初始密码在对话/报告里出现过）
- [ ] **吊销教程用 PAT**，换发新令牌后更新三处 remote：
  `git remote set-url origin https://用户名:新PAT@github.com/用户名/super-brain.git`
  （本地电脑、云服务器 `/root/super-brain`、其他 Agent 机器）
- [ ] **DeepSeek Key** 若疑泄露：控制台禁用重建 → 只改服务器 `llm.json`
- [ ] 服务器防火墙只开 22/80/443（轻量默认即可）
- [ ] llm.json、state.db 已 gitignore，永不入库

---

## 十一、日常怎么用（30 秒版）

| 你想干嘛 | 怎么做 |
|---|---|
| 记个灵感 | Obsidian 在 `00-Inbox` 新建笔记，写完就不用管，AI 自动归档 |
| 找知识 | `10-Knowledge` 三类目录翻，或 Obsidian 全局搜索 |
| 查谁干了啥 | 看 `50-Events/` 当天 jsonl |
| 看系统健不健康 | 服务器 `tail /var/log/watchdog.log`，或看仓库最新提交时间 |
| 加新 Agent | 在 `40-Agents/` 写个 yaml，遵守三条铁律，接入同步即可 |

---

## 十二、常见问题 FAQ

**Q：笔记会不会被 AI 改丢？**
A：不会。整理前原件在 Git 历史里永久可查；API 失败时原件不动；`50-Events` 全程留痕。

**Q：服务器到期忘续费？**
A：阿里云到期会短信提醒；数据在 GitHub 和本地都有，重买一台按第七~九章 10 分钟可重建。

**Q：一个月花多少？**
A：服务器 ¥50~56 + DeepSeek 整理笔记（每篇约 1 万 token 以内，几分钱）≈ **不到 60 元/月**。

**Q：能换别的模型吗？**
A：`llm.json` 改 `base_url` 和 `model` 即可，任何 OpenAI 兼容接口（Kimi、Qwen、GPT）都行。

---

## 附录：今天真实订单与版本（存档用）

- 服务器：阿里云轻量 香港 2C2G/40G/200Mbps，1 个月 ¥56（实付 ¥50.71），实例 Ubuntu-tvha
- 仓库里程碑：`升级完成报告` → `部署完成报告` → `runtime 上线` → `DeepSeek 全自动整理`
- 全部配置与脚本：见仓库 `40-Agents/`、`90-System/`，本教程与仓库同步更新

> 教程版本 v1.0 ｜ 2026-11-08 ｜ 由 Trae Agent 与大古老师共同完成
