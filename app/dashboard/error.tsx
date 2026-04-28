"use client";

export default function DashboardError({ error, reset }: { error: Error; reset: () => void }): JSX.Element {
  return (
    <section className="mx-auto max-w-3xl rounded-xl border border-danger/40 bg-danger/10 p-6" role="alert">
      <h2 className="text-lg font-semibold text-danger">Dashboard route failed to load</h2>
      <p className="mt-2 text-sm text-text">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-md bg-danger px-4 py-2 text-sm font-medium text-white"
      >
        Retry dashboard
      </button>
    </section>
  );
}
