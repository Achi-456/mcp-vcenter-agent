import Link from "next/link"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MessageSquare, Server, History, Settings, Activity } from "lucide-react"

const cards = [
  { href: "/chat", label: "Chat", desc: "Agent conversation interface with SSE streaming", icon: MessageSquare },
  { href: "/inventory", label: "Inventory", desc: "Browse VMs, hosts, and datastores", icon: Server },
  { href: "/sessions", label: "Sessions", desc: "Agent session history and replay", icon: History },
  { href: "/settings", label: "Settings", desc: "vCenter and LLM configuration", icon: Settings },
  { href: "/health", label: "System Health", desc: "Service status and diagnostics", icon: Activity },
]

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          AI-powered VMware vCenter administration
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(({ href, label, desc, icon: Icon }) => (
          <Card key={href} className="border-border bg-card p-6 transition-colors hover:border-emerald-600/30">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/20">
              <Icon className="h-5 w-5 text-emerald-400" />
            </div>
            <h3 className="text-sm font-semibold">{label}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
            <Link href={href}>
              <Button variant="outline" size="sm" className="mt-4 text-xs">
                Open
              </Button>
            </Link>
          </Card>
        ))}
      </div>
    </div>
  )
}
