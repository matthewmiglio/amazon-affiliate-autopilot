"use client";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { trackPageView } from "@/lib/analytics/client";

function slugFromPath(p: string | null): string | undefined {
  if (!p) return undefined;
  const m = p.match(/^\/p\/([^/?#]+)/);
  return m ? m[1] : undefined;
}

export function AnalyticsTracker() {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname) return;
    trackPageView(pathname, slugFromPath(pathname));
  }, [pathname]);
  return null;
}
