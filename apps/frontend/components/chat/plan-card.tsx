"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Route } from "lucide-react"

interface PlanCardProps {
  goal?: string
  steps?: Array<{
    label: string
    tool?: string
    risk_level?: string
  }>
  intent?: string
}

export function PlanCard({ goal, steps, intent }: PlanCardProps) {
  const displaySteps = steps || []
  const displayGoal = goal || (intent ? `Execute ${intent}` : undefined)

  return (
    <Card className="border-slate-500/20 bg-slate-500/5 px-3 py-2 text-[11px] space-y-1.5">
      <div className="flex items-center gap-1.5">
        <Route className="h-3 w-3 text-slate-400" />
        <span className="text-slate-400 font-medium text-[11px]">Plan</span>
      </div>
      {displayGoal && (
        <p className="text-muted-foreground text-[11px]">
          Goal: <span className="text-sidebar-foreground">{displayGoal}</span>
        </p>
      )}
      {displaySteps.length > 0 && (
        <ol className="list-decimal list-inside space-y-0.5 text-muted-foreground">
          {displaySteps.map((step, i) => (
            <li key={i} className="text-[11px]">
              {step.label}
              {step.tool && (
                <Badge variant="outline" className="ml-1 text-[9px] font-mono-code">
                  {step.tool}
                </Badge>
              )}
              {step.risk_level && (
                <Badge variant="outline" className="ml-1 text-[9px] text-amber-400 border-amber-500/30">
                  {step.risk_level}
                </Badge>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  )
}
