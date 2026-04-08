import { Link } from "react-router-dom";
import { Book } from "../api/types";

export default function BookCard({ book }: { book: Book }) {
  return (
    <Link
      to={`/books/${book.id}`}
      className="group block animate-fade-in"
      title={`${book.title} — ${book.author}`}
    >
      <div className="aspect-[2/3] overflow-hidden rounded bg-zinc-200 transition-transform group-hover:-translate-y-0.5 group-hover:shadow-md dark:bg-zinc-800">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={book.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center p-3 text-center">
            <div className="font-serif text-sm leading-tight text-zinc-700 dark:text-zinc-300">
              {book.title}
            </div>
            <div className="mt-1 text-xs text-zinc-500">{book.author}</div>
          </div>
        )}
      </div>
      <div className="mt-2 truncate text-xs font-medium text-zinc-800 dark:text-zinc-200">
        {book.title}
      </div>
      <div className="truncate text-xs text-zinc-500">{book.author}</div>
    </Link>
  );
}
