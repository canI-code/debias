import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  variant: "chat" | "table" | "chart";
}

export function LoadingSkeleton({ variant }: LoadingSkeletonProps): JSX.Element {
  if (variant === "chat") {
    return (
      <div className="space-y-4" aria-hidden>
        <div className="h-16 w-2/3 animate-pulse rounded-3xl rounded-tl-sm bg-panel-border/60 shadow-inner-glow" />
        <div className="ml-auto h-16 w-1/2 animate-pulse rounded-3xl rounded-tr-sm bg-accent/20 shadow-inner-glow" />
        <div className="h-16 w-3/5 animate-pulse rounded-3xl rounded-tl-sm bg-panel-border/60 shadow-inner-glow" />
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className="glass h-[360px] w-full animate-pulse rounded-3xl p-6 shadow-floating" aria-hidden>
        <div className="mb-6 h-6 w-56 rounded-full bg-panel-border/80 shadow-inner-glow" />
        <div className="h-[260px] rounded-2xl bg-panel-border/40 shadow-inner-glow" />
      </div>
    );
  }

  return (
    <div className="glass w-full overflow-hidden rounded-3xl p-6 shadow-floating" aria-hidden>
      <div className="mb-6 h-6 w-64 animate-pulse rounded-full bg-panel-border/80 shadow-inner-glow" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <div 
            key={index} 
            className={cn(
              "h-12 animate-pulse rounded-xl shadow-inner-glow", 
              index % 2 === 0 ? "bg-panel-border/60" : "bg-panel-border/40"
            )} 
          />
        ))}
      </div>
    </div>
  );
}
