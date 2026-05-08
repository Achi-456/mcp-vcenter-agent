"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wrench } from "lucide-react"

interface ToolCallCardProps {
  tool: string
  args?: Record<string, unknown>
  status?: string
}

export function ToolCallCard({ tool, args, status }: ToolCallCardProps) {
  return (
    <Card className="border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-[11px] space-y-1">
      <div className="flex items-center gap-1.5">
        <Wrench className="h-3 w-3 text-cyan-400" />
        <span className="font-mono-code text-cyan-400 font-medium">{tool}</span>
        <Badge variant="outline" className="text-[9px] ml-auto text-cyan-400 border-cyan-500/30">
          {status || "running"}
        </Badge>
      </div>
      {args && Object.keys(args).length > 0 && (
        <div className="mt-1">
          <p className="text-[10px] text-muted-foreground mb-0.5">args:</p>
          <pre className="text-[10px] text-muted-foreground/60 bg-black/20 rounded px-1.5 py-1 overflow-x-auto">
            {JSON.stringify(args, null, 2)}
          </pre>
        </div>
      )}
    </Card>
  )
}
