"use client"

import * as React from "react"
import { themes, type Theme } from "@/lib/themes"

type ThemeProviderContextType = {
  theme: string
  setTheme: (theme: string) => void
  availableThemes: Theme[]
}

const ThemeProviderContext = React.createContext<ThemeProviderContextType | undefined>(
  undefined
)

export function ThemeProvider({
  children,
  defaultTheme = "dark",
  storageKey = "vite-ui-theme",
  ...props
}: {
  children: React.ReactNode
  defaultTheme?: string
  storageKey?: string
}) {
  const [theme, setTheme] = React.useState<string>(() => {
    // Only access localStorage on client
    if (typeof window !== "undefined") {
      return localStorage.getItem(storageKey) || defaultTheme
    }
    return defaultTheme
  })

  React.useEffect(() => {
    const root = window.document.documentElement
    const themeConfig = themes[theme] || themes["light"]

    // Remove any existing theme-specific classes if you were using class-based themes
    // root.classList.remove("light", "dark")
    // root.classList.add(theme) 

    // Inject CSS variables
    Object.entries(themeConfig.colors).forEach(([key, value]) => {
      root.style.setProperty(key, value)
    })

    // Update dark mode class for Tailwind's "dark:" prefix support
    // We assume 'light' is the only one without dark mode, but let's be smarter:
    // If the background color is dark, add 'dark' class.
    // Simple heuristic: check if themes[theme] is not 'light'
    if (theme === 'light') {
        root.classList.remove('dark')
    } else {
        root.classList.add('dark')
    }

  }, [theme])

  const value = {
    theme,
    setTheme: (theme: string) => {
      localStorage.setItem(storageKey, theme)
      setTheme(theme)
    },
    availableThemes: Object.values(themes),
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = React.useContext(ThemeProviderContext)

  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider")

  return context
}
