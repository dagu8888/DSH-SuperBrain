// DSH Plugin: SuperBrain（云记忆）
// Cordis 插件契约：具名导出 apply(ctx)，注册可逆副作用（effect 返回 disposer）。
// 能力：把当前对话要点一键写入 super-brain 知识库 00-Inbox（云端 Agent 会自动整理归档），
//       并可手动触发 sync.sh 双向同步。
// 配置（可选）：{ repo: "/path/to/super-brain" } 或环境变量 SUPERBRAIN_REPO。

import { execFile } from 'node:child_process'
import { writeFile, mkdir } from 'node:fs/promises'
import { join } from 'node:path'

export const name = 'superbrain'
export const inject = []

function resolveRepo(config) {
  return config.repo || process.env.SUPERBRAIN_REPO || 'super-brain'
}

async function inboxAdd(repo, { title, content, author = 'dsh' }) {
  const date = new Date().toISOString().slice(0, 10)
  const safe = String(title || '未命名').replace(/[\\/:*?"<>|]/g, '-').slice(0, 60)
  const file = join(repo, '00-Inbox', `${date}-${safe}-${author}.md`)
  await mkdir(join(repo, '00-Inbox'), { recursive: true })
  await writeFile(file, `# ${title}\n\n${content}\n`, 'utf8')
  return file
}

function sync(repo, agentName = 'dsh') {
  return new Promise((resolve) => {
    execFile('bash', ['90-System/sync/sync.sh'], { cwd: repo, env: { ...process.env, AGENT_NAME: agentName }, timeout: 120000 },
      (err, stdout) => resolve({ ok: !err, output: String(stdout || '').trim() }))
  })
}

export function apply(ctx, config = {}) {
  const repo = resolveRepo(config)
  const api = {
    repo,
    inboxAdd: (args) => inboxAdd(repo, args),
    sync: () => sync(repo),
  }

  // 注册服务：其他插件可通过 ctx.superbrain 调用
  ctx.superbrain = api

  // 注册 Agent 工具（防御式：tools 服务存在且提供 register 时才挂载；effect 返回 disposer）
  return ctx.effect(() => {
    const tools = ctx.tools
    if (!tools || typeof tools.register !== 'function') return () => {}

    const disposeInbox = tools.register({
      name: 'superbrain_remember',
      description: '把一段值得长期记住的内容写入 SuperBrain 云知识库（00-Inbox），云端 Agent 会在 2 分钟内自动分类、起标题、写摘要并归档进 10-Knowledge，同步回所有设备。',
      parameters: {
        type: 'object',
        properties: {
          title: { type: 'string', description: '这条记忆的标题' },
          content: { type: 'string', description: '要记住的完整内容（Markdown）' },
        },
        required: ['title', 'content'],
      },
      execute: async ({ title, content }) => {
        const file = await inboxAdd(repo, { title, content })
        const r = await sync(repo)
        return `已写入云大脑：${file}；同步${r.ok ? '成功' : '待重试'}`
      },
    })

    const disposeSync = tools.register({
      name: 'superbrain_sync',
      description: '立即触发 SuperBrain 知识库与云端的双向同步（git pull --rebase + push）。',
      parameters: { type: 'object', properties: {} },
      execute: async () => {
        const r = await sync(repo)
        return r.ok ? `同步完成：${r.output}` : `同步失败：${r.output}`
      },
    })

    return () => { disposeInbox?.(); disposeSync?.() }
  })
}
