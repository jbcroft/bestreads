import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { StatsResponse } from "./types";

export async function fetchStats(): Promise<StatsResponse> {
  const r = await api.get<StatsResponse>("/stats");
  return r.data;
}

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: fetchStats });
}
