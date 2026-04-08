import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { RecommendationsResponse } from "./types";

export interface RecommendationFilters {
  count?: number;
  mood?: string;
  tag?: string;
}

export async function fetchRecommendations(
  filters: RecommendationFilters = {}
): Promise<RecommendationsResponse> {
  const r = await api.get<RecommendationsResponse>("/recommendations", {
    params: filters,
  });
  return r.data;
}

export function useRecommendations(filters: RecommendationFilters = {}) {
  return useQuery({
    queryKey: ["recommendations", filters],
    queryFn: () => fetchRecommendations(filters),
    staleTime: 1000 * 60 * 5,
  });
}
