'use client'

import { useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { compareFields } from '@/lib/diagnostics-data'
import type { ApiEnvelope } from '@/lib/types'
import { ComparisonTable, DiagnosticActionCard, DiagnosticResultPanel } from '@/components/diagnostics'
import { EmptyState, ErrorState, PageHeader, SectionCard, StatusBadge, ToolBadge } from '@/components/ui'

type DiagnosticTab = 'pyvmomi' | 'govc' | 'rest' | 'compare' | 'mcp'
type ResultState = {
  title: string
  result: ApiEnvelope<unknown> | null
}

const tabs: Array<{ key: DiagnosticTab; label: string }> = [
  { key: 'pyvmomi', label: 'pyVmomi' },
  { key: 'govc', label: 'govc' },
  { key: 'rest', label: 'vSphere REST' },
  { key: 'compare', label: 'Compare' },
  { key: 'mcp', label: 'MCP' },
]

export default function DiagnosticsPage() {
  const [activeTab, setActiveTab] = useState<DiagnosticTab>('pyvmomi')
  const [vmName, setVmName] = useState('')
  const [hostName, setHostName] = useState('')
  const [objectId, setObjectId] = useState('')
  const [libraryId, setLibraryId] = useState('')
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ResultState>({ title: 'Diagnostic Result', result: null })
  const [compareRows, setCompareRows] = useState<Array<{ field: string; pyvmomi: string; govc: string; status: string }>>([])

  async function run(title: string, loader: () => Promise<ApiEnvelope<unknown>>) {
    setValidationMessage(null)
    setCompareRows([])
    setLoading(true)
    const response = await loader()
    setResult({ title, result: response })
    setLoading(false)
  }

  function requireInput(value: string, message: string) {
    if (value.trim()) return true
    setValidationMessage(message)
    return false
  }

  function runWithInput(value: string, message: string, title: string, loader: () => Promise<ApiEnvelope<unknown>>) {
    if (!requireInput(value, message)) return
    void run(title, loader)
  }

  async function compareVm() {
    if (!requireInput(vmName, 'VM name is required before running compare.')) return
    setValidationMessage(null)
    setLoading(true)
    const [pyvmomi, govc] = await Promise.all([api.getVmDetails(vmName), api.getGovcVmInfo(vmName)])
    setCompareRows(
      compareFields(pyvmomi.ok ? pyvmomi.data : null, govc.ok ? govc.data : null, [
        { label: 'name', leftKeys: ['name', 'vm_name'], rightKeys: ['name', 'vm_name'] },
        { label: 'power state', leftKeys: ['power_state', 'powerState'], rightKeys: ['power_state', 'powerState'] },
        { label: 'CPU', leftKeys: ['cpu', 'num_cpu'], rightKeys: ['cpu', 'num_cpu'] },
        { label: 'memory', leftKeys: ['memory_gb', 'memory'], rightKeys: ['memory_gb', 'memory'] },
        { label: 'guest OS', leftKeys: ['guest_os', 'guestOs'], rightKeys: ['guest_os', 'guestOs'] },
        { label: 'host', leftKeys: ['host', 'host_name'], rightKeys: ['host', 'host_name'] },
      ]),
    )
    setResult({ title: 'Compare VM pyVmomi vs govc', result: { ok: true, data: { pyvmomi, govc } } })
    setLoading(false)
  }

  async function compareHost() {
    if (!requireInput(hostName, 'Host name is required before running compare.')) return
    setValidationMessage(null)
    setLoading(true)
    const [pyvmomi, govc] = await Promise.all([api.getHostDetails(hostName), api.getGovcHostInfo(hostName)])
    setCompareRows(
      compareFields(pyvmomi.ok ? pyvmomi.data : null, govc.ok ? govc.data : null, [
        { label: 'name', leftKeys: ['name', 'host'], rightKeys: ['name', 'host'] },
        { label: 'connection state', leftKeys: ['connection_state', 'status'], rightKeys: ['connection_state', 'status'] },
        { label: 'version', leftKeys: ['version'], rightKeys: ['version'] },
        { label: 'build', leftKeys: ['build'], rightKeys: ['build'] },
        { label: 'vendor', leftKeys: ['vendor'], rightKeys: ['vendor'] },
        { label: 'model', leftKeys: ['model'], rightKeys: ['model'] },
      ]),
    )
    setResult({ title: 'Compare Host pyVmomi vs govc', result: { ok: true, data: { pyvmomi, govc } } })
    setLoading(false)
  }

  async function compareDatastores() {
    setValidationMessage(null)
    setLoading(true)
    const [pyvmomi, govc] = await Promise.all([api.getDatastoreHealth(), api.getGovcDatastoreInfo()])
    setCompareRows([])
    setResult({ title: 'Compare Datastores pyVmomi vs govc', result: { ok: true, data: { pyvmomi, govc } } })
    setLoading(false)
  }

  const activeDescription = useMemo(() => tabs.find((tab) => tab.key === activeTab)?.label ?? 'Diagnostics', [activeTab])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Diagnostics"
        title="Diagnostics"
        description="Run safe read-only diagnostics across pyVmomi, govc, vSphere REST, and MCP metadata. No destructive actions."
      />

      <div className="flex flex-wrap gap-2 rounded-2xl border border-ops-steel/10 bg-white p-2 shadow-card">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.key ? 'bg-ops-navy text-white' : 'text-ops-steel hover:bg-ops-cream'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {validationMessage ? <ErrorState title="Input required" message={validationMessage} code="VALIDATION_ERROR" /> : null}

      <div className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <SectionCard title={`${activeDescription} Actions`} description="All actions call existing FastAPI read-only endpoints.">
          {activeTab === 'pyvmomi' ? (
            <div className="grid gap-4 md:grid-cols-2">
              <DiagnosticActionCard title="Environment Overview" description="Read vCenter environment summary." onRun={() => run('Environment Overview', api.getEnvironment)} />
              <DiagnosticActionCard title="Inspect VM" description="Inspect one VM by name." inputLabel="VM name" inputValue={vmName} onInputChange={setVmName} inputPlaceholder="roshellevm02" onRun={() => runWithInput(vmName, 'VM name is required.', 'VM Details', () => api.getVmDetails(vmName))} />
              <DiagnosticActionCard title="Inspect Host" description="Inspect one ESXi host." inputLabel="Host name" inputValue={hostName} onInputChange={setHostName} inputPlaceholder="esxi01.dclab.local" onRun={() => runWithInput(hostName, 'Host name is required.', 'Host Details', () => api.getHostDetails(hostName))} />
              <DiagnosticActionCard title="Datastore Health" description="Read datastore health summary." onRun={() => run('Datastore Health', api.getDatastoreHealth)} />
              <DiagnosticActionCard title="Active Alarms" description="Read active vCenter alarms." onRun={() => run('Active Alarms', api.getAlarms)} />
              <DiagnosticActionCard title="Recent Events" description="Read recent vCenter events." onRun={() => run('Recent Events', api.getEvents)} />
              <DiagnosticActionCard title="RKE2 VMs" description="Read RKE2 VM context." onRun={() => run('RKE2 VMs', api.getRke2Vms)} />
            </div>
          ) : null}

          {activeTab === 'govc' ? (
            <div className="grid gap-4 md:grid-cols-2">
              <DiagnosticActionCard title="govc about" description="Read govc/vCenter about info." onRun={() => run('govc about', api.getGovcAbout)} />
              <DiagnosticActionCard title="VM info" description="Read govc VM info." inputLabel="VM name" inputValue={vmName} onInputChange={setVmName} onRun={() => runWithInput(vmName, 'VM name is required.', 'govc VM info', () => api.getGovcVmInfo(vmName))} />
              <DiagnosticActionCard title="Host info" description="Read govc host info." inputLabel="Host" inputValue={hostName} onInputChange={setHostName} onRun={() => runWithInput(hostName, 'Host name is required.', 'govc Host info', () => api.getGovcHostInfo(hostName))} />
              <DiagnosticActionCard title="Datastore info" description="Read govc datastore info." onRun={() => run('govc Datastore info', api.getGovcDatastoreInfo)} />
              <DiagnosticActionCard title="Events" description="Read govc events." onRun={() => run('govc Events', api.getGovcEvents)} />
              <DiagnosticActionCard title="Volume list" description="Read govc volume list. Unsupported providers return clean errors." onRun={() => run('govc Volume list', api.getGovcVolumeLs)} />
            </div>
          ) : null}

          {activeTab === 'rest' ? (
            <div className="grid gap-4 md:grid-cols-2">
              <DiagnosticActionCard title="About" description="Read vSphere REST about info." onRun={() => run('vSphere REST About', api.getVsphereRestAbout)} />
              <DiagnosticActionCard title="Appliance Health" description="Read appliance health." onRun={() => run('Appliance Health', api.getVsphereRestApplianceHealth)} />
              <DiagnosticActionCard title="Tag Categories" description="List tag categories." onRun={() => run('Tag Categories', api.getVsphereRestTagCategories)} />
              <DiagnosticActionCard title="Tags" description="List tags." onRun={() => run('Tags', api.getVsphereRestTags)} />
              <DiagnosticActionCard title="Attached Tags" description="Requires object_id." inputLabel="object_id" inputValue={objectId} onInputChange={setObjectId} onRun={() => runWithInput(objectId, 'object_id is required before calling attached tags.', 'Attached Tags', () => api.getVsphereRestAttachedTags(objectId))} />
              <DiagnosticActionCard title="Content Libraries" description="List content libraries." onRun={() => run('Content Libraries', api.getVsphereRestContentLibraries)} />
              <DiagnosticActionCard title="Library Items" description="Requires library_id." inputLabel="library_id" inputValue={libraryId} onInputChange={setLibraryId} onRun={() => runWithInput(libraryId, 'library_id is required before calling library items.', 'Library Items', () => api.getVsphereRestLibraryItems(libraryId))} />
              <DiagnosticActionCard title="Recent Tasks" description="Provider-limited responses are shown cleanly." onRun={() => run('Recent Tasks', api.getVsphereRestRecentTasks)} />
            </div>
          ) : null}

          {activeTab === 'compare' ? (
            <div className="grid gap-4 md:grid-cols-2">
              <DiagnosticActionCard title="Compare VM pyVmomi vs govc" description="Compare obvious VM fields." inputLabel="VM name" inputValue={vmName} onInputChange={setVmName} onRun={compareVm} />
              <DiagnosticActionCard title="Compare Host pyVmomi vs govc" description="Compare obvious host fields." inputLabel="Host name" inputValue={hostName} onInputChange={setHostName} onRun={compareHost} />
              <DiagnosticActionCard title="Compare Datastores" description="Compare datastore health and govc datastore info." onRun={compareDatastores} />
            </div>
          ) : null}

          {activeTab === 'mcp' ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-ops-info bg-ops-info/20 p-4 text-sm text-ops-navy">
                Safe MCP execution is available through the AI Assistant. Arbitrary MCP execution is not exposed in the UI.
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <DiagnosticActionCard title="MCP Server Status" description="Read public MCP server status metadata." onRun={() => run('MCP Server Status', api.getMcpDefaultStatus)} />
                <DiagnosticActionCard title="MCP Tools Metadata" description="Read safe MCP tool metadata only." onRun={() => run('MCP Tools', api.getMcpTools)} />
              </div>
            </div>
          ) : null}
        </SectionCard>

        <div className="space-y-4">
          <div className="rounded-2xl border border-ops-steel/10 bg-white p-4 shadow-card">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status="read_only" />
              <ToolBadge label="no destructive actions" />
              <ToolBadge label="no raw govc command" />
              <ToolBadge label="no arbitrary MCP execution" active={false} />
            </div>
          </div>
          <DiagnosticResultPanel title={result.title} result={result.result} isLoading={loading} />
          {compareRows.length ? <ComparisonTable rows={compareRows} /> : null}
          {activeTab === 'mcp' && !result.result ? (
            <EmptyState title="MCP metadata only" description="Use the AI Assistant for safe MCP status prompts such as test MCP or show MCP time." />
          ) : null}
        </div>
      </div>
    </div>
  )
}
