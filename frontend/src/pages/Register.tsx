import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { extractErrorMessage } from "../lib/errors";
import { AuthShell } from "./Login";

export default function Register() {
  const { register, isAuthed, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();

  if (isAuthed) return <Navigate to="/" replace />;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await register(username, email, pw);
      navigate("/");
    } catch (ex) {
      setErr(extractErrorMessage(ex, "Registration failed"));
    }
  };

  return (
    <AuthShell title="Create your library">
      <form onSubmit={onSubmit} className="space-y-3">
        <Field label="Username (min 2 chars)" value={username} onChange={setUsername} minLength={2} />
        <Field label="Email" value={email} onChange={setEmail} type="email" />
        <Field label="Password (min 6 chars)" value={pw} onChange={setPw} type="password" minLength={6} />
        {err && <div className="text-xs text-red-600">{err}</div>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-accent py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
        >
          {loading ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-center text-xs text-zinc-500">
        Already have one?{" "}
        <Link to="/login" className="text-accent hover:underline">
          Sign in
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
  minLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  minLength?: number;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        minLength={minLength}
        className="w-full rounded border border-zinc-200 bg-transparent px-3 py-2 text-sm outline-none focus:border-accent dark:border-zinc-700"
      />
    </label>
  );
}
