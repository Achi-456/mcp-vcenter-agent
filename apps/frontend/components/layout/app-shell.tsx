"use client"

import { AppSidebar } from "./app-sidebar"
import { AppNavbar } from "./app-navbar"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <div className="ml-[260px] flex flex-1 flex-col">
        <AppNavbar />
        <main className="mt-16 flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
