import { useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, Loader2 } from "lucide-react";
import { useBookMutations } from "../api/books";
import { BookStatus } from "../api/types";
import { useToast } from "./Toast";

const STATUS_OPTIONS: { value: BookStatus; label: string }[] = [
  { value: "want_to_read", label: "Want to Read" },
  { value: "reading", label: "Reading" },
  { value: "finished", label: "Finished" },
  { value: "dnf", label: "DNF" },
];

export default function ManualAddModal({
  initialQuery = "",
  onClose,
}: {
  initialQuery?: string;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(initialQuery);
  const [author, setAuthor] = useState("");
  const [tags, setTags] = useState("");
  const [pageCount, setPageCount] = useState("");
  const [status, setStatus] = useState<BookStatus>("want_to_read");
  const [submitting, setSubmitting] = useState(false);
  const [added, setAdded] = useState(false);
  const { create } = useBookMutations();
  const toast = useToast();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !author.trim() || submitting) return;
    setSubmitting(true);
    try {
      await create.mutateAsync({
        title: title.trim(),
        author: author.trim(),
        page_count: pageCount ? parseInt(pageCount, 10) : undefined,
        status,
        tag_names: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setAdded(true);
      toast.push(`Added "${title.trim()}"`, "success");
      window.setTimeout(onClose, 1200);
    } catch {
      toast.push("Couldn't add the book — please try again", "error");
      setSubmitting(false);
    }
  };

  // Portal to <body>: this modal is mounted inside the sticky header, whose
  // backdrop-blur creates a containing block that would trap fixed positioning.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
        {added ? (
          <div className="flex flex-col items-center gap-3 py-8 text-center animate-fade-in">
            <CheckCircle2 size={40} className="text-accent" />
            <div>
              <div className="font-serif text-lg">Added to your library</div>
              <div className="mt-1 text-sm text-zinc-500">“{title.trim()}”</div>
            </div>
          </div>
        ) : (
          <>
            <h2 className="mb-4 font-serif text-xl">Add a book</h2>
            <form onSubmit={onSubmit} className="space-y-3">
              <fieldset disabled={submitting} className="space-y-3 disabled:opacity-60">
                <Field label="Title" value={title} onChange={setTitle} required />
                <Field label="Author" value={author} onChange={setAuthor} required />
                <div>
                  <span className="mb-1 block text-xs font-medium text-zinc-500">Status</span>
                  <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Status">
                    {STATUS_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        role="radio"
                        aria-checked={status === opt.value}
                        onClick={() => setStatus(opt.value)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                          status === opt.value
                            ? "border-accent bg-accent text-white"
                            : "border-zinc-200 text-zinc-600 hover:border-accent hover:text-accent dark:border-zinc-700 dark:text-zinc-300"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
                <Field label="Tags (comma separated)" value={tags} onChange={setTags} />
                <Field label="Page count" value={pageCount} onChange={setPageCount} type="number" />
              </fieldset>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={submitting}
                  className="rounded px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 disabled:opacity-50 dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-70"
                >
                  {submitting && <Loader2 size={14} className="animate-spin" />}
                  {submitting ? "Adding…" : "Add book"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full rounded border border-zinc-200 bg-transparent px-3 py-2 text-sm outline-none focus:border-accent dark:border-zinc-700"
      />
    </label>
  );
}
