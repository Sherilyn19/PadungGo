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

function respond(body: string, status: number, contentType: string) {
  const response = new Response(body, { status, headers: { 'Content-Type': contentType } })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
  return response
}

describe('API responses', () => {
  it.each([502, 503, 504])('explains unavailable HTML responses (%s)', async (status) => {
    const response = respond('<html>Gateway error</html>', status, 'text/html')
    const json = vi.spyOn(response, 'json')
    await expect(searchLocations('cebu')).rejects.toMatchObject({
      message: 'The PadungGo server is unavailable or starting up. Please try again in a minute.',
      status,
      retryable: true,
    })
    expect(json).not.toHaveBeenCalled()
  })

  it.each([400, 503])('preserves JSON error details (%s)', async (status) => {
    respond(JSON.stringify({ error: { message: 'x', retryable: false } }), status, 'application/json')
    await expect(searchLocations('cebu')).rejects.toMatchObject({ message: 'x', status, retryable: false })
  })

  it.each([400, 500])('uses generic messages for other errors (%s)', async (status) => {
    respond('error', status, 'text/plain')
    await expect(searchLocations('cebu')).rejects.toMatchObject({
      message: `The server returned an error (${status}).`, status, retryable: status >= 500,
    })
  })

  it.each([
    ['<html>Unexpected</html>', 'text/html'],
    ['{invalid', 'application/json'],
    ['null', 'application/json'],
  ])('rejects unexpected successful responses (%s)', async (body, type) => {
    respond(body, 200, type)
    await expect(searchLocations('cebu')).rejects.toMatchObject({
      message: 'The server sent an unexpected response. Please try again.', status: 200, retryable: true,
    })
  })

  it('returns parsed JSON', async () => {
    respond('{"results":[]}', 200, 'application/json; charset=utf-8')
    await expect(searchLocations('cebu')).resolves.toEqual({ results: [] })
  })

  it('uses status-based retryability when JSON has no error message', async () => {
    respond('{"error":{"retryable":false}}', 502, 'application/json')
    await expect(searchLocations('cebu')).rejects.toMatchObject({
      message: 'The PadungGo server is unavailable or starting up. Please try again in a minute.',
      status: 502, retryable: true,
    })
  })
})

describe('cancellation', () => {
  it('does not fetch when already cancelled', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const controller = new AbortController()
    controller.abort()
    await expect(searchLocations('cebu', controller.signal)).rejects.toMatchObject({
      message: 'Request cancelled.', status: 0, retryable: false,
    })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('forwards cancellation and removes the listener', async () => {
    const controller = new AbortController()
    const removeListener = vi.spyOn(controller.signal, 'removeEventListener')
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })))
    const request = searchLocations('cebu', controller.signal)
    controller.abort()
    await expect(request).rejects.toEqual(new ApiError('Request cancelled.', 0, false))
    expect(removeListener).toHaveBeenCalledWith('abort', expect.any(Function))
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
