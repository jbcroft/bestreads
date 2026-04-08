import { useState } from "react";
import { useBookMutations } from "../api/books";
import { useToast } from "./Toast";

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
  const { create } = useBookMutations();
  const toast = useToast();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !author.trim()) return;
    await create.mutateAsync({
      title: title.trim(),
      author: author.trim(),
      page_count: pageCount ? parseInt(pageCount, 10) : undefined,
      status: "want_to_read",
      tag_names: tags.split(",").map((t) => t.trim()).filter(Boolean),
    });
    toast.push(`Added "${title.trim()}"`, "success");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-4 font-serif text-xl">Add a book</h2>
        <form onSubmit={onSubmit} className="space-y-3">
          <Field label="Title" value={title} onChange={setTitle} required />
          <Field label="Author" value={author} onChange={setAuthor} required />
          <Field label="Tags (comma separated)" value={tags} onChange={setTags} />
          <Field label="Page count" value={pageCount} onChange={setPageCount} type="number" />
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Add book
            </button>
          </div>
        </form>
      </div>
    </div>
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
