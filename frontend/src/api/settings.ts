import { api } from "./client";

export interface ApiKeyView {
  api_key: string | null;
}

export interface ApiKeyPlain {
  api_key: string;
}

export async function viewApiKey(): Promise<ApiKeyView> {
  const r = await api.get<ApiKeyView>("/settings/api-key");
  return r.data;
}

export async function regenerateApiKey(): Promise<ApiKeyPlain> {
  const r = await api.post<ApiKeyPlain>("/settings/api-key/regenerate");
  return r.data;
}
