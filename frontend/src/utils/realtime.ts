export interface RealtimeEventPayload {
  [key: string]: unknown
}

export interface RealtimeEvent {
  event: string
  data?: RealtimeEventPayload
  sent_at?: string
}

interface RealtimeClientOptions {
  token?: string | null
  onEvent: (event: RealtimeEvent) => void
  onOpen?: () => void
  onClose?: () => void
}

interface RealtimeClient {
  close: () => void
}

const buildRealtimeUrl = (token?: string | null) => {
  const envBase = String(import.meta.env.VITE_WS_BASE_URL || '').trim()
  const fallbackBase = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  const base = envBase || fallbackBase
  const url = new URL('/ws/realtime', base)

  if (token && token.trim()) {
    url.searchParams.set('token', token.trim())
  }
  return url.toString()
}

export const createRealtimeClient = (options: RealtimeClientOptions): RealtimeClient => {
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let retries = 0
  let closedManually = false

  const clearTimers = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  const scheduleReconnect = () => {
    if (closedManually) {
      return
    }
    const delay = Math.min(10000, 800 * 2 ** retries) + Math.floor(Math.random() * 240)
    retries += 1
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  const connect = () => {
    clearTimers()
    const url = buildRealtimeUrl(options.token)
    socket = new WebSocket(url)

    socket.onopen = () => {
      retries = 0
      options.onOpen?.()
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send('ping')
        }
      }, 20000)
    }

    socket.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data) as RealtimeEvent
        if (!parsed || typeof parsed.event !== 'string') {
          return
        }
        if (parsed.event === 'connected' || parsed.event === 'pong') {
          return
        }
        options.onEvent(parsed)
      } catch {
        // ignore malformed message
      }
    }

    socket.onerror = () => {
      socket?.close()
    }

    socket.onclose = (evt) => {
      clearTimers()
      options.onClose?.()
      // 1008 means the backend rejected auth; avoid reconnect storm with invalid token.
      if (!closedManually && evt.code !== 1008) {
        scheduleReconnect()
      }
    }
  }

  connect()

  return {
    close: () => {
      closedManually = true
      clearTimers()
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, 'manual_close')
      } else {
        socket?.close()
      }
      socket = null
    }
  }
}
