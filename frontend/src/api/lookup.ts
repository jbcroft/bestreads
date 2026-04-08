import { api } from "./client";
import { LookupResult, LookupSearchItem } from "./types";

export async function lookupIsbn(isbn: string): Promise<LookupResult> {
  const r = await api.get<LookupResult>("/lookup", { params: { isbn } });
  return r.data;
}

export async function lookupSearch(
  q: string,
  limit = 8
): Promise<LookupSearchItem[]> {
  const r = await api.get<LookupSearchItem[]>("/lookup/search", {
    params: { q, limit },
  });
  return r.data;
}
