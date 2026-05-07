"use client"

import { useCallback, useRef, useState } from "react"

export interface SSEMessage {
  type: "session" | "node" | "done" | "error"
  session_id?: string
  node?: string
  output?: Record<string, unknown>
  message?: string
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.dclab.local"

export function useSSEChat() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (
      message: string,
      onEvent: (event: SSEMessage) => void,
      onError: (error: string) => void,
    ) => {
      setIsStreaming(true)
      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await fetch(`${BASE_URL}/api/v1/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({ session_id: sessionId, message }),
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
                if (evt.type === "session" && evt.session_id) {
                  setSessionId(evt.session_id)
                }
                onEvent(evt)
              } catch { /* skip */ }
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
