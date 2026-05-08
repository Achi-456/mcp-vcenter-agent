"use client"

import { Card } from "@/components/ui/card"
import { Shield } from "lucide-react"

interface BlockedCardProps {
  reason?: string
  message: string
}

export function BlockedCard({ reason, message }: BlockedCardProps) {
  return (
    <Card className="border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] space-y-1">
      <div className="flex items-center gap-1.5">
        <Shield className="h-3.5 w-3.5 text-amber-400" />
        <span className="text-amber-400 font-medium">High-Risk Action Blocked</span>
      </div>
      {reason && (
        <p className="text-amber-400/80 text-[10px]">Reason: {reason}</p>
      )}
      <p className="text-muted-foreground">{message}</p>
    </Card>
  )
}
