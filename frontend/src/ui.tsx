/* ==========================================================================
   ZMetrics UI — shared, accessible component primitives.
   One design language: buttons, fields, cards, table, modal, toast, etc.
   ========================================================================== */

import {
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Info,
  Search,
  X,
  type LucideIcon,
} from "lucide-react";

/* ----- Button ---------------------------------------------------------- */

type ButtonVariant = "primary" | "default" | "ghost" | "subtle" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  loading?: boolean;
  block?: boolean;
  icon?: LucideIcon;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "btn--primary",
  default: "",
  ghost: "btn--ghost",
  subtle: "btn--subtle",
  danger: "btn--danger",
};

export function Button({
  variant = "default",
  size = "md",
  loading = false,
  block = false,
  icon: Icon,
  className = "",
  disabled,
  children,
  ...rest
}: ButtonProps) {
  const cls = [
    "btn",
    VARIANT_CLASS[variant],
    size === "sm" ? "btn--sm" : "",
    block ? "btn--block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {loading ? <span className="spinner" aria-hidden="true" /> : Icon ? <Icon aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  label: string;
}

export function IconButton({ icon: Icon, label, className = "", ...rest }: IconButtonProps) {
  return (
    <button className={`icon-btn ${className}`} aria-label={label} title={label} {...rest}>
      <Icon aria-hidden="true" />
    </button>
  );
}

/* ----- Fields ---------------------------------------------------------- */

interface FieldShellProps {
  label?: string;
  required?: boolean;
  hint?: string;
  error?: string | null;
  className?: string;
  children: (controlId: string) => ReactNode;
}

function FieldShell({ label, required, hint, error, className = "", children }: FieldShellProps) {
  const id = useId();
  const errId = `${id}-err`;
  const hintId = `${id}-hint`;
  return (
    <div className={`field ${error ? "field--invalid" : ""} ${className}`}>
      {label && (
        <label className="field__label" htmlFor={id}>
          {label}
          {required && (
            <span className="field__req" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {children(id)}
      {hint && !error && (
        <span className="field__hint" id={hintId}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field__error" id={errId} role="alert">
          <AlertCircle aria-hidden="true" />
          {error}
        </span>
      )}
    </div>
  );
}

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  icon?: LucideIcon;
  fieldClassName?: string;
}

export function Input({
  label,
  hint,
  error,
  required,
  icon: Icon,
  fieldClassName,
  ...rest
}: InputProps) {
  return (
    <FieldShell
      label={label}
      required={required}
      hint={hint}
      error={error}
      className={fieldClassName}
    >
      {(id) => (
        <div className="field__control">
          {Icon && <Icon aria-hidden="true" />}
          <input id={id} aria-invalid={!!error} required={required} {...rest} />
        </div>
      )}
    </FieldShell>
  );
}

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  fieldClassName?: string;
}

export function Textarea({
  label,
  hint,
  error,
  required,
  fieldClassName,
  rows = 3,
  ...rest
}: TextareaProps) {
  return (
    <FieldShell
      label={label}
      required={required}
      hint={hint}
      error={error}
      className={fieldClassName}
    >
      {(id) => (
        <div className="field__control field__control--textarea">
          <textarea id={id} rows={rows} aria-invalid={!!error} required={required} {...rest} />
        </div>
      )}
    </FieldShell>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  placeholder?: string;
  options: SelectOption[];
  fieldClassName?: string;
}

export function Select({
  label,
  hint,
  error,
  required,
  placeholder,
  options,
  fieldClassName,
  ...rest
}: SelectProps) {
  return (
    <FieldShell
      label={label}
      required={required}
      hint={hint}
      error={error}
      className={fieldClassName}
    >
      {(id) => (
        <div className="field__control select-wrap">
          <select id={id} aria-invalid={!!error} required={required} {...rest}>
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <ChevronDown aria-hidden="true" />
        </div>
      )}
    </FieldShell>
  );
}

export interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  containerClassName?: string;
}

export function SearchInput({ containerClassName = "", ...rest }: SearchInputProps) {
  return (
    <div className={`search ${containerClassName}`}>
      <Search aria-hidden="true" />
      <input type="search" {...rest} />
    </div>
  );
}

/* ----- Card ------------------------------------------------------------ */

export function Card({
  className = "",
  children,
  ...rest
}: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`card ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function CardTitle({ icon: Icon, title }: { icon: LucideIcon; title: string }) {
  return (
    <div className="card-title">
      <Icon aria-hidden="true" />
      <h2>{title}</h2>
    </div>
  );
}

/* ----- Badge ----------------------------------------------------------- */

type BadgeTone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

export function Badge({
  tone = "neutral",
  plain = false,
  children,
}: {
  tone?: BadgeTone;
  plain?: boolean;
  children: ReactNode;
}) {
  return <span className={`badge badge--${tone} ${plain ? "badge--plain" : ""}`}>{children}</span>;
}

/* ----- Spinner / skeleton --------------------------------------------- */

export function Spinner({ large = false }: { large?: boolean }) {
  return <span className={`spinner ${large ? "spinner--lg" : ""}`} role="status" aria-label="Загрузка" />;
}

export function SpinnerCenter() {
  return (
    <div className="spinner-center">
      <Spinner large />
    </div>
  );
}

export function Skeleton({
  className = "",
  width,
  height,
}: {
  className?: string;
  width?: string | number;
  height?: string | number;
}) {
  return <div className={`skeleton ${className}`} style={{ width, height }} aria-hidden="true" />;
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div aria-hidden="true" style={{ display: "grid", gap: 12 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="skeleton--line" width={`${88 - i * 6}%`} />
      ))}
    </div>
  );
}

/* ----- Empty state ----------------------------------------------------- */

export function EmptyState({
  icon: Icon,
  title,
  text,
  action,
}: {
  icon: LucideIcon;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty__icon">
        <Icon aria-hidden="true" />
      </div>
      <div className="empty__title">{title}</div>
      {text && <p className="empty__text">{text}</p>}
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}

/* ----- Tooltip --------------------------------------------------------- */

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="tip" tabIndex={0}>
      {children}
      <span className="tip__bubble" role="tooltip">
        {label}
      </span>
    </span>
  );
}

/* ----- Modal ----------------------------------------------------------- */

export function Modal({
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {
        const focusable = ref.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prev?.focus();
    };
  }, [onClose]);

  return createPortal(
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className={`modal ${wide ? "modal--wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={ref}
      >
        <div className="modal__header">
          <h2 id={titleId}>{title}</h2>
          <IconButton icon={X} label="Закрыть" onClick={onClose} />
        </div>
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

/* ----- Toasts ---------------------------------------------------------- */

type ToastTone = "success" | "error" | "info";
interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}
interface ToastApi {
  success: (m: string) => void;
  error: (m: string) => void;
  info: (m: string) => void;
}

const ToastCtx = createContext<ToastApi | null>(null);

const TOAST_ICON: Record<ToastTone, LucideIcon> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastTone, message: string) => {
      const id = Date.now() + Math.random();
      setItems((prev) => [...prev, { id, tone, message }]);
      window.setTimeout(() => dismiss(id), 5000);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (m) => push("success", m),
      error: (m) => push("error", m),
      info: (m) => push("info", m),
    }),
    [push],
  );

  return (
    <ToastCtx.Provider value={api}>
      {children}
      {createPortal(
        <div className="toast-viewport" role="region" aria-label="Уведомления" aria-live="polite">
          {items.map((t) => {
            const Icon = TOAST_ICON[t.tone];
            return (
              <div className={`toast toast--${t.tone}`} key={t.id}>
                <Icon aria-hidden="true" />
                <div className="toast__msg">{t.message}</div>
                <button
                  className="toast__close"
                  onClick={() => dismiss(t.id)}
                  aria-label="Закрыть уведомление"
                >
                  <X aria-hidden="true" width={16} height={16} />
                </button>
              </div>
            );
          })}
        </div>,
        document.body,
      )}
    </ToastCtx.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

/* ----- DataTable ------------------------------------------------------- */

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  sortable?: boolean;
  cellLabel?: string;
}

type SortDir = "asc" | "desc";

export interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  getRowKey: (row: T) => string;
  searchKeys?: (row: T) => string;
  searchPlaceholder?: string;
  pageSize?: number;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
  toolbarExtra?: ReactNode;
  initialSortKey?: string;
}

