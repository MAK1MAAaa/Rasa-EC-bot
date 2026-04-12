<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

type ChatBubbleRole = 'user' | 'bot' | 'system'
type PendingDecision = 'confirm' | 'cancel'

interface ChatCard {
  type: string
  data: Record<string, any>
}

interface ChatAction {
  type: string
  label: string
  payload: Record<string, any>
  style?: string
}

interface ChatBubble {
  id: string
  role: ChatBubbleRole
  text: string
  cards: ChatCard[]
  actions: ChatAction[]
}

interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  bubbles: ChatBubble[]
}

interface ChatMessagePayload {
  text?: string
  cards?: any
  actions?: any
}

interface ChatSendResponse {
  messages: ChatMessagePayload[]
}

interface ChatUploadImageResponse {
  attachment_id: string
}

const authStore = useAuthStore()
const sending = ref(false)
const inputText = ref('')
const chatLogRef = ref<HTMLElement | null>(null)
const imageInputRef = ref<HTMLInputElement | null>(null)
const selectedImageFile = ref<File | null>(null)
const selectedImagePreviewUrl = ref('')

const quickPrompts = [
  '查询我的订单',
  '查询物流进度',
  '取消订单 ORD202604010001',
  '修改地址 ORD202604010001 地址: 上海市浦东新区世纪大道200号',
  '投诉物流 ORD202604010001 原因: 包裹长时间未更新'
]

const CHAT_GUEST_ID_KEY = 'chat_guest_id'
const CHAT_STORAGE_PREFIX = 'chat_sessions_v2'
const CHAT_ACTIVE_PREFIX = 'chat_active_session_v2'
const MAX_IMAGE_UPLOAD_MB = 8
const IMAGE_ACCEPT = ['image/jpeg', 'image/png', 'image/webp']

