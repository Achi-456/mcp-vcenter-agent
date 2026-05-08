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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Bot, X, ChevronRight, Zap, Server, HardDrive, Bell, Clock, Monitor, RefreshCw, Shield, Wrench, Lightbulb, AlertTriangle } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
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
  const [modelLoading, setModelLoading] = useState(false)
  const [modelError, setModelError] = useState<string | null>(null)
  const [providerConnected, setProviderConnected] = useState(true)
  const [llmStatus, setLLMStatus] = useState<LLMStatus>({ configured: false, provider: null, model: null, ready: false })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [highRisk, setHighRisk] = useState(false)
  const [suggestedNext, setSuggestedNext] = useState<string | null>(null)
  const [connectModalOpen, setConnectModalOpen] = useState(false)
  const [pendingProvider, setPendingProvider] = useState<string | null>(null)
  const [connectApiKey, setConnectApiKey] = useState("")
  const [connectBaseUrl, setConnectBaseUrl] = useState("")
  const [connectLoading, setConnectLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { send, stop, isStreaming, sessionId, status, newSession } = useSSEChat()

  useEffect(() => { api.getLLMProviders().then(r => setProviders(r.providers)).catch(() => {}) }, [])

  const checkProvider = useCallback(async (provider: string) => {
    setModelLoading(true)
    setModelError(null)
    try {
      const res = await api.getLLMModels(provider)
      if (!res.connected || res.error_code === "PROVIDER_NOT_CONNECTED") {
        setProviderConnected(false)
        setModelLoading(false)
        setPendingProvider(provider)
        setConnectModalOpen(true)
        return false
      }
      if (res.error_code) {
        setModelError(res.message || "Failed to fetch models")
        setProviderConnected(false)
        setModelLoading(false)
        return false
      }
      const modelList = res.models || []
      setModels(modelList)
      if (modelList.length > 0) {
        setSelectedModel(res.default_model || modelList[0].id)
      }
      setProviderConnected(true)
      setModelLoading(false)
      return true
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to fetch models"
      setModelError(msg)
      setProviderConnected(false)
      setModelLoading(false)
      return false
    }
  }, [])

  const onProviderChange = useCallback(async (provider: string) => {
    const prevProvider = selectedProvider
    const prevModel = selectedModel
    setSelectedProvider(provider)
    setModels([])
    setModelError(null)

    const ok = await checkProvider(provider)
    if (!ok) {
      setSelectedProvider(prevProvider)
      setSelectedModel(prevModel)
    }
  }, [selectedProvider, selectedModel, checkProvider])

  useEffect(() => {
    api.getLLMStatus().then(s => {
      setLLMStatus(s)
      if (s.configured && s.provider) {
        setSelectedProvider(s.provider)
        checkProvider(s.provider)
      }
    }).catch(() => {})
  }, [checkProvider])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const autoResize = () => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = "auto"
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
    }
  }

  const handleShortcut = useCallback((prompt: string) => {
    if (!providerConnected || !selectedModel) return

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
            if (existing) existing.status = "success"
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "tool_result": {
            const idx = currentTrace.findIndex(t => t.name === evt.tool && t.status === "running")
            if (idx >= 0) {
              currentTrace[idx] = { ...currentTrace[idx], status: evt.status === "success" ? "success" : "error", summary: evt.summary || "", dataCount: evt.data_count }
            }
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "tool_error": {
            currentTrace.push({ name: evt.tool, status: "error", summary: evt.message || evt.error_code || "Tool failed" })
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolTrace: [...currentTrace] } : m))
            break
          }
          case "llm_start": setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, llmGenerated: true } : m)); break
          case "fallback_used": setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, fallbackUsed: true } : m)); break
          case "final": setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: evt.content || "" } : m)); break
          case "suggested_next_step": setSuggestedNext(evt.content || null); setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, suggestedNextStep: evt.content } : m)); break
          case "blocked": setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, blocked: true, blockedMessage: evt.message } : m)); break
          case "error": setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, error: true, errorMessage: evt.message, content: evt.message } : m)); break
        }
      },
      (err) => { setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, error: true, errorMessage: err, content: `Error: ${err}` } : m)) },
    )
  }, [send, sessionId, selectedProvider, selectedModel, highRisk, providerConnected])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming || !providerConnected || !selectedModel) return
    setInput("")
    handleShortcut(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleConnect = async () => {
    if (!pendingProvider || !connectApiKey.trim()) return
    setConnectLoading(true)
    try {
      const testResult = await api.testLLMConnection({
        provider: pendingProvider,
        base_url: connectBaseUrl || "https://api.openai.com/v1",
        model: "default",
        api_key: connectApiKey,
      })
      if (!testResult.ok) {
        setModelError(testResult.message || "Connection test failed")
        setConnectLoading(false)
        return
      }
      await api.saveLLMConnection({
        provider: pendingProvider,
        base_url: connectBaseUrl || "https://api.openai.com/v1",
        model: "default",
        api_key: connectApiKey,
      })
      setConnectModalOpen(false)
      setConnectApiKey("")
      setConnectBaseUrl("")
      setConnectLoading(false)
      await checkProvider(pendingProvider)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed"
      setModelError(msg)
      setConnectLoading(false)
    }
  }

  const canSend = providerConnected && !!selectedModel && !isStreaming && !modelLoading

  if (!visible) {
    return (
      <button onClick={onToggle} className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex h-20 w-8 items-center justify-center rounded-l-lg border border-r-0 border-border bg-card text-muted-foreground hover:text-emerald-400 hover:border-emerald-500/30 transition-colors" title="Open AI Assistant">
        <ChevronRight className="h-4 w-4" />
      </button>
    )
  }

  return (
    <aside className="fixed right-0 top-0 z-50 flex h-dvh w-full sm:w-[420px] flex-col border-l border-border bg-sidebar shadow-2xl">
      <SessionHeader
        sessionId={sessionId}
        status={status}
        provider={selectedProvider}
        model={selectedModel}
        onNewSession={() => { setMessages([]); setSuggestedNext(null); newSession() }}
        onToggle={onToggle}
      />

      <div className="shrink-0 flex gap-2 border-b border-sidebar-border px-5 py-3">
        <Select value={selectedProvider} onValueChange={onProviderChange}>
          <SelectTrigger className="h-8 flex-1 text-xs bg-muted/30 border-sidebar-border">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            {providers.map(p => (
              <SelectItem key={p.id} value={p.id} className="text-xs">{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {modelLoading ? (
          <div className="flex h-8 flex-1 items-center justify-center text-xs text-muted-foreground bg-muted/30 rounded-md border border-sidebar-border">
            <Loader2 className="h-3 w-3 animate-spin mr-1" />Loading...
          </div>
        ) : (
          <Select value={selectedModel} onValueChange={setSelectedModel} disabled={!providerConnected || models.length === 0}>
            <SelectTrigger className="h-8 flex-1 text-xs bg-muted/30 border-sidebar-border">
              <SelectValue placeholder={providerConnected ? "Select model" : "Not connected"} />
            </SelectTrigger>
            <SelectContent>
              {models.map(m => (
                <SelectItem key={m.id} value={m.id} className="text-xs">{m.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {modelError && (
        <div className="shrink-0 border-b border-sidebar-border px-5 py-2">
          <Card className="border-red-500/20 bg-red-500/5 px-3 py-1.5 text-[11px] text-red-400 flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3" />{modelError}
          </Card>
        </div>
      )}

      {!providerConnected && (
        <div className="shrink-0 border-b border-sidebar-border px-5 py-2">
          <Card className="border-amber-500/20 bg-amber-500/5 px-3 py-1.5 text-[11px] text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3" />Connect {selectedProvider} first
          </Card>
        </div>
      )}

      <div className="shrink-0 border-b border-sidebar-border px-5 py-3">
        <p className="text-[11px] font-medium text-muted-foreground mb-2 uppercase tracking-wider">Quick Actions</p>
        <div className="grid grid-cols-2 gap-1.5">
          {PROMPT_SHORTCUTS.map(s => (
            <button key={s.id} onClick={() => handleShortcut(s.prompt)} disabled={!canSend}
              className="flex items-center gap-1.5 rounded-md border border-sidebar-border px-2 py-1.5 text-[11px] text-muted-foreground hover:text-sidebar-foreground hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-colors disabled:opacity-50">
              <s.icon className="h-3 w-3 text-emerald-400" />{s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3 space-y-3">
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
            {m.role === "user" && m.content && (
              <Card className="border-emerald-600/30 bg-emerald-600/10 px-3 py-2 text-xs max-w-[90%] text-emerald-50">
                <p className="whitespace-pre-wrap break-words">{m.content}</p>
              </Card>
            )}

            {m.role === "assistant" && (
              <div className="space-y-1.5">
                {m.blocked && m.blockedMessage && <BlockedCard reason="approval_required" message={m.blockedMessage} />}
                {m.error && m.errorMessage && <ErrorCard message={m.errorMessage} />}
                {m.events?.some(e => e.type === "intent") && (
                  <PlanCard intent={m.events.find(e => e.type === "intent" && "intent" in e)?.intent as string | undefined} />
                )}

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
                          return <ToolResultCard key={i} tool={t.name} status={event.status as "success" | "error"} summary={t.summary} data_count={t.dataCount} cached={isCacheHit || ("cached" in event ? Boolean((event as unknown as Record<string, unknown>).cached) : undefined)} />
                        }
                        if (isErrorTool && "error_code" in event) {
                          return <ToolResultCard key={i} tool={t.name} status="error" summary={t.summary} error_code={event.error_code} message={event.message} />
                        }
                        return <ToolResultCard key={i} tool={t.name} status={t.status === "success" ? "success" : "error"} summary={t.summary} data_count={t.dataCount} />
                      }
                      return null
                    })}
                  </div>
                )}

                {m.llmGenerated && !m.content && (
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground"><RefreshCw className="h-3 w-3 animate-spin" />Generating answer...</div>
                )}
                {m.fallbackUsed && (
                  <Card className="border-slate-500/20 bg-slate-500/5 px-3 py-1.5 text-[10px] text-muted-foreground">Answer generated by fallback formatter (LLM not configured)</Card>
                )}

                {m.content && !m.blocked && !m.error && (
                  <Card className="border-border bg-card px-3 py-2 text-xs text-sidebar-foreground">
                    <div className="prose prose-xs prose-invert max-w-none overflow-x-auto [&_table]:w-full [&_table]:text-[11px] [&_th]:text-left [&_th]:p-1 [&_td]:p-1 [&_h2]:text-sm [&_h2]:mt-2 [&_h2]:mb-1 [&_ul]:my-1 [&_li]:text-[11px] [&_hr]:my-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  </Card>
                )}

                {m.suggestedNextStep && (
                  <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px]">
                    <div className="flex items-center gap-1.5 mb-1"><Lightbulb className="h-3 w-3 text-cyan-400" /><span className="text-cyan-400 font-medium">Suggested next step</span></div>
                    <p className="text-muted-foreground">{m.suggestedNextStep}</p>
                  </Card>
                )}
              </div>
            )}
          </div>
        ))}

        {isStreaming && status !== "ready" && <TypingIndicator status={status} />}
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 border-t border-sidebar-border px-5 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <Switch checked={highRisk} onCheckedChange={setHighRisk} id="high-risk-switch" />
          <label htmlFor="high-risk-switch" className={cn("text-[11px] cursor-pointer select-none", highRisk ? "text-red-400 font-medium" : "text-muted-foreground")}>
            <Shield className="inline h-3 w-3 mr-1" />High-Risk Actions ({highRisk ? "allowed (may be blocked)" : "blocked"})
          </label>
        </div>
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => { setInput(e.target.value); autoResize() }}
            onKeyDown={handleKeyDown}
            placeholder={providerConnected ? "Ask about your vCenter..." : "Connect a provider first..."}
            disabled={!canSend}
            rows={1}
            className="max-h-40 min-h-[48px] flex-1 resize-none overflow-y-auto rounded-lg border border-sidebar-border bg-muted/30 px-3 py-2.5 text-xs text-sidebar-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 disabled:opacity-50"
          />
          {isStreaming ? (
            <Button variant="destructive" size="sm" className="h-10 px-3 shrink-0" onClick={stop}>
              <X className="h-4 w-4" />
            </Button>
          ) : (
            <Button size="sm" onClick={handleSend} disabled={!input.trim() || !canSend} className="h-10 px-3 shrink-0">
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Connect Provider Modal */}
      <Dialog open={connectModalOpen} onOpenChange={(open) => { if (!open) { setConnectModalOpen(false); setPendingProvider(null); setConnectApiKey(""); setConnectBaseUrl("") } }}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Connect {pendingProvider}</DialogTitle>
            <DialogDescription>{pendingProvider} is not connected yet. Add an API key to use this provider.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input id="api-key" type="password" value={connectApiKey} onChange={e => setConnectApiKey(e.target.value)} placeholder="sk-..." />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="base-url">Base URL (optional)</Label>
              <Input id="base-url" value={connectBaseUrl} onChange={e => setConnectBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
            </div>
            {modelError && <p className="text-xs text-red-400">{modelError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setConnectModalOpen(false); setPendingProvider(null); setConnectApiKey(""); setConnectBaseUrl("") }}>Cancel</Button>
            <Button onClick={handleConnect} disabled={!connectApiKey.trim() || connectLoading}>
              {connectLoading ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
              Connect Provider
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
