import { useNetwork } from "../api/network";
import NetworkGraph from "../components/NetworkGraph";

export default function Network() {
  const { data, isLoading, isError } = useNetwork();

  if (isError) {
    return (
      <div className="space-y-4 animate-fade-in">
        <h1 className="font-serif text-3xl">Network</h1>
        <p className="text-zinc-500">Failed to load network data. Please try again later.</p>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-800 dark:border-zinc-700 dark:border-t-zinc-200" />
      </div>
    );
  }

  if (data.nodes.length < 2) {
    return (
      <div className="space-y-4 animate-fade-in">
        <h1 className="font-serif text-3xl">Network</h1>
        <p className="text-zinc-500">
          Add more books to see your network. You need at least 2 books with
          descriptions or tags.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-3xl">Network</h1>
        <div className="flex gap-2">
          {data.clusters.map((c) => (
            <span
              key={c.id}
              className="flex items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-xs dark:bg-zinc-800"
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: c.color }}
              />
              {c.label}
            </span>
          ))}
        </div>
      </div>
      <NetworkGraph data={data} />
    </div>
  );
}
