<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface ChatBubble {
  id: string
  role: 'user' | 'bot' | 'system'
  text: string
}

interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  bubbles: ChatBubble[]
}

interface ChatSendResponse {
  messages: Array<{ text: string }>
}

const authStore = useAuthStore()
const sending = ref(false)
const inputText = ref('')
const chatLogRef = ref<HTMLElement | null>(null)

const quickPrompts = ['查询我的订单', '查询物流进度', '查询售后进度', '如何申请退货或换货', '推荐几款手机']

const CHAT_GUEST_ID_KEY = 'chat_guest_id'
const CHAT_STORAGE_PREFIX = 'chat_sessions_v2'
const CHAT_ACTIVE_PREFIX = 'chat_active_session_v2'

const readOrCreateGuestId = () => {
  const existing = localStorage.getItem(CHAT_GUEST_ID_KEY)
  if (existing) return existing
  const next = `guest-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(CHAT_GUEST_ID_KEY, next)
  return next
}

const guestIdentity = ref(readOrCreateGuestId())
const principalId = computed(() => authStore.user?.id || guestIdentity.value)
const sessionsStorageKey = computed(() => `${CHAT_STORAGE_PREFIX}:${principalId.value}`)
const activeStorageKey = computed(() => `${CHAT_ACTIVE_PREFIX}:${principalId.value}`)

const sessions = ref<ChatSession[]>([])
const activeSessionId = ref('')

const buildWelcomeBubble = (): ChatBubble => ({
  id: `welcome-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  role: 'bot',
  text: '你好，我是商城客服。可以帮你查订单、查物流、查售后，也可以推荐商品。'
})

const deriveSessionTitle = (session: ChatSession) => {
  const firstUser = session.bubbles.find((item) => item.role === 'user' && item.text.trim())
  if (!firstUser) return '新会话'
  const text = firstUser.text.trim().replace(/\s+/g, ' ')
  return text.length > 16 ? `${text.slice(0, 16)}...` : text
}

