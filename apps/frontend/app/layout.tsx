import type { Metadata } from "next"
import "./globals.css"
import { AppShell } from "@/components/layout"
import { Toaster } from "@/components/ui/sonner"

export const metadata: Metadata = {
  title: "AgenticOps — vCenter Console",
  description: "AI-powered VMware vCenter administration console",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <AppShell>{children}</AppShell>
        <Toaster />
      </body>
    </html>
  )
}
