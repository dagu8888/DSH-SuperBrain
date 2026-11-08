# AGENTS.md — SuperBrain 自动安装协议

> 你是被用户委派来搭建 SuperBrain 的 Agent。**严格按本协议执行**，每步验证后再进下一步。
> 原则：能替用户做的绝不让他做；必须由人做的（扫码、付款、提供密钥）才停下来问。

## 你需要向用户收集的信息（先一次性问完）

1. **GitHub**：用户名 + PAT（Settings → Developer settings → classic token，勾 `repo` 全权限）
2. **云服务器**：推荐阿里云轻量 香港 2C2G Ubuntu 24.04（≈¥56/月）；用户也可以提供**任何已有的 Linux 服务器**（有 root SSH 即可，跳过购买步骤）
3. **LLM**：推荐 DeepSeek（platform.deepseek.com 创建 API Key）；也接受任何 OpenAI 兼容接口（Kimi/Qwen/GPT，改 base_url+model 即可）
4. **本地知识库位置**：默认 `C:\Users\<用户>\super-brain`（Windows）或 `~/super-brain`

## 安装步骤

### S1 建唯一信息源
- 用用户 GitHub 建**私有**仓库 `super-brain`（可 API：`POST /user/repos` 带 PAT）
- 把 `kit/` 目录全部内容作为初始提交推上去（保留 00~90 目录结构）

### S2 本地双联
- `git clone https://<user>:<PAT>@github.com/<user>/super-brain.git` 到本地知识库位置
- 指引用户用 Obsidian「打开文件夹作为仓库」打开该目录

### S3 服务器部署（用户提供 IP + root 密码后）
```bash
ssh root@<IP>
apt-get update && apt-get install -y git python3   # Ubuntu
cd /root && git clone https://<user>:<PAT>@github.com/<user>/super-brain.git
crontab -e   # 加两行：
*/10 * * * * cd /root/super-brain && bash 90-System/watchdog/watchdog.sh >> /var/log/watchdog.log 2>&1
*/30 * * * * cd /root/super-brain && AGENT_NAME=server bash 90-System/sync/sync.sh >> /var/log/sync.log 2>&1
```
**验证**：`bash 90-System/watchdog/watchdog.sh` 输出 `WATCHDOG_OK`

### S4 运行时上线
```bash
cd /root/super-brain
cp 90-System/runtime/super-brain.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now super-brain
```
**验证**：`systemctl is-active super-brain` = active；`SELECT * FROM heartbeats` 有心跳

### S5 接入 LLM 自动整理
```bash
cat > /root/super-brain/90-System/runtime/llm.json <<'EOF'
{"api_key": "<用户Key>", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"}
EOF
chmod 600 /root/super-brain/90-System/runtime/llm.json
systemctl restart super-brain
```
**端到端验证**：往 `00-Inbox` 放一篇测试 .md → 2 分钟内应被移入 `10-Knowledge/<分类>/` 且带摘要

### S6 交付清单（写给用户）
- 服务器 IP / 登录方式 / 已跑服务（cron ×2 + systemd ×1）
- 安全提醒：改 SSH 密码（`passwd`）；PAT 与 API Key 不提交进仓库；`llm.json` 已 gitignore
- 日常使用：笔记丢 `00-Inbox` 即可，其余自动

## 红线
- 任何密钥/密码**绝不写进 git 提交**（llm.json、state.db 已在 .gitignore）
- 购买、支付类操作**只引导，不代付**
- 每步失败先诊断再重试，不盲目循环

## 排障速查
| 症状 | 排查 |
|---|---|
| 整理不触发 | `systemctl status super-brain`；查 llm.json 是否合法 JSON |
| 任务 failed | 测 `curl https://api.deepseek.com/v1/models -H "Authorization: Bearer <Key>"` |
| 同步失败 | 服务器上手动 `git pull` 看冲突；PAT 是否过期 |
| 没心跳 | 看 `journalctl -u super-brain -n 50` |
