"use client"

import { useState, useEffect, useCallback } from "react"
import { api, type LLMProvider, type LLMModel, type LLMStatus } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Bot, X, ChevronRight, Zap, Server, HardDrive, Bell, Clock,
  Monitor, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Shield, Wrench
} from "lucide-react"

interface Message {
  role: "user" | "assistant" | "tool"
  content: string
  toolName?: string
  toolResult?: string
}

const PROMPT_SHORTCUTS = [
  { id: "environment", label: "Environment Overview", icon: Monitor, endpoint: "getContextEnvironment" as const },
  { id: "powered-off", label: "Powered-off VMs", icon: Zap, endpoint: "getContextPoweredOff" as const },
  { id: "datastore", label: "Datastore Health", icon: HardDrive, endpoint: "getContextDatastoreHealth" as const },
  { id: "alarms", label: "Active Alarms", icon: Bell, endpoint: "getContextActiveAlarms" as const },
  { id: "events", label: "Recent Events", icon: Clock, endpoint: "getContextRecentEvents" as const },
  { id: "rke2", label: "RKE2 Cluster VMs", icon: Server, endpoint: "getContextRKE2VMs" as const },
]

const BLOCKED_ACTIONS = [
  "power off", "power on", "reboot", "shutdown", "delete", "migrate",
  "snapshot", "maintenance mode", "power_off", "power_on", "destroy",
]

export function AIAssistantPanel({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [models, setModels] = useState<LLMModel[]>([])
  const [selectedProvider, setSelectedProvider] = useState("gemini")
  const [selectedModel, setSelectedModel] = useState("")
  const [llmStatus, setLLMStatus] = useState<LLMStatus>({ configured: false, provider: null, model: null, ready: false })
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [highRisk, setHighRisk] = useState(false)
  const [sending, setSending] = useState(false)
  const [toolTrace, setToolTrace] = useState<{ name: string; status: string; result?: string }[]>([])

  useEffect(() => { api.getLLMProviders().then(r => setProviders(r.providers)).catch(() => {}) }, [])
  useEffect(() => { api.getLLMStatus().then(setLLMStatus).catch(() => {}) }, [])

  useEffect(() => {
    if (!selectedProvider) return
    api.getLLMModels(selectedProvider).then(r => {
      setModels(r.models)
      if (r.models.length > 0 && !selectedModel) setSelectedModel(r.models[0].id)
    }).catch(() => {})
  }, [selectedProvider])

  const handleShortcut = useCallback(async (ep: string) => {
    setSending(true)
    const label = PROMPT_SHORTCUTS.find(s => s.endpoint === ep)?.label || ep
    setMessages(prev => [...prev, { role: "user", content: `Run: ${label}` }])
    setToolTrace([{ name: ep, status: "running" }])
    try {
      const result = await (api as unknown as Record<string, () => Promise<unknown>>)[ep]()
      const data = result as { summary?: string }
      const txt = data?.summary || JSON.stringify(result)
      setMessages(prev => [...prev, { role: "assistant", content: txt }])
      setToolTrace(prev => [{ ...prev[0], status: "done", result: txt.slice(0, 200) }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Failed to fetch context." }])
      setToolTrace(prev => [{ ...prev[0], status: "error" }])
    }
    setSending(false)
    setHighRisk(false)
  }, [])

  const handleSend = () => {
    const text = input.trim()
    if (!text || sending) return
    setInput("")

    const lower = text.toLowerCase()
    const isBlocked = BLOCKED_ACTIONS.some(a => lower.includes(a.toLowerCase()))

    if (isBlocked && !highRisk) {
      setMessages(prev => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: `Blocked: "${text}" requires explicit high-risk approval. Enable the "High-Risk Actions" checkbox to proceed (Phase 1.4+ required for execution).` }
      ])
      return
    }

    if (isBlocked && highRisk) {
      setMessages(prev => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: `High-risk action acknowledged but deferred: Phase 1.3 is read-only. The agent engine will support "${text}" in a future phase with full safety gates.` }
      ])
      return
    }

    setMessages(prev => [...prev, { role: "user", content: text }])
    setSending(true)

    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Agent engine is ready (provider: ${selectedProvider}, model: ${selectedModel}). Full chat will connect via LangGraph SSE streaming in Phase 1.4. For now, use prompt shortcuts for read-only context queries.`
      }])
      setSending(false)
    }, 600)
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
    <div className="fixed right-0 top-0 z-40 flex h-screen w-[380px] flex-col border-l border-border bg-sidebar shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sidebar-border px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-sidebar-foreground">AI Assistant</p>
            <p className="text-[11px] text-muted-foreground font-mono-code">
              {llmStatus.ready ? "Connected" : "Not configured"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <div className={cn("h-2 w-2 rounded-full", llmStatus.ready ? "bg-emerald-500" : "bg-amber-500")} />
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Provider + Model Selectors */}
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
              onClick={() => handleShortcut(s.endpoint)}
              disabled={sending}
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
              <p className="text-xs text-muted-foreground">Select a prompt shortcut or ask about your vCenter environment.</p>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={cn("space-y-1", m.role === "user" ? "flex justify-end" : "")}>
            {m.role === "tool" && m.toolName && (
              <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <Wrench className="h-3 w-3 text-cyan-400" />
                  <span className="font-mono-code text-cyan-400">{m.toolName}</span>
                  <Badge variant="outline" className="text-[9px] ml-auto">tool</Badge>
                </div>
                {m.toolResult && <p className="mt-1 text-muted-foreground line-clamp-3">{m.toolResult}</p>}
              </Card>
            )}
            {m.content && (
              <Card className={cn(
                "px-3 py-2 text-xs max-w-[85%]",
                m.role === "user"
                  ? "border-emerald-600/30 bg-emerald-600/10 text-emerald-50"
                  : "border-border bg-card text-sidebar-foreground"
              )}>
                <p className="whitespace-pre-wrap break-words">{m.content}</p>
              </Card>
            )}
          </div>
        ))}

        {sending && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Processing...
          </div>
        )}
      </div>

      {/* Tool Trace Panel */}
      {toolTrace.length > 0 && (
        <div className="border-t border-sidebar-border px-5 py-3">
          <p className="text-[11px] font-medium text-muted-foreground mb-2 uppercase tracking-wider">Tool Trace</p>
          <div className="space-y-1.5">
            {toolTrace.map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px]">
                {t.status === "running" && <RefreshCw className="h-3 w-3 animate-spin text-amber-400" />}
                {t.status === "done" && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
                {t.status === "error" && <XCircle className="h-3 w-3 text-red-400" />}
                <span className="font-mono-code text-muted-foreground">{t.name}</span>
                <span className="text-muted-foreground/60">
                  {t.status === "running" ? "running..." : t.status === "done" ? "complete" : "failed"}
                </span>
                {t.result && <span className="text-muted-foreground/40 truncate max-w-[120px] block mt-0.5">{t.result}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-sidebar-border px-5 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <Switch
            checked={highRisk}
            onCheckedChange={setHighRisk}
            id="high-risk-switch"
          />
          <label htmlFor="high-risk-switch" className={cn("text-[11px] cursor-pointer select-none", highRisk ? "text-red-400 font-medium" : "text-muted-foreground")}>
            <Shield className="inline h-3 w-3 mr-1" />
            High-Risk Actions
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
            disabled={sending}
          />
          <Button size="sm" onClick={handleSend} disabled={!input.trim() || sending} className="h-10 px-3">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
