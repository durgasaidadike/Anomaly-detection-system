import { useCallback, useEffect, useRef, useState } from 'react'
import { getBackendHealth } from '../services/apiClient'

const HEALTH_REFRESH_INTERVAL = 30000

const INITIAL_HEALTH = {
  status: 'checking',
  data: null,
  error: null,
  lastCheckedAt: null,
}

export default function useBackendHealth() {
  const [health, setHealth] = useState(INITIAL_HEALTH)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const isMounted = useRef(false)
  const requestInProgress = useRef(false)

  const refresh = useCallback(async () => {
    if (requestInProgress.current) {
      return
    }

    requestInProgress.current = true

    if (isMounted.current) {
      setIsRefreshing(true)
    }

    try {
      const response = await getBackendHealth()

      // Validate the existing PRISM response contract.
      if (
        response?.status !== 'SUCCESS' ||
        !response?.data ||
        typeof response.data.status !== 'string'
      ) {
        throw new Error(
          'Backend returned an unexpected health response.'
        )
      }

      const serviceStatus = response.data.status.toUpperCase()
      const connected = serviceStatus === 'UP'

      if (isMounted.current) {
        setHealth({
          status: connected ? 'connected' : 'degraded',
          data: response.data,
          error: connected
            ? null
            : `Backend reported status: ${serviceStatus}`,
          lastCheckedAt: new Date(),
        })
      }
    } catch (error) {
      if (error?.name !== 'AbortError' && isMounted.current) {
        setHealth((previous) => ({
          ...previous,
          status: 'unavailable',
          error: error.message || 'Backend health check failed.',
          lastCheckedAt: new Date(),
        }))
      }
    } finally {
      requestInProgress.current = false

      if (isMounted.current) {
        setIsRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    isMounted.current = true

    refresh()

    const intervalId = window.setInterval(
      refresh,
      HEALTH_REFRESH_INTERVAL
    )

    return () => {
      isMounted.current = false
      window.clearInterval(intervalId)
    }
  }, [refresh])

  return {
    ...health,
    isRefreshing,
    refresh,
  }
}
