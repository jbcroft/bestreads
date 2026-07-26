import { useState } from "react";
import { BookCheck, Check, Loader2, RefreshCw, X } from "lucide-react";
import { dismissRecommendation, useRecommendations } from "../api/recommendations";
import { useBookMutations } from "../api/books";
import { RecommendationItem } from "../api/types";
import { useToast } from "./Toast";
import { useQueryClient } from "@tanstack/react-query";

type CardAction = "want_to_read" | "finished" | "dismiss";

function RecCard({ rec }: { rec: RecommendationItem }) {
  const { create } = useBookMutations();
  const toast = useToast();
  const qc = useQueryClient();
  const [pending, setPending] = useState<CardAction | null>(null);
  const [done, setDone] = useState<CardAction | null>(null);

  const add = async (status: "want_to_read" | "finished") => {
    setPending(status);
    try {
      await create.mutateAsync({ title: rec.title, author: rec.author, status });
      setDone(status);
      toast.push(
        status === "finished"
          ? `Added "${rec.title}" to your library as read`
          : `Added "${rec.title}"`,
        "success"
      );
    } catch {
      toast.push(`Couldn't add "${rec.title}"`, "error");
    } finally {
      setPending(null);
    }
  };

  const dismiss = async () => {
    setPending("dismiss");
    try {
      await dismissRecommendation({ title: rec.title, author: rec.author });
      setDone("dismiss");
      toast.push(`Won't suggest "${rec.title}" again`, "success");
      qc.invalidateQueries({ queryKey: ["recommendations"] });
    } catch {
      toast.push(`Couldn't dismiss "${rec.title}"`, "error");
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="flex flex-col justify-between rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div>
        <div className="font-serif text-base">{rec.title}</div>
        <div className="text-xs text-zinc-500">{rec.author}</div>
        <p className="mt-2 text-sm leading-snug text-zinc-600 dark:text-zinc-300">
          {rec.reason}
        </p>
      </div>
      {done === "dismiss" ? (
        <div className="mt-4 inline-flex items-center gap-1.5 self-start rounded bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
          <X size={13} />
          Not interested
        </div>
      ) : done ? (
        <div className="mt-4 inline-flex items-center gap-1.5 self-start rounded bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
          <Check size={13} />
          {done === "finished" ? "In your library as read" : "Added to Want to Read"}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => add("want_to_read")}
            disabled={pending !== null}
            className="inline-flex items-center gap-1.5 rounded bg-accent px-2.5 py-1 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {pending === "want_to_read" && <Loader2 size={13} className="animate-spin" />}
            Add to Want to Read
          </button>
          <button
            onClick={() => add("finished")}
            disabled={pending !== null}
            title="Add to your library marked as read and refresh recommendations"
            className="inline-flex items-center gap-1.5 rounded border border-zinc-300 px-2.5 py-1 text-xs font-medium text-zinc-600 hover:border-accent hover:text-accent disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300"
          >
            {pending === "finished" ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <BookCheck size={13} />
            )}
            Already read it
          </button>
          <button
            onClick={dismiss}
            disabled={pending !== null}
            title="Don't suggest this book again"
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-zinc-400 hover:text-red-500 disabled:opacity-50 dark:text-zinc-500 dark:hover:text-red-400"
          >
            {pending === "dismiss" ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <X size={13} />
            )}
            Not interested
          </button>
        </div>
      )}
    </div>
  );
}

export default function Recommendations() {
  const { data, isLoading, isFetching, refetch } = useRecommendations({ count: 3 });
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
          {isFetching ? "Updating…" : "Refresh"}
        </button>
      </div>
      <div
        className={`grid gap-4 transition-opacity md:grid-cols-3 ${
          isFetching ? "pointer-events-none opacity-50" : ""
        }`}
      >
        {data.recommendations.map((r, i) => (
          <RecCard key={`${r.title}-${i}`} rec={r} />
        ))}
      </div>
    </section>
  );
}
