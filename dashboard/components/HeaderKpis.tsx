type HeaderKpisProps = {
  views: number;
  clicks: number;
  ctr: number;
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return new Intl.NumberFormat("en-US").format(n);
}

export function HeaderKpis({ views, clicks, ctr }: HeaderKpisProps) {
  return (
    <div className="ml-auto flex items-center gap-8">
      <div className="text-center">
        <div className="text-2xl font-bold text-[var(--fg)] tabular-nums">{fmt(views)}</div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Views today</div>
      </div>
      <div className="h-10 w-px bg-[var(--border)]" />
      <div className="text-center">
        <div className="text-2xl font-bold text-[var(--accent)] tabular-nums">{fmt(clicks)}</div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Amazon clicks</div>
      </div>
      <div className="h-10 w-px bg-[var(--border)]" />
      <div className="text-center">
        <div className="text-2xl font-bold text-emerald-400 tabular-nums">
          {ctr ? `${Number(ctr).toFixed(2)}%` : "0%"}
        </div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">CTR today</div>
      </div>
    </div>
  );
}
