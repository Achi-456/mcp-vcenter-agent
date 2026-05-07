"use client"

import { useEffect, useState, useCallback } from "react"
import { api, type VCenterConnectionStatus, type LLMConnectionStatus } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "sonner"
import { KeyRound, Server, CheckCircle2, XCircle } from "lucide-react"

export default function SettingsPage() {
  // vCenter state
  const [vcStatus, setVcStatus] = useState<VCenterConnectionStatus | null>(null)
  const [vcForm, setVcForm] = useState({ name: "dclab-vcenter", vcenter_url: "", username: "", password: "", verify_ssl: false })
  const [vcTesting, setVcTesting] = useState(false)
  const [vcSaving, setVcSaving] = useState(false)
  const [vcDeleteOpen, setVcDeleteOpen] = useState(false)

  // LLM state
  const [llmStatus, setLlmStatus] = useState<LLMConnectionStatus | null>(null)
  const [llmForm, setLlmForm] = useState({ provider: "openai", base_url: "https://api.openai.com/v1", model: "gpt-4o", api_key: "" })
  const [llmTesting, setLlmTesting] = useState(false)
  const [llmSaving, setLlmSaving] = useState(false)
  const [llmDeleteOpen, setLlmDeleteOpen] = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const [vc, llm] = await Promise.all([api.getVCenterConnectionStatus(), api.getLLMConnectionStatus()])
      setVcStatus(vc)
      setLlmStatus(llm)
      if (vc.configured) setVcForm((p) => ({ ...p, vcenter_url: vc.vcenter_url || "", username: "" }))
      if (llm.configured) setLlmForm((p) => ({ ...p, provider: llm.provider || "openai", base_url: llm.base_url || "", model: llm.model || "" }))
    } catch {
      // backend offline
    }
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  // ── vCenter actions ──

  const vcTest = async () => {
    setVcTesting(true)
    try {
      const r = await api.testVCenterConnection(vcForm)
      if (r.ok) toast.success(r.message)
      else toast.error(r.message)
    } catch (e: unknown) { toast.error(String(e)) }
    finally { setVcTesting(false) }
  }

  const vcSave = async () => {
    setVcSaving(true)
    try {
      const r = await api.saveVCenterConnection(vcForm)
      if (r.ok) {
        toast.success(r.message)
        setVcForm((p) => ({ ...p, password: "" }))
        await loadStatus()
      } else {
        toast.error(r.message)
      }
    } catch (e: unknown) { toast.error(String(e)) }
    finally { setVcSaving(false) }
  }

  const vcDelete = async () => {
    try {
      await api.deleteVCenterConnection()
      toast.success("vCenter credentials deleted")
      setVcDeleteOpen(false)
      await loadStatus()
    } catch (e: unknown) { toast.error(String(e)) }
  }

  // ── LLM actions ──

  const llmTest = async () => {
    setLlmTesting(true)
    try {
      const r = await api.testLLMConnection(llmForm)
      if (r.ok) toast.success(r.message)
      else toast.error(r.message)
    } catch (e: unknown) { toast.error(String(e)) }
    finally { setLlmTesting(false) }
  }

  const llmSave = async () => {
    setLlmSaving(true)
    try {
      const r = await api.saveLLMConnection(llmForm)
      if (r.ok) {
        toast.success(r.message)
        setLlmForm((p) => ({ ...p, api_key: "" }))
        await loadStatus()
      } else {
        toast.error(r.message)
      }
    } catch (e: unknown) { toast.error(String(e)) }
    finally { setLlmSaving(false) }
  }

  const llmDelete = async () => {
    try {
      await api.deleteLLMConnection()
      toast.success("LLM credentials deleted")
      setLlmDeleteOpen(false)
      await loadStatus()
    } catch (e: unknown) { toast.error(String(e)) }
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="text-xs text-muted-foreground">Credentials & Connections</p>
      </div>

      {/* ── vCenter Card ── */}
      <Card className="border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-semibold">vCenter Connection</h2>
          </div>
          {vcStatus?.configured ? (
            <Badge className="bg-emerald-600/20 text-emerald-400">
              <CheckCircle2 className="mr-1 h-3 w-3" />Configured
            </Badge>
          ) : (
            <Badge variant="secondary">
              <XCircle className="mr-1 h-3 w-3" />Not Configured
            </Badge>
          )}
        </div>

        {vcStatus?.configured && (
          <div className="rounded-lg bg-muted/50 p-3 text-xs space-y-0.5">
            <p><span className="text-muted-foreground">URL:</span> <span className="font-mono-code">{vcStatus.vcenter_url}</span></p>
            <p><span className="text-muted-foreground">User:</span> <span className="font-mono-code">{vcStatus.username_hint}</span></p>
            <p><span className="text-muted-foreground">Password:</span> {vcStatus.password_set ? "Saved" : "Not saved"}</p>
            <p><span className="text-muted-foreground">Last Test:</span> {vcStatus.last_test_status || "Never"}</p>
          </div>
        )}

        <div className="grid gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Connection Name</Label>
            <Input className="h-9 text-sm" value={vcForm.name} onChange={(e) => setVcForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">vCenter URL</Label>
            <Input className="h-9 text-sm" placeholder="https://vcenter.dclab.local" value={vcForm.vcenter_url} onChange={(e) => setVcForm((p) => ({ ...p, vcenter_url: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Username</Label>
              <Input className="h-9 text-sm" placeholder="administrator@vsphere.local" value={vcForm.username} onChange={(e) => setVcForm((p) => ({ ...p, username: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Password</Label>
              <Input className="h-9 text-sm" type="password" placeholder={vcStatus?.configured ? "Replace password" : "Enter password"} value={vcForm.password} onChange={(e) => setVcForm((p) => ({ ...p, password: e.target.value }))} />
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Switch id="vc-ssl" checked={vcForm.verify_ssl} onCheckedChange={(v) => setVcForm((p) => ({ ...p, verify_ssl: v }))} />
            <Label htmlFor="vc-ssl" className="text-xs">Verify SSL Certificate</Label>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={vcTest} disabled={vcTesting || !vcForm.vcenter_url || !vcForm.username || !vcForm.password}>
            {vcTesting ? "Testing..." : "Test Connection"}
          </Button>
          <Button size="sm" onClick={vcSave} disabled={vcSaving || !vcForm.vcenter_url || !vcForm.username || !vcForm.password}>
            {vcSaving ? "Saving..." : "Save Credentials"}
          </Button>
          {vcStatus?.configured && (
            <Button variant="destructive" size="sm" onClick={() => setVcDeleteOpen(true)}>Delete</Button>
          )}
        </div>
      </Card>

      {/* ── LLM Card ── */}
      <Card className="border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-semibold">LLM Provider</h2>
          </div>
          {llmStatus?.configured ? (
            <Badge className="bg-emerald-600/20 text-emerald-400">
              <CheckCircle2 className="mr-1 h-3 w-3" />Configured
            </Badge>
          ) : (
            <Badge variant="secondary">
              <XCircle className="mr-1 h-3 w-3" />Not Configured
            </Badge>
          )}
        </div>

        {llmStatus?.configured && (
          <div className="rounded-lg bg-muted/50 p-3 text-xs space-y-0.5">
            <p><span className="text-muted-foreground">Provider:</span> {llmStatus.provider}</p>
            <p><span className="text-muted-foreground">Model:</span> <span className="font-mono-code">{llmStatus.model}</span></p>
            <p><span className="text-muted-foreground">API Key:</span> {llmStatus.api_key_set ? "Saved" : "Not saved"}</p>
            <p><span className="text-muted-foreground">Last Test:</span> {llmStatus.last_test_status || "Never"}</p>
          </div>
        )}

        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Provider</Label>
              <Input className="h-9 text-sm" value={llmForm.provider} onChange={(e) => setLlmForm((p) => ({ ...p, provider: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Base URL</Label>
              <Input className="h-9 text-sm" value={llmForm.base_url} onChange={(e) => setLlmForm((p) => ({ ...p, base_url: e.target.value }))} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Model</Label>
              <Input className="h-9 text-sm" value={llmForm.model} onChange={(e) => setLlmForm((p) => ({ ...p, model: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">API Key</Label>
              <Input className="h-9 text-sm" type="password" placeholder={llmStatus?.configured ? "Replace key" : "Enter key"} value={llmForm.api_key} onChange={(e) => setLlmForm((p) => ({ ...p, api_key: e.target.value }))} />
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={llmTest} disabled={llmTesting || !llmForm.api_key}>
            {llmTesting ? "Testing..." : "Test LLM"}
          </Button>
          <Button size="sm" onClick={llmSave} disabled={llmSaving || !llmForm.api_key}>
            {llmSaving ? "Saving..." : "Save Credentials"}
          </Button>
          {llmStatus?.configured && (
            <Button variant="destructive" size="sm" onClick={() => setLlmDeleteOpen(true)}>Delete</Button>
          )}
        </div>
      </Card>

      {/* Delete Confirm Dialogs */}
      <Dialog open={vcDeleteOpen} onOpenChange={setVcDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete vCenter Credentials?</DialogTitle>
            <DialogDescription>This will remove the stored credentials. Inventory and agents will lose vCenter access.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setVcDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" size="sm" onClick={vcDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={llmDeleteOpen} onOpenChange={setLlmDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete LLM Credentials?</DialogTitle>
            <DialogDescription>This will remove the stored API key. Chat and agent features will stop working.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setLlmDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" size="sm" onClick={llmDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
