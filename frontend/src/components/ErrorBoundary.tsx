import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown): void {
    // eslint-disable-next-line no-console
    console.error("UI crash:", error, info);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-stone-50 p-6 dark:bg-zinc-950">
          <div className="w-full max-w-md rounded-md border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
            <h1 className="mb-2 font-serif text-2xl">Something went wrong</h1>
            <p className="mb-4 text-sm text-zinc-600 dark:text-zinc-300">
              {this.state.error.message || "Unknown error."}
            </p>
            <button
              onClick={() => {
                this.reset();
                window.location.href = "/";
              }}
              className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Return home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
