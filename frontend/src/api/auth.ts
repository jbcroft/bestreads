import { api, clearTokens, setTokens } from "./client";
import { TokenPair, UserPublic } from "./types";

export async function register(
  username: string,
  email: string,
  password: string
): Promise<UserPublic> {
  const r = await api.post<UserPublic>("/auth/register", {
    username,
    email,
    password,
  });
  return r.data;
}

export async function login(
  usernameOrEmail: string,
  password: string
): Promise<TokenPair> {
  const r = await api.post<TokenPair>("/auth/login", {
    username_or_email: usernameOrEmail,
    password,
  });
  setTokens(r.data.access_token, r.data.refresh_token);
  return r.data;
}

export function logout(): void {
  clearTokens();
}
