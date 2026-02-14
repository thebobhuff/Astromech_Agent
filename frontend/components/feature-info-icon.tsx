"use client";

import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FeatureInfoIconProps {
  featureId: string;
  featureName?: string;
}

export function FeatureInfoIcon({ featureId, featureName }: FeatureInfoIconProps) {
  // Only show in development mode
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className="inline-flex items-center justify-center w-4 h-4 text-sky-reflection-400 hover:text-sky-reflection-300 opacity-60 hover:opacity-100 transition-all cursor-help"
            title={featureName ? `${featureName} (${featureId})` : featureId}
          >
            <Info className="w-4 h-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="bg-charcoal-blue-800 border-charcoal-blue-700 text-slate-200">
          <div className="text-xs">
            <div className="font-mono font-bold text-sky-reflection-400">{featureId}</div>
            {featureName && <div className="text-slate-300 mt-1">{featureName}</div>}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
