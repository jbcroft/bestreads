import { RefreshCw } from "lucide-react";
import { useRecommendations } from "../api/recommendations";
import { useBookMutations } from "../api/books";
import { useToast } from "./Toast";
import { useQueryClient } from "@tanstack/react-query";

export default function Recommendations() {
  const { data, isLoading, isFetching, refetch } = useRecommendations({ count: 3 });
  const { create } = useBookMutations();
  const toast = useToast();
  const qc = useQueryClient();

  if (isLoading) {
    return <div className="h-32 animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-900" />;
  }
  if (!data || !data.available) {
    return (
      <div className="rounded-md border border-dashed border-zinc-300 px-6 py-8 text-sm text-zinc-500 dark:border-zinc-700">
        {data?.message || "Add a few more books to unlock personalized recommendations."}
      </div>
    );
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-serif text-xl">You might like</h2>
        <button
          onClick={() => {
            qc.removeQueries({ queryKey: ["recommendations"] });
            refetch();
          }}
          disabled={isFetching}
          className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-accent disabled:opacity-50"
        >
          <RefreshCw size={12} className={isFetching ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {data.recommendations.map((r, i) => (
          <div
            key={`${r.title}-${i}`}
            className="flex flex-col justify-between rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div>
              <div className="font-serif text-base">{r.title}</div>
              <div className="text-xs text-zinc-500">{r.author}</div>
              <p className="mt-2 text-sm leading-snug text-zinc-600 dark:text-zinc-300">
                {r.reason}
              </p>
            </div>
            <button
              onClick={async () => {
                await create.mutateAsync({
                  title: r.title,
                  author: r.author,
                  status: "want_to_read",
                });
                toast.push(`Added "${r.title}"`, "success");
              }}
              className="mt-4 self-start rounded bg-accent px-2.5 py-1 text-xs font-medium text-white hover:bg-accent-hover"
            >
              Add to Want to Read
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
