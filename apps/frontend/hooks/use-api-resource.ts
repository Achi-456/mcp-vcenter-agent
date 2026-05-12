'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ApiEnvelope } from '@/lib/types'

type ResourceState<T> = {
  data: T | null
  error: string | null
  errorCode: string | null
  isLoading: boolean
  isRefreshing: boolean
  lastUpdated: Date | null
  refresh: () => Promise<void>
}

type ResourceOptions = {
  refreshIntervalMs?: number
}

export function useApiResource<T>(loader: () => Promise<ApiEnvelope<T>>, options: ResourceOptions = {}): ResourceState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    setIsRefreshing(true)
    const result = await loader()

    if (result.ok) {
      setData(result.data)
      setError(null)
      setErrorCode(null)
      setLastUpdated(new Date())
    } else {
      setError(result.message)
      setErrorCode(result.error_code ?? 'API_ERROR')
    }

    setIsLoading(false)
    setIsRefreshing(false)
  }, [loader])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!options.refreshIntervalMs) return
    const interval = window.setInterval(() => {
      void refresh()
    }, options.refreshIntervalMs)

    return () => window.clearInterval(interval)
  }, [options.refreshIntervalMs, refresh])

  return useMemo(
    () => ({
      data,
      error,
      errorCode,
      isLoading,
      isRefreshing,
      lastUpdated,
      refresh,
    }),
    [data, error, errorCode, isLoading, isRefreshing, lastUpdated, refresh],
  )
}
