import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export default function ChatLoading(): JSX.Element {
  return (
    <div className="mx-auto max-w-4xl">
      <LoadingSkeleton variant="chat" />
    </div>
  );
}
