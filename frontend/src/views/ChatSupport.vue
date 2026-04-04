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

const quickPrompts = [
  '查询我的订单',
  '推荐几款手机',
  '推荐一些高性价比电脑',
  '帮我看下物流要怎么查'
]

const bubbles = ref<ChatBubble[]>([
  {
    id: 'welcome',
    role: 'bot',
    text: '你好，我是智能客服。你可以咨询订单、物流、商品推荐，或直接闲聊。'
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
      pushBubble('bot', '我暂时没有生成回复，请稍后再试。')
    } else {
      replies.forEach((item) => {
        if (typeof item.text === 'string' && item.text.trim()) {
          pushBubble('bot', item.text.trim())
        }
      })
    }
  } catch (err: any) {
    pushBubble('system', err.response?.data?.detail || '客服服务暂时不可用，请稍后再试。')
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
        <h1>智能客服中心</h1>
        <span class="user-chip">当前会话：{{ userLabel }}</span>
      </div>
      <p>订单查询、商品推荐、物流咨询一站式处理。回复里的链接可直接跳转到对应页面。</p>
      <div class="quick-actions">
        <button v-for="item in quickPrompts" :key="item" type="button" @click="sendQuickPrompt(item)">
          {{ item }}
        </button>
      </div>
    </div>

    <div class="chat-panel">
      <div ref="chatLogRef" class="chat-log" role="log" aria-live="polite">
        <article v-for="item in bubbles" :key="item.id" :class="`bubble ${item.role}`">
          <span class="tag">{{ item.role === 'user' ? '你' : item.role === 'bot' ? '客服' : '系统' }}</span>
          <p v-html="renderMessageHtml(item.text)"></p>
        </article>
      </div>

      <div class="input-row">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入你的问题，例如：查询我的订单 / 推荐几款手机"
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
  max-width: 1040px;
  margin: 0 auto;
  padding: 24px 18px 40px;
  display: grid;
  gap: 16px;
}

.hero {
  border-radius: 20px;
  padding: 22px;
  color: #fff;
  background:
    radial-gradient(circle at 85% 0%, rgba(255, 255, 255, 0.24), transparent 40%),
    linear-gradient(130deg, #0f2d53 0%, #0b5aa6 48%, #0f766e 100%);
  box-shadow: 0 18px 34px rgba(11, 76, 142, 0.22);
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
  font-size: 30px;
}

.hero p {
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
}

.user-chip {
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
}

.quick-actions {
  margin-top: 6px;
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
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 18px;
  overflow: hidden;
  display: grid;
  grid-template-rows: 1fr auto;
  min-height: 560px;
}

.chat-log {
  padding: 16px;
  overflow-y: auto;
  background:
    radial-gradient(circle at 0% 0%, rgba(207, 231, 255, 0.42), transparent 36%),
    linear-gradient(180deg, #f8fbff 0%, #f3f8fd 100%);
  display: grid;
  gap: 10px;
}

.bubble {
  max-width: 84%;
  border-radius: 14px;
  padding: 10px 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  display: grid;
  gap: 4px;
  border: 1px solid transparent;
}

.bubble p {
  margin: 0;
}

.tag {
  font-size: 11px;
  opacity: 0.75;
}

.bubble.user {
  justify-self: end;
  background: #0b5aa6;
  color: #fff;
  border-color: rgba(255, 255, 255, 0.16);
}

.bubble.bot {
  justify-self: start;
  background: #eaf4ff;
  color: #1a3657;
  border-color: #cfe3f7;
}

.bubble.system {
  justify-self: center;
  background: #fff1f2;
  color: #be123c;
  max-width: 92%;
  border-color: #fecdd3;
}

.input-row {
  border-top: 1px solid #e0eaf5;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  background: #fff;
}

.input-row input {
  border: 1px solid #c5d8ee;
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 14px;
}

.input-row button {
  border: none;
  border-radius: 12px;
  padding: 0 18px;
  background: #0b5aa6;
  color: #fff;
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

:deep(.bubble.user a) {
  color: #dff2ff;
}

@media (max-width: 760px) {
  .hero h1 {
    font-size: 26px;
  }

  .chat-panel {
    min-height: 72vh;
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
