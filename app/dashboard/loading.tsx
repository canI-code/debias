import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export default function DashboardLoading(): JSX.Element {
  return (
    <div className="space-y-4">
      <LoadingSkeleton variant="table" />
      <LoadingSkeleton variant="chart" />
    </div>
  );
}
