"use client";
import FingerprintJS from "@fingerprintjs/fingerprintjs";

const VISITOR_KEY = "tld_visitor_id";
const SESSION_KEY = "tld_session_id";
const SESSION_TS  = "tld_session_ts";
const SESSION_MAX_MS = 30 * 60 * 1000; // 30 min

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return "v-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

let fpPromise: Promise<string> | null = null;

export async function getVisitorId(): Promise<string> {
  if (typeof window === "undefined") return "";
  const cached = localStorage.getItem(VISITOR_KEY);
  if (cached) return cached;
  if (!fpPromise) {
    fpPromise = (async () => {
      try {
        const fp = await FingerprintJS.load();
        const res = await fp.get();
        return res.visitorId;
      } catch {
        return uuid();
      }
    })();
  }
  const id = await fpPromise;
  localStorage.setItem(VISITOR_KEY, id);
  return id;
}

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  const now = Date.now();
  const last = Number(localStorage.getItem(SESSION_TS) || 0);
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid || (now - last) > SESSION_MAX_MS) {
    sid = uuid();
    localStorage.setItem(SESSION_KEY, sid);
  }
  localStorage.setItem(SESSION_TS, String(now));
  return sid;
}
