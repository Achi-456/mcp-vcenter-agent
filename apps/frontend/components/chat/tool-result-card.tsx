"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, Database } from "lucide-react"

interface ToolResultCardProps {
  tool: string
  status: "success" | "error"
  summary?: string
  data_count?: number
  error_code?: string
  message?: string
  cached?: boolean
}

export function ToolResultCard({ tool, status, summary, data_count, error_code, message, cached }: ToolResultCardProps) {
  const isSuccess = status === "success"

  return (
    <Card className={`px-3 py-2 text-[11px] space-y-1 ${
      isSuccess
        ? "border-emerald-500/20 bg-emerald-500/5"
        : "border-red-500/20 bg-red-500/5"
    }`}>
      <div className="flex items-center gap-1.5">
        {isSuccess ? (
          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
        ) : (
          <XCircle className="h-3 w-3 text-red-400" />
        )}
        <span className="font-mono-code text-sidebar-foreground">{tool}</span>
        <Badge variant="outline" className={`text-[9px] ml-auto ${
          isSuccess
            ? "text-emerald-400 border-emerald-500/30"
            : "text-red-400 border-red-500/30"
        }`}>
          {isSuccess ? "success" : "error"}
        </Badge>
        {cached && (
          <Badge variant="secondary" className="text-[9px]">
            cached
          </Badge>
        )}
      </div>

      {summary && (
        <p className="text-muted-foreground">{summary}</p>
      )}

      {isSuccess && data_count !== undefined && (
        <div className="flex items-center gap-1 text-muted-foreground/60">
          <Database className="h-3 w-3" />
          <span>{data_count} items</span>
        </div>
      )}

      {!isSuccess && error_code && (
        <div className="text-red-400/80 text-[10px]">
          <p>{error_code}{message ? `: ${message}` : ""}</p>
        </div>
      )}
    </Card>
  )
}
