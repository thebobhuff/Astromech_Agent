"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Home, 
  Wrench, 
  Brain, 
  MessageCircle, 
  Cpu,
  Activity,
  Bot,
  Users,
  Info
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FeatureInfoIcon } from "@/components/feature-info-icon";

const navItems = [
  { name: "Home", href: "/", icon: Home, featureId: "FE-001" },
  { name: "Agents", href: "/agents", icon: Users, featureId: "FE-011" },
  { name: "Standing Orders", href: "/core/heartbeat", icon: Activity, featureId: "FE-009" },
  { name: "Vault", href: "/vault", icon: Wrench, featureId: "FE-008" },
  { name: "Skills", href: "/skills", icon: Brain, featureId: "FE-003" },
  { name: "Channels", href: "/channels", icon: MessageCircle, featureId: "FE-007" },
  { name: "Models", href: "/models", icon: Bot, featureId: "FE-010" },
  { name: "Core", href: "/core", icon: Cpu, featureId: "FE-014" },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <div className="w-full md:w-16 h-16 md:h-full bg-charcoal-blue-950 border-t md:border-t-0 md:border-r border-charcoal-blue-800 flex flex-row md:flex-col items-center justify-between md:justify-start px-6 md:px-0 py-0 md:py-4 gap-4 z-50 order-2 md:order-none shrink-0">
      <div className="hidden md:block mb-4">
        <div className="w-10 h-10 bg-baltic-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-baltic-blue-900/20">
          A
        </div>
      </div>
      
      <nav className="flex flex-row md:flex-col gap-2 w-full justify-between md:justify-start md:px-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <div key={item.href} className="relative group">
              <Link
                href={item.href}
                className={cn(
                  "flex items-center justify-center w-10 h-10 md:w-12 md:h-12 rounded-xl transition-all duration-200 group relative",
                  isActive 
                    ? "bg-baltic-blue-600/20 text-sky-reflection-400" 
                    : "text-slate-400 hover:bg-charcoal-blue-800 hover:text-slate-100"
                )}
                title={item.name}
              >
                <item.icon className={cn("w-5 h-5 md:w-6 md:h-6", isActive && "animate-pulse")} />
                
                {/* Tooltip-ish label - Desktop only */}
                <span className="hidden md:block absolute left-14 bg-charcoal-blue-900 border border-charcoal-blue-700 text-slate-200 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                  {item.name}
                </span>
                
                {isActive && (
                  <>
                    <div className="hidden md:block absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-sky-reflection-500 rounded-r-full" />
                    <div className="md:hidden absolute bottom-0 left-1/2 -translate-x-1/2 h-1 w-8 bg-sky-reflection-500 rounded-t-full" />
                  </>
                )}
              </Link>
              
              {/* Dev mode feature info icon */}
              {process.env.NODE_ENV === "development" && (
                <div className="absolute -top-1 -right-1 opacity-60 hover:opacity-100">
                  <FeatureInfoIcon featureId={item.featureId} featureName={item.name} />
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
