import { serverClient } from "@/lib/supabase";
import { rangeFromSearch, fmtInt } from "@/lib/range";

type SP = Promise<{ [k: string]: string | string[] | undefined }>;
type Row = { referrer_host: string; views: number; clicks: number };

export default async function ReferrersPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const { from, to } = rangeFromSearch(sp);
  const sb = serverClient();
  const { data } = await sb.rpc("analytics_referrer_breakdown", { from_ts: from, to_ts: to });
  const rows = (data as Row[]) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Referrers</h1>
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
            {rows.length === 0 ? (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-[var(--muted)]">No referrer data yet.</td></tr>
            ) : rows.map(r => (
              <tr key={r.referrer_host} className="border-t border-[var(--border)]">
                <td className="px-4 py-3">{r.referrer_host}</td>
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
