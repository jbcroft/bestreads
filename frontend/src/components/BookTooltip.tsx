import { Link } from "react-router-dom";
import type { NetworkNode } from "../api/types";

interface Props {
  node: NetworkNode;
  x: number;
  y: number;
  onClose: () => void;
}

export default function BookTooltip({ node, x, y, onClose }: Props) {
  return (
    <div
      className="pointer-events-auto absolute z-50 w-72 rounded-lg border border-zinc-200 bg-white p-4 shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
      style={{ left: x + 12, top: y - 12 }}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-2 top-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
        aria-label="Close"
      >
        &times;
      </button>
      <h3 className="pr-6 font-serif text-lg font-semibold leading-tight">
        {node.title}
      </h3>
      <p className="mt-0.5 text-sm text-zinc-500">{node.author}</p>

      {node.rating != null && (
        <p className="mt-1 text-sm text-amber-500">
          {"★".repeat(node.rating)}
          {"☆".repeat(5 - node.rating)}
        </p>
      )}

      {node.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {node.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {node.description && (
        <p className="mt-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
          {node.description.length > 150
            ? node.description.slice(0, 150) + "…"
            : node.description}
        </p>
      )}

      <Link
        to={`/books/${node.id}`}
        className="mt-3 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
      >
        View details &rarr;
      </Link>
    </div>
  );
}
