export const runtime = 'edge'

function json(data: unknown, init?: { status?: number }): Response {
  return new Response(JSON.stringify(data), {
    status: init?.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function POST(
  request: Request,
  { params }: { params: { sid: string } },
): Promise<Response> {
  const bridgeUrl = process.env.BRIDGE_URL
  if (!bridgeUrl) {
    return json({ error: 'BRIDGE_URL is not configured' }, { status: 500 })
  }

  const { sid } = params
  try {
    const body = await request.json()
    const headers = new Headers({ 'Content-Type': 'application/json' })
    if (process.env.BRIDGE_API_KEY) {
      headers.set('Authorization', `Bearer ${process.env.BRIDGE_API_KEY}`)
    }

    const upstream = await fetch(new URL(`/session/${encodeURIComponent(sid)}/question`, bridgeUrl).toString(), {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    const data = await upstream.json()
    return json(data, { status: upstream.status })
  } catch {
    return json({ error: 'Bridge is unavailable' }, { status: 502 })
  }
}
