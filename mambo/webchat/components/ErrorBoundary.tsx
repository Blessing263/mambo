"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[Mambo] Render error:", error.message, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center"
          style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}
        >
          <div className="text-4xl" aria-hidden="true">⚠</div>
          <h2 className="text-lg font-semibold font-display">
            Something went wrong
          </h2>
          <p className="max-w-sm text-sm" style={{ color: "var(--text-secondary)" }}>
            Mambo encountered an unexpected error. Please reload the page to try again.
          </p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
            className="mt-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition active:scale-[0.97]"
            style={{ background: "var(--grad-accent)" }}
          >
            Reload page
          </button>
          {this.state.error && process.env.NODE_ENV !== "production" && (
            <pre className="mt-4 max-w-lg overflow-auto rounded-lg p-3 text-left text-xs"
              style={{ background: "var(--bg-secondary)", color: "var(--text-tertiary)" }}>
              {this.state.error.message}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
