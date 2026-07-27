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

export async function GET(
  _request: Request,
  { params }: { params: { sid: string } },
): Promise<Response> {
  const bridgeUrl = getBridgeUrl()
  if (!bridgeUrl) {
    return json({ error: 'BRIDGE_URL is not configured' }, { status: 500 })
  }

  const { sid } = params
  const headers = new Headers()
  if (process.env.BRIDGE_API_KEY) {
    headers.set('Authorization', `Bearer ${process.env.BRIDGE_API_KEY}`)
  }

  try {
    const url = `${bridgeUrl}/session/${encodeURIComponent(sid)}/history`
    const upstream = await fetch(url, { headers })
    const data = await upstream.json().catch(() => null)
    if (data) {
      return new Response(JSON.stringify(data), {
        status: upstream.status,
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store, no-cache, must-revalidate',
        },
      })
    }
    return json({ error: `Bridge returned non-JSON (${upstream.status})` }, { status: 502 })
  } catch (e) {
    return json({ error: `Bridge unreachable: ${e instanceof Error ? e.message : String(e)}` }, { status: 502 })
  }
}
