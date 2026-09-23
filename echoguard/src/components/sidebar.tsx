"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  History,
  Users,
  Settings,
  Shield,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "/", label: "Live Analysis", icon: Activity, description: "Real-time monitoring" },
  { href: "/call-history", label: "Call History", icon: History, description: "Past call records" },
  { href: "/identities", label: "Identities", icon: Users, description: "Voice profiles" },
  { href: "/settings", label: "Settings", icon: Settings, description: "Configuration" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();

  // Get initials for avatar
  const getInitials = () => {
    if (!user) return "OP";
    if (user.full_name) {
      const parts = user.full_name.trim().split(/\s+/);
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].slice(0, 2).toUpperCase();
    }
    return user.username.slice(0, 2).toUpperCase();
  };

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col bg-gray-900 text-white transition-all duration-300 ease-in-out relative z-30",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-gray-800 shrink-0">
        <div className="bg-[#F6821F] p-1.5 rounded-md shrink-0">
          <Shield className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <span className="ml-3 text-lg font-bold tracking-tight whitespace-nowrap">
            VoxGuard
          </span>
        )}
      </div>

      {/* Nav Links */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group",
                isActive
                  ? "bg-[#F6821F] text-white shadow-lg shadow-orange-500/20"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}
              title={collapsed ? item.label : undefined}
            >
              <item.icon className={cn("w-5 h-5 shrink-0", isActive ? "text-white" : "text-gray-500 group-hover:text-white")} />
              {!collapsed && (
                <div className="flex flex-col">
                  <span>{item.label}</span>
                  {!isActive && (
                    <span className="text-[10px] text-gray-600 group-hover:text-gray-400 leading-tight">
                      {item.description}
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Status Indicator */}
      {!collapsed && (
        <div className="px-4 py-3 mx-2 mb-2 bg-gray-800/50 rounded-lg border border-gray-700/50">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-medium text-emerald-400">System Online</span>
          </div>
          <p className="text-[10px] text-gray-500">AMVTF Engine v2.4 Active</p>
        </div>
      )}

      {/* Operator Profile */}
      <div className="border-t border-gray-800 p-3.5 pb-4 shrink-0 relative z-30">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full bg-gradient-to-br from-[#F6821F] to-[#E85D04] flex items-center justify-center text-xs font-bold shrink-0 text-white shadow-sm"
            title={user ? `${user.full_name} (${user.username})` : "Operator"}
          >
            {getInitials()}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate" title={user?.full_name || "Operator"}>
                {user?.full_name || user?.username || "Operator"}
              </p>
              <p className="text-[10px] text-gray-500 truncate" title={user?.role || "SOC Analyst"}>
                {user?.role || "SOC Analyst"}
              </p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => logout()}
              className="text-gray-500 hover:text-red-400 transition-colors p-1 rounded hover:bg-gray-800"
              title="Log Out of SOC Console"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-gray-800 border border-gray-700 rounded-full flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700 transition-colors z-40"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </aside>
  );
}
