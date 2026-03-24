"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { AuthForm } from "@/components/auth/auth-form";
import { apiClient, ApiClientError } from "@/lib/api/client";
import { setStoredToken } from "@/lib/auth-storage";

export default function RegisterPage() {
  const router = useRouter();

  return (
    <main className="shell auth-screen">
      <div className="container" style={{ padding: "72px 0" }}>
        <AuthForm
          title="Create workspace"
          subtitle="Set up an ArbiLens organization and start reviewing contracts with deterministic scoring."
          fields={[
            { name: "organization_name", label: "Organization name", autoComplete: "organization" },
            { name: "full_name", label: "Full name", autoComplete: "name" },
            { name: "email", label: "Work email", type: "email", autoComplete: "email" },
            { name: "password", label: "Password", type: "password", autoComplete: "new-password" },
          ]}
          submitLabel="Create account"
          loadingLabel="Creating account…"
          onSubmit={async (values) => {
            try {
              const response = await apiClient.register({
                organization_name: values.organization_name ?? "",
                full_name: values.full_name ?? "",
                email: values.email ?? "",
                password: values.password ?? "",
              });
              setStoredToken(response.access_token);
              router.push("/dashboard");
            } catch (err) {
              throw new Error(err instanceof ApiClientError ? err.message : "Registration failed.");
            }
          }}
          footer={
            <>
              Already have an account?{" "}
              <Link href="/login" style={{ color: "var(--accent)", fontWeight: 700 }}>
                Sign in
              </Link>
            </>
          }
        />
      </div>
    </main>
  );
}
