export const runtime = 'edge'

function json(data: unknown, init?: { status?: number }): Response {
  return new Response(JSON.stringify(data), {
    status: init?.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function GET(request: Request): Promise<Response> {
  const sid = new URL(request.url).searchParams.get('sid')
  const bridgeUrl = process.env.BRIDGE_URL

  if (!sid) {
    return json({ error: 'sid query parameter is required' }, { status: 400 })
  }
  if (!bridgeUrl) {
    return json({ error: 'BRIDGE_URL is not configured' }, { status: 500 })
  }

  const sseHeaders = {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  }

  const bridge = new URL(`/session/${encodeURIComponent(sid)}/stream`, bridgeUrl)
  const headers = new Headers()
  if (process.env.BRIDGE_API_KEY) {
    headers.set('Authorization', `Bearer ${process.env.BRIDGE_API_KEY}`)
  }

  try {
    const upstream = await fetch(bridge.toString(), { headers, signal: request.signal })
    if (!upstream.ok || !upstream.body) {
      return json(
        { error: `Bridge SSE request failed (${upstream.status})` },
        { status: upstream.status || 502 },
      )
    }
    return new Response(upstream.body, { headers: sseHeaders })
  } catch {
    return json({ error: 'Bridge is unavailable' }, { status: 502 })
  }
}
