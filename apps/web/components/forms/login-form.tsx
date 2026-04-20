"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { setSession } from "@/lib/auth";
import { API_BASE_URL } from "@/lib/config";

const schema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required")
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { username: "", password: "" } });

  return (
    <form
      className="panel w-full max-w-xl space-y-5 p-8"
      onSubmit={handleSubmit(async (values) => {
        setError("");
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(values)
        });
        const data = await response.json();
        if (!response.ok) {
          setError(data.detail ?? "Login failed");
          return;
        }
        setSession(data.access_token, data.refresh_token, data.user);
        const firstRole = data.user.roles[0];
        router.push(firstRole === "auditee" ? "/planning/audit-plans" : "/dashboard");
      })}
    >
      <div>
        <p className="chip">Replica Access</p>
        <h1 className="mt-3 font-serif text-4xl">Sign in to the audit workspace</h1>
        <p className="mt-3 text-sm text-slate">Use the seeded demo users to explore role segregation, planning flows, reports, and remediation tracking.</p>
      </div>
      <div className="space-y-2">
        <label htmlFor="username" className="text-sm font-semibold">Username</label>
        <input id="username" className="field" {...register("username")} />
        {errors.username ? <p className="text-sm text-ember">{errors.username.message}</p> : null}
      </div>
      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-semibold">Password</label>
        <input id="password" type="password" className="field" {...register("password")} />
        {errors.password ? <p className="text-sm text-ember">{errors.password.message}</p> : null}
      </div>
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <button type="submit" disabled={isSubmitting} className="button-primary w-full">
        {isSubmitting ? "Signing in..." : "Sign in"}
      </button>
      <div className="rounded-2xl border border-sand bg-mist px-4 py-4 text-sm text-slate">
        Demo users: `superadmin`, `auditoruser1`, `auditeeuser1` with password `Password@123`.
      </div>
    </form>
  );
}
