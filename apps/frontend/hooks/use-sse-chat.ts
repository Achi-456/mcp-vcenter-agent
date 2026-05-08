"use client"

import { useCallback, useRef, useState } from "react"

export interface SSEMessage {
  type: "start" | "thought" | "tool_call" | "tool_result" | "token" | "final" | "blocked" | "error" | "done" | "session" | "node"
  session_id?: string
  run_id?: string
  content?: string
  tool?: string
  status?: string
  args?: Record<string, unknown>
  summary?: string
  node?: string
  output?: Record<string, unknown>
  reason?: string
  error_code?: string
  message?: string
}

export interface ChatStreamRequest {
  message: string
  session_id: string | null
  provider: string
  model: string
  allow_high_risk: boolean
  page_context?: Record<string, unknown>
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.dclab.local"

export function useSSEChat() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (
      request: ChatStreamRequest,
      onEvent: (event: SSEMessage) => void,
      onError: (error: string) => void,
    ) => {
      setIsStreaming(true)
      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await fetch(`${BASE_URL}/api/v1/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({
            message: request.message,
            session_id: request.session_id || sessionId,
            provider: request.provider || "gemini",
            model: request.model || "gemini-2.5-flash",
            allow_high_risk: request.allow_high_risk || false,
            page_context: request.page_context,
          }),
          signal: controller.signal,
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const reader = res.body?.getReader()
        if (!reader) throw new Error("No stream")

        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() || ""
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const evt = JSON.parse(line.slice(6)) as SSEMessage
                if (evt.type === "session" || evt.type === "start") {
                  if (evt.session_id) setSessionId(evt.session_id)
                }
                onEvent(evt)
              } catch { /* skip malformed JSON */ }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          onError(err.message)
        }
      } finally {
        setIsStreaming(false)
      }
    },
    [sessionId],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const newSession = useCallback(() => {
    setSessionId(null)
  }, [])

  return { send, stop, newSession, isStreaming, sessionId }
}
