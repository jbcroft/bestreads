import { BookOpen } from "lucide-react";
import { Book } from "../api/types";
import BookCard from "./BookCard";

export default function CoverGrid({ books }: { books: Book[] }) {
  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-md border border-dashed border-zinc-300 px-6 py-12 text-center dark:border-zinc-700">
        <BookOpen size={28} className="text-zinc-400 dark:text-zinc-600" />
        <div className="mt-3 text-sm font-medium text-zinc-600 dark:text-zinc-400">
          Nothing here yet.
        </div>
        <div className="mt-1 text-xs text-zinc-500">
          Try adjusting your filters or add a book.
        </div>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-3 gap-5 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
      {books.map((b) => (
        <BookCard key={b.id} book={b} />
      ))}
    </div>
  );
}
