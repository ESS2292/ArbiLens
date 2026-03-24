"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { AuthForm } from "@/components/auth/auth-form";
import { apiClient, ApiClientError } from "@/lib/api/client";
import { setStoredToken } from "@/lib/auth-storage";

export default function LoginPage() {
  const router = useRouter();

  return (
    <main className="shell auth-screen">
      <div className="container" style={{ padding: "72px 0" }}>
        <AuthForm
          title="Sign in"
          subtitle="Access your ArbiLens workspace to upload contracts and review risk findings."
          fields={[
            { name: "email", label: "Email", type: "email", autoComplete: "email" },
            { name: "password", label: "Password", type: "password", autoComplete: "current-password" },
          ]}
          submitLabel="Sign in"
          loadingLabel="Signing in…"
          onSubmit={async (values) => {
            try {
              const response = await apiClient.login({
                email: values.email ?? "",
                password: values.password ?? "",
              });
              setStoredToken(response.access_token);
              router.push("/dashboard");
            } catch (err) {
              throw new Error(err instanceof ApiClientError ? err.message : "Login failed.");
            }
          }}
          footer={
            <>
              Need an account?{" "}
              <Link href="/register" style={{ color: "var(--accent)", fontWeight: 700 }}>
                Register
              </Link>
            </>
          }
        />
      </div>
    </main>
  );
}
