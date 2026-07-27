export const runtime = 'edge'

function json(data: unknown, init?: { status?: number }): Response {
  return new Response(JSON.stringify(data), {
    status: init?.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function getBridgeUrl(): string | null {
  const raw = process.env.BRIDGE_URL
  if (!raw) return null
  return raw.trim().replace(/\/+$/, '')
}

export async function POST(request: Request): Promise<Response> {
  const bridgeUrl = getBridgeUrl()
  if (!bridgeUrl) {
    return json({ error: 'BRIDGE_URL is not configured' }, { status: 500 })
  }

  try {
    const body = await request.json()
    const headers = new Headers({ 'Content-Type': 'application/json' })
    if (process.env.BRIDGE_API_KEY) {
      headers.set('Authorization', `Bearer ${process.env.BRIDGE_API_KEY}`)
    }

    const url = `${bridgeUrl}/session/new`
    const upstream = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    const data = await upstream.json().catch(() => null)
    if (data) return json(data, { status: upstream.status })
    return json({ error: `Bridge returned non-JSON (${upstream.status})` }, { status: 502 })
  } catch (e) {
    return json({ error: `Bridge unreachable: ${e instanceof Error ? e.message : String(e)}` }, { status: 502 })
  }
}
