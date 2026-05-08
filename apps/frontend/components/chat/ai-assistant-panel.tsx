"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { api, type LLMProvider, type LLMModel, type LLMStatus } from "@/lib/api"
import { useSSEChat } from "@/hooks/use-sse-chat"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Bot, X, ChevronRight, Zap, Server, HardDrive, Bell, Clock,
  Monitor, RefreshCw, Shield, Wrench, Lightbulb
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import type { ChatEvent, ChatMessage, ToolTraceEntry } from "@/lib/chat-events"
import { PlanCard } from "./plan-card"
import { ToolCallCard } from "./tool-call-card"
import { ToolResultCard } from "./tool-result-card"
import { TypingIndicator } from "./typing-indicator"
import { BlockedCard } from "./blocked-card"
import { ErrorCard } from "./error-card"
import { SessionHeader } from "./session-header"

const PROMPT_SHORTCUTS = [
  { id: "tools", label: "List Tools", icon: Wrench, prompt: "list down all the tools you have" },
  { id: "environment", label: "Environment", icon: Monitor, prompt: "Give me an environment overview of my vCenter infrastructure." },
  { id: "powered-off", label: "Powered-off VMs", icon: Zap, prompt: "Show me all powered-off VMs in my vCenter environment." },
  { id: "datastore", label: "Datastore Health", icon: HardDrive, prompt: "Analyze datastore health and highlight any critical datastores above 90% usage." },
  { id: "alarms", label: "Active Alarms", icon: Bell, prompt: "Summarize all active alarms grouped by severity." },
  { id: "events", label: "Recent Events", icon: Clock, prompt: "Show me recent events with errors and warnings." },
  { id: "rke2", label: "RKE2 VMs", icon: Server, prompt: "Show me all RKE2 cluster VMs." },
]

