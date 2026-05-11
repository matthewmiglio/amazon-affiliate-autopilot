import { NextRequest } from "next/server";
import { createClient } from "@supabase/supabase-js";

export const runtime = "edge";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const sb = createClient(url, key, { auth: { persistSession: false } });

const ALLOWED = new Set(["page_view", "amazon_click", "outbound_click"]);

export async function POST(req: NextRequest) {
  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }
  const event_type = String(body.event_type ?? "");
  if (!ALLOWED.has(event_type)) {
    return new Response("bad event_type", { status: 400 });
  }
  let referrer_host: string | null = null;
  if (typeof body.referrer === "string" && body.referrer) {
    try { referrer_host = new URL(body.referrer).hostname; } catch { /* keep null */ }
  }
  const h = req.headers;
  await sb.from("analytics_events").insert({
    event_type,
    path:        typeof body.path        === "string" ? body.path        : null,
    slug:        typeof body.slug        === "string" ? body.slug        : null,
    referrer:    typeof body.referrer    === "string" ? body.referrer    : null,
    referrer_host,
    destination: typeof body.destination === "string" ? body.destination : null,
    visitor_id:  typeof body.visitor_id  === "string" ? body.visitor_id  : null,
    session_id:  typeof body.session_id  === "string" ? body.session_id  : null,
    ua:          h.get("user-agent"),
    country:     h.get("x-vercel-ip-country"),
    region:      h.get("x-vercel-ip-country-region"),
    city:        h.get("x-vercel-ip-city"),
  });
  return new Response(null, { status: 204 });
}
