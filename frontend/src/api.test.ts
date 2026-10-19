import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, searchLocations } from './api'

// Simulates fetch honouring its AbortSignal, like the browser does.
function pendingFetchUntilAborted() {
  return vi.fn(
    (_url: string, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
      }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('searchLocations cancellation', () => {
  it('does not send a request when the signal is already aborted', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const caller = new AbortController()
    caller.abort()

    const error = await searchLocations('Colon', caller.signal).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toBe('Request cancelled.')
    expect((error as ApiError).retryable).toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('aborts the in-flight fetch when the caller cancels', async () => {
    const fetchMock = pendingFetchUntilAborted()
    vi.stubGlobal('fetch', fetchMock)
    const caller = new AbortController()

    const pending = searchLocations('Colon', caller.signal).catch((e: unknown) => e)
    caller.abort()
    const error = await pending

    expect(fetchMock).toHaveBeenCalledOnce()
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal?.aborted).toBe(true)
    expect((error as ApiError).message).toBe('Request cancelled.')
    expect((error as ApiError).retryable).toBe(false)
  })

  it('removes its abort listener from the caller signal once the request finishes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ results: [] }), { status: 200 })),
    )
    const caller = new AbortController()
    const removeSpy = vi.spyOn(caller.signal, 'removeEventListener')

    await expect(searchLocations('Colon', caller.signal)).resolves.toEqual({ results: [] })

    expect(removeSpy).toHaveBeenCalledWith('abort', expect.any(Function))
  })
})
