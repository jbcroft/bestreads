import { useState } from "react";
import { Grid, List } from "lucide-react";
import clsx from "clsx";
import { useBooks, BookListFilters } from "../api/books";
import { useTags } from "../api/tags";
import CoverGrid from "../components/CoverGrid";
import { BookStatus } from "../api/types";
import { Link } from "react-router-dom";

const STATUSES: BookStatus[] = ["want_to_read", "reading", "finished"];
const STATUS_LABELS: Record<BookStatus, string> = {
  want_to_read: "Want to read",
  reading: "Reading",
  finished: "Finished",
};

export default function Library() {
  const [status, setStatus] = useState<BookStatus | undefined>();
  const [tag, setTag] = useState<string | undefined>();
  const [q, setQ] = useState("");
  const [minRating, setMinRating] = useState<number | undefined>();
  const [sort, setSort] = useState<NonNullable<BookListFilters["sort"]>>("date_added");
  const [view, setView] = useState<"grid" | "list">("grid");

  const tagsQ = useTags();
  const booksQ = useBooks({
    status,
    tag,
    q: q || undefined,
    min_rating: minRating,
    sort,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="font-serif text-3xl">Library</h1>
        <div className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white p-0.5 text-xs dark:border-zinc-800 dark:bg-zinc-900">
          <button
            className={clsx(
              "rounded p-1.5",
              view === "grid" ? "bg-zinc-100 dark:bg-zinc-800" : "text-zinc-500"
            )}
            onClick={() => setView("grid")}
          >
            <Grid size={14} />
          </button>
          <button
            className={clsx(
              "rounded p-1.5",
              view === "list" ? "bg-zinc-100 dark:bg-zinc-800" : "text-zinc-500"
            )}
            onClick={() => setView("list")}
          >
            <List size={14} />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <input
          placeholder="Search title, author, notes…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="min-w-[180px] flex-1 bg-transparent text-sm outline-none"
        />

        <div className="flex gap-1">
          <FilterChip active={!status} onClick={() => setStatus(undefined)}>
            All
          </FilterChip>
          {STATUSES.map((s) => (
            <FilterChip key={s} active={status === s} onClick={() => setStatus(s)}>
              {STATUS_LABELS[s]}
            </FilterChip>
          ))}
        </div>

        <select
          value={tag ?? ""}
          onChange={(e) => setTag(e.target.value || undefined)}
          className="rounded border border-zinc-200 bg-transparent px-2 py-1 text-xs dark:border-zinc-700"
        >
          <option value="">All tags</option>
          {tagsQ.data?.map((t) => (
            <option key={t.id} value={t.name}>
              {t.name}
            </option>
          ))}
        </select>

        <select
          value={minRating ?? ""}
          onChange={(e) => setMinRating(e.target.value ? Number(e.target.value) : undefined)}
          className="rounded border border-zinc-200 bg-transparent px-2 py-1 text-xs dark:border-zinc-700"
        >
          <option value="">Any rating</option>
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>
              {n}+ stars
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          className="rounded border border-zinc-200 bg-transparent px-2 py-1 text-xs dark:border-zinc-700"
        >
          <option value="date_added">Recently added</option>
          <option value="title">Title</option>
          <option value="author">Author</option>
          <option value="rating">Rating</option>
          <option value="finished_at">Date finished</option>
        </select>
      </div>

      {booksQ.isLoading ? (
        <div className="h-64 animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-900" />
      ) : view === "grid" ? (
        <CoverGrid books={booksQ.data ?? []} />
      ) : (
        <ul className="divide-y divide-zinc-100 rounded-md border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-900">
          {(booksQ.data ?? []).map((b) => (
            <li key={b.id}>
              <Link
                to={`/books/${b.id}`}
                className="flex items-center gap-4 px-4 py-3 hover:bg-stone-50 dark:hover:bg-zinc-800/60"
              >
                {b.cover_url ? (
                  <img
                    src={b.cover_url}
                    alt=""
                    className="h-12 w-8 flex-shrink-0 rounded bg-zinc-100 object-cover dark:bg-zinc-800"
                  />
                ) : (
                  <div className="h-12 w-8 flex-shrink-0 rounded bg-zinc-100 dark:bg-zinc-800" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{b.title}</div>
                  <div className="truncate text-xs text-zinc-500">{b.author}</div>
                </div>
                <div className="text-xs text-zinc-500">{STATUS_LABELS[b.status]}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "rounded-full border px-2.5 py-1 text-xs transition",
        active
          ? "border-accent bg-accent text-white"
          : "border-zinc-200 text-zinc-600 hover:border-zinc-300 dark:border-zinc-700 dark:text-zinc-300"
      )}
    >
      {children}
    </button>
  );
}
