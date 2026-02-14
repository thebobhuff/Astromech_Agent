"use client";

import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Send } from "lucide-react";
import { cn } from "@/lib/utils";

type PlaceholdersAndVanishInputProps = {
  placeholders: string[];
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  disabled?: boolean;
  allowEmptySubmit?: boolean;
  className?: string;
  inputClassName?: string;
};

export function PlaceholdersAndVanishInput({
  placeholders,
  value,
  onChange,
  onSubmit,
  disabled = false,
  allowEmptySubmit = false,
  className,
  inputClassName,
}: PlaceholdersAndVanishInputProps) {
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [focused, setFocused] = useState(false);
  const [isVanishing, setIsVanishing] = useState(false);
  const [vanishingText, setVanishingText] = useState("");

  const activePlaceholder = useMemo(() => {
    if (!placeholders.length) return "";
    return placeholders[placeholderIndex % placeholders.length];
  }, [placeholderIndex, placeholders]);

  const canSubmit = allowEmptySubmit || value.trim().length > 0;

  useEffect(() => {
    if (focused || value.trim().length > 0 || placeholders.length <= 1) return;

    const timer = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
    }, 2600);

    return () => clearInterval(timer);
  }, [focused, placeholders.length, value]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (disabled || !canSubmit) return;

    if (value.trim().length > 0) {
      setVanishingText(value);
      setIsVanishing(true);
      setTimeout(() => setIsVanishing(false), 360);
    }

    onSubmit(e);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative flex w-full items-center gap-2 rounded-md border border-charcoal-blue-700 bg-charcoal-blue-950/80 px-3 py-2",
        className
      )}
    >
      <div className="relative h-8 flex-1 overflow-hidden">
        <input
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          className={cn(
            "h-full w-full bg-transparent pr-2 text-sm text-slate-100 outline-none placeholder:text-transparent disabled:cursor-not-allowed disabled:opacity-50",
            isVanishing ? "text-transparent" : "",
            inputClassName
          )}
          placeholder={activePlaceholder}
          aria-label="Message input"
        />

        <AnimatePresence mode="wait">
          {!focused && value.length === 0 && activePlaceholder && (
            <motion.span
              key={activePlaceholder}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 0.65, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="pointer-events-none absolute inset-0 flex items-center text-sm text-slate-400"
            >
              {activePlaceholder}
            </motion.span>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {isVanishing && vanishingText && (
            <motion.span
              key={vanishingText}
              initial={{ opacity: 0.95, filter: "blur(0px)", y: 0 }}
              animate={{ opacity: 0, filter: "blur(6px)", y: -10 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="pointer-events-none absolute inset-0 flex items-center text-sm text-slate-200"
            >
              {vanishingText}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      <button
        type="submit"
        disabled={disabled || !canSubmit}
        className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-baltic-blue-600 text-white transition-colors hover:bg-baltic-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="Send message"
      >
        <Send className="h-4 w-4" />
      </button>
    </form>
  );
}
