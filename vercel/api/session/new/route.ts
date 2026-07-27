export const runtime = 'edge'

export async function POST(request: Request): Promise<Response> {
  const bridgeUrl = process.env.BRIDGE_URL
  if (!bridgeUrl) {
    return Response.json({ error: 'BRIDGE_URL is not configured' }, { status: 500 })
  }

  try {
    const body = await request.json()
    const headers = new Headers({ 'Content-Type': 'application/json' })
    if (process.env.BRIDGE_API_KEY) {
      headers.set('Authorization', `Bearer ${process.env.BRIDGE_API_KEY}`)
    }

    const upstream = await fetch(new URL('/session/new', bridgeUrl).toString(), {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    const data = await upstream.json()
    return Response.json(data, { status: upstream.status })
  } catch {
    return Response.json({ error: 'Bridge is unavailable' }, { status: 502 })
  }
}
