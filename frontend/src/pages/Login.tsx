import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { extractErrorMessage } from "../lib/errors";

export default function Login() {
  const { login, isAuthed, loading } = useAuth();
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();

  if (isAuthed) return <Navigate to="/" replace />;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await login(id, pw);
      navigate("/");
    } catch (ex) {
      setErr(extractErrorMessage(ex, "Invalid credentials"));
    }
  };

  return (
    <AuthShell title="Sign in">
      <form onSubmit={onSubmit} className="space-y-3">
        <Field label="Username or email" value={id} onChange={setId} />
        <Field label="Password" type="password" value={pw} onChange={setPw} />
        {err && <div className="text-xs text-red-600">{err}</div>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-accent py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-6 text-center text-xs text-zinc-500">
        New here?{" "}
        <Link to="/register" className="text-accent hover:underline">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        className="w-full rounded border border-zinc-200 bg-transparent px-3 py-2 text-sm outline-none focus:border-accent dark:border-zinc-700"
      />
    </label>
  );
}

export function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center font-serif text-3xl">Bestreads</h1>
        <p className="mb-8 text-center text-sm text-zinc-500">{title}</p>
        {children}
      </div>
    </div>
  );
}
