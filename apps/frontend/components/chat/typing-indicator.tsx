"use client"

import { cn } from "@/lib/utils"
import type { ChatStatus } from "@/lib/chat-events"

interface TypingIndicatorProps {
  status: ChatStatus | string
}

const LABELS: Record<string, string> = {
  thinking: "Assistant is thinking...",
  planning: "Planning tool execution...",
  running_tool: "Running vCenter tool...",
  streaming: "Writing answer...",
  blocked: "Action blocked",
  error: "Error occurred",
}

export function TypingIndicator({ status }: TypingIndicatorProps) {
  if (status === "ready") return null

  const label = LABELS[status] || "Processing..."

  return (
    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground px-1">
      <div className="flex gap-0.5">
        <span className={cn(
          "h-1.5 w-1.5 rounded-full bg-muted-foreground/40 animate-bounce",
          status === "blocked" && "bg-amber-500",
          status === "error" && "bg-red-500",
        )} style={{ animationDelay: "0ms" }} />
        <span className={cn(
          "h-1.5 w-1.5 rounded-full bg-muted-foreground/40 animate-bounce",
          status === "blocked" && "bg-amber-500",
          status === "error" && "bg-red-500",
        )} style={{ animationDelay: "150ms" }} />
        <span className={cn(
          "h-1.5 w-1.5 rounded-full bg-muted-foreground/40 animate-bounce",
          status === "blocked" && "bg-amber-500",
          status === "error" && "bg-red-500",
        )} style={{ animationDelay: "300ms" }} />
      </div>
      <span>{label}</span>
    </div>
  )
}
