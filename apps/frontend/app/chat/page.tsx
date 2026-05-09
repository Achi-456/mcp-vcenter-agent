"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { useSSEChat } from "@/hooks/use-sse-chat"
import type { ChatEvent } from "@/lib/chat-events"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "agent"
  content: string
  nodes?: string[]
  plan?: { goal: string; risk: string; steps: Array<{ id: string; agent: string; tool: string; reason: string }> }
  error?: string
}

function ChatContent() {
  const searchParams = useSearchParams()
  const initialSessionId = searchParams?.get("session_id")

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const { send, stop, isStreaming, sessionId, newSession } = useSSEChat()

  useEffect(() => {
    if (initialSessionId) {
      api.getSession(initialSessionId).then(data => {
        if (data && data.values && data.values.messages) {
          const history: Message[] = data.values.messages.map((m: any) => ({
            role: m.type === "human" ? "user" : "agent",
            content: m.content || "",
            nodes: m.tool_calls ? m.tool_calls.map((t: any) => `tool:${t.name}`) : [],
          }))
          // Only take human/ai messages, exclude raw tool outputs for cleaner UI
          setMessages(history.filter(m => m.content || (m.nodes && m.nodes.length > 0)))
          
          // We need a way to set the session ID in the hook if it wasn't started by a send
          // But useSSEChat will pick it up on the next send if we pass it manually
        }
      })
    }
  }, [initialSessionId])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "agent", content: "", nodes: [] }])

    send(
      { 
        message: text, 
        session_id: sessionId || initialSessionId, 
        provider: "gemini", 
        model: "gemini-2.5-flash", 
        allow_high_risk: false 
      },
      (evt: ChatEvent) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = { ...updated[updated.length - 1] }
          last.nodes = [...(last.nodes || [])]
          if (evt.type === "start") { /* session started */ }
          if (evt.type === "intent") { last.nodes!.push(`intent:${evt.intent}`) }
          if (evt.type === "tool_call") { last.nodes!.push(`tool:${evt.tool}`) }
          if (evt.type === "tool_result") { last.nodes!.push(`result:${evt.tool}`) }
          if (evt.type === "final") { last.content = evt.content || last.content }
          if (evt.type === "blocked") { last.error = evt.message }
          if (evt.type === "error") last.error = evt.message
          updated[updated.length - 1] = last
          return updated
        })
      },
      (err) => {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { ...updated[updated.length - 1], error: err }
          return updated
        })
      },
    )
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h1 className="text-lg font-semibold">Agent Chat</h1>
          <p className="text-xs text-muted-foreground">
            {sessionId ? `Session ${sessionId.slice(0, 8)}...` : "New Session"}
          </p>
        </div>
        <Button variant="ghost" size="sm" className="text-xs" onClick={newSession}>
          + New
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <h2 className="text-lg font-semibold text-muted-foreground">AgenticOps Chat</h2>
              <p className="mt-1 text-sm text-muted-foreground/60">
                Ask about VMs, hosts, or operational tasks
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
            <div className="max-w-[80%] space-y-2">
              <Card className={cn(
                "px-4 py-3 text-sm",
                msg.role === "user"
                  ? "border-emerald-600/30 bg-emerald-600/10"
                  : "border-border bg-card"
              )}>
                <p className="whitespace-pre-wrap">{msg.content || (isStreaming && i === messages.length - 1 ? "..." : "")}</p>
              </Card>

              {msg.plan && (
                <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-[10px]">
                      {msg.plan.risk}
                    </Badge>
                    <span className="text-muted-foreground">{msg.plan.goal}</span>
                  </div>
                  {msg.plan.steps?.map((s) => (
                    <div key={s.id} className="flex gap-2 mt-1">
                      <span className="text-cyan-400 font-mono-code text-xs">{s.tool}</span>
                      <span className="text-muted-foreground">{s.reason}</span>
                    </div>
                  ))}
                </Card>
              )}

              {msg.nodes && msg.nodes.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {msg.nodes.map((n, j) => (
                    <Badge key={j} variant="secondary" className="text-[10px]">{n}</Badge>
                  ))}
                </div>
              )}

              {msg.error && (
                <Card className="border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                  {msg.error}
                </Card>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 border-t border-border pt-4">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder="Ask about your vCenter infrastructure..."
          className="min-h-[44px] resize-none text-sm"
          disabled={isStreaming}
          rows={1}
        />
        {isStreaming ? (
          <Button variant="destructive" size="sm" onClick={stop}>Stop</Button>
        ) : (
          <Button size="sm" onClick={handleSend} disabled={!input.trim()}>Send</Button>
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex h-[calc(100vh-7rem)] items-center justify-center">Loading chat...</div>}>
      <ChatContent />
    </Suspense>
  )
}
