"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  MessageSquare,
  Server,
  History,
  Settings,
  Activity,
  Bot,
} from "lucide-react"

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/inventory", label: "Inventory", icon: Server },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/health", label: "System Health", icon: Activity },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-[260px] flex-col bg-sidebar border-r border-sidebar-border">
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600">
          <Bot className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-sidebar-foreground tracking-tight">
            AgenticOps
          </p>
          <p className="text-[11px] font-medium text-muted-foreground font-mono-code">
            dclab.local
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-4">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-emerald-600/20 text-emerald-400"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-border/40 hover:text-sidebar-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-sidebar-border px-3 py-4 space-y-2">
        <StatusBadge label="API" status="checking" />
        <StatusBadge label="vCenter" status="checking" />
        <StatusBadge label="Agent" status="checking" />
      </div>
    </aside>
  )
}

function StatusBadge({ label, status }: { label: string; status: "ok" | "error" | "checking" }) {
  const colors = {
    ok: "bg-emerald-500",
    error: "bg-red-500",
    checking: "bg-amber-500",
  }
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={cn("h-2 w-2 rounded-full", colors[status])} />
      <span className="text-sidebar-foreground/60">{label}</span>
      <span className="text-sidebar-foreground/40">{status === "checking" ? "checking" : status}</span>
    </div>
  )
}
