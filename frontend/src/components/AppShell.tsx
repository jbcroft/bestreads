import { Link, NavLink } from "react-router-dom";
import { LogOut, Moon, Sun } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
import QuickAdd from "./QuickAdd";
import clsx from "clsx";

const navLinks = [
  { to: "/", label: "Home", end: true },
  { to: "/library", label: "Library" },
  { to: "/stats", label: "Stats" },
  { to: "/settings", label: "Settings" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-30 border-b border-zinc-200/70 bg-stone-50/90 backdrop-blur dark:border-zinc-800/70 dark:bg-zinc-950/90">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
          <Link to="/" className="font-serif text-2xl font-semibold tracking-tight">
            Bestreads
          </Link>
          <nav className="hidden gap-5 text-sm sm:flex">
            {navLinks.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  clsx(
                    "transition-colors",
                    isActive
                      ? "text-zinc-900 dark:text-zinc-100"
                      : "text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex-1">
            <QuickAdd />
          </div>
          <button
            type="button"
            onClick={toggle}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
            className="rounded-md p-2 text-zinc-500 hover:bg-zinc-200/60 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-100"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            type="button"
            onClick={logout}
            title="Sign out"
            className="rounded-md p-2 text-zinc-500 hover:bg-zinc-200/60 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-100"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}
