import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  can: (role: User["role"]) => boolean;
}
const Ctx = createContext<AuthState>(null as unknown as AuthState);
const RANK = { viewer: 1, analyst: 2, admin: 3 };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) { setReady(true); return; }
    api<User>("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api<{ access_token: string; user: User }>("/auth/login", { method: "POST", form: new URLSearchParams({ username, password }) });
    setToken(res.access_token);
    setUser(res.user);
  };
  const logout = () => { setToken(null); setUser(null); };
  const can = (role: User["role"]) => !!user && RANK[user.role] >= RANK[role];

  return <Ctx.Provider value={{ user, ready, login, logout, can }}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
