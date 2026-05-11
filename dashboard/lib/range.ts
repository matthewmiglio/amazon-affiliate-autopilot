export function rangeFromSearch(searchParams: Record<string, string | string[] | undefined>) {
  const now = new Date();
  const defFrom = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const from = typeof searchParams.from === "string" ? new Date(searchParams.from) : defFrom;
  const to   = typeof searchParams.to   === "string" ? new Date(searchParams.to)   : now;
  return { from: from.toISOString(), to: to.toISOString(), fromDate: from, toDate: to };
}

export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}

export function fmtPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${Number(n).toFixed(2)}%`;
}
