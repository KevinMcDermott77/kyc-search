export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
      {message}
    </div>
  );
}
