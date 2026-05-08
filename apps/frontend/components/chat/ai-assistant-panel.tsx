"use client"

import { useState, useEffect, useCallback } from "react"
import { api, type LLMProvider, type LLMModel, type LLMStatus } from "@/lib/api"
import { useSSEChat, type SSEMessage } from "@/hooks/use-sse-chat"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Bot, X, ChevronRight, Zap, Server, HardDrive, Bell, Clock,
  Monitor, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Shield, Wrench,
  Lightbulb, Search
} from "lucide-react"
import ReactMarkdown from "react-markdown"

interface Message {
  role: "user" | "assistant" | "blocked" | "tool"
  content: string
  toolName?: string
  toolResult?: string
  isMarkdown?: boolean
}

interface ToolTraceEntry {
  name: string
  status: "running" | "success" | "error"
  summary?: string
  dataCount?: number
}

const PROMPT_SHORTCUTS = [
  { id: "tools", label: "List Tools", icon: Wrench, prompt: "list down all the tools you have" },
  { id: "environment", label: "Environment", icon: Monitor, prompt: "Give me an environment overview of my vCenter infrastructure." },
  { id: "powered-off", label: "Powered-off VMs", icon: Zap, prompt: "Show me all powered-off VMs in my vCenter environment." },
  { id: "datastore", label: "Datastore Health", icon: HardDrive, prompt: "Analyze datastore health and highlight any critical datastores above 90% usage." },
  { id: "alarms", label: "Active Alarms", icon: Bell, prompt: "Summarize all active alarms grouped by severity." },
  { id: "events", label: "Recent Events", icon: Clock, prompt: "Show me recent events with errors and warnings." },
  { id: "rke2", label: "RKE2 VMs", icon: Server, prompt: "Show me all RKE2 cluster VMs." },
]

type Status = "Ready" | "Thinking" | "Classifying" | "Running tool" | "Streaming" | "Blocked" | "Error"

