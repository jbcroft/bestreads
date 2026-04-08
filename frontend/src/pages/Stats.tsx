import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useStats } from "../api/stats";

export default function Stats() {
  const { data, isLoading } = useStats();

  if (isLoading || !data) {
    return <div className="h-64 animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-900" />;
  }

  return (
    <div className="space-y-10 animate-fade-in">
      <h1 className="font-serif text-3xl">Stats</h1>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Total books" value={data.total_books} />
        <Metric label="Reading" value={data.by_status.reading ?? 0} />
        <Metric label="Finished" value={data.by_status.finished ?? 0} />
        <Metric
          label="Avg rating"
          value={data.avg_rating != null ? data.avg_rating.toFixed(1) : "—"}
        />
      </section>

      <section>
        <h2 className="mb-4 font-serif text-xl">Finished by month</h2>
        <div className="h-64 rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.finished_by_month}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.1} />
              <XAxis dataKey="month" fontSize={11} />
              <YAxis allowDecimals={false} fontSize={11} />
              <Tooltip
                cursor={{ fill: "rgba(180,65,43,0.08)" }}
                contentStyle={{ fontSize: 12 }}
              />
              <Bar dataKey="count" fill="#B4412B" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="mb-4 font-serif text-xl">Top tags</h2>
          <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            {data.top_tags.length === 0 ? (
              <p className="text-sm text-zinc-500">No tags yet.</p>
            ) : (
              <ul className="space-y-2">
                {data.top_tags.map((t) => (
                  <li key={t.name} className="flex items-center justify-between text-sm">
                    <span>{t.name}</span>
                    <span className="text-zinc-500">{t.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div>
          <h2 className="mb-4 font-serif text-xl">This year</h2>
          <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="font-serif text-4xl">{data.finished_this_year}</div>
            <div className="text-sm text-zinc-500">books finished in {new Date().getFullYear()}</div>
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className="mt-1 font-serif text-3xl">{value}</div>
    </div>
  );
}
