import { serverClient } from "@/lib/supabase";
import { rangeFromSearch, fmtInt, fmtPct } from "@/lib/range";
import { Card } from "@/components/Card";
import { TrafficChart } from "@/components/TrafficChart";
import { TabNav } from "@/components/TabNav";
import { HeaderKpis } from "@/components/HeaderKpis";

type SP = Promise<{ [k: string]: string | string[] | undefined }>;

type SummaryRow = {
  views?: number;
  clicks?: number;
  outbound?: number;
  visitors?: number;
  sessions?: number;
  ctr?: number;
};
type ProductRow = { slug: string; views: number; clicks: number; ctr: number };
type ReferrerRow = { referrer_host: string; views: number; clicks: number };
type GeoRow = { country: string; region: string; city: string; views: number; clicks: number };
type TrafficRow = { bucket_start: string; views: number; clicks: number; outbound: number };

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "products", label: "Top products" },
  { id: "referrers", label: "Referrers" },
  { id: "geo", label: "Geo" },
];

export default async function DashboardPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const { from, to } = rangeFromSearch(sp);

  // "Today" window for header KPIs
  const todayStart = new Date();
  todayStart.setUTCHours(0, 0, 0, 0);
  const todayFrom = todayStart.toISOString();
  const todayTo = new Date().toISOString();

  const sb = serverClient();

  const [
    { data: summary },
    { data: traffic },
    { data: products },
    { data: referrers },
    { data: geo },
    { data: todaySummary },
  ] = await Promise.all([
    sb.rpc("analytics_summary", { from_ts: from, to_ts: to }),
    sb.rpc("analytics_traffic_over_time", { from_ts: from, to_ts: to, bucket: "day" }),
    sb.rpc("analytics_top_products", { from_ts: from, to_ts: to, limit_n: 50 }),
    sb.rpc("analytics_referrer_breakdown", { from_ts: from, to_ts: to }),
    sb.rpc("analytics_geo_breakdown", { from_ts: from, to_ts: to }),
    sb.rpc("analytics_summary", { from_ts: todayFrom, to_ts: todayTo }),
  ]);

  const s: SummaryRow = (Array.isArray(summary) ? summary[0] : summary) ?? {};
  const t: SummaryRow = (Array.isArray(todaySummary) ? todaySummary[0] : todaySummary) ?? {};

  const productRows = (products as ProductRow[]) ?? [];
  const referrerRows = (referrers as ReferrerRow[]) ?? [];
  const geoRows = (geo as GeoRow[]) ?? [];
  const trafficRows = (traffic as TrafficRow[]) ?? [];

  return (
    <>
      <header className="sticky top-0 z-50 h-20 flex items-center px-6 bg-[var(--card)] border-b border-[var(--border)] shadow-lg shadow-black/40">
        <div className="max-w-7xl w-full mx-auto flex items-center">
          <div className="flex items-center gap-4">
            <div className="h-11 w-11 rounded-lg bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center text-[var(--accent)] font-bold text-lg">
              LD
            </div>
            <div>
              <h1 className="text-xl font-bold text-[var(--accent)] leading-tight">
                Luxe Drawer · Analytics
              </h1>
              <p className="text-xs text-[var(--muted)]">Real-time Analytics</p>
            </div>
          </div>
          <HeaderKpis
            views={t.views ?? 0}
            clicks={t.clicks ?? 0}
            ctr={t.ctr ?? 0}
          />
        </div>
      </header>

      <TabNav sections={SECTIONS} />

      <main className="flex-1 px-6 py-10 max-w-7xl w-full mx-auto space-y-16">
        <section id="overview" className="space-y-6 scroll-mt-40">
          <div className="flex items-baseline justify-between">
            <h2 className="text-2xl font-semibold">Overview</h2>
            <span className="text-xs text-[var(--muted)]">
              {new Date(from).toLocaleDateString()} → {new Date(to).toLocaleDateString()}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card label="Page views" value={fmtInt(s.views)} />
            <Card label="Amazon clicks" value={fmtInt(s.clicks)} sub={fmtPct(s.ctr) + " CTR"} />
            <Card label="Outbound" value={fmtInt(s.outbound)} />
            <Card label="Visitors" value={fmtInt(s.visitors)} />
            <Card label="Sessions" value={fmtInt(s.sessions)} />
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
            <h3 className="text-xs uppercase tracking-wider text-[var(--muted)] mb-4">
              Traffic over time
            </h3>
            <TrafficChart data={trafficRows} />
          </div>
        </section>

        <section id="products" className="space-y-6 scroll-mt-40">
          <h2 className="text-2xl font-semibold">Top products</h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-[var(--muted)] uppercase text-xs tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Slug</th>
                  <th className="text-right px-4 py-3">Views</th>
                  <th className="text-right px-4 py-3">Clicks</th>
                  <th className="text-right px-4 py-3">CTR</th>
                </tr>
              </thead>
              <tbody>
                {productRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-[var(--muted)]">
                      No product events yet.
                    </td>
                  </tr>
                ) : (
                  productRows.map((r) => (
                    <tr key={r.slug} className="border-t border-[var(--border)]">
                      <td className="px-4 py-3 font-mono text-xs">
                        <a
                          href={`https://theluxedrawer.com/p/${r.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[var(--accent)] hover:underline"
                        >
                          {r.slug}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.views)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtPct(r.ctr)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section id="referrers" className="space-y-6 scroll-mt-40">
          <h2 className="text-2xl font-semibold">Referrers</h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-[var(--muted)] uppercase text-xs tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Host</th>
                  <th className="text-right px-4 py-3">Views</th>
                  <th className="text-right px-4 py-3">Clicks</th>
                </tr>
              </thead>
              <tbody>
                {referrerRows.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-[var(--muted)]">
                      No referrer data yet.
                    </td>
                  </tr>
                ) : (
                  referrerRows.map((r) => (
                    <tr key={r.referrer_host} className="border-t border-[var(--border)]">
                      <td className="px-4 py-3">{r.referrer_host}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.views)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section id="geo" className="space-y-6 scroll-mt-40">
          <h2 className="text-2xl font-semibold">Geography</h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-[var(--muted)] uppercase text-xs tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Country</th>
                  <th className="text-left px-4 py-3">Region</th>
                  <th className="text-left px-4 py-3">City</th>
                  <th className="text-right px-4 py-3">Views</th>
                  <th className="text-right px-4 py-3">Clicks</th>
                </tr>
              </thead>
              <tbody>
                {geoRows.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted)]">
                      No geo data yet (events from localhost have no geo).
                    </td>
                  </tr>
                ) : (
                  geoRows.map((r, i) => (
                    <tr
                      key={`${r.country}-${r.region}-${r.city}-${i}`}
                      className="border-t border-[var(--border)]"
                    >
                      <td className="px-4 py-3">{r.country}</td>
                      <td className="px-4 py-3">{r.region}</td>
                      <td className="px-4 py-3">{r.city}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.views)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
