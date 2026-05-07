"use client"

import { useEffect, useState } from "react"
import { api, type Session } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { RefreshCw } from "lucide-react"

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)

  const fetch = async () => {
    setLoading(true)
    try {
      const data = await api.getSessions()
      setSessions(data.items || [])
    } catch {
      // not configured yet
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Sessions</h1>
          <p className="text-xs text-muted-foreground">Agent conversation history</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetch} disabled={loading}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : sessions.length === 0 ? (
        <Card className="border-dashed border-border p-12 text-center">
          <p className="text-sm text-muted-foreground">No sessions yet</p>
          <p className="mt-1 text-xs text-muted-foreground/60">Chat with the agent to create sessions</p>
        </Card>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Title</TableHead>
                <TableHead className="text-xs">Session ID</TableHead>
                <TableHead className="text-xs">Created</TableHead>
                <TableHead className="text-xs">Messages</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="text-sm font-medium">{s.title || "-"}</TableCell>
                  <TableCell className="text-xs font-mono-code text-muted-foreground">{s.id}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{s.created_at}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{s.message_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
