import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { Tag } from "./types";

export async function fetchTags(): Promise<Tag[]> {
  const r = await api.get<Tag[]>("/tags");
  return r.data;
}

export function useTags() {
  return useQuery({ queryKey: ["tags"], queryFn: fetchTags });
}
