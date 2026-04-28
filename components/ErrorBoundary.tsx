"use client";

import { type ReactNode } from "react";
import { ErrorBoundary as ReactErrorBoundary } from "react-error-boundary";

interface ErrorBoundaryProps {
  children: ReactNode;
}

function Fallback(): JSX.Element {
  return (
    <section className="mx-auto mt-6 max-w-3xl rounded-xl border border-danger/40 bg-danger/10 p-6" role="alert" aria-live="assertive">
      <h2 className="text-lg font-semibold text-danger">Rendering issue detected</h2>
      <p className="mt-2 text-sm text-text">
        A recoverable UI error occurred. Please refresh the page. Your saved chat and settings remain in local storage.
      </p>
      <button
        type="button"
        className="mt-4 rounded-md bg-danger px-4 py-2 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger"
        onClick={() => window.location.reload()}
      >
        Reload application
      </button>
    </section>
  );
}

export function ErrorBoundary({ children }: ErrorBoundaryProps): JSX.Element {
  return (
    <ReactErrorBoundary
      fallbackRender={() => <Fallback />}
      onError={(error, info) => {
        console.error("frontend_error_boundary", { error, componentStack: info.componentStack });
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
