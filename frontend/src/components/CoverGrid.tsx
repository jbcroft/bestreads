import { Book } from "../api/types";
import BookCard from "./BookCard";

export default function CoverGrid({ books }: { books: Book[] }) {
  if (books.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-zinc-300 px-6 py-10 text-center text-sm text-zinc-500 dark:border-zinc-700">
        Nothing here yet.
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
