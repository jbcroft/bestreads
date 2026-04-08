import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import { Book, BookStatus, SearchResponse, Tag } from "./types";

export interface BookListFilters {
  status?: BookStatus;
  tag?: string;
  q?: string;
  min_rating?: number;
  sort?: "date_added" | "title" | "author" | "rating" | "finished_at";
}

export async function fetchBooks(filters: BookListFilters = {}): Promise<Book[]> {
  const r = await api.get<Book[]>("/books", { params: filters });
  return r.data;
}

export async function fetchBook(id: string): Promise<Book> {
  const r = await api.get<Book>(`/books/${id}`);
  return r.data;
}

export interface BookCreatePayload {
  title: string;
  author: string;
  isbn?: string;
  page_count?: number;
  description?: string;
  status?: BookStatus;
  rating?: number;
  notes?: string;
  tag_names?: string[];
  cover_image_path?: string;
  cover_url?: string;
}

export async function createBook(payload: BookCreatePayload): Promise<Book> {
  const r = await api.post<Book>("/books", payload);
  return r.data;
}

export async function updateBook(
  id: string,
  payload: Partial<BookCreatePayload>
): Promise<Book> {
  const r = await api.patch<Book>(`/books/${id}`, payload);
  return r.data;
}

export async function deleteBook(id: string): Promise<void> {
  await api.delete(`/books/${id}`);
}

export async function transitionBook(
  id: string,
  action: "start" | "finish" | "reset"
): Promise<Book> {
  const r = await api.post<Book>(`/books/${id}/${action}`);
  return r.data;
}

export async function setBookTags(id: string, tag_names: string[]): Promise<Book> {
  const r = await api.patch<Book>(`/books/${id}/tags`, { tag_names });
  return r.data;
}

export async function uploadCover(id: string, file: File): Promise<Book> {
  const form = new FormData();
  form.append("file", file);
  const r = await api.post<Book>(`/books/${id}/cover`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return r.data;
}

export async function searchAll(q: string): Promise<SearchResponse> {
  const r = await api.get<SearchResponse>("/search", { params: { q } });
  return r.data;
}

// ---------- Hooks ----------

export function useBooks(filters: BookListFilters = {}) {
  return useQuery({
    queryKey: ["books", filters],
    queryFn: () => fetchBooks(filters),
  });
}

export function useBook(id: string | undefined) {
  return useQuery({
    queryKey: ["book", id],
    queryFn: () => fetchBook(id!),
    enabled: !!id,
  });
}

export function useBookMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["books"] });
    qc.invalidateQueries({ queryKey: ["stats"] });
    qc.invalidateQueries({ queryKey: ["recommendations"] });
  };

  const create = useMutation({
    mutationFn: createBook,
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<BookCreatePayload> }) =>
      updateBook(id, payload),
    onSuccess: (book) => {
      invalidate();
      qc.setQueryData(["book", book.id], book);
    },
  });
  const remove = useMutation({
    mutationFn: deleteBook,
    onSuccess: invalidate,
  });
  const transition = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "start" | "finish" | "reset" }) =>
      transitionBook(id, action),
    onSuccess: (book) => {
      invalidate();
      qc.setQueryData(["book", book.id], book);
    },
  });
  const setTags = useMutation({
    mutationFn: ({ id, tag_names }: { id: string; tag_names: string[] }) =>
      setBookTags(id, tag_names),
    onSuccess: (book) => {
      invalidate();
      qc.setQueryData(["book", book.id], book);
    },
  });
  const cover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => uploadCover(id, file),
    onSuccess: (book) => {
      invalidate();
      qc.setQueryData(["book", book.id], book);
    },
  });

  return { create, update, remove, transition, setTags, cover };
}
