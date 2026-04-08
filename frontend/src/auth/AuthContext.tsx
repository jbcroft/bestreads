import { createContext, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { clearTokens, getAccessToken } from "../api/client";

interface AuthState {
  isAuthed: boolean;
  loading: boolean;
  login: (id: string, pw: string) => Promise<void>;
  register: (u: string, e: string, p: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthed, setIsAuthed] = useState<boolean>(() => !!getAccessToken());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setIsAuthed(!!getAccessToken());
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      isAuthed,
      loading,
      login: async (id, pw) => {
        setLoading(true);
        try {
          await authApi.login(id, pw);
          setIsAuthed(true);
        } finally {
          setLoading(false);
        }
      },
      register: async (u, e, p) => {
        setLoading(true);
        try {
          await authApi.register(u, e, p);
          await authApi.login(u, p);
          setIsAuthed(true);
        } finally {
          setLoading(false);
        }
      },
      logout: () => {
        clearTokens();
        setIsAuthed(false);
      },
    }),
    [isAuthed, loading]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
