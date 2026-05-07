"use client"

import { useEffect, useState, useCallback } from "react"
import { api, type Setting } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

type Cat = "vcenter" | "llm" | "agent" | "user"

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([])
  const [editing, setEditing] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null)
  const [activeCat, setActiveCat] = useState<Cat>("vcenter")
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<{ vcenter: { status: string }; llm: { status: string; provider: string } } | null>(null)

  const load = useCallback(async () => {
    try {
      const d = await api.getSettings()
      setSettings(d.items || [])
      const init: Record<string, string> = {}
      for (const s of d.items || []) init[s.key] = s.value || ""
      setEditing(init)
      const st = await api.getSettingsStatus()
      setStatus(st)
    } catch { /* offline */ } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (key: string) => {
    setSaving(key)
    try { await api.updateSetting(key, editing[key] || ""); await load() }
    catch { /* */ } finally { setSaving(null) }
  }

  const test = async (kind: "vcenter" | "llm") => {
    setTestResult(null)
    try { setTestResult(kind === "vcenter" ? await api.testVcenter() : await api.testLLM()) }
    catch (e: unknown) { setTestResult({ status: "error", message: String(e) }) }
  }

  const cats: { key: Cat; label: string }[] = [
    { key: "vcenter", label: "vCenter" },
    { key: "llm", label: "LLM" },
    { key: "agent", label: "Agent" },
    { key: "user", label: "User" },
  ]

  if (loading) return <p className="text-sm text-muted-foreground">Loading settings...</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="text-xs text-muted-foreground">
          vCenter: {status?.vcenter?.status || "?"} · LLM: {status?.llm?.provider || "?"} ({status?.llm?.status || "?"})
        </p>
      </div>

      <div className="flex gap-6">
        <div className="w-40 space-y-0.5">
          {cats.map((c) => (
            <button
              key={c.key}
              onClick={() => setActiveCat(c.key)}
              className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                activeCat === c.key ? "bg-emerald-600/20 text-emerald-400" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex-1 max-w-lg space-y-4">
          {settings.filter((s) => s.category === activeCat).map((s) => (
            <Card key={s.key} className="border-border bg-card p-4 space-y-2">
              <label className="text-xs font-medium text-muted-foreground">{s.label || s.key}</label>
              <div className="flex gap-2">
                <Input
                  type={s.sensitive ? "password" : "text"}
                  value={editing[s.key] ?? ""}
                  onChange={(e) => setEditing((p) => ({ ...p, [s.key]: e.target.value }))}
                  className="h-9 text-sm"
                  placeholder={s.sensitive ? "••••••••" : ""}
                />
                <Button size="sm" variant="outline" onClick={() => save(s.key)} disabled={saving === s.key}>
                  {saving === s.key ? "..." : "Save"}
                </Button>
              </div>
            </Card>
          ))}

          {activeCat === "vcenter" && (
            <Button variant="outline" size="sm" onClick={() => test("vcenter")}>Test vCenter Connection</Button>
          )}
          {activeCat === "llm" && (
            <Button variant="outline" size="sm" onClick={() => test("llm")}>Test LLM Connection</Button>
          )}

          {testResult && (
            <Card className={`p-3 text-sm ${
              testResult.status === "ok" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-red-500/30 bg-red-500/10 text-red-400"
            }`}>
              {testResult.status === "ok" ? "OK: " : "Error: "}{testResult.message}
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
