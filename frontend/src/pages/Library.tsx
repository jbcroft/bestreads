import { useState } from "react";
import { Grid, List, Search, Star } from "lucide-react";
import clsx from "clsx";
import { useBooks, BookListFilters } from "../api/books";
import { useTags } from "../api/tags";
import CoverGrid from "../components/CoverGrid";
import { Book, BookStatus } from "../api/types";
import { Link } from "react-router-dom";

const STATUSES: BookStatus[] = ["want_to_read", "reading", "finished"];
const STATUS_LABELS: Record<BookStatus, string> = {
  want_to_read: "Want to read",
  reading: "Reading",
  finished: "Finished",
  dnf: "DNF",
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

  const books = booksQ.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl leading-none">Library</h1>
          <div className="mt-1 text-sm text-zinc-500">
            {booksQ.isLoading ? "Loading…" : `${books.length} ${books.length === 1 ? "book" : "books"}`}
          </div>
        </div>
        <div className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white p-0.5 text-xs dark:border-zinc-800 dark:bg-zinc-900">
          <button
            aria-label="Grid view"
            className={clsx(
              "rounded p-1.5 transition-colors",
              view === "grid"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            )}
            onClick={() => setView("grid")}
          >
            <Grid size={14} />
          </button>
          <button
            aria-label="List view"
            className={clsx(
              "rounded p-1.5 transition-colors",
              view === "list"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            )}
            onClick={() => setView("list")}
          >
            <List size={14} />
          </button>
        </div>
      </div>

      <div className="space-y-3 rounded-md border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="relative">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
          />
          <input
            placeholder="Search title, author, notes…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full rounded border border-zinc-200 bg-transparent py-1.5 pl-8 pr-3 text-sm outline-none transition-colors hover:border-zinc-300 focus:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-600 dark:focus:border-zinc-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-1">
            <FilterChip active={!status} onClick={() => setStatus(undefined)}>
              All
            </FilterChip>
            {STATUSES.map((s) => (
              <FilterChip key={s} active={status === s} onClick={() => setStatus(s)}>
                {STATUS_LABELS[s]}
              </FilterChip>
            ))}
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select
              value={tag ?? ""}
              onChange={(e) => setTag(e.target.value || undefined)}
              className="rounded border border-zinc-200 bg-white px-2 py-1 text-xs transition-colors hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600"
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
              className="rounded border border-zinc-200 bg-white px-2 py-1 text-xs transition-colors hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600"
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
              className="rounded border border-zinc-200 bg-white px-2 py-1 text-xs transition-colors hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600"
            >
              <option value="date_added">Recently added</option>
              <option value="title">Title</option>
              <option value="author">Author</option>
              <option value="rating">Rating</option>
              <option value="finished_at">Date finished</option>
            </select>
          </div>
        </div>
      </div>

      {booksQ.isLoading ? (
        <div className="h-64 animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-900" />
      ) : view === "grid" ? (
        <CoverGrid books={books} />
      ) : books.length === 0 ? (
        <div className="rounded-md border border-dashed border-zinc-300 px-6 py-10 text-center text-sm text-zinc-500 dark:border-zinc-700">
          Nothing here yet.
        </div>
      ) : (
        <ul className="divide-y divide-zinc-100 overflow-hidden rounded-md border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-900">
          {books.map((b) => (
            <LibraryListRow key={b.id} book={b} />
          ))}
        </ul>
      )}
    </div>
  );
}

function LibraryListRow({ book }: { book: Book }) {
  const hasMeta =
    book.rating != null || book.page_count != null || book.tags.length > 0;

  return (
    <li>
      <Link
        to={`/books/${book.id}`}
        className="flex items-center gap-4 px-4 py-4 transition-colors hover:bg-stone-50 dark:hover:bg-zinc-800/60"
      >
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt=""
            className="h-16 w-11 flex-shrink-0 rounded bg-zinc-100 object-cover shadow-sm dark:bg-zinc-800"
            loading="lazy"
          />
        ) : (
          <div className="h-16 w-11 flex-shrink-0 rounded bg-zinc-100 shadow-sm dark:bg-zinc-800" />
        )}

        <div className="min-w-0 flex-1">
          <div className="truncate font-medium text-zinc-900 dark:text-zinc-100">
            {book.title}
          </div>
          <div className="truncate text-xs text-zinc-500">{book.author}</div>
          {hasMeta && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
              {book.rating != null && (
                <div className="flex items-center gap-0.5" aria-label={`Rated ${book.rating} of 5`}>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Star
                      key={n}
                      size={11}
                      className={
                        n <= book.rating!
                          ? "fill-accent text-accent"
                          : "text-zinc-300 dark:text-zinc-700"
                      }
                    />
                  ))}
                </div>
              )}
              {book.page_count != null && <span>{book.page_count} pages</span>}
              {book.tags.slice(0, 2).map((t) => (
                <span
                  key={t.id}
                  className="rounded-full border border-zinc-200 px-2 py-0.5 text-[11px] text-zinc-500 dark:border-zinc-700"
                >
                  {t.name}
                </span>
              ))}
            </div>
          )}
        </div>

        <StatusPill status={book.status} />
      </Link>
    </li>
  );
}

function StatusPill({ status }: { status: BookStatus }) {
  const base = "rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap";
  if (status === "reading") {
    return (
      <span className={clsx(base, "bg-accent/10 text-accent dark:bg-accent/20")}>
        {STATUS_LABELS[status]}
      </span>
    );
  }
  return (
    <span className={clsx(base, "bg-stone-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400")}>
      {STATUS_LABELS[status]}
    </span>
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
        "rounded-full border px-2.5 py-1 text-xs transition-colors",
        active
          ? "border-accent bg-accent text-white"
          : "border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-stone-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
      )}
    >
      {children}
    </button>
  );
}