export function DataTable<T>({
  rows,
  columns,
  getRowKey,
  searchKeys,
  searchPlaceholder = "Поиск…",
  pageSize = 10,
  onRowClick,
  empty,
  toolbarExtra,
  initialSortKey,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(initialSortKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !searchKeys) return rows;
    return rows.filter((r) => searchKeys(r).toLowerCase().includes(q));
  }, [rows, query, searchKeys]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return filtered;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
  }, [filtered, sortKey, sortDir, columns]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageRows = useMemo(
    () => sorted.slice((safePage - 1) * pageSize, safePage * pageSize),
    [sorted, safePage, pageSize],
  );

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  return (
    <div>
      {(searchKeys || toolbarExtra) && (
        <div className="table-toolbar">
          {searchKeys && (
            <SearchInput
              containerClassName="grow"
              placeholder={searchPlaceholder}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          )}
          {toolbarExtra}
        </div>
      )}

      {sorted.length === 0 ? (
        empty ?? <EmptyState icon={Search} title="Ничего не найдено" text="Измените запрос или фильтры." />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th
                      key={c.key}
                      className={c.sortable && c.sortValue ? "sortable" : ""}
                      onClick={() => c.sortable && c.sortValue && toggleSort(c.key)}
                      aria-sort={
                        sortKey === c.key ? (sortDir === "asc" ? "ascending" : "descending") : undefined
                      }
                    >
                      {c.sortable && c.sortValue ? (
                        <span className={`th-sort ${sortKey === c.key ? "is-active" : ""}`}>
                          {c.header}
                          {sortKey === c.key ? (
                            sortDir === "asc" ? (
                              <ArrowUp aria-hidden="true" />
                            ) : (
                              <ArrowDown aria-hidden="true" />
                            )
                          ) : (
                            <ArrowUpDown aria-hidden="true" />
                          )}
                        </span>
                      ) : (
                        c.header
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => (
                  <tr
                    key={getRowKey(row)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    style={onRowClick ? { cursor: "pointer" } : undefined}
                  >
                    {columns.map((c) => (
                      <td key={c.key} data-label={c.cellLabel ?? c.header}>
                        {c.render ? c.render(row) : ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <span>
                {(safePage - 1) * pageSize + 1}–{Math.min(safePage * pageSize, sorted.length)} из{" "}
                {sorted.length}
              </span>
              <div className="pagination__pages">
                <Button
                  size="sm"
                  variant="subtle"
                  icon={ChevronLeft}
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Назад
                </Button>
                <span style={{ padding: "0 8px" }}>
                  {safePage} / {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="subtle"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Вперёд
                  <ChevronRight aria-hidden="true" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ----- Breadcrumbs ----------------------------------------------------- */

export interface Crumb {
  label: string;
  onClick?: () => void;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      {items.map((c, i) => {
        const last = i === items.length - 1;
        return (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            {last || !c.onClick ? (
              <span className="breadcrumbs__current" aria-current="page">
                {c.label}
              </span>
            ) : (
              <button type="button" onClick={c.onClick}>
                {c.label}
              </button>
            )}
            {!last && (
              <span className="breadcrumbs__sep" aria-hidden="true">
                /
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
