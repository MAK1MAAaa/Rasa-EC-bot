<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface ChatBubble {
  id: string
  role: 'user' | 'bot' | 'system'
  text: string
}

interface ChatSendResponse {
  messages: Array<{ text: string }>
}

const authStore = useAuthStore()
const sending = ref(false)
const inputText = ref('')
const chatLogRef = ref<HTMLElement | null>(null)

const quickPrompts = ['查我的订单', '推荐几款手机', '推荐高性价比电脑', '物流怎么查']

const bubbles = ref<ChatBubble[]>([
  {
    id: 'welcome',
    role: 'bot',
    text: '你好，我是商城客服。'
  }
])

const senderId = computed(() => {
  const stored = localStorage.getItem('chat_sender_id')
  if (stored) {
    return stored
  }
  const base = authStore.user?.id || `guest-${Date.now()}`
  localStorage.setItem('chat_sender_id', base)
  return base
})

const userLabel = computed(() => authStore.user?.username || '游客')

const pushBubble = (role: ChatBubble['role'], text: string) => {
  bubbles.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    text
  })
}

const escapeHtml = (value: string) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

const renderMessageHtml = (value: string) => {
  const escaped = escapeHtml(value)
  const linked = escaped.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
  )
  return linked.replace(/\n/g, '<br/>')
}

const scrollToBottom = async () => {
  await nextTick()
  chatLogRef.value?.scrollTo({ top: chatLogRef.value.scrollHeight, behavior: 'smooth' })
}

const sendMessage = async (overrideText?: string) => {
  const message = (overrideText ?? inputText.value).trim()
  if (!message || sending.value) {
    return
  }

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
