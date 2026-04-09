import clsx from "clsx";
import { BookStatus } from "../api/types";
import { TransitionAction } from "../api/books";

const OPTIONS: { value: BookStatus; label: string; action: TransitionAction }[] = [
  { value: "want_to_read", label: "Want to read", action: "reset" },
  { value: "reading", label: "Reading", action: "start" },
  { value: "finished", label: "Finished", action: "finish" },
  { value: "dnf", label: "DNF", action: "dnf" },
];

export default function StatusControl({
  current,
  onChange,
}: {
  current: BookStatus;
  onChange: (action: TransitionAction) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-zinc-200 bg-white p-0.5 text-xs dark:border-zinc-800 dark:bg-zinc-900">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.action)}
          className={clsx(
            "rounded px-3 py-1.5 font-medium transition",
            current === o.value
              ? "bg-accent text-white"
              : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
