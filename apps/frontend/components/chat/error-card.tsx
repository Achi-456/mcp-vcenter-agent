"use client"

import { Card } from "@/components/ui/card"
import { AlertTriangle } from "lucide-react"

interface ErrorCardProps {
  message: string
  error_code?: string
}

export function ErrorCard({ message, error_code }: ErrorCardProps) {
  return (
    <Card className="border-red-500/20 bg-red-500/5 px-3 py-2 text-[11px] space-y-1">
      <div className="flex items-center gap-1.5">
        <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
        <span className="text-red-400 font-medium">Error</span>
      </div>
      {error_code && (
        <p className="text-red-400/80 text-[10px]">{error_code}</p>
      )}
      <p className="text-muted-foreground">{message}</p>
    </Card>
  )
}
