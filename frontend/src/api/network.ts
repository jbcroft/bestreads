import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { NetworkResponse } from "./types";

export async function fetchNetwork(): Promise<NetworkResponse> {
  const r = await api.get<NetworkResponse>("/network");
  return r.data;
}

export function useNetwork() {
  return useQuery({ queryKey: ["network"], queryFn: fetchNetwork });
}
