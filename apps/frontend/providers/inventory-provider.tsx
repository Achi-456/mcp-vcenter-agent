"use client"

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react"
import { api, type InventoryOverview, type VM, type Host, type Datastore, type NetworkItem, type Cluster, type Alarm, type VMEvent } from "@/lib/api"

interface CacheState<T> {
  data: T | null
  isInitialLoading: boolean
  isRefreshing: boolean
  error: string | null
  lastUpdatedAt: string | null
}

interface InventoryContextType {
  overview: CacheState<InventoryOverview>
  vms: CacheState<VM[]>
  hosts: CacheState<Host[]>
  clusters: CacheState<Cluster[]>
  datastores: CacheState<Datastore[]>
  networks: CacheState<NetworkItem[]>
  alarms: CacheState<Alarm[]>
  events: CacheState<VMEvent[]>
  refreshOverview: () => Promise<void>
  refreshVMs: () => Promise<void>
  refreshHosts: () => Promise<void>
  refreshClusters: () => Promise<void>
  refreshDatastores: () => Promise<void>
  refreshNetworks: () => Promise<void>
  refreshAlarms: () => Promise<void>
  refreshEvents: () => Promise<void>
  refreshAll: () => Promise<void>
}

const initialCache = <T,>(): CacheState<T> => ({
  data: null, isInitialLoading: true, isRefreshing: false, error: null, lastUpdatedAt: null,
})

const InventoryContext = createContext<InventoryContextType | null>(null)

export function InventoryProvider({ children }: { children: ReactNode }) {
  const [overview, setOverview] = useState<CacheState<InventoryOverview>>(initialCache)
  const [vms, setVMs] = useState<CacheState<VM[]>>(initialCache)
  const [hosts, setHosts] = useState<CacheState<Host[]>>(initialCache)
  const [clusters, setClusters] = useState<CacheState<Cluster[]>>(initialCache)
  const [datastores, setDatastores] = useState<CacheState<Datastore[]>>(initialCache)
  const [networks, setNetworks] = useState<CacheState<NetworkItem[]>>(initialCache)
  const [alarms, setAlarms] = useState<CacheState<Alarm[]>>(initialCache)
  const [events, setEvents] = useState<CacheState<VMEvent[]>>(initialCache)
  const initialLoadDone = useRef(false)

  const doFetchOverview = useCallback(async () => {
    setOverview(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try {
      const d = await api.getInventoryOverview()
      setOverview({ data: d, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed"
      setOverview(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg }))
    }
  }, [])

  const doRefreshOverview = useCallback(async () => {
    setOverview(prev => ({ ...prev, isRefreshing: true, error: null }))
    try {
      const d = await api.getInventoryOverview(true)
      setOverview(prev => ({ data: d, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed"
      setOverview(prev => ({ ...prev, isRefreshing: false, error: msg }))
    }
  }, [])

  const doFetchVMs = useCallback(async () => {
    setVMs(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getVMs(); setVMs({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setVMs(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshVMs = useCallback(async () => {
    setVMs(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getVMs(true); setVMs({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setVMs(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchHosts = useCallback(async () => {
    setHosts(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getHosts(); setHosts({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setHosts(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshHosts = useCallback(async () => {
    setHosts(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getHosts(true); setHosts({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setHosts(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchClusters = useCallback(async () => {
    setClusters(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getClusters(); setClusters({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setClusters(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshClusters = useCallback(async () => {
    setClusters(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getClusters(true); setClusters({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setClusters(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchDatastores = useCallback(async () => {
    setDatastores(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getDatastores(); setDatastores({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setDatastores(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshDatastores = useCallback(async () => {
    setDatastores(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getDatastores(true); setDatastores({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setDatastores(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchNetworks = useCallback(async () => {
    setNetworks(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getNetworks(); setNetworks({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setNetworks(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshNetworks = useCallback(async () => {
    setNetworks(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getNetworks(true); setNetworks({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setNetworks(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchAlarms = useCallback(async () => {
    setAlarms(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getAlarms(); setAlarms({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setAlarms(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshAlarms = useCallback(async () => {
    setAlarms(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getAlarms(true); setAlarms({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setAlarms(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const doFetchEvents = useCallback(async () => {
    setEvents(prev => ({ ...prev, isRefreshing: prev.data !== null, isInitialLoading: prev.data === null, error: null }))
    try { const d = await api.getEvents(); setEvents({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setEvents(prev => ({ ...prev, isInitialLoading: false, isRefreshing: false, error: msg })) }
  }, [])

  const doRefreshEvents = useCallback(async () => {
    setEvents(prev => ({ ...prev, isRefreshing: true, error: null }))
    try { const d = await api.getEvents(true); setEvents({ data: d.items, isInitialLoading: false, isRefreshing: false, error: null, lastUpdatedAt: new Date().toISOString() }) }
    catch (e: unknown) { const msg = e instanceof Error ? e.message : "Failed"; setEvents(prev => ({ ...prev, isRefreshing: false, error: msg })) }
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.allSettled([doRefreshOverview(), doRefreshVMs(), doRefreshHosts(), doRefreshClusters(), doRefreshDatastores(), doRefreshNetworks(), doRefreshAlarms(), doRefreshEvents()])
  }, [doRefreshOverview, doRefreshVMs, doRefreshHosts, doRefreshClusters, doRefreshDatastores, doRefreshNetworks, doRefreshAlarms, doRefreshEvents])

  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true
      doFetchOverview()
      doFetchVMs()
      doFetchHosts()
      doFetchClusters()
      doFetchDatastores()
      doFetchNetworks()
      doFetchAlarms()
      doFetchEvents()
    }
    const id = setInterval(refreshAll, 120000)
    return () => clearInterval(id)
  }, [doFetchOverview, doFetchVMs, doFetchHosts, doFetchClusters, doFetchDatastores, doFetchNetworks, doFetchAlarms, doFetchEvents, refreshAll])

  return (
    <InventoryContext.Provider value={{
      overview, vms, hosts, clusters, datastores, networks, alarms, events,
      refreshOverview: doRefreshOverview, refreshVMs: doRefreshVMs, refreshHosts: doRefreshHosts,
      refreshClusters: doRefreshClusters, refreshDatastores: doRefreshDatastores, refreshNetworks: doRefreshNetworks,
      refreshAlarms: doRefreshAlarms, refreshEvents: doRefreshEvents, refreshAll,
    }}>
      {children}
    </InventoryContext.Provider>
  )
}

export function useInventory() {
  const ctx = useContext(InventoryContext)
  if (!ctx) throw new Error("useInventory must be used within InventoryProvider")
  return ctx
}
