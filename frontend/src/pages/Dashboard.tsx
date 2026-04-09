import { useBooks } from "../api/books";
import CoverGrid from "../components/CoverGrid";
import Recommendations from "../components/Recommendations";

export default function Dashboard() {
  const wantQ = useBooks({ status: "want_to_read" });
  const readingQ = useBooks({ status: "reading" });
  const finishedQ = useBooks({ status: "finished" });
  const dnfQ = useBooks({ status: "dnf" });

  return (
    <div className="space-y-12">
      <Recommendations />

      <Shelf
        title="Reading"
        count={readingQ.data?.length ?? 0}
        loading={readingQ.isLoading}
      >
        {readingQ.data && <CoverGrid books={readingQ.data} />}
      </Shelf>

      <Shelf
        title="Want to read"
        count={wantQ.data?.length ?? 0}
        loading={wantQ.isLoading}
      >
        {wantQ.data && <CoverGrid books={wantQ.data} />}
      </Shelf>

      <Shelf
        title="Finished"
        count={finishedQ.data?.length ?? 0}
        loading={finishedQ.isLoading}
      >
        {finishedQ.data && <CoverGrid books={finishedQ.data} />}
      </Shelf>

      <Shelf
        title="Did not finish"
        count={dnfQ.data?.length ?? 0}
        loading={dnfQ.isLoading}
      >
        {dnfQ.data && <CoverGrid books={dnfQ.data} />}
      </Shelf>
    </div>
  );
}

function Shelf({
  title,
  count,
  loading,
  children,
}: {
  title: string;
  count: number;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-serif text-2xl">{title}</h2>
        <span className="text-xs text-zinc-500">{count} books</span>
      </div>
      {loading ? (
        <div className="grid grid-cols-3 gap-5 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[2/3] animate-pulse rounded bg-zinc-100 dark:bg-zinc-900"
            />
          ))}
        </div>
      ) : (
        children
      )}
    </section>
  );
}
