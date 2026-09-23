"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import Sidebar from "@/components/sidebar";
import { Shield } from "lucide-react";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const isLoginPage = pathname === "/login";

  useEffect(() => {
    if (!isLoading) {
      if (!user && !isLoginPage) {
        router.replace("/login");
      } else if (user && isLoginPage) {
        router.replace("/");
      }
    }
  }, [user, isLoading, isLoginPage, router]);

  // If on login page, render full screen without dashboard sidebar
  if (isLoginPage) {
    if (user && !isLoading) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#090D16] text-white">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#F6821F] flex items-center justify-center animate-pulse">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <p className="text-sm text-gray-400 font-mono">Redirecting to SOC Console...</p>
          </div>
        </div>
      );
    }
    return <main className="min-h-screen w-full bg-[#090D16]">{children}</main>;
  }

  // If loading authentication state on protected routes
  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#090D16] text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#F6821F] to-[#E85D04] flex items-center justify-center shadow-lg shadow-orange-500/20 animate-pulse">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-orange-500"></span>
            </span>
          </div>
          <div className="text-center">
            <h2 className="text-base font-semibold tracking-wide text-gray-100">VoxGuard SOC Security</h2>
            <p className="text-xs text-gray-400 mt-1 font-mono">Verifying local session credentials...</p>
          </div>
        </div>
      </div>
    );
  }

  // If unauthenticated and redirecting
  if (!user) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#090D16] text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#F6821F] flex items-center justify-center animate-pulse">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <p className="text-sm text-gray-400 font-mono">Redirecting to Login...</p>
        </div>
      </div>
    );
  }

  // Authenticated layout with dashboard sidebar
  return (
    <div className="flex min-h-screen w-full bg-[#F9FAFB] text-gray-900">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        {children}
      </div>
    </div>
  );
}
