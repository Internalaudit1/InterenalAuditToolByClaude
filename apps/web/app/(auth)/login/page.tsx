import { HclLogo } from "@/components/branding/hcl-logo";
import { LoginForm } from "@/components/forms/login-form";

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl items-center gap-10 px-6 py-10">
      <div className="flex-1">
        <HclLogo subtitle="Internal Audit Workspace" className="max-w-sm" />
        <h1 className="mt-4 max-w-2xl font-serif text-6xl leading-tight">An enterprise-grade replica for planning, follow-up, reporting, and audit control evidence.</h1>
        <p className="mt-5 max-w-2xl text-lg text-slate">
          This implementation recreates the observed workflow logic from the source analysis, fixes the weak controls noted in the report, and seeds realistic demo data for UAT.
        </p>
      </div>
      <LoginForm />
    </div>
  );
}
