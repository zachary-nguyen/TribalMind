import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/10 text-primary",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive/20 text-red-400",
        outline: "border-border text-foreground",
        debug: "border-transparent bg-slate-700/50 text-slate-400",
        info: "border-transparent bg-blue-900/50 text-blue-300",
        warning: "border-transparent bg-yellow-900/50 text-yellow-300",
        error: "border-transparent bg-red-900/50 text-red-400",
        graph: "border-transparent bg-teal-900/50 text-teal-300",
        success: "border-transparent bg-green-900/50 text-green-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