const createSession = (): ChatSession => {
  const now = new Date().toISOString()
  return {
    id: `s-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title: '新会话',
    createdAt: now,
    updatedAt: now,
    bubbles: [buildWelcomeBubble()]
  }
}

const safeParseSessions = (raw: string | null): ChatSession[] => {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .map((item) => {
        const bubbles = Array.isArray(item?.bubbles)
          ? item.bubbles
              .filter((b: any) => ['user', 'bot', 'system'].includes(b?.role) && typeof b?.text === 'string')
              .map((b: any) => ({
                id: typeof b.id === 'string' && b.id ? b.id : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                role: b.role as ChatBubble['role'],
                text: String(b.text)
              }))
          : []

        const fallback = createSession()
        return {
          id: typeof item?.id === 'string' && item.id ? item.id : fallback.id,
          title: typeof item?.title === 'string' && item.title ? item.title : '新会话',
          createdAt: typeof item?.createdAt === 'string' && item.createdAt ? item.createdAt : fallback.createdAt,
          updatedAt: typeof item?.updatedAt === 'string' && item.updatedAt ? item.updatedAt : fallback.updatedAt,
          bubbles: bubbles.length > 0 ? bubbles : [buildWelcomeBubble()]
        }
      })
      .filter((session) => !!session.id)
  } catch {
    return []
  }
}

const persistChatState = () => {
  localStorage.setItem(sessionsStorageKey.value, JSON.stringify(sessions.value))
  if (activeSessionId.value) {
    localStorage.setItem(activeStorageKey.value, activeSessionId.value)
  }
}

const currentSession = computed(() => sessions.value.find((item) => item.id === activeSessionId.value) || null)
const bubbles = computed(() => currentSession.value?.bubbles || [])

const userLabel = computed(() => authStore.user?.username || '游客')
const senderId = computed(() => `${principalId.value}:${activeSessionId.value || 'default'}`)

const ensureCurrentSession = () => {
  if (currentSession.value) return currentSession.value
  const first = sessions.value[0]
  if (first) {
    activeSessionId.value = first.id
    return first
  }
  const created = createSession()
  sessions.value = [created]
  activeSessionId.value = created.id
  persistChatState()
  return created
}

const moveSessionToTop = (sessionId: string) => {
  const idx = sessions.value.findIndex((item) => item.id === sessionId)
  if (idx <= 0) return
  const [session] = sessions.value.splice(idx, 1)
  sessions.value.unshift(session)
}

const touchSession = (session: ChatSession) => {
  session.updatedAt = new Date().toISOString()
  session.title = deriveSessionTitle(session)
  moveSessionToTop(session.id)
}

const pushBubble = (role: ChatBubble['role'], text: string) => {
  const session = ensureCurrentSession()
  session.bubbles.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    text
  })
  touchSession(session)
  persistChatState()
}

const createNewSession = () => {
  const created = createSession()
  sessions.value.unshift(created)
  activeSessionId.value = created.id
  persistChatState()
  inputText.value = ''
  scrollToBottom()
}

const switchSession = (id: string) => {
  if (id === activeSessionId.value) return
  activeSessionId.value = id
  inputText.value = ''
  persistChatState()
  scrollToBottom()
}

const clearCurrentSession = () => {
  const session = ensureCurrentSession()
  session.bubbles = [buildWelcomeBubble()]
  session.title = '新会话'
  session.updatedAt = new Date().toISOString()
  persistChatState()
}

const deleteSession = (id: string) => {
  sessions.value = sessions.value.filter((item) => item.id !== id)
  if (sessions.value.length === 0) {
    const created = createSession()
    sessions.value = [created]
    activeSessionId.value = created.id
  } else if (activeSessionId.value === id) {
    activeSessionId.value = sessions.value[0].id
  }
  persistChatState()
}

const loadChatState = () => {
  const cached = safeParseSessions(localStorage.getItem(sessionsStorageKey.value))
  if (cached.length === 0) {
    const initial = createSession()
    sessions.value = [initial]
    activeSessionId.value = initial.id
    persistChatState()
    return
  }

  cached.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
  sessions.value = cached

  const storedActive = localStorage.getItem(activeStorageKey.value)
  const matched = storedActive && cached.some((item) => item.id === storedActive)
  activeSessionId.value = matched ? (storedActive as string) : cached[0].id
  persistChatState()
}

const escapeHtml = (value: string) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

const isAppHost = (hostname: string) => {
  const current = window.location.hostname
  return hostname === current || hostname === 'localhost' || hostname === '127.0.0.1'
}

const rewriteChatLink = (rawUrl: string) => {
  try {
    const url = new URL(rawUrl, window.location.origin)
    if (isAppHost(url.hostname) && url.pathname.startsWith('/products/')) {
      url.searchParams.set('from', 'chat')
      return `${url.pathname}${url.search}${url.hash}`
    }
    if (isAppHost(url.hostname) && (url.pathname.startsWith('/orders') || url.pathname.startsWith('/order/'))) {
      return `${url.pathname}${url.search}${url.hash}`
    }
    return rawUrl
  } catch {
    return rawUrl
  }
}

const linkTarget = (rawUrl: string) => {
  try {
    const url = new URL(rawUrl, window.location.origin)
    if (isAppHost(url.hostname) && (url.pathname.startsWith('/products/') || url.pathname.startsWith('/orders') || url.pathname.startsWith('/order/'))) {
      return '_self'
    }
    return '_blank'
  } catch {
    return '_blank'
  }
}

const renderMessageHtml = (value: string) => {
  const urlRegex = /https?:\/\/[^\s<]+/g
  let output = ''
  let lastIndex = 0
  let match: RegExpExecArray | null = null

  while ((match = urlRegex.exec(value)) !== null) {
    const start = match.index
    const rawUrl = match[0]
    output += escapeHtml(value.slice(lastIndex, start))

    const href = escapeHtml(rewriteChatLink(rawUrl))
    const label = escapeHtml(rawUrl)
    const target = linkTarget(rawUrl)
    output += `<a href="${href}" target="${target}" rel="noopener noreferrer">${label}</a>`
    lastIndex = start + rawUrl.length
  }

  output += escapeHtml(value.slice(lastIndex))
  return output.replace(/\n/g, '<br/>')
}

const scrollToBottom = async () => {
  await nextTick()
  chatLogRef.value?.scrollTo({ top: chatLogRef.value.scrollHeight, behavior: 'smooth' })
}

const sendMessage = async (overrideText?: string) => {
  const message = (overrideText ?? inputText.value).trim()
  if (!message || sending.value) return

  pushBubble('user', message)
  inputText.value = ''
  sending.value = true

  try {
    const response = await api.post<ChatSendResponse>('/chat/send', {
      message,
      sender_id: senderId.value
    })
    const replies = Array.isArray(response.data.messages) ? response.data.messages : []
    if (replies.length === 0) {
      pushBubble('bot', '暂时没有回复，请稍后重试。')
    } else {
      replies.forEach((item) => {
        if (typeof item.text === 'string' && item.text.trim()) {
          pushBubble('bot', item.text.trim())
        }
      })
    }
  } catch (err: any) {
    pushBubble('system', err.response?.data?.detail || '客服服务暂不可用，请稍后再试。')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

const sendQuickPrompt = async (prompt: string) => {
  await sendMessage(prompt)
}

const formatSessionTime = (isoText: string) => {
  const dt = new Date(isoText)
  if (Number.isNaN(dt.getTime())) return '-'
  return dt.toLocaleString()
}

onMounted(async () => {
  loadChatState()
  await scrollToBottom()
})

watch(
  () => authStore.user?.id,
  async () => {
    loadChatState()
    await scrollToBottom()
  }
)
</script>

<template>
  <section class="chat-page">
    <div class="hero">
      <div class="hero-head">
        <h1>在线客服</h1>
        <span class="user-chip">{{ userLabel }}</span>
      </div>
      <div class="quick-actions">
        <button v-for="item in quickPrompts" :key="item" type="button" @click="sendQuickPrompt(item)">
          {{ item }}
        </button>
      </div>
    </div>

    <div class="support-layout">
      <aside class="history-panel">
        <div class="history-head">
          <h2>会话管理</h2>
          <div class="history-actions">
            <button type="button" @click="createNewSession">新建</button>
            <button type="button" @click="clearCurrentSession">清空当前</button>
          </div>
        </div>

        <div class="history-list">
          <article v-for="session in sessions" :key="session.id" :class="session.id === activeSessionId ? 'history-item active' : 'history-item'">
            <button type="button" class="history-main" @click="switchSession(session.id)">
              <strong>{{ session.title }}</strong>
              <span>{{ formatSessionTime(session.updatedAt) }}</span>
            </button>
            <button type="button" class="history-del" @click.stop="deleteSession(session.id)">删除</button>
          </article>
        </div>
      </aside>

      <div class="chat-panel">
        <div ref="chatLogRef" class="chat-log" role="log" aria-live="polite">
          <article v-for="item in bubbles" :key="item.id" :class="`bubble ${item.role}`">
            <span class="tag">{{ item.role === 'user' ? '我' : item.role === 'bot' ? '客服' : '系统' }}</span>
            <p v-html="renderMessageHtml(item.text)"></p>
          </article>
        </div>

        <div class="input-row">
          <input
            v-model="inputText"
            type="text"
            placeholder="输入问题..."
            @keyup.enter="sendMessage"
          >
          <button type="button" :disabled="sending || !inputText.trim()" @click="sendMessage()">
            {{ sending ? '发送中...' : '发送' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.chat-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 18px 40px;
  display: grid;
  gap: 16px;
}

.hero {
  border-radius: 20px;
  padding: 20px;
  color: #fff7ea;
  background: linear-gradient(130deg, #2f2413 0%, #765322 52%, #315f58 100%);
  box-shadow: 0 18px 34px rgba(56, 39, 15, 0.25);
  display: grid;
  gap: 10px;
}

.hero-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.hero h1 {
  margin: 0;
  font-size: 28px;
}

.user-chip {
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
}

.quick-actions {
  margin-top: 2px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-actions button {
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.support-layout {
  display: grid;
  grid-template-columns: 290px 1fr;
  gap: 14px;
}

.history-panel {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 12px;
  display: grid;
  gap: 10px;
  height: fit-content;
}

.history-head {
  display: grid;
  gap: 8px;
}

.history-head h2 {
  margin: 0;
  font-size: 18px;
  color: #32291a;
}

.history-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.history-actions button {
  border: none;
  border-radius: 10px;
  padding: 8px 10px;
  background: #2f2413;
  color: #fff6e8;
  font-size: 12px;
  cursor: pointer;
}

.history-list {
  max-height: 520px;
  overflow: auto;
  display: grid;
  gap: 8px;
  padding-right: 2px;
}

.history-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
  border: 1px solid #e3d6c0;
  border-radius: 12px;
  background: #fff8ee;
  padding: 6px;
}

.history-item.active {
  border-color: #b6863e;
  box-shadow: 0 0 0 2px rgba(182, 134, 62, 0.16);
}

.history-main {
  border: none;
  background: transparent;
  text-align: left;
  display: grid;
  gap: 4px;
  cursor: pointer;
}

.history-main strong {
  color: #3f2f16;
  font-size: 13px;
  line-height: 1.4;
}

.history-main span {
  color: #7d7568;
  font-size: 11px;
}

.history-del {
  border: none;
  border-radius: 8px;
  padding: 4px 8px;
  background: #efe1c8;
  color: #624d29;
  font-size: 11px;
  cursor: pointer;
  align-self: center;
}

.chat-panel {
  background:
    radial-gradient(circle at 0% 0%, rgba(238, 219, 184, 0.44), transparent 36%),
    linear-gradient(180deg, #fffbf3 0%, #f8f2e6 100%);
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: clamp(640px, 76vh, 860px);
}

.chat-log {
  padding: 18px 16px 0;
  flex: 1 1 auto;
  min-height: 0;
  align-items: start;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(87, 64, 31, 0.42) rgba(112, 92, 56, 0.12);
  background: transparent;
  display: grid;
  gap: 2px;
}

.chat-log::-webkit-scrollbar {
  width: 10px;
}

.chat-log::-webkit-scrollbar-track {
  background: rgba(112, 92, 56, 0.12);
  border-radius: 999px;
}

.chat-log::-webkit-scrollbar-thumb {
  background: rgba(87, 64, 31, 0.42);
  border-radius: 999px;
}

.chat-log::-webkit-scrollbar-thumb:hover {
  background: rgba(87, 64, 31, 0.62);
}

.bubble {
  width: fit-content;
  max-width: min(84%, 720px);
  height: fit-content;
  border-radius: 14px;
  padding: 10px 12px;
  margin: 6px 0;
  line-height: 1.65;
  white-space: pre-wrap;
  display: grid;
  gap: 4px;
  border: 1px solid transparent;
}

.chat-log .bubble:last-child {
  margin-bottom: 0;
}

.bubble p {
  margin: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.tag {
  font-size: 11px;
  opacity: 0.75;
}

.bubble.user {
  justify-self: end;
  background: #2f2413;
  color: #fff7eb;
}

.bubble.bot {
  justify-self: start;
  align-self: flex-start;
  background: #f1e3ca;
  color: #433721;
  border-color: #e1cfb0;
}

.bubble.system {
  justify-self: center;
  background: #fff1f2;
  color: #be123c;
  max-width: min(92%, 760px);
  border-color: #fecdd3;
}

.input-row {
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  margin-top: 0;
  padding: 10px 12px 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  background: transparent;
}

.input-row input {
  border: 1px solid #d8cbb4;
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 14px;
  background: #fffef9;
}

.input-row button {
  border: none;
  border-radius: 999px;
  padding: 0 18px;
  background: #2f2413;
  color: #fff7ea;
  font-weight: 600;
  cursor: pointer;
}

.input-row button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

:deep(.bubble a) {
  color: inherit;
  text-decoration: underline;
  word-break: break-all;
}

@media (max-width: 980px) {
  .support-layout {
    grid-template-columns: 1fr;
  }

  .history-panel {
    order: 2;
  }

  .chat-panel {
    order: 1;
  }
}

@media (max-width: 760px) {
  .hero h1 {
    font-size: 24px;
  }

  .chat-panel {
    min-height: 78vh;
  }

  .bubble {
    max-width: 94%;
  }

  .input-row {
    grid-template-columns: 1fr;
  }

  .input-row button {
    min-height: 42px;
  }
}
</style>
