import { motion } from "framer-motion";

export default function GlassButton({ children, className = "", ...props }) {
  return (
    <motion.button
      whileTap={{ scale: 0.95, y: 1 }}
      transition={{ type: "spring", stiffness: 420, damping: 23, mass: 0.65 }}
      className={`glassBtn ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
