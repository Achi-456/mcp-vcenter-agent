"use client"

import { useCallback, useRef, useState } from "react"
import type { ChatEvent, ChatStatus } from "@/lib/chat-events"
import { parseSSELine } from "@/lib/chat-events"

export type { ChatEvent, ChatStatus }

export interface ChatStreamRequest {
  message: string
  session_id: string | null
  provider: string
  model: string
  allow_high_risk: boolean
  page_context?: Record<string, unknown>
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ""

export function useSSEChat() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [status, setStatus] = useState<ChatStatus>("ready")
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (
      request: ChatStreamRequest,
      onEvent: (event: ChatEvent) => void,
      onError: (error: string) => void,
    ) => {
      setIsStreaming(true)
      setStatus("thinking")
      setError(null)
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
            const trimmed = line.trim()

            // Skip empty lines and event: lines (we parse from data: only)
            if (!trimmed || trimmed.startsWith("event:") || trimmed.startsWith(":")) continue

            const evt = parseSSELine(trimmed)
            if (!evt) continue

            // Update internal state based on event
            if (evt.type === "start") {
              if (evt.session_id) setSessionId(evt.session_id)
              if (evt.run_id) setCurrentRunId(evt.run_id)
              setStatus("thinking")
            }
            if (evt.type === "intent") setStatus("planning")
            if (evt.type === "tool_call") setStatus("running_tool")
            if (evt.type === "llm_start" || evt.type === "token") setStatus("streaming")
            if (evt.type === "blocked") setStatus("blocked")
            if (evt.type === "error") setStatus("error")
            if (evt.type === "done") setStatus("ready")

            onEvent(evt)
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message)
          setStatus("error")
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
    setStatus("ready")
  }, [])

  const newSession = useCallback(() => {
    setSessionId(null)
    setCurrentRunId(null)
    setStatus("ready")
    setError(null)
  }, [])

  return { send, stop, newSession, isStreaming, sessionId, currentRunId, status, error }
}