const readOrCreateGuestId = () => {
  const existing = localStorage.getItem(CHAT_GUEST_ID_KEY)
  if (existing) return existing
  const next = `guest-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(CHAT_GUEST_ID_KEY, next)
  return next
}

const sanitizeCards = (rawCards: any): ChatCard[] => {
  if (!Array.isArray(rawCards)) return []
  return rawCards
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const type = typeof item.type === 'string' ? item.type.trim() : ''
      if (!type) return null
      const data = item.data && typeof item.data === 'object' && !Array.isArray(item.data) ? item.data : {}
      return { type, data }
    })
    .filter((item): item is ChatCard => !!item)
}

const sanitizeActions = (rawActions: any): ChatAction[] => {
  if (!Array.isArray(rawActions)) return []
  return rawActions
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const type = typeof item.type === 'string' ? item.type.trim() : ''
      const label = typeof item.label === 'string' ? item.label.trim() : ''
      if (!type || !label) return null
      const payload = item.payload && typeof item.payload === 'object' && !Array.isArray(item.payload) ? item.payload : {}
      return {
        type,
        label,
        payload,
        style: typeof item.style === 'string' && item.style.trim() ? item.style.trim() : undefined
      }
    })
    .filter((item): item is ChatAction => !!item)
}

const buildBubble = (role: ChatBubbleRole, text: string, cards: ChatCard[] = [], actions: ChatAction[] = []): ChatBubble => ({
  id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  role,
  text,
  cards,
  actions
})

const guestIdentity = ref(readOrCreateGuestId())
const principalId = computed(() => authStore.user?.id || guestIdentity.value)
const sessionsStorageKey = computed(() => `${CHAT_STORAGE_PREFIX}:${principalId.value}`)
const activeStorageKey = computed(() => `${CHAT_ACTIVE_PREFIX}:${principalId.value}`)

const sessions = ref<ChatSession[]>([])
const activeSessionId = ref('')

const decisionModal = ref<{
  visible: boolean
  decision: PendingDecision
  card: ChatCard | null
  loading: boolean
}>({
  visible: false,
  decision: 'confirm',
  card: null,
  loading: false
})

const buildWelcomeBubble = (): ChatBubble =>
  buildBubble(
    'bot',
    '你好，我是商城客服。可以帮你查订单、改收货信息、取消订单、投诉物流，也能处理售后；涉及写操作时，我会先请求你确认。'
  )

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
              .filter((b: any) => ['user', 'bot', 'system'].includes(b?.role))
              .map((b: any) => {
                const text = typeof b?.text === 'string' ? b.text : ''
                const cards = sanitizeCards(b?.cards)
                const actions = sanitizeActions(b?.actions)
                return {
                  id: typeof b?.id === 'string' && b.id ? b.id : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                  role: b.role as ChatBubbleRole,
                  text,
                  cards,
                  actions
                }
              })
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

const userLabel = computed(() => authStore.user?.username || '访客')
const senderId = computed(() => `${principalId.value}:${activeSessionId.value || 'default'}`)

const modalTitle = computed(() => (decisionModal.value.decision === 'confirm' ? '确认执行操作' : '确认取消操作'))
const modalConfirmLabel = computed(() => {
  if (decisionModal.value.loading) return '处理中...'
  return decisionModal.value.decision === 'confirm' ? '确认执行' : '确认取消'
})

const modalCardDetails = computed(() => {
  const card = decisionModal.value.card
  if (!card || card.type !== 'pending_action') return [] as Array<{ label: string; value: string }>
  const details = Array.isArray(card.data?.details) ? card.data.details : []
  return details
    .map((item: any) => {
      const label = typeof item?.label === 'string' ? item.label.trim() : ''
      const value = typeof item?.value === 'string' ? item.value.trim() : ''
      return label && value ? { label, value } : null
    })
    .filter((item: any): item is { label: string; value: string } => !!item)
})

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
  session.title = '新会话'
  moveSessionToTop(session.id)
}

const pushBubble = (role: ChatBubbleRole, text: string, cards: ChatCard[] = [], actions: ChatAction[] = []) => {
  const session = ensureCurrentSession()
  session.bubbles.push(buildBubble(role, text, cards, actions))
  touchSession(session)
  persistChatState()
}

const appendReplyMessages = (messages: ChatMessagePayload[]) => {
  const replies = Array.isArray(messages) ? messages : []
  if (replies.length === 0) {
    pushBubble('bot', '暂时没有拿到有效回复，请再试一次。')
    return
  }

  let hasValidReply = false
  replies.forEach((item) => {
    const text = typeof item?.text === 'string' ? item.text.trim() : ''
    const cards = sanitizeCards(item?.cards)
    const actions = sanitizeActions(item?.actions)
    if (text || cards.length > 0 || actions.length > 0) {
      hasValidReply = true
      pushBubble('bot', text, cards, actions)
    }
  })

  if (!hasValidReply) {
    pushBubble('bot', '暂时没有拿到有效回复，请再试一次。')
  }
}

const createNewSession = () => {
  const created = createSession()
  sessions.value.unshift(created)
  activeSessionId.value = created.id
  persistChatState()
  inputText.value = ''
  clearImageSelection()
  scrollToBottom()
}

const switchSession = (id: string) => {
  if (id === activeSessionId.value) return
  activeSessionId.value = id
  inputText.value = ''
  clearImageSelection()
  persistChatState()
  scrollToBottom()
}

const clearCurrentSession = () => {
  const session = ensureCurrentSession()
  session.bubbles = [buildWelcomeBubble()]
  session.title = '新会话'
  session.updatedAt = new Date().toISOString()
  clearImageSelection()
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

const openLink = (rawUrl: string) => {
  const href = rewriteChatLink(rawUrl)
  const target = linkTarget(rawUrl)
  if (target === '_self') {
    window.location.href = href
    return
  }
  window.open(href, '_blank', 'noopener,noreferrer')
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

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
  if (status === 'cancelled') return '已取消'
  if (status === 'in_transit') return '运输中'
  if (status === 'delivered') return '已送达'
  return status || '未知状态'
}

const afterSalesStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    submitted: '待处理',
    merchant_approved: '商家已同意',
    processing: '处理中',
    merchant_rejected: '商家已拒绝',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status || '未知状态'
}

const afterSalesTypeLabel = (value: string) => {
  if (value === 'return') return '退货'
  if (value === 'exchange') return '换货'
  return value || '售后'
}

const complaintStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    submitted: '待处理',
    processing: '处理中',
    resolved: '已解决',
    rejected: '已驳回',
    cancelled: '已取消'
  }
  return map[status] || status || '未知状态'
}

const getText = (value: any, fallback = '-') => {
  if (typeof value !== 'string') return fallback
  const cleaned = value.trim()
  return cleaned || fallback
}

const getNum = (value: any, fallback = 0) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

const formatMoney = (value: any) => `楼 ${getNum(value).toFixed(2)}`

const formatRating = (value: any) => {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(1) : '-'
}

const formatShipHours = (value: any) => {
  const hours = Number(value)
  if (!Number.isFinite(hours) || hours < 0) return '-'
  return hours === 0 ? '即时发货' : `${hours} 小时发货`
}

const toTextList = (value: any): string[] => {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => (typeof item === 'string' ? item.trim() : ''))
    .filter(Boolean)
}

const formatDateText = (value: any) => {
  if (typeof value !== 'string' || !value.trim()) return '-'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleString()
}

const findPendingCard = () => {
  const current = bubbles.value
  for (let i = current.length - 1; i >= 0; i -= 1) {
    const card = current[i].cards.find((item) => item.type === 'pending_action')
    if (card) return card
  }
  return null
}

const openDecisionModal = (decision: PendingDecision, card?: ChatCard | null) => {
  decisionModal.value.visible = true
  decisionModal.value.decision = decision
  decisionModal.value.loading = false
  decisionModal.value.card = card || findPendingCard()
}

const closeDecisionModal = () => {
  if (decisionModal.value.loading) return
  decisionModal.value.visible = false
  decisionModal.value.card = null
}

const submitPendingDecision = async () => {
  if (decisionModal.value.loading) return
  decisionModal.value.loading = true

  const decision = decisionModal.value.decision
  pushBubble('user', decision === 'confirm' ? '确认执行' : '取消操作')

  try {
    const response = await api.post<ChatSendResponse>('/chat/pending-action/decision', { decision })
    appendReplyMessages(response.data.messages)
    decisionModal.value.visible = false
    decisionModal.value.card = null
  } catch (err: any) {
    pushBubble('system', err.response?.data?.detail || '待确认操作处理失败，请稍后再试。')
  } finally {
    decisionModal.value.loading = false
    await scrollToBottom()
  }
}

const onBubbleAction = (action: ChatAction, cardContext?: ChatCard | null) => {
  if (action.type === 'pending_action_decision') {
    const decision = action.payload?.decision === 'cancel' ? 'cancel' : 'confirm'
    openDecisionModal(decision, cardContext || null)
    return
  }

  const actionUrl = typeof action.payload?.url === 'string' ? action.payload.url : ''
  if (actionUrl) {
    openLink(actionUrl)
    return
  }

  pushBubble('system', '当前操作暂不支持直接执行。')
}

const scrollToBottom = async () => {
  await nextTick()
  chatLogRef.value?.scrollTo({ top: chatLogRef.value.scrollHeight, behavior: 'smooth' })
}

const clearImageSelection = () => {
  if (selectedImagePreviewUrl.value) {
    URL.revokeObjectURL(selectedImagePreviewUrl.value)
  }
  selectedImagePreviewUrl.value = ''
  selectedImageFile.value = null
  if (imageInputRef.value) {
    imageInputRef.value.value = ''
  }
}

const triggerImagePicker = () => {
  if (sending.value) return
  imageInputRef.value?.click()
}

const onImageSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    clearImageSelection()
    return
  }
  if (!IMAGE_ACCEPT.includes(file.type)) {
    pushBubble('system', '仅支持 JPG/PNG/WEBP 图片。')
    clearImageSelection()
    return
  }
  if (file.size > MAX_IMAGE_UPLOAD_MB * 1024 * 1024) {
    pushBubble('system', `图片不能超过 ${MAX_IMAGE_UPLOAD_MB}MB。`)
    clearImageSelection()
    return
  }

  if (selectedImagePreviewUrl.value) {
    URL.revokeObjectURL(selectedImagePreviewUrl.value)
  }
  selectedImageFile.value = file
  selectedImagePreviewUrl.value = URL.createObjectURL(file)
}

const uploadSelectedImage = async (): Promise<string | null> => {
  if (!selectedImageFile.value) return null
  const formData = new FormData()
  formData.append('file', selectedImageFile.value)
  const response = await api.post<ChatUploadImageResponse>('/chat/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data.attachment_id
}

const sendMessage = async (overrideText?: string) => {
  const message = (overrideText ?? inputText.value).trim()
  if (sending.value || (!message && !selectedImageFile.value)) return

  pushBubble('user', message || '[图片]')
  inputText.value = ''
  sending.value = true

  try {
    const attachmentId = await uploadSelectedImage()
    const attachments = attachmentId ? [attachmentId] : []
    const response = await api.post<ChatSendResponse>('/chat/send', {
      message,
      sender_id: senderId.value,
      attachments
    })
    appendReplyMessages(response.data.messages)
    clearImageSelection()
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

onBeforeUnmount(() => {
  clearImageSelection()
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
        <h1>智能客服</h1>
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
          <h2>会话历史</h2>
          <div class="history-actions">
            <button type="button" @click="createNewSession">新建会话</button>
            <button type="button" @click="clearCurrentSession">清空当前</button>
          </div>
        </div>

        <div class="history-list">
          <article
            v-for="session in sessions"
            :key="session.id"
            :class="session.id === activeSessionId ? 'history-item active' : 'history-item'"
          >
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
            <span class="tag">{{ item.role === 'user' ? '用户' : item.role === 'bot' ? '客服' : '系统' }}</span>
            <p v-if="item.text" v-html="renderMessageHtml(item.text)"></p>

            <div v-if="item.cards.length > 0" class="bubble-cards">
              <article
                v-for="(card, cardIndex) in item.cards"
                :key="`${item.id}-${cardIndex}`"
                :class="['chat-card', `type-${card.type}`]"
              >
                <template v-if="card.type === 'product'">
                  <div class="card-head">
                    <strong>{{ getText(card.data.name, '商品') }}</strong>
                    <span class="pill">{{ getText(card.data.category, '商品') }}</span>
                  </div>
                  <div class="card-row">
                    <span>{{ formatMoney(card.data.price) }}</span>
                    <span v-if="getNum(card.data.original_price) > getNum(card.data.price)">原价 {{ formatMoney(card.data.original_price) }}</span>
                  </div>
                  <div class="card-row muted">
                    <span>{{ getText(card.data.brand, '未知品牌') }}</span>
                    <span v-if="card.data.model">{{ getText(card.data.model, '') }}</span>
                  </div>
                  <div class="card-row muted">
                    <span>评分 {{ formatRating(card.data.rating) }}</span>
                    <span>月销 {{ getNum(card.data.monthly_sales) }}</span>
                  </div>
                  <div class="card-row muted">
                    <span>{{ formatShipHours(card.data.ship_in_hours) }}</span>
                    <span>库存 {{ getNum(card.data.stock) }}</span>
                  </div>
                  <div v-if="toTextList(card.data.tags).length > 0" class="tag-list">
                    <span v-for="tag in toTextList(card.data.tags).slice(0, 4)" :key="tag" class="pill">{{ tag }}</span>
                  </div>
                  <div class="card-row muted" v-if="card.data.shop_name">{{ card.data.shop_name }}</div>
                  <div class="card-actions" v-if="card.data.product_link">
                    <button type="button" @click="openLink(card.data.product_link)">查看商品</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'order'">
                  <div class="card-head">
                    <strong>订单 {{ getText(card.data.id) }}</strong>
                    <span class="pill">{{ getText(card.data.status_label, orderStatusLabel(getText(card.data.status, ''))) }}</span>
                  </div>
                  <div class="card-row">
                    <span>{{ getNum(card.data.item_count) }} 件商品</span>
                    <span>{{ formatMoney(card.data.total_amount) }}</span>
                  </div>
                  <div class="card-row muted">{{ formatDateText(card.data.created_at) }}</div>
                  <div class="card-actions" v-if="card.data.order_link">
                    <button type="button" @click="openLink(card.data.order_link)">查看订单</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'logistics'">
                  <div class="card-head">
                    <strong>物流 {{ getText(card.data.id) }}</strong>
                    <span class="pill">{{ getText(card.data.status_label, orderStatusLabel(getText(card.data.status, ''))) }}</span>
                  </div>
                  <div class="card-row muted" v-if="card.data.tracking_no">运单号：{{ getText(card.data.tracking_no) }}</div>
                  <div class="card-row muted" v-if="card.data.current_location">当前位置：{{ getText(card.data.current_location) }}</div>
                  <div class="card-row muted" v-if="card.data.estimated_delivery_text || card.data.estimated_delivery_at">
                    预计送达：{{ getText(card.data.estimated_delivery_text, formatDateText(card.data.estimated_delivery_at)) }}
                  </div>
                  <div class="card-row muted" v-if="Array.isArray(card.data.route_plan) && card.data.route_plan.length > 0">
                    路线规划：{{ card.data.route_plan.join(' -> ') }}
                  </div>
                  <div class="card-actions" v-if="card.data.order_link">
                    <button type="button" @click="openLink(card.data.order_link)">查看订单</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'after_sales'">
                  <div class="card-head">
                    <strong>售后 {{ getText(card.data.id) }}</strong>
                    <span class="pill">{{ getText(card.data.status_label, afterSalesStatusLabel(getText(card.data.status, ''))) }}</span>
                  </div>
                  <div class="card-row">订单编号：{{ getText(card.data.order_id) }}</div>
                  <div class="card-row">售后类型：{{ getText(card.data.type_label, afterSalesTypeLabel(getText(card.data.type, ''))) }}</div>
                  <div class="card-row muted" v-if="card.data.created_at_text || card.data.created_at">
                    申请时间：{{ getText(card.data.created_at_text, formatDateText(card.data.created_at)) }}
                  </div>
                  <div class="card-row muted" v-if="card.data.reason">原因：{{ getText(card.data.reason) }}</div>
                  <div class="card-actions" v-if="card.data.order_link">
                    <button type="button" @click="openLink(card.data.order_link)">查看订单</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'logistics_complaint'">
                  <div class="card-head">
                    <strong>物流投诉 {{ getText(card.data.id) }}</strong>
                    <span class="pill">{{ getText(card.data.status_label, complaintStatusLabel(getText(card.data.status, ''))) }}</span>
                  </div>
                  <div class="card-row">订单编号：{{ getText(card.data.order_id) }}</div>
                  <div class="card-row muted" v-if="card.data.created_at || card.data.updated_at">
                    更新时间：{{ formatDateText(card.data.updated_at || card.data.created_at) }}
                  </div>
                  <div class="card-row muted" v-if="card.data.reason">投诉原因：{{ getText(card.data.reason) }}</div>
                  <div class="card-row muted" v-if="card.data.resolution_note">处理备注：{{ getText(card.data.resolution_note) }}</div>
                  <div class="card-actions" v-if="card.data.order_link">
                    <button type="button" @click="openLink(card.data.order_link)">查看订单</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'pending_action'">
                  <div class="card-head">
                    <strong>{{ getText(card.data.title, '待确认操作') }}</strong>
                    <span class="pill warn">待确认</span>
                  </div>
                  <div class="card-row muted" v-if="card.data.description">{{ getText(card.data.description, '') }}</div>
                  <div v-if="Array.isArray(card.data.details)" class="detail-list">
                    <div
                      v-for="(detail, detailIndex) in card.data.details"
                      :key="`${item.id}-${cardIndex}-${detailIndex}`"
                      class="detail-item"
                    >
                      <span>{{ getText(detail?.label, '-') }}</span>
                      <strong>{{ getText(detail?.value, '-') }}</strong>
                    </div>
                  </div>
                  <div class="card-actions">
                    <button type="button" @click="openDecisionModal('confirm', card)">确认</button>
                    <button type="button" class="danger" @click="openDecisionModal('cancel', card)">取消</button>
                  </div>
                </template>

                <template v-else-if="card.type === 'image_analysis'">
                  <div class="card-head">
                    <strong>图片分析结果</strong>
                    <span class="pill">{{ getText(card.data.severity, 'medium') }}</span>
                  </div>
                  <div class="card-row">问题类型：{{ getText(card.data.issue_type, 'unknown') }}</div>
                  <div class="card-row muted" v-if="card.data.evidence">依据：{{ getText(card.data.evidence) }}</div>
                  <div class="card-row muted" v-if="card.data.suggested_action">建议：{{ getText(card.data.suggested_action) }}</div>
                  <div class="card-row muted">置信度：{{ `${Math.round(getNum(card.data.confidence) * 100)}%` }}</div>
                  <div class="card-actions">
                    <button
                      type="button"
                      @click="sendMessage(`请根据图片分析结果生成售后待确认草案，附件ID：${getText(card.data.attachment_id, '')}`)"
                    >
                      生成售后草案
                    </button>
                  </div>
                </template>

                <template v-else>
                  <div class="card-head">
                    <strong>{{ card.type }}</strong>
                  </div>
                  <div class="card-row muted">{{ JSON.stringify(card.data) }}</div>
                </template>
              </article>
            </div>

            <div v-if="item.actions.length > 0" class="bubble-actions">
              <button
                v-for="(action, actionIndex) in item.actions"
                :key="`${item.id}-action-${actionIndex}`"
                :class="action.style || ''"
                type="button"
                @click="onBubbleAction(action, item.cards.find((card) => card.type === 'pending_action') || null)"
              >
                {{ action.label }}
              </button>
            </div>
          </article>
        </div>

        <div class="input-row">
          <input
            ref="imageInputRef"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="hidden-file-input"
            @change="onImageSelected"
          >
          <div v-if="selectedImagePreviewUrl" class="attachment-preview">
            <img :src="selectedImagePreviewUrl" alt="attachment preview">
            <button type="button" class="danger" @click="clearImageSelection">移除图片</button>
          </div>
          <button type="button" class="upload-btn" :disabled="sending" @click="triggerImagePicker">
            上传图片
          </button>
          <input
            v-model="inputText"
            type="text"
            placeholder="输入你的问题..."
            @keyup.enter="sendMessage"
          >
          <button type="button" :disabled="sending || (!inputText.trim() && !selectedImageFile)" @click="sendMessage()">
            {{ sending ? '发送中...' : '发送' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="decisionModal.visible" class="decision-mask" @click.self="closeDecisionModal">
      <section class="decision-card">
        <h3>{{ modalTitle }}</h3>
        <p v-if="decisionModal.card?.data?.description" class="modal-desc">{{ getText(decisionModal.card.data.description, '') }}</p>

        <div v-if="modalCardDetails.length > 0" class="detail-list">
          <div v-for="(detail, index) in modalCardDetails" :key="`modal-${index}`" class="detail-item">
            <span>{{ detail.label }}</span>
            <strong>{{ detail.value }}</strong>
          </div>
        </div>

        <div class="decision-actions">
          <button type="button" class="ghost" :disabled="decisionModal.loading" @click="closeDecisionModal">关闭</button>
          <button
            type="button"
            :class="decisionModal.decision === 'confirm' ? 'primary' : 'danger'"
            :disabled="decisionModal.loading"
            @click="submitPendingDecision"
          >
            {{ modalConfirmLabel }}
          </button>
        </div>
      </section>
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
  gap: 6px;
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
  max-width: min(90%, 760px);
  height: fit-content;
  border-radius: 14px;
  padding: 10px 12px;
  margin: 6px 0;
  line-height: 1.65;
  white-space: pre-wrap;
  display: grid;
  gap: 8px;
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

.bubble-cards {
  display: grid;
  gap: 8px;
}

.chat-card {
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid #e6d8be;
  border-radius: 12px;
  padding: 10px;
  display: grid;
  gap: 6px;
  color: #2d2416;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.pill {
  border-radius: 999px;
  background: #f2e2c2;
  color: #543f1e;
  font-size: 11px;
  padding: 4px 10px;
}

.pill.warn {
  background: #feedd0;
  color: #7a4b14;
}

.card-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}

.card-row.muted {
  color: #6f6554;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-list {
  display: grid;
  gap: 6px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  font-size: 13px;
}

.detail-item span {
  color: #6f6554;
}

.card-actions,
.bubble-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.card-actions button,
.bubble-actions button {
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  background: #2f2413;
  color: #fff7ea;
  cursor: pointer;
  font-size: 12px;
}

.card-actions button.danger,
.bubble-actions button.danger {
  background: #be123c;
}

.input-row {
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  margin-top: 0;
  padding: 10px 12px 12px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  background: transparent;
}

.hidden-file-input {
  display: none;
}

.attachment-preview {
  grid-column: 1 / 4;
  display: flex;
  align-items: center;
  gap: 10px;
}

.attachment-preview img {
  width: 54px;
  height: 54px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid #d9c9ad;
}

.upload-btn {
  border: none;
  border-radius: 999px;
  padding: 0 14px;
  background: #315f58;
  color: #f2fff8;
  font-size: 12px;
  cursor: pointer;
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

.decision-mask {
  position: fixed;
  inset: 0;
  background: rgba(31, 24, 13, 0.42);
  display: grid;
  place-items: center;
  z-index: 40;
  padding: 16px;
}

.decision-card {
  width: min(520px, 100%);
  background: #fffaf1;
  border: 1px solid #e5d5b7;
  border-radius: 16px;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.decision-card h3 {
  margin: 0;
  color: #332717;
}

.modal-desc {
  margin: 0;
  color: #6f6554;
  font-size: 14px;
}

.decision-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.decision-actions button {
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}

.decision-actions .ghost {
  background: #efe3cb;
  color: #4d3a1e;
}

.decision-actions .primary {
  background: #2f2413;
  color: #fff7ea;
}

.decision-actions .danger {
  background: #be123c;
  color: #fff7fb;
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
    max-width: 96%;
  }

  .input-row {
    grid-template-columns: 1fr;
  }

  .attachment-preview {
    grid-column: 1;
  }

  .input-row button {
    min-height: 42px;
  }

  .decision-actions {
    flex-direction: column;
  }
}
</style>






