import { Star } from "lucide-react";
import clsx from "clsx";

export default function StarRating({
  value,
  onChange,
}: {
  value: number | null;
  onChange?: (v: number | null) => void;
}) {
  const readonly = !onChange;
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => {
        const active = value !== null && n <= value;
        return (
          <button
            key={n}
            type="button"
            disabled={readonly}
            onClick={() => onChange && onChange(value === n ? null : n)}
            className={clsx(
              "rounded p-0.5",
              readonly ? "cursor-default" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
            )}
            title={`${n} star${n === 1 ? "" : "s"}`}
          >
            <Star
              size={18}
              className={active ? "fill-accent text-accent" : "text-zinc-300 dark:text-zinc-600"}
            />
          </button>
        );
      })}
    </div>
  );
}
