"use client";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";

type Row = { bucket_start: string; views: number; clicks: number; outbound: number };

export function TrafficChart({ data }: { data: Row[] }) {
  if (!data?.length) {
    return <div className="text-sm text-[var(--muted)] py-10 text-center">No traffic in range yet.</div>;
  }
  const fmt = data.map(d => ({
    ...d,
    day: new Date(d.bucket_start).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  }));
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={fmt} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#232229" strokeDasharray="3 3" />
          <XAxis dataKey="day" stroke="#8b8a85" fontSize={12} />
          <YAxis stroke="#8b8a85" fontSize={12} allowDecimals={false} />
          <Tooltip contentStyle={{ background: "#15141a", border: "1px solid #232229", color: "#f4f3ee" }} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#8b8a85" }} />
          <Line type="monotone" dataKey="views"    stroke="#d6b27a" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="clicks"   stroke="#7ad6b2" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="outbound" stroke="#b27ad6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
