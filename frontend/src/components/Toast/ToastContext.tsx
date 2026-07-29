import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import Toast from "./Toast";
import type { ToastMessage } from "./Toast";

interface ToastContextType {
  toast: (msg: Omit<ToastMessage, "id">) => void;
  error: (message: string, detail?: string) => void;
  warning: (message: string, detail?: string) => void;
  success: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

let _nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const addToast = useCallback((msg: Omit<ToastMessage, "id">) => {
    const id = ++_nextId;
    setMessages((prev) => [...prev.slice(-4), { ...msg, id }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const toast = useCallback(
    (msg: Omit<ToastMessage, "id">) => addToast(msg),
    [addToast]
  );

  const error = useCallback(
    (message: string, detail?: string) => addToast({ type: "error", message, detail }),
    [addToast]
  );

  const warning = useCallback(
    (message: string, detail?: string) => addToast({ type: "warning", message, detail }),
    [addToast]
  );

  const success = useCallback(
    (message: string) => addToast({ type: "success", message }),
    [addToast]
  );

  return (
    <ToastContext.Provider value={{ toast, error, warning, success }}>
      {children}
      <Toast messages={messages} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
