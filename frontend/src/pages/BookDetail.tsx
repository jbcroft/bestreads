import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Edit3, Trash2 } from "lucide-react";
import { useBook, useBookMutations, TransitionAction } from "../api/books";
import StatusControl from "../components/StatusControl";
import StarRating from "../components/StarRating";
import TagChips from "../components/TagChips";
import { useToast } from "../components/Toast";

export default function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: book, isLoading } = useBook(id);
  const { transition, update, remove, setTags } = useBookMutations();
  const toast = useToast();
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesDraft, setNotesDraft] = useState("");
  const [editingInfo, setEditingInfo] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [authorDraft, setAuthorDraft] = useState("");

  if (isLoading || !book) {
    return <div className="h-64 animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-900" />;
  }

  const onTransition = async (action: TransitionAction) => {
    await transition.mutateAsync({ id: book.id, action });
    toast.push("Status updated", "success");
  };

  const onRate = async (rating: number | null) => {
    await update.mutateAsync({ id: book.id, payload: { rating: rating ?? undefined } });
    toast.push("Rating saved", "success");
  };

  const onSaveInfo = async () => {
    const title = titleDraft.trim();
    const author = authorDraft.trim();
    if (!title || !author) {
      toast.push("Title and author can't be empty", "error");
      return;
    }
    await update.mutateAsync({ id: book.id, payload: { title, author } });
    toast.push("Book updated", "success");
    setEditingInfo(false);
  };

  const onSaveNotes = async () => {
    await update.mutateAsync({ id: book.id, payload: { notes: notesDraft } });
    toast.push("Notes saved", "success");
    setEditingNotes(false);
  };

  const onDelete = async () => {
    if (!confirm("Delete this book from your library?")) return;
    await remove.mutateAsync(book.id);
    toast.push("Book deleted", "success");
    navigate("/library");
  };

  return (
    <div className="animate-fade-in">
      <div className="grid gap-10 md:grid-cols-[220px,1fr]">
        <div>
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={book.title}
              className="aspect-[2/3] w-full rounded object-cover shadow-sm"
            />
          ) : (
            <div className="flex aspect-[2/3] w-full items-center justify-center rounded bg-zinc-100 p-4 text-center dark:bg-zinc-900">
              <div>
                <div className="font-serif">{book.title}</div>
                <div className="text-xs text-zinc-500">{book.author}</div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          {editingInfo ? (
            <div className="space-y-2">
              <input
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                placeholder="Title"
                autoFocus
                className="w-full rounded border border-zinc-200 bg-transparent px-3 py-2 font-serif text-2xl outline-none focus:border-accent dark:border-zinc-700"
              />
              <input
                value={authorDraft}
                onChange={(e) => setAuthorDraft(e.target.value)}
                placeholder="Author"
                className="w-full rounded border border-zinc-200 bg-transparent px-3 py-2 text-base outline-none focus:border-accent dark:border-zinc-700"
              />
              <div className="flex gap-2">
                <button
                  onClick={onSaveInfo}
                  disabled={update.isPending}
                  className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditingInfo(false)}
                  className="rounded px-3 py-1.5 text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              <div className="flex items-start gap-2">
                <h1 className="font-serif text-3xl leading-tight">{book.title}</h1>
                <button
                  onClick={() => {
                    setTitleDraft(book.title);
                    setAuthorDraft(book.author);
                    setEditingInfo(true);
                  }}
                  title="Edit title and author"
                  className="mt-2 text-zinc-400 opacity-0 transition-opacity hover:text-accent focus:opacity-100 group-hover:opacity-100"
                >
                  <Edit3 size={16} />
                </button>
              </div>
              <p className="mt-1 text-base text-zinc-500">{book.author}</p>
            </div>
          )}

          <StatusControl current={book.status} onChange={onTransition} />

          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-zinc-500">Rating</div>
            <StarRating value={book.rating} onChange={onRate} />
          </div>

          <div>
            <div className="mb-2 text-xs uppercase tracking-wide text-zinc-500">Tags</div>
            <TagChips
              tags={book.tags}
              editable
              onChange={(names) => setTags.mutate({ id: book.id, tag_names: names })}
            />
          </div>

          {book.description && (
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-zinc-500">About</div>
              <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                {book.description}
              </p>
            </div>
          )}

          <div>
            <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wide text-zinc-500">
              <span>Notes</span>
              <button
                onClick={() => {
                  setNotesDraft(book.notes ?? "");
                  setEditingNotes((v) => !v);
                }}
                className="inline-flex items-center gap-1 normal-case text-zinc-500 hover:text-accent"
              >
                <Edit3 size={12} /> {editingNotes ? "Cancel" : "Edit"}
              </button>
            </div>
            {editingNotes ? (
              <div className="space-y-2">
                <textarea
                  value={notesDraft}
                  onChange={(e) => setNotesDraft(e.target.value)}
                  rows={8}
                  placeholder="Write notes in markdown…"
                  className="w-full rounded border border-zinc-200 bg-transparent p-3 font-mono text-sm outline-none focus:border-accent dark:border-zinc-700"
                />
                <button
                  onClick={onSaveNotes}
                  className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
                >
                  Save
                </button>
              </div>
            ) : book.notes ? (
              <article className="prose prose-sm prose-zinc max-w-none dark:prose-invert">
                <ReactMarkdown>{book.notes}</ReactMarkdown>
              </article>
            ) : (
              <p className="text-sm text-zinc-500">No notes yet.</p>
            )}
          </div>

          <div className="flex justify-end pt-4">
            <button
              onClick={onDelete}
              className="inline-flex items-center gap-2 rounded text-xs text-zinc-500 hover:text-red-600"
            >
              <Trash2 size={14} /> Delete from library
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
