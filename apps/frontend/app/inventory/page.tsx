import { EmptyState, PageHeader, SectionCard, ToolBadge } from '@/components/ui'

const tabs = ['Virtual Machines', 'Hosts', 'Datastores']

export default function InventoryPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory"
        title="vCenter Inventory"
        description="Phase 9A scaffolds the vCenter-style inventory workspace. Searchable VM, host, and datastore tables are implemented in Phase 9D."
      />

      <SectionCard title="Inventory Views" description="Read-only inventory navigation.">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <ToolBadge key={tab} label={tab} />
          ))}
        </div>
        <div className="mt-5">
          <EmptyState
            title="Inventory tables are scheduled for Phase 9D"
            description="This scaffold will use /api/v1/inventory/vms, /hosts, /datastores, plus detail drawers for VM and host context."
          />
        </div>
      </SectionCard>
    </div>
  )
}
