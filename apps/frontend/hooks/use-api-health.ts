"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"

type HealthStatus = "ok" | "degraded" | "error" | "checking"

export function useApiHealth(interval = 30000) {
  const [status, setStatus] = useState<HealthStatus>("checking")

  const check = useCallback(async () => {
    try {
      const data = await api.health()
      setStatus(data.status === "ok" ? "ok" : "degraded")
    } catch {
      setStatus("error")
    }
  }, [])

  useEffect(() => {
    check()
    const id = setInterval(check, interval)
    return () => clearInterval(id)
  }, [check, interval])

  return { status }
}
