import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'vCenter Agentic Ops',
  description: 'Clean rebuild baseline for vCenter Agentic Ops Platform',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

