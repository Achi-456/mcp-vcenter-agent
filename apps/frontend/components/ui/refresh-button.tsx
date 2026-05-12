type RefreshButtonProps = {
  onRefresh: () => void | Promise<void>
  isRefreshing?: boolean
}

export function RefreshButton({ onRefresh, isRefreshing = false }: RefreshButtonProps) {
  return (
    <button
      type="button"
      onClick={() => void onRefresh()}
      disabled={isRefreshing}
      className="inline-flex items-center justify-center rounded-xl bg-ops-navy px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-ops-steel disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isRefreshing ? 'Refreshing...' : 'Refresh'}
    </button>
  )
}
