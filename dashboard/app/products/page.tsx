import { serverClient } from "@/lib/supabase";
import { rangeFromSearch, fmtInt, fmtPct } from "@/lib/range";

type SP = Promise<{ [k: string]: string | string[] | undefined }>;
type Row = { slug: string; views: number; clicks: number; ctr: number };

export default async function ProductsPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const { from, to } = rangeFromSearch(sp);
  const sb = serverClient();
  const { data } = await sb.rpc("analytics_top_products", { from_ts: from, to_ts: to, limit_n: 50 });
  const rows = (data as Row[]) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Top products</h1>
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
            {rows.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-[var(--muted)]">No product events yet.</td></tr>
            ) : rows.map(r => (
              <tr key={r.slug} className="border-t border-[var(--border)]">
                <td className="px-4 py-3 font-mono text-xs">
                  <a href={`https://theluxedrawer.com/p/${r.slug}`} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] hover:underline">
                    {r.slug}
                  </a>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.views)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmtPct(r.ctr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
