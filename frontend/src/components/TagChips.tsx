import { X } from "lucide-react";
import { useState } from "react";
import { Tag } from "../api/types";

export default function TagChips({
  tags,
  editable = false,
  onChange,
}: {
  tags: Tag[];
  editable?: boolean;
  onChange?: (names: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  const remove = (name: string) => {
    if (!onChange) return;
    onChange(tags.filter((t) => t.name !== name).map((t) => t.name));
  };

  const add = () => {
    if (!draft.trim() || !onChange) return;
    const next = Array.from(new Set([...tags.map((t) => t.name), draft.trim()]));
    onChange(next);
    setDraft("");
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.map((t) => (
        <span
          key={t.id}
          className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white px-2.5 py-0.5 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
        >
          {t.name}
          {editable && (
            <button onClick={() => remove(t.name)} className="rounded hover:text-accent">
              <X size={12} />
            </button>
          )}
        </span>
      ))}
      {editable && (
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="+ tag"
          className="w-24 bg-transparent text-xs outline-none placeholder:text-zinc-400"
        />
      )}
    </div>
  );
}
