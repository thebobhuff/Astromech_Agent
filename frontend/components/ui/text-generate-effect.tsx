"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type TextGenerateEffectProps = {
  words: string;
  className?: string;
  duration?: number;
  filter?: boolean;
};

export function TextGenerateEffect({
  words,
  className,
  duration = 0.35,
  filter = true,
}: TextGenerateEffectProps) {
  const splitWords = useMemo(() => words.split(" "), [words]);

  return (
    <div className={cn("font-normal", className)}>
      {splitWords.map((word, idx) => (
        <motion.span
          key={`${word}-${idx}`}
          initial={{ opacity: 0, filter: filter ? "blur(8px)" : "none", y: 4 }}
          animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
          transition={{ duration, delay: idx * 0.02 }}
          className="inline-block"
        >
          {word}&nbsp;
        </motion.span>
      ))}
    </div>
  );
}
