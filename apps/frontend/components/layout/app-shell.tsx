'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { StatusBadge } from '@/components/ui'

const navItems = [
  { href: '/', label: 'Dashboard' },
  { href: '/chat', label: 'AI Assistant' },
  { href: '/inventory', label: 'Inventory' },
  { href: '/diagnostics', label: 'Diagnostics' },
  { href: '/tools', label: 'Tools' },
  { href: '/health', label: 'System Health' },
  { href: '/settings', label: 'Settings' },
  { href: '/sessions', label: 'Sessions' },
]

function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex min-h-screen w-full flex-col bg-ops-navy text-white lg:fixed lg:inset-y-0 lg:left-0 lg:w-72">
      <div className="border-b border-white/10 px-6 py-6">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-ops-info">AgenticOps</p>
        <h1 className="mt-2 text-xl font-bold">Console</h1>
        <p className="mt-2 text-xs leading-5 text-white/65">vCenter-style operations with AI-assisted diagnostics.</p>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-5">
        {navItems.map((item) => {
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-xl px-4 py-3 text-sm font-semibold transition ${
                active ? 'bg-ops-steel text-white shadow-sm' : 'text-white/78 hover:bg-white/10 hover:text-white'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>

      <div className="space-y-3 border-t border-white/10 p-5 text-xs">
        <div className="flex items-center justify-between gap-3">
          <span className="text-white/70">FastAPI</span>
          <StatusBadge status="checking" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-white/70">vCenter</span>
          <StatusBadge status="checking" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-white/70">Agent</span>
          <StatusBadge status="checking" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-white/70">MCP</span>
          <StatusBadge status="safe" />
        </div>
      </div>
    </aside>
  )
}

function TopStatusBar() {
  return (
    <header className="sticky top-0 z-20 border-b border-ops-steel/10 bg-white/90 px-5 py-3 backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-ops-steel">AgenticOps Console</p>
          <p className="mt-1 text-sm text-ops-muted">vCenter: core-infra-vc01.dclab.com</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status="api ready" />
          <StatusBadge status="agent ready" />
          <StatusBadge status="mcp safe" />
          <span className="rounded-full bg-ops-beige px-3 py-1 text-xs font-semibold text-ops-navy">Manual refresh</span>
        </div>
      </div>
    </header>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-ops-cream lg:pl-72">
      <Sidebar />
      <div className="ops-grid min-h-screen">
        <TopStatusBar />
        <main className="mx-auto max-w-7xl px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  )
}
