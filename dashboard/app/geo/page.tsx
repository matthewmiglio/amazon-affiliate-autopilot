import { serverClient } from "@/lib/supabase";
import { rangeFromSearch, fmtInt } from "@/lib/range";

type SP = Promise<{ [k: string]: string | string[] | undefined }>;
type Row = { country: string; region: string; city: string; views: number; clicks: number };

export default async function GeoPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const { from, to } = rangeFromSearch(sp);
  const sb = serverClient();
  const { data } = await sb.rpc("analytics_geo_breakdown", { from_ts: from, to_ts: to });
  const rows = (data as Row[]) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Geography</h1>
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
            {rows.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-[var(--muted)]">No geo data yet (events from localhost have no geo).</td></tr>
            ) : rows.map((r, i) => (
              <tr key={`${r.country}-${r.region}-${r.city}-${i}`} className="border-t border-[var(--border)]">
                <td className="px-4 py-3">{r.country}</td>
                <td className="px-4 py-3">{r.region}</td>
                <td className="px-4 py-3">{r.city}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.views)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.clicks)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
