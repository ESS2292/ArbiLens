"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getStoredToken } from "@/lib/auth-storage";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getStoredToken() ? "/dashboard" : "/login");
  }, [router]);

  return null;
}
