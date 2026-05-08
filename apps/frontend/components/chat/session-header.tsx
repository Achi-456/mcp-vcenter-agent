"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { RefreshCw, Bot } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ChatStatus } from "@/lib/chat-events"

interface SessionHeaderProps {
  sessionId: string | null
  status: ChatStatus | string
  provider: string
  model: string
  onNewSession: () => void
  onToggle: () => void
}

const STATUS_DOT: Record<string, string> = {
  ready: "bg-emerald-500",
  thinking: "bg-blue-500 animate-pulse",
  planning: "bg-blue-500 animate-pulse",
  running_tool: "bg-blue-500 animate-pulse",
  streaming: "bg-blue-500 animate-pulse",
  blocked: "bg-amber-500",
  error: "bg-red-500",
}

export function SessionHeader({ sessionId, status, provider, model, onNewSession, onToggle }: SessionHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-sidebar-border px-5 py-3">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600">
          <Bot className="h-3.5 w-3.5 text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-sidebar-foreground">AI Assistant</p>
          <div className="flex items-center gap-1">
            <div className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[status] || "bg-muted-foreground")} />
            <p className="text-[11px] text-muted-foreground capitalize">{status}</p>
            {sessionId && (
              <span className="text-[9px] text-muted-foreground/50 ml-1 font-mono-code">
                {sessionId.slice(0, 8)}...
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <div className="hidden sm:flex items-center gap-1 mr-1">
          <Badge variant="outline" className="text-[9px] text-muted-foreground/60">
            {provider}/{model}
          </Badge>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onNewSession} title="New Session">
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggle}>
          <Bot className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
