import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { lookupSearch } from "../api/lookup";
import { LookupSearchItem } from "../api/types";
import { useBookMutations } from "../api/books";
import { useToast } from "./Toast";
import ManualAddModal from "./ManualAddModal";

export default function QuickAdd() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<LookupSearchItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [picked, setPicked] = useState<LookupSearchItem | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const { create } = useBookMutations();
  const toast = useToast();

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(async () => {
      setLoading(true);
      try {
        const res = await lookupSearch(q, 8);
        setResults(res);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [q]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const onPick = (item: LookupSearchItem) => {
    setPicked(item);
    setOpen(false);
  };

  const onConfirm = async (tag_names: string[]) => {
    if (!picked) return;
    await create.mutateAsync({
      title: picked.title,
      author: picked.author,
      isbn: picked.isbn ?? undefined,
      cover_url: picked.cover_url ?? undefined,
      status: "want_to_read",
      tag_names,
    });
    toast.push(`Added "${picked.title}" to Want to Read`, "success");
    setPicked(null);
    setQ("");
  };

  return (
    <div ref={containerRef} className="relative mx-auto max-w-xl">
      <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <Search size={16} className="text-zinc-400" />
        <input
          type="text"
          placeholder="Search a book to add…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          className="w-full bg-transparent outline-none placeholder:text-zinc-400"
        />
      </div>

      {open && (results.length > 0 || loading) && (
        <div className="absolute left-0 right-0 top-full z-40 mt-2 max-h-96 overflow-auto rounded-lg border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          {loading && results.length === 0 ? (
            <div className="p-3 text-sm text-zinc-500">Searching Open Library…</div>
          ) : (
            <>
              {results.map((r, i) => (
                <button
                  key={`${r.title}-${r.author}-${i}`}
                  onClick={() => onPick(r)}
                  className="flex w-full items-start gap-3 border-b border-zinc-100 px-3 py-3 text-left last:border-b-0 hover:bg-stone-50 dark:border-zinc-800 dark:hover:bg-zinc-800/70"
                >
                  {r.cover_url ? (
                    <img src={r.cover_url} alt="" className="h-12 w-8 flex-shrink-0 rounded bg-zinc-100 object-cover dark:bg-zinc-800" />
                  ) : (
                    <div className="h-12 w-8 flex-shrink-0 rounded bg-zinc-100 dark:bg-zinc-800" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{r.title}</div>
                    <div className="truncate text-xs text-zinc-500">
                      {r.author}
                      {r.year ? ` · ${r.year}` : ""}
                    </div>
                  </div>
                </button>
              ))}
              <button
                onClick={() => {
                  setManualOpen(true);
                  setOpen(false);
                }}
                className="block w-full border-t border-zinc-100 px-3 py-3 text-left text-xs text-accent hover:bg-stone-50 dark:border-zinc-800 dark:hover:bg-zinc-800/70"
              >
                Can't find it? Add manually →
              </button>
            </>
          )}
        </div>
      )}

      {picked && (
        <ConfirmAddCard
          item={picked}
          onCancel={() => setPicked(null)}
          onConfirm={onConfirm}
        />
      )}

      {manualOpen && <ManualAddModal initialQuery={q} onClose={() => setManualOpen(false)} />}
    </div>
  );
}

function ConfirmAddCard({
  item,
  onCancel,
  onConfirm,
}: {
  item: LookupSearchItem;
  onCancel: () => void;
  onConfirm: (tag_names: string[]) => void;
}) {
  const [tags, setTags] = useState("");
  return (
    <div className="absolute left-0 right-0 top-full z-40 mt-2 rounded-lg border border-zinc-200 bg-white p-4 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex gap-4">
        {item.cover_url ? (
          <img
            src={item.cover_url}
            alt=""
            className="h-24 w-16 rounded bg-zinc-100 object-cover dark:bg-zinc-800"
          />
        ) : (
          <div className="h-24 w-16 rounded bg-zinc-100 dark:bg-zinc-800" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate font-serif text-lg">{item.title}</div>
          <div className="truncate text-sm text-zinc-500">{item.author}</div>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="tags (comma separated, optional)"
            className="mt-3 w-full rounded border border-zinc-200 bg-transparent px-2 py-1 text-sm outline-none dark:border-zinc-700"
          />
        </div>
      </div>
      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Cancel
        </button>
        <button
          onClick={() =>
            onConfirm(
              tags
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean)
            )
          }
          className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
        >
          Add to Want to Read
        </button>
      </div>
    </div>
  );
}
