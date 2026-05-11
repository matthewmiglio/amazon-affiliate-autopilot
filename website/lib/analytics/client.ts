"use client";
import { getVisitorId, getSessionId } from "./ids";

type EventBody = {
  event_type: "page_view" | "amazon_click" | "outbound_click";
  path?: string;
  slug?: string;
  destination?: string;
  referrer?: string;
  visitor_id?: string;
  session_id?: string;
};

function isLocalhost(): boolean {
  if (typeof window === "undefined") return true;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" || h.endsWith(".local");
}

async function send(body: EventBody): Promise<void> {
  if (typeof window === "undefined") return;
  if (isLocalhost()) {
    // Skip noise from dev; uncomment the line below if you want to test locally.
    // console.debug("[analytics:skip-localhost]", body);
    return;
  }
  body.visitor_id = body.visitor_id ?? (await getVisitorId());
  body.session_id = body.session_id ?? getSessionId();
  body.referrer = body.referrer ?? document.referrer ?? undefined;

  const payload = JSON.stringify(body);
  const url = "/api/analytics";

  if (typeof navigator !== "undefined" && "sendBeacon" in navigator) {
    const blob = new Blob([payload], { type: "application/json" });
    if (navigator.sendBeacon(url, blob)) return;
  }
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    });
  } catch {
    /* fire-and-forget */
  }
}

export function trackPageView(path: string, slug?: string): void {
  void send({ event_type: "page_view", path, slug });
}

export function trackAmazonClick(args: { slug: string; destination: string; path?: string }): void {
  void send({
    event_type: "amazon_click",
    slug: args.slug,
    destination: args.destination,
    path: args.path ?? (typeof window !== "undefined" ? window.location.pathname : undefined),
  });
}

export function trackOutboundClick(args: { destination: string; path?: string }): void {
  void send({
    event_type: "outbound_click",
    destination: args.destination,
    path: args.path ?? (typeof window !== "undefined" ? window.location.pathname : undefined),
  });
}