export function AIAssistantPanel({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [models, setModels] = useState<LLMModel[]>([])
  const [selectedProvider, setSelectedProvider] = useState("gemini")
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash")
  const [llmStatus, setLLMStatus] = useState<LLMStatus>({ configured: false, provider: null, model: null, ready: false })
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [highRisk, setHighRisk] = useState(false)
  const [status, setStatus] = useState<Status>("Ready")
  const [toolTrace, setToolTrace] = useState<ToolTraceEntry[]>([])
  const [suggestedNext, setSuggestedNext] = useState<string | null>(null)

  const { send, stop, isStreaming, sessionId, newSession } = useSSEChat()

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

  const handleShortcut = useCallback((prompt: string) => {
    setMessages(prev => [...prev, { role: "user", content: prompt }])
    setToolTrace([])
    setSuggestedNext(null)
    const tempTrace: ToolTraceEntry[] = []

    send(
      { message: prompt, session_id: sessionId, provider: selectedProvider, model: selectedModel, allow_high_risk: false },
      (evt: SSEMessage) => {
        switch (evt.type) {
          case "start":
            setStatus("Thinking")
            break
          case "intent":
            setStatus("Classifying")
            break
          case "safety_check":
            break
          case "tool_call": {
            setStatus("Running tool")
            const name = evt.tool || "unknown"
            tempTrace.push({ name, status: "running" })
            setToolTrace([...tempTrace])
            break
          }
          case "tool_result": {
            const idx = tempTrace.findIndex(t => t.name === evt.tool && t.status === "running")
            if (idx >= 0) {
              tempTrace[idx] = {
                ...tempTrace[idx],
                status: evt.status === "success" ? "success" : "error",
                summary: evt.summary || "",
                dataCount: evt.data_count,
              }
            }
            setToolTrace([...tempTrace])
            break
          }
          case "final":
            setStatus("Ready")
            setMessages(prev => [...prev, {
              role: "assistant",
              content: evt.content || "",
              isMarkdown: true,
            }])
            break
          case "suggested_next_step":
            setSuggestedNext(evt.content || null)
            break
          case "blocked":
            setStatus("Blocked")
            setMessages(prev => [...prev, {
              role: "blocked",
              content: evt.message || "This action is blocked for safety.",
            }])
            break
          case "error":
            setStatus("Error")
            setMessages(prev => [...prev, { role: "assistant", content: `Error: ${evt.message || "Unknown error"}` }])
            break
          case "done":
            setStatus("Ready")
            break
        }
      },
      (err) => {
        setStatus("Error")
        setMessages(prev => [...prev, { role: "assistant", content: `Connection error: ${err}` }])
      },
    )
  }, [send, sessionId, selectedProvider, selectedModel])

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
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sidebar-border px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-sidebar-foreground">AI Assistant</p>
            <div className="flex items-center gap-1">
              <div className={cn("h-1.5 w-1.5 rounded-full",
                status === "Ready" ? "bg-emerald-500" :
                status === "Error" ? "bg-red-500" :
                status === "Blocked" ? "bg-amber-500" : "bg-blue-500 animate-pulse"
              )} />
              <p className="text-[11px] text-muted-foreground">{status}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={newSession} title="New Session">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

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

        {messages.map((m, i) => (
          <div key={i} className={cn("space-y-1", m.role === "user" ? "flex justify-end" : "")}>
            {m.role === "tool" && m.toolName && (
              <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <Wrench className="h-3 w-3 text-cyan-400" />
                  <span className="font-mono-code text-cyan-400">{m.toolName}</span>
                  <Badge variant="outline" className="text-[9px] ml-auto">tool</Badge>
                </div>
                {m.toolResult && <p className="mt-1 text-muted-foreground">{m.toolResult}</p>}
              </Card>
            )}
            {m.role === "blocked" && (
              <Card className="border-red-500/20 bg-red-500/5 px-3 py-2 text-xs flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-red-400 font-medium">Action Blocked</p>
                  <p className="text-muted-foreground mt-0.5">{m.content}</p>
                </div>
              </Card>
            )}
            {m.content && m.role !== "tool" && (
              <Card className={cn(
                "px-3 py-2 text-xs max-w-[90%]",
                m.role === "user"
                  ? "border-emerald-600/30 bg-emerald-600/10 text-emerald-50"
                  : "border-border bg-card text-sidebar-foreground"
              )}>
                {m.isMarkdown ? (
                  <div className="prose prose-xs prose-invert max-w-none [&_table]:w-full [&_table]:text-[11px] [&_th]:text-left [&_th]:p-1 [&_td]:p-1 [&_h2]:text-sm [&_h2]:mt-2 [&_h2]:mb-1 [&_ul]:my-1 [&_li]:text-[11px] [&_hr]:my-2">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap break-words">{m.content}</p>
                )}
              </Card>
            )}
          </div>
        ))}

        {isStreaming && status !== "Ready" && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <RefreshCw className="h-3 w-3 animate-spin" />
            {status === "Thinking" && "Thinking..."}
            {status === "Classifying" && "Classifying request..."}
            {status === "Running tool" && "Running tools..."}
          </div>
        )}
      </div>

      {/* Tool Trace */}
      {toolTrace.length > 0 && (
        <div className="border-t border-sidebar-border px-5 py-3 max-h-[140px] overflow-y-auto">
          <p className="text-[11px] font-medium text-muted-foreground mb-2 uppercase tracking-wider">Tool Trace</p>
          <div className="space-y-1.5">
            {toolTrace.map((t, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[11px]">
                {t.status === "running" && <RefreshCw className="h-3 w-3 animate-spin text-amber-400 mt-0.5" />}
                {t.status === "success" && <CheckCircle2 className="h-3 w-3 text-emerald-400 mt-0.5" />}
                {t.status === "error" && <XCircle className="h-3 w-3 text-red-400 mt-0.5" />}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <span className="font-mono-code text-muted-foreground">{t.name}</span>
                    <span className={cn("text-[10px]",
                      t.status === "success" ? "text-emerald-400" :
                      t.status === "error" ? "text-red-400" : "text-amber-400"
                    )}>
                      {t.status === "running" ? "running" : t.status === "success" ? "success" : "failed"}
                    </span>
                    {t.dataCount && (
                      <Badge variant="secondary" className="text-[9px]">{t.dataCount} items</Badge>
                    )}
                  </div>
                  {t.summary && (
                    <p className="text-muted-foreground/60 truncate">{t.summary}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Next Step */}
      {suggestedNext && status === "Ready" && (
        <div className="border-t border-sidebar-border px-5 py-2">
          <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px]">
            <div className="flex items-center gap-1.5 mb-1">
              <Lightbulb className="h-3 w-3 text-cyan-400" />
              <span className="text-cyan-400 font-medium">Suggested next step</span>
            </div>
            <p className="text-muted-foreground">{suggestedNext}</p>
          </Card>
        </div>
      )}

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
