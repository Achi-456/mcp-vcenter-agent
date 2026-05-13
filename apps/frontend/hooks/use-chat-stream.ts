'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { api, apiUrl } from '@/lib/api'
import type { ChatMessage, ChatStreamEvent, ChatEventType, PersistedChatMessage } from '@/lib/types'

const EVENT_TYPES: ChatEventType[] = [
  'start',
  'intent',
  'safety_check',
  'agent_start',
  'tool_call',
  'tool_result',
  'validation',
  'final',
  'error',
  'done',
]

function newId(prefix: string) {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function isChatEventType(value: unknown): value is ChatEventType {
  return typeof value === 'string' && EVENT_TYPES.includes(value as ChatEventType)
}

function parseSseFrames(buffer: string) {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const parts = normalized.split('\n\n')
  return {
    frames: parts.slice(0, -1),
    remainder: parts.at(-1) ?? '',
  }
}

function parseFrame(frame: string): ChatStreamEvent | null {
  const lines = frame.split('\n')
  const eventLine = lines.find((line) => line.startsWith('event:'))
  const dataLines = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart())
  const raw = dataLines.join('\n')

  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    let eventType: ChatEventType | null = null
    const namedEvent = eventLine?.slice(6).trim()
    if (isChatEventType(parsed.type)) {
      eventType = parsed.type
    } else if (isChatEventType(namedEvent)) {
      eventType = namedEvent
    }

    if (!eventType) return null

    return {
      id: newId('event'),
      type: eventType,
      timestamp: new Date().toISOString(),
      payload: parsed,
      raw,
    }
  } catch {
    return {
      id: newId('event'),
      type: 'error',
      timestamp: new Date().toISOString(),
      payload: {
        type: 'error',
        error_code: 'SSE_PARSE_ERROR',
        message: 'Unable to parse a chat stream event.',
      },
      raw,
    }
  }
}

function finalContent(events: ChatStreamEvent[]) {
  const finalEvent = [...events].reverse().find((event) => event.type === 'final')
  const content = finalEvent?.payload.content
  return typeof content === 'string' ? content : ''
}

function persistedToChatMessage(message: PersistedChatMessage): ChatMessage | null {
  if (message.role !== 'user' && message.role !== 'assistant') return null
  const events =
    message.role === 'assistant'
      ? [
          {
            id: newId('event'),
            type: 'final' as ChatEventType,
            timestamp: message.created_at,
            payload: { type: 'final', content: message.content, ...(message.metadata?.final as Record<string, unknown> | undefined) },
            raw: JSON.stringify({ type: 'final', content: message.content }),
          },
          {
            id: newId('event'),
            type: 'done' as ChatEventType,
            timestamp: message.created_at,
            payload: { type: 'done' },
            raw: JSON.stringify({ type: 'done' }),
          },
        ]
      : undefined
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: message.created_at,
    metadata: message.metadata,
    events,
  }
}

export function useChatStream(initialSessionId?: string | null) {
  const router = useRouter()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId ?? null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!initialSessionId) return
    let cancelled = false
    setIsLoadingHistory(true)
    setStreamError(null)
    void api.getSessionMessages(initialSessionId).then((response) => {
      if (cancelled) return
      if (response.ok) {
        setSessionId(initialSessionId)
        setMessages(response.data.map(persistedToChatMessage).filter((item): item is ChatMessage => Boolean(item)))
      } else {
        setStreamError(response.message)
      }
      setIsLoadingHistory(false)
    })
    return () => {
      cancelled = true
    }
  }, [initialSessionId])

  const startNewSession = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setMessages([])
    setSessionId(null)
    setIsStreaming(false)
    setIsLoadingHistory(false)
    setStreamError(null)
    router.replace('/chat')
  }, [router])

  const sendMessage = useCallback(
    async (message: string) => {
      const trimmed = message.trim()
      if (!trimmed || isStreaming) return

      const userMessage: ChatMessage = {
        id: newId('user'),
        role: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
      }
      const assistantId = newId('assistant')
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        events: [],
      }

      setMessages((current) => [...current, userMessage, assistantMessage])
      setStreamError(null)
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const response = await fetch(apiUrl('/api/v1/chat/stream'), {
          method: 'POST',
          headers: {
            Accept: 'text/event-stream',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: trimmed, session_id: sessionId }),
          signal: controller.signal,
        })

        if (!response.ok || !response.body) {
          throw new Error(`Chat stream failed with HTTP ${response.status}.`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const parsed = parseSseFrames(buffer)
          buffer = parsed.remainder

          for (const frame of parsed.frames) {
            const event = parseFrame(frame)
            if (!event) continue

            if (event.type === 'start') {
              const incomingSession = event.payload.session_id
              if (typeof incomingSession === 'string') {
                setSessionId(incomingSession)
                router.replace(`/chat?session_id=${encodeURIComponent(incomingSession)}`)
              }
            }

            setMessages((current) =>
              current.map((item) => {
                if (item.id !== assistantId) return item
                const events = [...(item.events ?? []), event]
                return {
                  ...item,
                  events,
                  content: finalContent(events),
                }
              }),
            )

            if (event.type === 'done') {
              setIsStreaming(false)
            }
          }
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          const messageText = error instanceof Error ? error.message : 'Chat stream failed.'
          setStreamError(messageText)
          const errorEvent: ChatStreamEvent = {
            id: newId('event'),
            type: 'error',
            timestamp: new Date().toISOString(),
            payload: {
              type: 'error',
              error_code: 'STREAM_ERROR',
              message: messageText,
            },
            raw: JSON.stringify({ type: 'error', message: messageText }),
          }

          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? {
                    ...item,
                    events: [...(item.events ?? []), errorEvent],
                  }
                : item,
            ),
          )
        }
      } finally {
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [isStreaming, sessionId],
  )

  return useMemo(
    () => ({
      messages,
      sessionId,
      isStreaming,
      isLoadingHistory,
      streamError,
      sendMessage,
      startNewSession,
    }),
    [messages, sessionId, isStreaming, isLoadingHistory, streamError, sendMessage, startNewSession],
  )
}
