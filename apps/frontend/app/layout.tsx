import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'vCenter Agentic Ops',
  description: 'Phase 08 application scaffold',
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
