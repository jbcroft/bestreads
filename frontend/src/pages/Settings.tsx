import { useEffect, useState } from "react";
import { Copy } from "lucide-react";
import { regenerateApiKey, viewApiKey } from "../api/settings";
import { useTheme } from "../theme/ThemeContext";
import { useToast } from "../components/Toast";

export default function Settings() {
  const [masked, setMasked] = useState<string | null>(null);
  const [plain, setPlain] = useState<string | null>(null);
  const { theme, toggle } = useTheme();
  const toast = useToast();

  useEffect(() => {
    viewApiKey().then((r) => setMasked(r.api_key));
  }, []);

  const onRegenerate = async () => {
    const r = await regenerateApiKey();
    setPlain(r.api_key);
    setMasked(r.api_key.slice(0, 6) + "…" + r.api_key.slice(-4));
    toast.push("New API key generated", "success");
  };

  const onCopy = async () => {
    if (!plain) return;
    await navigator.clipboard.writeText(plain);
    toast.push("Copied to clipboard", "success");
  };

  return (
    <div className="max-w-2xl space-y-10 animate-fade-in">
      <h1 className="font-serif text-3xl">Settings</h1>

      <section>
        <h2 className="mb-3 font-serif text-xl">Appearance</h2>
        <div className="flex items-center justify-between rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div>
            <div className="font-medium">Theme</div>
            <div className="text-xs text-zinc-500">Currently using {theme} mode</div>
          </div>
          <button
            onClick={toggle}
            className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover"
          >
            Switch to {theme === "dark" ? "light" : "dark"}
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-serif text-xl">MCP API key</h2>
        <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-300">
            Give this key to an MCP client (like Claude Desktop) to let Claude manage your
            library on your behalf.
          </p>
          <div className="mb-3 rounded bg-stone-100 p-2 font-mono text-xs dark:bg-zinc-800">
            {masked ?? "— no key yet —"}
          </div>
          {plain && (
            <div className="mb-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950/40">
              <div className="mb-1 font-medium text-amber-900 dark:text-amber-200">
                Save this key now — you won't see it again.
              </div>
              <div className="flex items-center gap-2">
                <code className="min-w-0 flex-1 overflow-x-auto rounded bg-white px-2 py-1 font-mono text-xs dark:bg-zinc-900">
                  {plain}
                </code>
                <button
                  onClick={onCopy}
                  className="inline-flex items-center gap-1 rounded bg-accent px-2 py-1 text-xs font-medium text-white hover:bg-accent-hover"
                >
                  <Copy size={12} /> Copy
                </button>
              </div>
            </div>
          )}
          <button
            onClick={onRegenerate}
            className="rounded border border-zinc-300 px-3 py-1.5 text-xs font-medium hover:bg-stone-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {masked ? "Regenerate key" : "Generate key"}
          </button>
        </div>
      </section>
    </div>
  );
}
