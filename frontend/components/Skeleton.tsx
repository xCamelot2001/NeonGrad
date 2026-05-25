// Reusable skeleton building blocks

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-slate-800 ${className}`} />
  );
}

// A single shimmer job card skeleton (for the dashboard list)
export function JobCardSkeleton() {
  return (
    <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="flex items-start gap-4">
        {/* Score ring placeholder */}
        <div className="shrink-0 w-14 h-14 rounded-full bg-slate-800 animate-pulse" />
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <SkeletonBlock className="h-4 w-40" />
            <SkeletonBlock className="h-4 w-20 rounded-full" />
          </div>
          <SkeletonBlock className="h-3 w-28" />
          <SkeletonBlock className="h-3 w-64 mt-1" />
          <div className="flex gap-1.5 mt-2">
            <SkeletonBlock className="h-5 w-16 rounded-full" />
            <SkeletonBlock className="h-5 w-14 rounded-full" />
            <SkeletonBlock className="h-5 w-12 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

// A single Kanban card skeleton
export function KanbanCardSkeleton() {
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-3 space-y-2 animate-pulse">
      <SkeletonBlock className="h-3.5 w-full" />
      <SkeletonBlock className="h-3.5 w-3/4" />
      <SkeletonBlock className="h-3 w-1/2 mt-1" />
      <SkeletonBlock className="h-5 w-16 rounded-full mt-2" />
    </div>
  );
}

// Stat bar skeleton (3 cards)
export function StatBarSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-4 mb-8">
      {[0, 1, 2].map((i) => (
        <div key={i} className="rounded-xl border border-slate-800 p-4 bg-slate-900/40 animate-pulse space-y-2">
          <SkeletonBlock className="h-7 w-10" />
          <SkeletonBlock className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}
