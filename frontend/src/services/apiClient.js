const API_PREFIX = '/api/'

export class ApiClientError extends Error {
  constructor(message, { status = null, payload = null, cause = null } = {}) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.payload = payload
    this.cause = cause
  }
}

export async function getJson(endpoint, { signal } = {}) {
  // Dashboard API calls must use the Spring Boot /api boundary.
  if (
    typeof endpoint !== 'string' ||
    !endpoint.startsWith(API_PREFIX)
  ) {
    throw new TypeError(
      'API endpoint must be a relative Spring Boot /api path.'
    )
  }

  let response

  try {
    response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw error
    }

    throw new ApiClientError(
      'Unable to reach the PRISM Spring Boot backend.',
      { cause: error }
    )
  }

  let payload

  try {
    payload = await response.json()
  } catch (error) {
    throw new ApiClientError(
      'Spring Boot returned an invalid JSON response.',
      {
        status: response.status,
        cause: error,
      }
    )
  }

  if (!response.ok) {
    const backendMessage =
      payload?.errors?.[0]?.message

    throw new ApiClientError(
      backendMessage ||
        `Spring Boot request failed with HTTP ${response.status}.`,
      {
        status: response.status,
        payload,
      }
    )
  }

  return payload
}

export function getBackendHealth(options = {}) {
  return getJson('/api/health', options)
}
