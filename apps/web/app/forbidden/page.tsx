import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
      <div className="panel space-y-5 p-10 text-center">
        <p className="chip">403</p>
        <h1 className="font-serif text-5xl">This route is outside your role boundary.</h1>
        <p className="text-slate">The frontend blocks the route for usability, and the backend also enforces authorization for the underlying data and workflow actions.</p>
        <Link href="/dashboard" className="button-primary">
          Return to workspace
        </Link>
      </div>
    </div>
  );
}
