const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    let detail = response.statusText
    if (typeof data === 'object' && data !== null && 'detail' in data) {
      const rawDetail = (data as { detail: unknown }).detail
      if (typeof rawDetail === 'string') {
        detail = rawDetail
      } else if (Array.isArray(rawDetail)) {
        const messages = rawDetail
          .map((item) => {
            if (typeof item === 'string') {
              return item
            }
            if (item !== null && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg)
            }
            return JSON.stringify(item)
          })
          .filter((item) => item.length > 0)
        detail = messages.length > 0 ? messages.join('; ') : response.statusText
      } else if (rawDetail !== null && rawDetail !== undefined) {
        detail = String(rawDetail)
      }
    } else if (typeof data === 'string' && data.length > 0) {
      detail = data
    }

    throw new ApiError(response.status, detail)
  }

  return data as T
}
