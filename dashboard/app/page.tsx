import { serverClient } from "@/lib/supabase";
import { rangeFromSearch, fmtInt, fmtPct } from "@/lib/range";
import { Card } from "@/components/Card";
import { TrafficChart } from "@/components/TrafficChart";

type SP = Promise<{ [k: string]: string | string[] | undefined }>;

export default async function OverviewPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const { from, to } = rangeFromSearch(sp);
  const sb = serverClient();

  const [{ data: summary }, { data: traffic }] = await Promise.all([
    sb.rpc("analytics_summary", { from_ts: from, to_ts: to }),
    sb.rpc("analytics_traffic_over_time", { from_ts: from, to_ts: to, bucket: "day" }),
  ]);
  const s = (Array.isArray(summary) ? summary[0] : summary) ?? {};

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Overview</h1>
        <span className="text-xs text-[var(--muted)]">{new Date(from).toLocaleDateString()} → {new Date(to).toLocaleDateString()}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card label="Page views"   value={fmtInt(s.views)} />
        <Card label="Amazon clicks" value={fmtInt(s.clicks)} sub={fmtPct(s.ctr) + " CTR"} />
        <Card label="Outbound"     value={fmtInt(s.outbound)} />
        <Card label="Visitors"     value={fmtInt(s.visitors)} />
        <Card label="Sessions"     value={fmtInt(s.sessions)} />
      </div>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
        <h2 className="text-sm uppercase tracking-wider text-[var(--muted)] mb-4">Traffic over time</h2>
        <TrafficChart data={(traffic as never[]) ?? []} />
      </section>
    </div>
  );
}