export function AIAssistantPanel({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [models, setModels] = useState<LLMModel[]>([])
  const [selectedProvider, setSelectedProvider] = useState("gemini")
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash")
  const [llmStatus, setLLMStatus] = useState<LLMStatus>({ configured: false, provider: null, model: null, ready: false })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [highRisk, setHighRisk] = useState(false)
  const [suggestedNext, setSuggestedNext] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { send, stop, isStreaming, sessionId, status, newSession } = useSSEChat()

  useEffect(() => { api.getLLMProviders().then(r => setProviders(r.providers)).catch(() => {}) }, [])
  useEffect(() => { api.getLLMStatus().then(setLLMStatus).catch(() => {}) }, [])

  useEffect(() => {
    if (!selectedProvider) return
    api.getLLMModels(selectedProvider).then(r => {
      setModels(r.models)
      if (r.models.length > 0) {
        setSelectedModel(prev => r.models.some(m => m.id === prev) ? prev : r.models[0].id)
      }
    }).catch(() => {})
  }, [selectedProvider])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleShortcut = useCallback((prompt: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setSuggestedNext(null)

    const assistantId = `assistant-${Date.now()}`
    const currentTrace: ToolTraceEntry[] = []
    const currentEvents: ChatEvent[] = []

    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
      events: currentEvents,
      toolTrace: currentTrace,
    }
    setMessages(prev => [...prev, assistantMsg])

    send(
      { message: prompt, session_id: sessionId, provider: selectedProvider, model: selectedModel, allow_high_risk: highRisk },
      (evt: ChatEvent) => {
        currentEvents.push(evt)

        switch (evt.type) {
          case "tool_call": {
            currentTrace.push({ name: evt.tool, status: "running", args: evt.args })
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "tool_cache_hit": {
            const existing = currentTrace.find(t => t.name === evt.tool)
            if (existing) {
              existing.status = "success"
            }
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "tool_result": {
            const idx = currentTrace.findIndex(t => t.name === evt.tool && t.status === "running")
            if (idx >= 0) {
              currentTrace[idx] = {
                ...currentTrace[idx],
                status: evt.status === "success" ? "success" : "error",
                summary: evt.summary || "",
                dataCount: evt.data_count,
              }
            }
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "tool_error": {
            currentTrace.push({
              name: evt.tool,
              status: "error",
              summary: evt.message || evt.error_code || "Tool failed",
            })
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "llm_start": {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, llmGenerated: true } : m))
            break
          }
          case "fallback_used": {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, fallbackUsed: true } : m))
            break
          }
          case "final": {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: evt.content || "" } : m))
            break
          }
          case "suggested_next_step": {
            setSuggestedNext(evt.content || null)
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, suggestedNextStep: evt.content } : m))
            break
          }
          case "blocked": {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, blocked: true, blockedMessage: evt.message } : m))
            break
          }
          case "error": {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, error: true, errorMessage: evt.message, content: evt.message } : m))
            break
          }
        }
      },
      (err) => {
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, error: true, errorMessage: err, content: `Error: ${err}` } : m))
      },
    )
  }, [send, sessionId, selectedProvider, selectedModel, highRisk])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    handleShortcut(text)
  }

  if (!visible) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex h-20 w-8 items-center justify-center rounded-l-lg border border-r-0 border-border bg-card text-muted-foreground hover:text-emerald-400 hover:border-emerald-500/30 transition-colors"
        title="Open AI Assistant"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    )
  }

  return (
    <div className="fixed right-0 top-0 z-40 flex h-screen w-[400px] flex-col border-l border-border bg-sidebar shadow-2xl">
      <SessionHeader
        sessionId={sessionId}
        status={status}
        provider={selectedProvider}
        model={selectedModel}
        onNewSession={() => { setMessages([]); setSuggestedNext(null); newSession() }}
        onToggle={onToggle}
      />

      {/* Provider + Model */}
      <div className="flex gap-2 border-b border-sidebar-border px-5 py-3">
        <Select value={selectedProvider} onValueChange={setSelectedProvider}>
          <SelectTrigger className="h-8 flex-1 text-xs bg-muted/30 border-sidebar-border">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            {providers.map(p => (
              <SelectItem key={p.id} value={p.id} className="text-xs">{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={selectedModel} onValueChange={setSelectedModel}>
          <SelectTrigger className="h-8 flex-1 text-xs bg-muted/30 border-sidebar-border">
            <SelectValue placeholder="Model" />
          </SelectTrigger>
          <SelectContent>
            {models.map(m => (
              <SelectItem key={m.id} value={m.id} className="text-xs">{m.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Prompt Shortcuts */}
      <div className="border-b border-sidebar-border px-5 py-3">
        <p className="text-[11px] font-medium text-muted-foreground mb-2 uppercase tracking-wider">Quick Actions</p>
        <div className="grid grid-cols-2 gap-1.5">
          {PROMPT_SHORTCUTS.map(s => (
            <button
              key={s.id}
              onClick={() => handleShortcut(s.prompt)}
              disabled={isStreaming}
              className="flex items-center gap-1.5 rounded-md border border-sidebar-border px-2 py-1.5 text-[11px] text-muted-foreground hover:text-sidebar-foreground hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-colors disabled:opacity-50"
            >
              <s.icon className="h-3 w-3 text-emerald-400" />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <Bot className="mx-auto h-6 w-6 text-muted-foreground/40 mb-2" />
              <p className="text-xs text-muted-foreground">Select a quick action or ask about your vCenter.</p>
              <p className="text-[11px] text-muted-foreground/60 mt-1">Try: &quot;list down all the tools you have&quot;</p>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={cn("space-y-1", m.role === "user" ? "flex justify-end" : "")}>
            {/* User message */}
            {m.role === "user" && m.content && (
              <Card className="border-emerald-600/30 bg-emerald-600/10 px-3 py-2 text-xs max-w-[90%] text-emerald-50">
                <p className="whitespace-pre-wrap break-words">{m.content}</p>
              </Card>
            )}

            {/* Assistant message */}
            {m.role === "assistant" && (
              <div className="space-y-1.5">
                {/* Blocked card */}
                {m.blocked && m.blockedMessage && (
                  <BlockedCard reason="approval_required" message={m.blockedMessage} />
                )}

                {/* Error card */}
                {m.error && m.errorMessage && (
                  <ErrorCard message={m.errorMessage} />
                )}

                {/* Plan card from intent event */}
                {m.events?.some(e => e.type === "intent") && (
                  <PlanCard
                    intent={m.events.find(e => e.type === "intent" && "intent" in e)?.intent as string | undefined}
                  />
                )}

                {/* Tool trace */}
                {m.toolTrace && m.toolTrace.length > 0 && (
                  <div className="space-y-1">
                    {m.toolTrace.map((t, i) => {
                      const event = m.events?.find(e =>
                        (e.type === "tool_call" && "tool" in e && e.tool === t.name) ||
                        (e.type === "tool_result" && "tool" in e && e.tool === t.name) ||
                        (e.type === "tool_error" && "tool" in e && e.tool === t.name) ||
                        (e.type === "tool_cache_hit" && "tool" in e && e.tool === t.name)
                      )
                      if (t.status === "running" && event?.type === "tool_call") {
                        return <ToolCallCard key={i} tool={t.name} args={t.args} status="running" />
                      }
                      if ((t.status === "success" || t.status === "error") && event) {
                        const et = event.type

                        const isErrorTool = et === "tool_error"
                        const isToolResult = et === "tool_result"
                        const isCacheHit = et === "tool_cache_hit"

                        if (isToolResult && "status" in event) {
                          return (
                            <ToolResultCard
                              key={i}
                              tool={t.name}
                              status={event.status as "success" | "error"}
                              summary={t.summary}
                              data_count={t.dataCount}
                              cached={isCacheHit || ("cached" in event ? Boolean((event as unknown as Record<string, unknown>).cached) : undefined)}
                            />
                          )
                        }
                        if (isErrorTool && "error_code" in event) {
                          return (
                            <ToolResultCard
                              key={i}
                              tool={t.name}
                              status="error"
                              summary={t.summary}
                              error_code={event.error_code}
                              message={event.message}
                            />
                          )
                        }
                        return (
                          <ToolResultCard
                            key={i}
                            tool={t.name}
                            status={t.status === "success" ? "success" : "error"}
                            summary={t.summary}
                            data_count={t.dataCount}
                          />
                        )
                      }
                      return null
                    })}
                  </div>
                )}

                {/* LLM generation status badge */}
                {m.llmGenerated && !m.content && (
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Generating answer...
                  </div>
                )}

                {/* Fallback used badge */}
                {m.fallbackUsed && (
                  <Card className="border-slate-500/20 bg-slate-500/5 px-3 py-1.5 text-[10px] text-muted-foreground">
                    Answer generated by fallback formatter (LLM not configured)
                  </Card>
                )}

                {/* Final answer content */}
                {m.content && !m.blocked && !m.error && (
                  <Card className="border-border bg-card px-3 py-2 text-xs text-sidebar-foreground">
                    <div className="prose prose-xs prose-invert max-w-none [&_table]:w-full [&_table]:text-[11px] [&_th]:text-left [&_th]:p-1 [&_td]:p-1 [&_h2]:text-sm [&_h2]:mt-2 [&_h2]:mb-1 [&_ul]:my-1 [&_li]:text-[11px] [&_hr]:my-2">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </Card>
                )}

                {/* Suggested next step */}
                {m.suggestedNextStep && (
                  <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px]">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Lightbulb className="h-3 w-3 text-cyan-400" />
                      <span className="text-cyan-400 font-medium">Suggested next step</span>
                    </div>
                    <p className="text-muted-foreground">{m.suggestedNextStep}</p>
                  </Card>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isStreaming && status !== "ready" && (
          <TypingIndicator status={status} />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-sidebar-border px-5 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <Switch checked={highRisk} onCheckedChange={setHighRisk} id="high-risk-switch" />
          <label htmlFor="high-risk-switch" className={cn("text-[11px] cursor-pointer select-none", highRisk ? "text-red-400 font-medium" : "text-muted-foreground")}>
            <Shield className="inline h-3 w-3 mr-1" />
            High-Risk Actions (blocked in Phase 1.4)
          </label>
        </div>
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            placeholder="Ask about your vCenter..."
            className="min-h-[40px] resize-none text-xs bg-muted/30 border-sidebar-border"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button variant="destructive" size="sm" className="h-10 px-3" onClick={stop}>
              <X className="h-4 w-4" />
            </Button>
          ) : (
            <Button size="sm" onClick={handleSend} disabled={!input.trim()} className="h-10 px-3">
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
