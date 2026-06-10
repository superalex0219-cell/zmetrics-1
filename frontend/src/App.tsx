import {
  type CSSProperties,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Download,
  FileText,
  Hammer,
  ImageUp,
  LayoutDashboard,
  Loader2,
  LockKeyhole,
  Map,
  MapPinned,
  Menu,
  RefreshCcw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
  Users,
  X,
} from "lucide-react";

import { api, checkBackend, downloadWithAuth, kc } from "./api";
import type {
  AnalysisJob,
  AnalysisResult,
  AuditLogEntry,
  AuthUser,
  BlastEvent,
  BlastPassport,
  CapturedFrame,
  Fraction,
  NavItem,
  NavKey,
  Quarry,
  Recommendation,
  Report,
  SiteSection,
} from "./types";

const navItems: NavItem[] = [
  { key: "auth", label: "Авторизация", icon: LockKeyhole },
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "quarries", label: "Карьеры", icon: Map },
  { key: "sites", label: "Участки", icon: MapPinned },
  { key: "passports", label: "Паспорта БВР", icon: ClipboardList },
  { key: "analyses", label: "Анализы", icon: BarChart3 },
  { key: "reports", label: "Отчеты", icon: FileText },
  { key: "recommendations", label: "Рекомендации", icon: Sparkles },
  { key: "admin", label: "Администрирование", icon: ShieldCheck },
];

type ToastState = {
  type: "success" | "error" | "info";
  message: string;
} | null;

export default function App() {
  const [active, setActive] = useState<NavKey>("dashboard");
  const [backendOnline, setBackendOnline] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [quarriesLoading, setQuarriesLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  const [quarries, setQuarries] = useState<Quarry[]>([]);
  const [selectedQuarryId, setSelectedQuarryId] = useState<string | null>(null);
  const [sections, setSections] = useState<SiteSection[]>([]);
  const [passports, setPassports] = useState<BlastPassport[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [latestAnalysisResult, setLatestAnalysisResult] = useState<AnalysisResult | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  const activeNavItem = navItems.find((item) => item.key === active) ?? navItems[0];
  const selectedQuarry = quarries.find((item) => item.id === selectedQuarryId) ?? null;

  const notify = useCallback((type: NonNullable<ToastState>["type"], message: string) => {
    setToast({ type, message });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const refreshQuarries = useCallback(async (preferredQuarryId?: string) => {
    if (!kc.authenticated) return;

    setQuarriesLoading(true);
    try {
      const qs = await api.quarries.list();
      setQuarries(qs);
      setSelectedQuarryId((current) => {
        if (preferredQuarryId && qs.some((q) => q.id === preferredQuarryId)) {
          return preferredQuarryId;
        }
        if (current && qs.some((q) => q.id === current)) {
          return current;
        }
        return qs[0]?.id ?? null;
      });
    } finally {
      setQuarriesLoading(false);
    }
  }, []);

  // On mount: check backend, sync auth state, load quarries if authenticated
  useEffect(() => {
    checkBackend().then(setBackendOnline);

    if (kc.authenticated) {
      const tp = kc.tokenParsed as Record<string, unknown> | undefined;
      setAuthUser({
        sub: kc.subject ?? "",
        preferred_username: tp?.["preferred_username"] as string | undefined,
        name: tp?.["name"] as string | undefined,
        email: tp?.["email"] as string | undefined,
      });

      void refreshQuarries().catch(console.error);
    }
  }, [refreshQuarries]);

  // When quarry selection changes, reload sections, passports, reports
  useEffect(() => {
    if (!selectedQuarryId) {
      setSections([]);
      setPassports([]);
      setReports([]);
      setLatestAnalysisResult(null);
      setContentLoading(false);
      return;
    }

    let cancelled = false;
    setContentLoading(true);

    void Promise.allSettled([
      api.sections.list(selectedQuarryId),
      api.passports.list(selectedQuarryId),
      api.reports.list(selectedQuarryId),
    ]).then(([sectsResult, passpsResult, repsResult]) => {
      if (cancelled) return;

      if (sectsResult.status === "fulfilled") setSections(sectsResult.value);
      else {
        console.error(sectsResult.reason);
        notify("error", "Не удалось загрузить участки");
      }

      if (passpsResult.status === "fulfilled") setPassports(passpsResult.value);
      else {
        console.error(passpsResult.reason);
        notify("error", "Не удалось загрузить паспорта");
      }

      const reps = repsResult.status === "fulfilled" ? repsResult.value : [];
      if (repsResult.status === "rejected") {
        console.error(repsResult.reason);
        notify("error", "Не удалось загрузить отчеты");
      }
      setReports(reps);

      if (reps.length > 0) {
        api.analysisResults
          .get(reps[0].analysis_result_id)
          .then((result) => {
            if (!cancelled) setLatestAnalysisResult(result);
          })
          .catch((err) => {
            console.error(err);
            if (!cancelled) notify("error", "Не удалось загрузить последний анализ");
          })
          .finally(() => {
            if (!cancelled) setContentLoading(false);
          });
      } else {
        setLatestAnalysisResult(null);
        setContentLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [notify, selectedQuarryId]);

  const navigateTo = (key: NavKey) => {
    setActive(key);
    setMobileNavOpen(false);
  };

  const handleQuarryCreated = async (quarry: Quarry) => {
    try {
      await refreshQuarries(quarry.id);
      notify("success", `Карьер «${quarry.name}» создан`);
    } catch (err) {
      console.error(err);
      setQuarries((prev) => [quarry, ...prev.filter((item) => item.id !== quarry.id)]);
      setSelectedQuarryId(quarry.id);
      notify("info", "Карьер создан, список будет синхронизирован при следующем обновлении");
    }
    navigateTo("sites");
  };

  const handleSectionCreated = (section: SiteSection) => {
    setSections((prev) => [section, ...prev.filter((item) => item.id !== section.id)]);
    notify("success", `Участок «${section.name}» создан`);
  };

  const handleLoadRecommendations = async (reportId: string) => {
    try {
      const recs = await api.recommendations.list(reportId);
      setRecommendations(recs);
      navigateTo("recommendations");
    } catch (err) {
      console.error(err);
      notify("error", "Не удалось загрузить рекомендации");
    }
  };

  const handleReviewRecommendation = async (rec: Recommendation, status: string) => {
    try {
      const updated = await api.recommendations.review(rec.report_id, rec.id, status);
      setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      notify("success", "Статус рекомендации обновлен");
    } catch (err) {
      console.error(err);
      notify("error", "Не удалось обновить рекомендацию");
    }
  };

  return (
    <div className={mobileNavOpen ? "app-shell nav-open" : "app-shell"}>
      <div
        className="nav-backdrop"
        aria-hidden="true"
        onClick={() => setMobileNavOpen(false)}
      />
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">
          <Hammer aria-hidden="true" />
          <div>
            <strong>ZMetrics</strong>
            <span>БВР контроль</span>
          </div>
          <button
            className="icon-button sidebar-close"
            type="button"
            title="Закрыть меню"
            aria-label="Закрыть меню"
            onClick={() => setMobileNavOpen(false)}
          >
            <X aria-hidden="true" />
          </button>
        </div>
        <nav className="nav-list" aria-label="Основные разделы">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={active === item.key ? "nav-item active" : "nav-item"}
              type="button"
              title={item.label}
              aria-current={active === item.key ? "page" : undefined}
              onClick={() => navigateTo(item.key)}
            >
              <item.icon aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-card">
          <span>Выбранный карьер</span>
          <strong>{selectedQuarry?.name ?? "Не выбран"}</strong>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="icon-button mobile-menu-button"
              type="button"
              title="Открыть меню"
              aria-label="Открыть меню"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu aria-hidden="true" />
            </button>
            <div>
              <Breadcrumbs activeItem={activeNavItem} selectedQuarry={selectedQuarry} />
              <h1>{activeNavItem.label}</h1>
            </div>
          </div>
          <div className="topbar-actions">
            {authUser && (
              <span className="user-chip">
                <UserRound aria-hidden="true" />
                {authUser.preferred_username ?? authUser.email ?? ""}
              </span>
            )}
            <button
              className="icon-button"
              type="button"
              title="Обновить список карьеров"
              aria-label="Обновить список карьеров"
              disabled={quarriesLoading}
              onClick={() =>
                void refreshQuarries(selectedQuarryId ?? undefined).catch((err) => {
                  console.error(err);
                  notify("error", "Не удалось обновить карьеры");
                })
              }
            >
              {quarriesLoading ? <Loader2 aria-hidden="true" /> : <RefreshCcw aria-hidden="true" />}
            </button>
            <div className={backendOnline ? "connection online" : "connection"}>
              <span />
              API {backendOnline ? "онлайн" : "недоступен"}
            </div>
          </div>
        </header>

        {contentLoading && active !== "auth" && <LoadingBanner label="Обновляем данные" />}

        <section className="page-content" aria-busy={contentLoading}>
          {active === "auth" && <AuthPage authUser={authUser} />}
          {active === "dashboard" && (
          <Dashboard
            quarries={quarries}
            selectedQuarry={selectedQuarry}
            sections={sections}
            passports={passports}
            reports={reports}
            latestResult={latestAnalysisResult}
            onNavigate={navigateTo}
          />
          )}
          {active === "quarries" && (
            <QuarriesPage quarries={quarries} onCreated={handleQuarryCreated} />
          )}
          {active === "sites" && (
            <SitesPage
              quarries={quarries}
              selectedQuarryId={selectedQuarryId}
              onSelectQuarry={setSelectedQuarryId}
              sections={sections}
              onCreated={handleSectionCreated}
            />
          )}
          {active === "passports" && (
            <PassportsPage
              quarries={quarries}
              sections={sections}
              selectedQuarryId={selectedQuarryId}
              onSelectQuarry={setSelectedQuarryId}
              passports={passports}
              onCreated={(p) => {
                setPassports((prev) => [p, ...prev]);
                notify("success", "Паспорт БВР создан");
              }}
              onUpdated={(p) => {
                setPassports((prev) => prev.map((x) => (x.id === p.id ? p : x)));
                notify("success", "Паспорт БВР обновлен");
              }}
            />
          )}
          {active === "analyses" && (
            <AnalysesPage
              quarries={quarries}
              selectedQuarryId={selectedQuarryId}
              onSelectQuarry={setSelectedQuarryId}
              onNavigate={navigateTo}
            />
          )}
          {active === "reports" && (
            <ReportsPage
              quarries={quarries}
              selectedQuarryId={selectedQuarryId}
              onSelectQuarry={setSelectedQuarryId}
              reports={reports}
              onLoadRecommendations={handleLoadRecommendations}
              onError={(message) => notify("error", message)}
            />
          )}
          {active === "recommendations" && (
            <RecommendationsPage
              recommendations={recommendations}
              onReview={handleReviewRecommendation}
            />
          )}
          {active === "admin" && <AdminPage />}
        </section>
      </main>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

function Breadcrumbs({
  activeItem,
  selectedQuarry,
}: {
  activeItem: NavItem;
  selectedQuarry: Quarry | null;
}) {
  return (
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      <span>ZMetrics</span>
      <ChevronRight aria-hidden="true" />
      {selectedQuarry && (
        <>
          <span>{selectedQuarry.name}</span>
          <ChevronRight aria-hidden="true" />
        </>
      )}
      <strong>{activeItem.label}</strong>
    </nav>
  );
}

function LoadingBanner({ label }: { label: string }) {
  return (
    <div className="loading-banner" role="status" aria-live="polite">
      <Loader2 aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function Toast({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  if (!toast) return null;
  const Icon = toast.type === "success" ? CheckCircle2 : toast.type === "error" ? AlertCircle : Sparkles;
  return (
    <div className={`toast ${toast.type}`} role="status" aria-live="polite">
      <Icon aria-hidden="true" />
      <span>{toast.message}</span>
      <button className="icon-button" type="button" aria-label="Закрыть уведомление" onClick={onClose}>
        <X aria-hidden="true" />
      </button>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: NavItem["icon"];
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <Icon aria-hidden="true" />
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  );
}

function AuthPage({ authUser }: { authUser: AuthUser | null }) {
  return (
    <section className="content-grid two">
      <div className="form-panel">
        {authUser ? (
          <div style={{ display: "grid", gap: 14 }}>
            <p style={{ margin: 0 }}>
              Вы вошли как{" "}
              <strong>
                {authUser.name ?? authUser.preferred_username ?? authUser.email ?? authUser.sub}
              </strong>
            </p>
            {authUser.email && (
              <p style={{ margin: 0, color: "var(--muted)" }}>{authUser.email}</p>
            )}
            <button className="primary" type="button" onClick={() => void kc.logout()}>
              <LockKeyhole aria-hidden="true" />
              Выйти
            </button>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 14 }}>
            <p style={{ margin: 0, color: "var(--muted)" }}>
              Войдите через корпоративный Keycloak для получения доступа к данным.
            </p>
            <button className="primary" type="button" onClick={() => void kc.login()}>
              <LockKeyhole aria-hidden="true" />
              Войти через Keycloak
            </button>
          </div>
        )}
      </div>
      <div className="data-panel">
        <PanelTitle icon={Users} title="Роли доступа" />
        <div className="role-grid">
          <RoleBadge label="Администратор" value="полный доступ" />
          <RoleBadge label="Взрывник" value="БВР и анализы" />
          <RoleBadge label="Маркшейдер" value="участки и отчеты" />
          <RoleBadge label="Пользователь" value="просмотр" />
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function Dashboard({
  quarries,
  selectedQuarry,
  sections,
  passports,
  reports,
  latestResult,
  onNavigate,
}: {
  quarries: Quarry[];
  selectedQuarry: Quarry | null;
  sections: SiteSection[];
  passports: BlastPassport[];
  reports: Report[];
  latestResult: AnalysisResult | null;
  onNavigate: (key: NavKey) => void;
}) {
  const fractions: Fraction[] = useMemo(() => {
    if (!latestResult?.size_distribution) return [];
    return latestResult.size_distribution.map((bin) => ({
      label: `${bin.size_mm} мм`,
      percent: bin.cumulative_passing_pct,
    }));
  }, [latestResult]);

  const workflow = [
    { label: "Карьер", done: quarries.length > 0, count: quarries.length, icon: Map },
    { label: "Участок", done: sections.length > 0, count: sections.length, icon: MapPinned },
    { label: "Паспорт", done: passports.length > 0, count: passports.length, icon: ClipboardList },
    { label: "Анализ", done: latestResult !== null, count: latestResult ? 1 : 0, icon: BarChart3 },
    { label: "Отчет", done: reports.length > 0, count: reports.length, icon: FileText },
  ];

  return (
    <div className="dashboard-screen">
      <section className="dashboard-command">
        <div className="command-copy">
          <span className="section-kicker">Оперативный контур</span>
          <h2>{selectedQuarry ? selectedQuarry.name : "Подготовьте первый карьер"}</h2>
          <p>
            Рабочий экран для цепочки БВР: структура карьера, паспорта, анализ фрагментации,
            отчеты и рекомендации в одном месте.
          </p>
          <div className="command-actions">
            <button className="primary" type="button" onClick={() => onNavigate("quarries")}>
              <Map aria-hidden="true" />
              Карьеры
            </button>
            <button type="button" onClick={() => onNavigate("passports")}>
              <ClipboardList aria-hidden="true" />
              Паспорт БВР
            </button>
            <button type="button" onClick={() => onNavigate("reports")}>
              <FileText aria-hidden="true" />
              Отчеты
            </button>
          </div>
        </div>
        <div className="command-visual">
          <img
            src="/assets/rock-sample.png"
            alt="Фрагменты горной массы"
            loading="lazy"
            decoding="async"
          />
          <div className="command-badge">
            <span>P80</span>
            <strong>{latestResult?.p80_mm != null ? `${latestResult.p80_mm} мм` : "нет данных"}</strong>
          </div>
        </div>
      </section>

      <section className="metrics-grid">
        <MetricCard icon={Map} label="Карьеры" value={String(quarries.length)} tone="teal" />
        <MetricCard
          icon={Activity}
          label="D80"
          value={latestResult?.p80_mm != null ? `${latestResult.p80_mm} мм` : "—"}
          tone="blue"
        />
        <MetricCard icon={FileText} label="Отчеты" value={String(reports.length)} tone="green" />
        <MetricCard
          icon={MapPinned}
          label="Участки"
          value={String(sections.length)}
          tone="amber"
        />
      </section>

      <section className="workflow-panel">
        <div className="section-heading">
          <div>
            <span className="section-kicker">Workflow</span>
            <h2>Готовность данных</h2>
          </div>
          <span className="status-pill">{workflow.filter((step) => step.done).length}/5 этапов</span>
        </div>
        <div className="workflow-grid">
          {workflow.map((step) => (
            <WorkflowStep key={step.label} {...step} />
          ))}
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="data-panel">
          <PanelTitle icon={BarChart3} title="Распределение фракций" />
          {fractions.length > 0 ? (
            <Histogram fractions={fractions} />
          ) : (
            <EmptyState
              icon={BarChart3}
              title="Нет данных анализа"
              description="После обработки capture session здесь появится распределение фракций."
            />
          )}
        </div>

        <RecentReports reports={reports.slice(0, 4)} onOpenReports={() => onNavigate("reports")} />
      </section>

      <section className="dashboard-grid">
        <section className="data-panel">
          <PanelTitle icon={ClipboardList} title="Последние участки" />
          <SectionTable rows={sections.slice(0, 8)} />
        </section>
        <section className="quick-panel">
          <DashboardQuickAction
            icon={MapPinned}
            title="Создать участок"
            description="Добавьте рабочую зону для нового паспорта БВР."
            onClick={() => onNavigate("sites")}
          />
          <DashboardQuickAction
            icon={Sparkles}
            title="Проверить рекомендации"
            description="Откройте последние предложения после отчета."
            onClick={() => onNavigate("recommendations")}
          />
        </section>
      </section>
    </div>
  );
}

function WorkflowStep({
  label,
  done,
  count,
  icon: Icon,
}: {
  label: string;
  done: boolean;
  count: number;
  icon: NavItem["icon"];
}) {
  return (
    <article className={done ? "workflow-step done" : "workflow-step"}>
      <Icon aria-hidden="true" />
      <div>
        <strong>{label}</strong>
        <span>{done ? `${count} в системе` : "ожидает данных"}</span>
      </div>
    </article>
  );
}

function RecentReports({
  reports,
  onOpenReports,
}: {
  reports: Report[];
  onOpenReports: () => void;
}) {
  return (
    <section className="data-panel recent-panel">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Последние</span>
          <h2>Отчеты</h2>
        </div>
        <button type="button" onClick={onOpenReports}>
          <FileText aria-hidden="true" />
          Все
        </button>
      </div>
      {reports.length > 0 ? (
        <div className="recent-list">
          {reports.map((report) => (
            <article key={report.id} className="recent-item">
              <div>
                <strong>{report.title}</strong>
                <span>{new Date(report.created_at).toLocaleDateString("ru-RU")}</span>
              </div>
              <span className={report.analysis_method === "mock" ? "warning-badge" : "status-pill"}>
                {report.analysis_method === "mock" ? "mock" : "real"}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="Отчетов пока нет"
          description="Они появятся после завершения анализа capture session."
        />
      )}
    </section>
  );
}

function DashboardQuickAction({
  icon: Icon,
  title,
  description,
  onClick,
}: {
  icon: NavItem["icon"];
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button className="quick-action" type="button" onClick={onClick}>
      <Icon aria-hidden="true" />
      <span>
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      <ChevronRight aria-hidden="true" />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Quarries
// ---------------------------------------------------------------------------

function parseOptionalNumber(value: string, label: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return null;

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${label}: введите число`);
  }
  return parsed;
}

function QuarriesPage({
  quarries,
  onCreated,
}: {
  quarries: Quarry[];
  onCreated: (quarry: Quarry) => void | Promise<void>;
}) {
  const [form, setForm] = useState({
    name: "",
    location_description: "",
    latitude: "",
    longitude: "",
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaveError(null);

    if (!form.name.trim()) {
      setSaveError("Укажите название карьера");
      return;
    }

    try {
      setSaving(true);
      const created = await api.quarries.create({
        name: form.name.trim(),
        location_description: form.location_description.trim() || null,
        latitude: parseOptionalNumber(form.latitude, "Широта"),
        longitude: parseOptionalNumber(form.longitude, "Долгота"),
      });
      setForm({ name: "", location_description: "", latitude: "", longitude: "" });
      await onCreated(created);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Не удалось создать карьер");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="management-layout">
      <aside className="management-aside">
        <div className="management-copy">
          <span className="section-kicker">Справочник</span>
          <h2>Карьеры</h2>
          <p>Создавайте площадки и сразу переходите к участкам, паспортам БВР и отчетам.</p>
        </div>
        <form className="form-panel compact" onSubmit={handleSubmit}>
          <PanelTitle icon={Map} title="Новый карьер" />
          <label>
            Название
            <input
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Например, Demo Quarry"
            />
          </label>
          <label>
            Локация
            <input
              value={form.location_description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, location_description: e.target.value }))
              }
              placeholder="Описание местоположения"
            />
          </label>
          <label>
            Широта
            <input
              value={form.latitude}
              onChange={(e) => setForm((prev) => ({ ...prev, latitude: e.target.value }))}
              placeholder="55.7512"
              inputMode="decimal"
            />
          </label>
          <label>
            Долгота
            <input
              value={form.longitude}
              onChange={(e) => setForm((prev) => ({ ...prev, longitude: e.target.value }))}
              placeholder="37.6184"
              inputMode="decimal"
            />
          </label>
          {saveError && <p className="form-error">{saveError}</p>}
          <button className="primary" type="submit" disabled={saving}>
            <Map aria-hidden="true" />
            {saving ? "Создаем..." : "Создать карьер"}
          </button>
        </form>
      </aside>

      <div className="management-main">
        <div className="section-heading">
          <div>
            <span className="section-kicker">Всего: {quarries.length}</span>
            <h2>Список карьеров</h2>
          </div>
        </div>
        {quarries.length === 0 ? (
          <EmptyState
            icon={Map}
            title="Карьеров пока нет"
            description="Создайте первый карьер, чтобы открыть участки, паспорта БВР и последующие отчеты."
          />
        ) : (
          <section className="list-grid quarry-grid">
            {quarries.map((quarry) => (
              <article className="entity-card quarry-card" key={quarry.id}>
                <div className="entity-head">
                  <Map aria-hidden="true" />
                  <strong>{quarry.name}</strong>
                </div>
                <dl>
                  <div>
                    <dt>Локация</dt>
                    <dd>{quarry.location_description ?? "—"}</dd>
                  </div>
                  {quarry.latitude != null && quarry.longitude != null && (
                    <div>
                      <dt>Координаты</dt>
                      <dd>
                        {quarry.latitude.toFixed(4)}, {quarry.longitude.toFixed(4)}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt>ID</dt>
                    <dd style={{ fontFamily: "monospace", fontSize: "0.85em" }}>
                      {quarry.id.slice(-8)}
                    </dd>
                  </div>
                </dl>
              </article>
            ))}
          </section>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sites
// ---------------------------------------------------------------------------

function SitesPage({
  quarries,
  selectedQuarryId,
  onSelectQuarry,
  sections,
  onCreated,
}: {
  quarries: Quarry[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  sections: SiteSection[];
  onCreated: (section: SiteSection) => void;
}) {
  const [query, setQuery] = useState("");
  const [form, setForm] = useState({ name: "", block_number: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const filteredSections = useMemo(() => {
    const s = query.trim().toLowerCase();
    if (!s) return sections;
    return sections.filter((sec) =>
      `${sec.name} ${sec.block_number ?? ""} ${sec.description ?? ""}`.toLowerCase().includes(s),
    );
  }, [sections, query]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaveError(null);

    if (!selectedQuarryId) {
      setSaveError("Сначала создайте или выберите карьер");
      return;
    }
    if (!form.name.trim()) {
      setSaveError("Укажите название участка");
      return;
    }

    try {
      setSaving(true);
      const created = await api.sections.create(selectedQuarryId, {
        name: form.name.trim(),
        block_number: form.block_number.trim() || null,
        description: form.description.trim() || null,
      });
      setForm({ name: "", block_number: "", description: "" });
      onCreated(created);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Не удалось создать участок");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="management-layout">
      <aside className="management-aside">
        <div className="management-copy">
          <span className="section-kicker">Структура</span>
          <h2>Участки</h2>
          <p>Разбейте карьер на рабочие зоны, чтобы паспорта БВР были привязаны к месту работ.</p>
        </div>
        <form className="form-panel compact" onSubmit={handleSubmit}>
          <PanelTitle icon={MapPinned} title="Новый участок" />
          <label>
            Название
            <input
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Например, Block A"
              disabled={!selectedQuarryId}
            />
          </label>
          <label>
            Номер блока
            <input
              value={form.block_number}
              onChange={(e) => setForm((prev) => ({ ...prev, block_number: e.target.value }))}
              placeholder="A-001"
              disabled={!selectedQuarryId}
            />
          </label>
          <label>
            Описание
            <input
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Рабочая зона, уступ, примечание"
              disabled={!selectedQuarryId}
            />
          </label>
          {saveError && <p className="form-error">{saveError}</p>}
          <button className="primary" type="submit" disabled={!selectedQuarryId || saving}>
            <MapPinned aria-hidden="true" />
            {saving ? "Создаем..." : "Создать участок"}
          </button>
        </form>
      </aside>

      <div className="management-main">
        <div className="toolbar section-toolbar">
          <label className="search-box">
            <Search aria-hidden="true" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Поиск участков"
              aria-label="Поиск участков"
            />
          </label>
          <QuarrySelect quarries={quarries} value={selectedQuarryId} onChange={onSelectQuarry} />
        </div>
        <div className="data-panel">
          {selectedQuarryId ? (
            <SectionTable rows={filteredSections} />
          ) : (
            <EmptyState
              icon={MapPinned}
              title="Карьер не выбран"
              description="Создайте или выберите карьер, чтобы добавить первый участок."
            />
          )}
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Passports
// ---------------------------------------------------------------------------

// The single transition each status allows. Statuses absent from this map
// (COMPLETED, SUPERSEDED) are terminal — no button is rendered. One click maps to
// exactly one POST; there is no chaining and no automatic progression.
type TransitionAction = "submit" | "approve" | "activate" | "complete";

const NEXT_TRANSITION: Record<string, { action: TransitionAction; label: string }> = {
  draft: { action: "submit", label: "Подать на проверку" },
  submitted: { action: "approve", label: "Утвердить" },
  approved: { action: "activate", label: "Активировать" },
  active: { action: "complete", label: "Завершить" },
};

const STATUS_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  draft: { bg: "#eef2f6", color: "var(--muted)", label: "Черновик" },
  submitted: { bg: "#fdf0e1", color: "var(--amber)", label: "На проверке" },
  approved: { bg: "#e8f0fe", color: "var(--blue)", label: "Утверждён" },
  active: { bg: "#e8f5f2", color: "var(--teal)", label: "Активен" },
  completed: { bg: "#e7f6ec", color: "var(--green)", label: "Завершён" },
  superseded: { bg: "#eef2f6", color: "var(--muted)", label: "Заменён" },
};

// String-typed form state; converted to numbers/nulls before the API call.
type BlastEventFormData = {
  blast_datetime: string;
  actual_explosive_kg: string;
  weather_conditions: string;
  notes: string;
};

// The blast-event inputs sit outside `.form-panel`, so they don't inherit its
// field styling — apply the same look inline to stay consistent.
const detailFieldStyle: CSSProperties = {
  minHeight: 42,
  border: "1px solid var(--line)",
  borderRadius: 8,
  padding: "0 12px",
  color: "var(--ink)",
  background: "white",
  font: "inherit",
};

function PassportsPage({
  quarries,
  sections,
  selectedQuarryId,
  onSelectQuarry,
  passports,
  onCreated,
  onUpdated,
}: {
  quarries: Quarry[];
  sections: SiteSection[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  passports: BlastPassport[];
  onCreated: (p: BlastPassport) => void;
  onUpdated: (p: BlastPassport) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BlastPassport | null>(null);
  const [blastEvent, setBlastEvent] = useState<BlastEvent | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [transitioning, setTransitioning] = useState(false);
  const [showBlastEventForm, setShowBlastEventForm] = useState(false);

  const handleSelectPassport = async (passport: BlastPassport) => {
    if (!selectedQuarryId) return;
    setShowCreate(false);
    setDetailId(passport.id);
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    setBlastEvent(null);
    setAuditLog([]);
    setShowBlastEventForm(false);

    // allSettled: a missing blast event (404) and a forbidden audit log (403) are
    // expected outcomes — they must not surface as a load failure.
    const [fullPassport, eventResult, auditResult] = await Promise.allSettled([
      api.passports.get(selectedQuarryId, passport.id),
      api.blastEvents.get(selectedQuarryId, passport.id),
      api.auditLogs.forPassport(passport.id),
    ]);

    if (fullPassport.status === "fulfilled") {
      setDetail(fullPassport.value);
    } else {
      // Only the passport fetch failing is a real error worth showing.
      setDetailError(
        fullPassport.reason instanceof Error
          ? fullPassport.reason.message
          : "Ошибка загрузки паспорта",
      );
    }
    if (eventResult.status === "fulfilled") {
      setBlastEvent(eventResult.value); // 404 → stays null (no blast event yet)
    }
    if (auditResult.status === "fulfilled") {
      setAuditLog(auditResult.value); // 403 → stays [] (caller is not an admin)
    }
    setDetailLoading(false);
  };

  const handleTransition = async (action: TransitionAction) => {
    if (!detail || !selectedQuarryId) return;
    setTransitioning(true);
    setDetailError(null);
    try {
      const updated = await api.passports[action](selectedQuarryId, detail.id);
      setDetail(updated);
      onUpdated(updated);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : `Ошибка: ${action}`);
    } finally {
      setTransitioning(false);
    }
  };

  const handleCreateBlastEvent = async (form: BlastEventFormData) => {
    if (!detail || !selectedQuarryId) return;
    if (!form.blast_datetime) return; // required — never POST without a datetime
    setTransitioning(true);
    setDetailError(null);
    try {
      const event = await api.blastEvents.create(selectedQuarryId, detail.id, {
        blast_datetime: form.blast_datetime,
        actual_explosive_kg: form.actual_explosive_kg
          ? parseFloat(form.actual_explosive_kg)
          : null,
        weather_conditions: form.weather_conditions || null,
        notes: form.notes || null,
      });
      setBlastEvent(event);
      setShowBlastEventForm(false);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "Ошибка создания взрыва");
    } finally {
      setTransitioning(false);
    }
  };

  const openCreate = () => {
    setShowCreate(true);
    setDetailId(null);
    setDetail(null);
  };

  const closeDetail = () => {
    setDetailId(null);
    setDetail(null);
  };

  return (
    <section className="content-grid two">
      <div className="data-panel">
        <PanelTitle icon={ClipboardList} title="Паспорта БВР" />
        <div className="toolbar compact-toolbar">
          <QuarrySelect
            quarries={quarries}
            value={selectedQuarryId}
            onChange={onSelectQuarry}
            className="grow"
          />
          <button type="button" onClick={openCreate} title="Создать паспорт">
            <ClipboardList aria-hidden="true" />
            Создать
          </button>
        </div>
        <div className="passport-list">
          {passports.map((passport) => (
            <article
              className={`passport-row ${detailId === passport.id ? "selected" : ""}`}
              key={passport.id}
              onClick={() => void handleSelectPassport(passport)}
              style={{
                cursor: "pointer",
                borderColor: detailId === passport.id ? "var(--teal)" : undefined,
                background: detailId === passport.id ? "var(--surface-2)" : undefined,
              }}
            >
              <div>
                <strong>#{passport.id.slice(-8)}</strong>
                <PassportStatusBadge status={passport.status} />
              </div>
              <span>
                {passport.hole_diameter_mm != null ? `${passport.hole_diameter_mm} мм` : "—"}
              </span>
              <span>
                {passport.number_of_holes != null ? `${passport.number_of_holes} скв.` : "—"}
              </span>
              <span>
                {passport.total_explosive_kg != null
                  ? `${passport.total_explosive_kg} кг`
                  : "—"}
              </span>
            </article>
          ))}
          {passports.length === 0 && (
            <EmptyState
              icon={ClipboardList}
              title="Паспорта не найдены"
              description="Создайте паспорт БВР для выбранного участка, чтобы продолжить рабочий сценарий."
            />
          )}
        </div>
      </div>

      {detailId !== null ? (
        detailLoading && !detail ? (
          <div className="data-panel">
            <LoadingBanner label="Загружаем паспорт" />
          </div>
        ) : detail ? (
          <PassportDetail
            passport={detail}
            blastEvent={blastEvent}
            auditLog={auditLog}
            loading={detailLoading}
            error={detailError}
            transitioning={transitioning}
            showBlastEventForm={showBlastEventForm}
            onTransition={handleTransition}
            onShowBlastEventForm={() => setShowBlastEventForm(true)}
            onHideBlastEventForm={() => setShowBlastEventForm(false)}
            onCreateBlastEvent={handleCreateBlastEvent}
            onClose={closeDetail}
          />
        ) : (
          <div className="data-panel" style={{ display: "grid", gap: 12, alignContent: "start" }}>
            <button type="button" onClick={closeDetail} style={{ justifySelf: "start" }}>
              ← К списку
            </button>
            <p style={{ color: "var(--rose)", margin: 0 }}>
              {detailError ?? "Не удалось загрузить паспорт"}
            </p>
          </div>
        )
      ) : showCreate ? (
        <PassportCreateForm
          sections={sections}
          selectedQuarryId={selectedQuarryId}
          onCreated={onCreated}
        />
      ) : (
        <div className="data-panel panel-stack">
          <EmptyState
            icon={ClipboardList}
            title="Паспорт не выбран"
            description="Выберите паспорт из списка или создайте новый для текущего карьера."
          />
          <button
            className="primary"
            type="button"
            onClick={openCreate}
          >
            <ClipboardList aria-hidden="true" />
            Создать паспорт
          </button>
        </div>
      )}
    </section>
  );
}

function PassportStatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] ?? { bg: "#eef2f6", color: "var(--muted)", label: status };
  return (
    <span className="status-pill" style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

function PassportDetail({
  passport,
  blastEvent,
  auditLog,
  loading,
  error,
  transitioning,
  showBlastEventForm,
  onTransition,
  onShowBlastEventForm,
  onHideBlastEventForm,
  onCreateBlastEvent,
  onClose,
}: {
  passport: BlastPassport;
  blastEvent: BlastEvent | null;
  auditLog: AuditLogEntry[];
  loading: boolean;
  error: string | null;
  transitioning: boolean;
  showBlastEventForm: boolean;
  onTransition: (action: TransitionAction) => void;
  onShowBlastEventForm: () => void;
  onHideBlastEventForm: () => void;
  onCreateBlastEvent: (form: BlastEventFormData) => void;
  onClose: () => void;
}) {
  const next = NEXT_TRANSITION[passport.status];
  const showBlastSection = passport.status === "approved" || passport.status === "active";

  return (
    <div className="data-panel" style={{ display: "grid", gap: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
        }}
      >
        <button type="button" onClick={onClose}>
          ← К списку
        </button>
        {loading && (
          <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Обновление…</span>
        )}
      </div>

      <PanelTitle icon={ClipboardList} title={`Паспорт #${passport.id.slice(-8)}`} />

      <dl>
        <div>
          <dt>Статус</dt>
          <dd>
            <PassportStatusBadge status={passport.status} />
          </dd>
        </div>
        <div>
          <dt>Ревизия</dt>
          <dd>{passport.revision_number}</dd>
        </div>
        <div>
          <dt>Участок</dt>
          <dd style={{ fontFamily: "monospace", fontSize: "0.85em" }}>
            {passport.site_section_id.slice(-8)}
          </dd>
        </div>
        <div>
          <dt>Тип ВВ</dt>
          <dd>{passport.explosive_type ?? "—"}</dd>
        </div>
        <div>
          <dt>Количество скважин</dt>
          <dd>{passport.number_of_holes ?? "—"}</dd>
        </div>
        <div>
          <dt>Диаметр скв.</dt>
          <dd>{passport.hole_diameter_mm != null ? `${passport.hole_diameter_mm} мм` : "—"}</dd>
        </div>
        <div>
          <dt>Глубина скв.</dt>
          <dd>{passport.hole_depth_m != null ? `${passport.hole_depth_m} м` : "—"}</dd>
        </div>
        <div>
          <dt>ЛНС, м</dt>
          <dd>{passport.burden_m != null ? `${passport.burden_m} м` : "—"}</dd>
        </div>
        <div>
          <dt>Расстояние, м</dt>
          <dd>{passport.spacing_m != null ? `${passport.spacing_m} м` : "—"}</dd>
        </div>
        <div>
          <dt>Забойка, м</dt>
          <dd>{passport.stemming_m != null ? `${passport.stemming_m} м` : "—"}</dd>
        </div>
        <div>
          <dt>Масса ВВ</dt>
          <dd>{passport.total_explosive_kg != null ? `${passport.total_explosive_kg} кг` : "—"}</dd>
        </div>
        <div>
          <dt>Цель P80</dt>
          <dd>{passport.target_p80_mm != null ? `${passport.target_p80_mm} мм` : "не задан"}</dd>
        </div>
        {passport.blast_date_planned && (
          <div>
            <dt>Плановая дата</dt>
            <dd>{new Date(passport.blast_date_planned).toLocaleDateString("ru-RU")}</dd>
          </div>
        )}
        {passport.notes && (
          <div>
            <dt>Примечания</dt>
            <dd>{passport.notes}</dd>
          </div>
        )}
        <div>
          <dt>Создан</dt>
          <dd>{new Date(passport.created_at).toLocaleDateString("ru-RU")}</dd>
        </div>
      </dl>

      <div style={{ display: "grid", gap: 10 }}>
        {next ? (
          <button
            className="primary"
            type="button"
            disabled={transitioning}
            onClick={() => onTransition(next.action)}
            style={{ justifySelf: "start" }}
          >
            {transitioning ? "Выполнение…" : next.label}
          </button>
        ) : passport.status === "completed" ? (
          <p style={{ color: "var(--green)", margin: 0 }}>Паспорт завершён</p>
        ) : passport.status === "superseded" ? (
          <p style={{ color: "var(--muted)", margin: 0 }}>Паспорт заменён</p>
        ) : null}
        {error && <p style={{ color: "var(--rose)", margin: 0 }}>{error}</p>}
      </div>

      {showBlastSection && (
        <div
          style={{
            borderTop: "1px solid var(--line)",
            paddingTop: 14,
            display: "grid",
            gap: 12,
          }}
        >
          {blastEvent ? (
            <>
              <div className="panel-title" style={{ marginBottom: 0 }}>
                <Activity aria-hidden="true" />
                <h2>Взрыв проведён</h2>
              </div>
              <dl>
                <div>
                  <dt>Дата/время</dt>
                  <dd>{new Date(blastEvent.blast_datetime).toLocaleString("ru-RU")}</dd>
                </div>
                <div>
                  <dt>Фактич. ВВ</dt>
                  <dd>
                    {blastEvent.actual_explosive_kg != null
                      ? `${blastEvent.actual_explosive_kg} кг`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Погода</dt>
                  <dd>{blastEvent.weather_conditions ?? "—"}</dd>
                </div>
                <div>
                  <dt>Заметки</dt>
                  <dd>{blastEvent.notes ?? "—"}</dd>
                </div>
              </dl>
            </>
          ) : showBlastEventForm ? (
            <BlastEventForm
              transitioning={transitioning}
              onSubmit={onCreateBlastEvent}
              onCancel={onHideBlastEventForm}
            />
          ) : (
            <button type="button" onClick={onShowBlastEventForm} style={{ justifySelf: "start" }}>
              <Activity aria-hidden="true" />
              Зарегистрировать взрыв
            </button>
          )}
        </div>
      )}

      {auditLog.length > 0 && (
        <div
          style={{
            borderTop: "1px solid var(--line)",
            paddingTop: 14,
            display: "grid",
            gap: 12,
          }}
        >
          <div className="panel-title" style={{ marginBottom: 0 }}>
            <Settings aria-hidden="true" />
            <h2>История изменений</h2>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Действие</th>
                  <th>Было</th>
                  <th>Стало</th>
                </tr>
              </thead>
                <tbody>
                  {auditLog.map((entry) => (
                    <tr key={entry.id}>
                      <td data-label="Дата">{new Date(entry.occurred_at).toLocaleString("ru-RU")}</td>
                      <td data-label="Действие">{entry.action}</td>
                      <td data-label="Было">{entry.old_value ? JSON.stringify(entry.old_value) : "—"}</td>
                      <td data-label="Стало">{entry.new_value ? JSON.stringify(entry.new_value) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function BlastEventForm({
  transitioning,
  onSubmit,
  onCancel,
}: {
  transitioning: boolean;
  onSubmit: (form: BlastEventFormData) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<BlastEventFormData>({
    blast_datetime: "",
    actual_explosive_kg: "",
    weather_conditions: "",
    notes: "",
  });

  return (
    <form
      style={{ display: "grid", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        if (!form.blast_datetime) return; // required — guard before POST
        onSubmit(form);
      }}
    >
      <label style={{ display: "grid", gap: 6, color: "var(--muted)" }}>
        Дата и время взрыва *
        <input
          type="datetime-local"
          required
          value={form.blast_datetime}
          onChange={(e) => setForm((prev) => ({ ...prev, blast_datetime: e.target.value }))}
          style={detailFieldStyle}
        />
      </label>
      <label style={{ display: "grid", gap: 6, color: "var(--muted)" }}>
        Фактическая масса ВВ, кг
        <input
          type="number"
          value={form.actual_explosive_kg}
          onChange={(e) => setForm((prev) => ({ ...prev, actual_explosive_kg: e.target.value }))}
          placeholder="2380"
          style={detailFieldStyle}
        />
      </label>
      <label style={{ display: "grid", gap: 6, color: "var(--muted)" }}>
        Погодные условия
        <input
          type="text"
          value={form.weather_conditions}
          onChange={(e) => setForm((prev) => ({ ...prev, weather_conditions: e.target.value }))}
          placeholder="Ясно, +18°C, ветер 3 м/с"
          style={detailFieldStyle}
        />
      </label>
      <label style={{ display: "grid", gap: 6, color: "var(--muted)" }}>
        Заметки
        <textarea
          value={form.notes}
          onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
          rows={3}
          style={{ ...detailFieldStyle, minHeight: 70, padding: "10px 12px" }}
        />
      </label>
      <div style={{ display: "flex", gap: 10 }}>
        <button className="primary" type="submit" disabled={transitioning}>
          <Activity aria-hidden="true" />
          {transitioning ? "Сохранение…" : "Зарегистрировать"}
        </button>
        <button type="button" onClick={onCancel} disabled={transitioning}>
          Отмена
        </button>
      </div>
    </form>
  );
}

function PassportCreateForm({
  sections,
  selectedQuarryId,
  onCreated,
}: {
  sections: SiteSection[];
  selectedQuarryId: string | null;
  onCreated: (p: BlastPassport) => void;
}) {
  const emptyForm = {
    site_section_id: "",
    explosive_type: "",
    number_of_holes: "",
    hole_diameter_mm: "",
    hole_depth_m: "",
    burden_m: "",
    spacing_m: "",
    stemming_m: "",
    total_explosive_kg: "",
    target_p80_mm: "",
    blast_date_planned: "",
    notes: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!selectedQuarryId || !form.site_section_id) {
      setSaveError("Выберите участок");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const body = {
        site_section_id: form.site_section_id,
        explosive_type: form.explosive_type || null,
        number_of_holes: form.number_of_holes ? parseInt(form.number_of_holes, 10) : null,
        hole_diameter_mm: form.hole_diameter_mm ? parseFloat(form.hole_diameter_mm) : null,
        hole_depth_m: form.hole_depth_m ? parseFloat(form.hole_depth_m) : null,
        burden_m: form.burden_m ? parseFloat(form.burden_m) : null,
        spacing_m: form.spacing_m ? parseFloat(form.spacing_m) : null,
        stemming_m: form.stemming_m ? parseFloat(form.stemming_m) : null,
        total_explosive_kg: form.total_explosive_kg ? parseFloat(form.total_explosive_kg) : null,
        target_p80_mm: form.target_p80_mm ? parseFloat(form.target_p80_mm) : null,
        blast_date_planned: form.blast_date_planned || null,
        notes: form.notes || null,
      };
      const created = await api.passports.create(selectedQuarryId, body);
      onCreated(created);
      setForm(emptyForm);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      className="form-panel compact"
      onSubmit={(e) => {
        e.preventDefault();
        void handleSave();
      }}
    >
      <label style={{ gridColumn: "1 / -1" }}>
        Участок
        <select
          value={form.site_section_id}
          onChange={(e) => setForm((prev) => ({ ...prev, site_section_id: e.target.value }))}
          style={{
            minHeight: 42,
            border: "1px solid var(--line)",
            borderRadius: 8,
            padding: "0 12px",
            color: "var(--ink)",
            background: "white",
          }}
        >
          <option value="" disabled>
            Выберите участок
          </option>
          {sections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
              {s.block_number ? ` (${s.block_number})` : ""}
            </option>
          ))}
        </select>
      </label>
      <label>
        Тип ВВ
        <input
          type="text"
          value={form.explosive_type}
          onChange={(e) => setForm((prev) => ({ ...prev, explosive_type: e.target.value }))}
          placeholder="Гранулит АС-8"
        />
      </label>
      <label>
        Количество скважин
        <input
          type="number"
          min="1"
          value={form.number_of_holes}
          onChange={(e) => setForm((prev) => ({ ...prev, number_of_holes: e.target.value }))}
          placeholder="24"
        />
      </label>
      <label>
        Диаметр скв., мм
        <input
          type="number"
          value={form.hole_diameter_mm}
          onChange={(e) => setForm((prev) => ({ ...prev, hole_diameter_mm: e.target.value }))}
          placeholder="115"
        />
      </label>
      <label>
        Глубина скв., м
        <input
          type="number"
          value={form.hole_depth_m}
          onChange={(e) => setForm((prev) => ({ ...prev, hole_depth_m: e.target.value }))}
          placeholder="12.5"
        />
      </label>
      <label>
        ЛНС, м
        <input
          type="number"
          value={form.burden_m}
          onChange={(e) => setForm((prev) => ({ ...prev, burden_m: e.target.value }))}
          placeholder="3.5"
        />
      </label>
      <label>
        Расстояние, м
        <input
          type="number"
          value={form.spacing_m}
          onChange={(e) => setForm((prev) => ({ ...prev, spacing_m: e.target.value }))}
          placeholder="4.0"
        />
      </label>
      <label>
        Забойка, м
        <input
          type="number"
          value={form.stemming_m}
          onChange={(e) => setForm((prev) => ({ ...prev, stemming_m: e.target.value }))}
          placeholder="3.0"
        />
      </label>
      <label>
        Масса ВВ, кг
        <input
          type="number"
          value={form.total_explosive_kg}
          onChange={(e) => setForm((prev) => ({ ...prev, total_explosive_kg: e.target.value }))}
          placeholder="4360"
        />
      </label>
      <label>
        Цель P80, мм
        <input
          type="number"
          value={form.target_p80_mm}
          onChange={(e) => setForm((prev) => ({ ...prev, target_p80_mm: e.target.value }))}
          placeholder="300"
        />
      </label>
      <label>
        Плановая дата взрыва
        <input
          type="datetime-local"
          value={form.blast_date_planned}
          onChange={(e) => setForm((prev) => ({ ...prev, blast_date_planned: e.target.value }))}
        />
      </label>
      <label style={{ gridColumn: "1 / -1" }}>
        Примечания
        <input
          type="text"
          value={form.notes}
          onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
          placeholder="Дополнительная информация"
        />
      </label>
      {saveError && (
        <p style={{ color: "var(--rose)", margin: 0, gridColumn: "1 / -1" }}>{saveError}</p>
      )}
      <button className="primary" type="submit" disabled={saving} style={{ gridColumn: "1 / -1" }}>
        <ClipboardList aria-hidden="true" />
        {saving ? "Сохранение..." : "Сохранить"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Analyses — camera capture panel
// ---------------------------------------------------------------------------

function captureFrameFromVideo(
  video: HTMLVideoElement,
): { left: { blob: Blob; dataUrl: string }; right: { blob: Blob; dataUrl: string } | null } {
  const w = video.videoWidth;
  const h = video.videoHeight;
  const isSbs = w / h > 1.8;

  const canvas = document.createElement('canvas');
  const ctx2d = canvas.getContext('2d')!;

  if (isSbs) {
    const halfW = Math.floor(w / 2);

    canvas.width = halfW;
    canvas.height = h;
    ctx2d.drawImage(video, 0, 0, halfW, h, 0, 0, halfW, h);
    const leftDataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const leftBlob = dataUrlToBlob(leftDataUrl);

    ctx2d.clearRect(0, 0, halfW, h);
    ctx2d.drawImage(video, halfW, 0, halfW, h, 0, 0, halfW, h);
    const rightDataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const rightBlob = dataUrlToBlob(rightDataUrl);

    return {
      left: { blob: leftBlob, dataUrl: leftDataUrl },
      right: { blob: rightBlob, dataUrl: rightDataUrl },
    };
  } else {
    canvas.width = w;
    canvas.height = h;
    ctx2d.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    return { left: { blob: dataUrlToBlob(dataUrl), dataUrl }, right: null };
  }
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [header, b64] = dataUrl.split(',');
  const mime = header.match(/:(.*?);/)?.[1] ?? 'image/jpeg';
  const bytes = atob(b64 ?? '');
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mime });
}

function AnalysesPage({
  quarries,
  selectedQuarryId,
  onSelectQuarry,
  onNavigate,
}: {
  quarries: Quarry[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string | null) => void;
  onNavigate: (key: NavKey) => void;
}) {
  // Passport selection
  const [analysisPassportId, setAnalysisPassportId] = useState<string | null>(null);
  const [analysisPassports, setAnalysisPassports] = useState<BlastPassport[]>([]);

  // Browser camera
  const [browserCameras, setBrowserCameras] = useState<MediaDeviceInfo[]>([]);
  const [selectedCamId, setSelectedCamId] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isSbs, setIsSbs] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Captured frames gallery
  const [frames, setFrames] = useState<CapturedFrame[]>([]);
  const [nextFrameIndex, setNextFrameIndex] = useState(0);

  // Launch state machine
  type LaunchState = 'idle' | 'uploading' | 'enqueued' | 'polling' | 'completed' | 'failed';
  const [launchState, setLaunchState] = useState<LaunchState>('idle');
  const [launchStep, setLaunchStep] = useState('');
  const [currentJob, setCurrentJob] = useState<AnalysisJob | null>(null);
  const [jobResult, setJobResult] = useState<AnalysisResult | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Stop stream and polling on unmount or screen change
  useEffect(() => {
    return () => {
      stream?.getTracks().forEach((t) => t.stop());
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [stream]);

  // Attach stream to video element after it mounts (stream renders the <video> conditionally)
  useEffect(() => {
    if (!stream || !videoRef.current) return;
    videoRef.current.srcObject = stream;
    videoRef.current.play().catch(() => {});
    videoRef.current.onloadedmetadata = () => {
      if (!videoRef.current) return;
      setIsSbs(videoRef.current.videoWidth / videoRef.current.videoHeight > 1.8);
    };
  }, [stream]);

  // Load cameras
  useEffect(() => {
    if (!kc.authenticated) return;
    navigator.mediaDevices
      .enumerateDevices()
      .then((devs) => setBrowserCameras(devs.filter((d) => d.kind === 'videoinput')))
      .catch(() => setBrowserCameras([]));
  }, []);

  // Load passports for selected quarry (only APPROVED / ACTIVE)
  useEffect(() => {
    if (!selectedQuarryId) { setAnalysisPassports([]); return; }
    api.passports.list(selectedQuarryId).then((all) =>
      setAnalysisPassports(
        all.filter((p) => ['approved', 'active'].includes(p.status.toLowerCase())),
      ),
    ).catch(() => setAnalysisPassports([]));
  }, [selectedQuarryId]);

  async function handleSelectCamera(deviceId: string) {
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
    setSelectedCamId(deviceId);
    setIsSbs(false);

    try {
      const realDeviceId = browserCameras.find(
        (c, i) => (c.deviceId || `cam-${i}`) === deviceId
      )?.deviceId;
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: realDeviceId ? { deviceId: { exact: realDeviceId } } : true,
      });
      setStream(newStream);
      // srcObject is attached in useEffect after <video> mounts
    } catch (err) {
      setLaunchError(`Нет доступа к камере: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  function handleCapture() {
    if (!videoRef.current || !stream) return;
    if (!videoRef.current.videoWidth || !videoRef.current.videoHeight) return;
    const { left, right } = captureFrameFromVideo(videoRef.current);
    const id = crypto.randomUUID();
    const idx = nextFrameIndex;

    const newFrames: CapturedFrame[] = [
      {
        id,
        blob: left.blob,
        dataUrl: left.dataUrl,
        width: videoRef.current.videoWidth / (right ? 2 : 1),
        height: videoRef.current.videoHeight,
        artifactType: 'left_frame',
        frameIndex: idx,
        capturedAt: Date.now(),
      },
    ];

    if (right) {
      newFrames.push({
        id: crypto.randomUUID(),
        blob: right.blob,
        dataUrl: right.dataUrl,
        width: videoRef.current.videoWidth / 2,
        height: videoRef.current.videoHeight,
        artifactType: 'right_frame',
        frameIndex: idx,
        capturedAt: Date.now(),
      });
    }

    setFrames((prev) => [...prev, ...newFrames]);
    setNextFrameIndex((n) => n + 1);
  }

  function handleDeleteFrame(frameId: string) {
    setFrames((prev) => prev.filter((f) => f.id !== frameId));
  }

  async function handleLaunch() {
    if (!selectedQuarryId || !analysisPassportId) return;
    const leftFrames = frames.filter((f) => f.artifactType === 'left_frame');
    if (leftFrames.length === 0) return;

    setLaunchError(null);
    setCurrentJob(null);
    setJobResult(null);

    try {
      setLaunchStep('Подготовка устройства...');
      setLaunchState('uploading');

      // Ensure device exists — create default ZED 2 if none registered yet
      let devices = await api.devices.list();
      if (devices.length === 0) {
        try {
          await api.devices.create({ serial_number: 'ZED2-001', model: 'ZED 2' });
        } catch {
          // 409 = already exists (race) — re-fetch
        }
        devices = await api.devices.list();
        if (devices.length === 0) throw new Error('Не удалось зарегистрировать устройство. Обратитесь к администратору.');
      }
      const device = devices[0];

      // Ensure calibration exists — create default if none
      let cals = await api.devices.listCalibrations(device.id);
      if (cals.length === 0) {
        await api.devices.addCalibration(device.id, {
          left_camera_matrix:  { fx: 700, fy: 700, cx: 640, cy: 360 },
          right_camera_matrix: { fx: 700, fy: 700, cx: 640, cy: 360 },
          left_dist_coeffs:    { k1: 0, k2: 0, p1: 0, p2: 0, k3: 0 },
          right_dist_coeffs:   { k1: 0, k2: 0, p1: 0, p2: 0, k3: 0 },
          rotation_matrix:     { data: [1, 0, 0, 0, 1, 0, 0, 0, 1] },
          translation_vector:  { data: [-0.12, 0, 0] },
          baseline_mm: 120,
          image_width_px: 1280,
          image_height_px: 720,
        });
        cals = await api.devices.listCalibrations(device.id);
      }
      const cal = cals[0];

      setLaunchStep('Проверяю запись взрыва...');
      try {
        await api.blastEvents.get(selectedQuarryId, analysisPassportId);
      } catch {
        await api.blastEvents.create(selectedQuarryId, analysisPassportId, {
          blast_datetime: new Date().toISOString(),
        });
      }

      setLaunchStep('Создаю сессию съёмки...');
      const session = await api.captureFlow.createSession(selectedQuarryId, analysisPassportId, {
        device_id: device.id,
        calibration_id: cal.id,
      });
      setSessionId(session.id);

      const allFrames = frames;
      for (const frame of allFrames) {
        setLaunchStep(`Загружаю ${frame.artifactType} #${frame.frameIndex}...`);
        const file = new File([frame.blob], `${frame.artifactType}_${frame.frameIndex}.jpg`, {
          type: 'image/jpeg',
        });
        await api.captureFlow.uploadArtifact(
          session.id,
          file,
          frame.artifactType,
          frame.frameIndex,
        );
      }

      setLaunchStep('Ставлю задачу в очередь...');
      const job = await api.captureFlow.enqueueJob(session.id);
      setCurrentJob(job);
      setLaunchState('enqueued');
      startPolling(session.id, job.id);

    } catch (err) {
      setLaunchError(err instanceof Error ? err.message : String(err));
      setLaunchState('failed');
    }
  }

  function startPolling(sid: string, jid: string) {
    setLaunchState('polling');
    pollRef.current = setInterval(() => {
      void (async () => {
        try {
          const j = await api.captureFlow.pollJob(sid, jid);
          setCurrentJob(j);
          if (j.status === 'completed') {
            clearInterval(pollRef.current!); pollRef.current = null;
            try {
              const result = await api.captureFlow.getJobResult(sid, j.id);
              setJobResult(result);
            } catch { /* result not yet written */ }
            setLaunchState('completed');
          } else if (j.status === 'failed') {
            clearInterval(pollRef.current!); pollRef.current = null;
            setLaunchError(j.error_message ?? 'Ошибка воркера');
            setLaunchState('failed');
          }
        } catch { /* network error — keep polling */ }
      })();
    }, 3000);
  }

  function handleReset() {
    if (pollRef.current) clearInterval(pollRef.current);
    setLaunchState('idle');
    setLaunchStep('');
    setCurrentJob(null);
    setJobResult(null);
    setSessionId(null);
    setLaunchError(null);
    setFrames([]);
    setNextFrameIndex(0);
  }

  const isBusy = !['idle', 'completed', 'failed'].includes(launchState);
  const hasLeftFrame = frames.some((f) => f.artifactType === 'left_frame');
  const canLaunch = !!selectedQuarryId && !!analysisPassportId && hasLeftFrame && !isBusy;
  const isMock = JSON.stringify(currentJob?.pipeline_log ?? {}).toLowerCase().includes('synthetic');

  return (
    <div className="analysis-screen">
        <h2>Анализ развала — захват с камеры</h2>

        {/* 1. ПАСПОРТ */}
        <section className="form-section">
          <h3>1. Паспорт</h3>
          <div className="form-row">
            <label>Карьер</label>
            <select
              value={selectedQuarryId ?? ''}
              onChange={(e) => { onSelectQuarry(e.target.value || null); setAnalysisPassportId(null); }}
              disabled={isBusy}
            >
              <option value="">— выберите карьер —</option>
              {quarries.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Паспорт</label>
            <select
              value={analysisPassportId ?? ''}
              onChange={(e) => setAnalysisPassportId(e.target.value || null)}
              disabled={!selectedQuarryId || isBusy}
            >
              <option value="">— выберите паспорт (APPROVED / ACTIVE) —</option>
              {analysisPassports.map((p) => (
                <option key={p.id} value={p.id}>
                  #{p.revision_number} · {p.status} · P80 цель: {p.target_p80_mm ?? '—'} мм
                </option>
              ))}
            </select>
            {selectedQuarryId && analysisPassports.length === 0 && (
              <span className="analysis-hint analysis-hint--warning">
                Нет паспортов APPROVED/ACTIVE. Перейдите в Паспорта и утвердите паспорт.
              </span>
            )}
          </div>
        </section>

        {/* 2. КАМЕРА */}
        <section className="form-section">
          <h3>2. Камера</h3>
          <div className="form-row">
            <label>Устройство</label>
            <select
              value={selectedCamId ?? ''}
              onChange={(e) => { if (e.target.value !== '') void handleSelectCamera(e.target.value); }}
              disabled={isBusy}
            >
              <option value="">— выберите камеру —</option>
              {browserCameras.map((c, i) => (
                <option key={c.deviceId || `cam-${i}`} value={c.deviceId || `cam-${i}`}>
                  {c.label || `Камера ${i + 1}`}
                </option>
              ))}
            </select>
            {browserCameras.length === 0 && (
              <span className="analysis-hint analysis-hint--warning">
                Камеры не найдены. Разрешите доступ к камере в браузере.
              </span>
            )}
          </div>

          {stream && (
            <div className="camera-preview">
              {isSbs && (
                <p className="analysis-hint analysis-hint--ok">
                  ✓ Обнаружен SBS-режим (ZED 2) — кадр будет автоматически разделён на left+right
                </p>
              )}
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="camera-preview__video"
              />
              <button
                className="primary"
                onClick={handleCapture}
                disabled={isBusy}
              >
                📸 Сделать снимок {isSbs ? '(stereo)' : ''}
              </button>
            </div>
          )}
        </section>

        {/* 3. ГАЛЕРЕЯ КАДРОВ */}
        {frames.length > 0 && (
          <section className="form-section">
            <h3>3. Кадры ({frames.length})</h3>
            <div className="frame-gallery">
              {frames.map((f) => (
                <div
                  key={f.id}
                  className="frame-thumb"
                >
                  <img
                    src={f.dataUrl}
                    alt={`${f.artifactType} #${f.frameIndex}`}
                  />
                  <div className="frame-thumb__meta">
                    {f.artifactType === 'left_frame' ? 'L' : 'R'} #{f.frameIndex}
                  </div>
                  <button
                    onClick={() => handleDeleteFrame(f.id)}
                    disabled={isBusy}
                    className="frame-thumb__delete"
                    aria-label="Удалить кадр"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 4. АНАЛИЗ */}
        <section className="form-section">
          <h3>4. Анализ</h3>
          <div className="form-row">
            {launchState === 'idle' && (
              <button className="primary" disabled={!canLaunch} onClick={() => void handleLaunch()}>
                Отправить на анализ ({frames.filter((f) => f.artifactType === 'left_frame').length} left
                {frames.some((f) => f.artifactType === 'right_frame') ? ' + right' : ''})
              </button>
            )}
            {isBusy && (
              <button className="primary" disabled>Выполняется...</button>
            )}
            {(launchState === 'completed' || launchState === 'failed') && (
              <button className="secondary" onClick={handleReset}>Новый захват</button>
            )}
          </div>

          {(launchState === 'uploading' || launchState === 'enqueued') && (
            <div className="analysis-banner info-banner"><span className="spinner" /> {launchStep}</div>
          )}
          {launchState === 'polling' && currentJob && (
            <div className="analysis-banner info-banner">
              <span className="spinner" /> Воркер: <strong>{currentJob.status}</strong>
            </div>
          )}

          {launchState === 'completed' && (
            <div className="analysis-banner success-banner">
              ✅ Анализ завершён
              {isMock && <span className="badge-mock"> ⚠ Синтетические данные</span>}
              {jobResult?.p80_mm != null && (
                <div className="analysis-result-line">
                  P80: <strong>{jobResult.p80_mm.toFixed(0)} мм</strong>
                  {jobResult.confidence_score != null && (
                    <> · Уверенность: <strong>{jobResult.confidence_score.toFixed(2)}</strong></>
                  )}
                </div>
              )}
              <button
                className="primary"
                onClick={() => onNavigate('reports')}
              >
                Открыть отчёт
              </button>
            </div>
          )}

          {launchState === 'failed' && launchError && (
            <div className="analysis-banner error-banner">❌ {launchError}</div>
          )}

          {sessionId && (
            <details className="analysis-details">
              <summary>Технические детали</summary>
              <div>Session: {sessionId}</div>
              {currentJob && <div>Job: {currentJob.id} · {currentJob.status}</div>}
              {currentJob?.pipeline_log && (
                <pre>
                  {JSON.stringify(currentJob.pipeline_log, null, 2)}
                </pre>
              )}
            </details>
          )}
        </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

function ReportsPage({
  quarries,
  selectedQuarryId,
  onSelectQuarry,
  reports,
  onLoadRecommendations,
  onError,
}: {
  quarries: Quarry[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  reports: Report[];
  onLoadRecommendations: (reportId: string) => Promise<void>;
  onError: (message: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<"newest" | "oldest" | "title">("newest");

  const visibleReports = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const filtered = normalized
      ? reports.filter((report) =>
          `${report.title} ${report.report_type} ${report.analysis_method}`
            .toLowerCase()
            .includes(normalized),
        )
      : reports;

    return [...filtered].sort((a, b) => {
      if (sortMode === "title") return a.title.localeCompare(b.title, "ru");
      const aTime = new Date(a.created_at).getTime();
      const bTime = new Date(b.created_at).getTime();
      return sortMode === "newest" ? bTime - aTime : aTime - bTime;
    });
  }, [query, reports, sortMode]);

  const handleDownload = async (report: Report) => {
    try {
      await downloadWithAuth(
        api.reports.exportUrl(report.id),
        `report-${report.id.slice(-8)}.json`,
      );
    } catch (err) {
      console.error("Download failed:", err);
      onError("Не удалось скачать JSON отчета");
    }
  };

  return (
    <section className="data-panel">
      <PanelTitle icon={FileText} title="Сформированные отчеты" />
      <div className="toolbar report-toolbar">
        <label className="search-box">
          <Search aria-hidden="true" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск отчетов"
            aria-label="Поиск отчетов"
          />
        </label>
        <select
          className="control-select"
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as typeof sortMode)}
          aria-label="Сортировка отчетов"
        >
          <option value="newest">Сначала новые</option>
          <option value="oldest">Сначала старые</option>
          <option value="title">По названию</option>
        </select>
        <QuarrySelect quarries={quarries} value={selectedQuarryId} onChange={onSelectQuarry} />
      </div>
      <div className="report-list">
        {visibleReports.map((report) => (
          <article className="report-row" key={report.id}>
            <div>
              <strong>{report.title}</strong>
              <span>{report.report_type}</span>
              {report.analysis_method === "mock" && (
                <span className="warning-badge">Синтетические данные</span>
              )}
            </div>
            <span>{new Date(report.created_at).toLocaleDateString("ru-RU")}</span>
            <button type="button" title="Скачать JSON" onClick={() => void handleDownload(report)}>
              <Download aria-hidden="true" />
              JSON
            </button>
            <button
              type="button"
              title="Открыть рекомендации"
              onClick={() => void onLoadRecommendations(report.id)}
            >
              <Sparkles aria-hidden="true" />
              Рекомендации
            </button>
          </article>
        ))}
        {visibleReports.length === 0 && (
          <EmptyState
            icon={FileText}
            title="Отчеты не найдены"
            description={
              reports.length === 0
                ? "После завершения анализа отчеты появятся здесь."
                : "Попробуйте изменить поисковый запрос или сортировку."
            }
          />
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

function RecommendationsPage({
  recommendations,
  onReview,
}: {
  recommendations: Recommendation[];
  onReview: (rec: Recommendation, status: string) => Promise<void>;
}) {
  if (recommendations.length === 0) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Рекомендации не выбраны"
        description="Откройте отчет и нажмите «Рекомендации», чтобы загрузить предложения по параметрам БВР."
      />
    );
  }

  return (
    <section className="list-grid recommendations">
      {recommendations.map((item) => (
        <article
          className={`entity-card ${priorityClass(item.status)}`}
          key={item.id}
        >
          <div className="entity-head">
            <Sparkles aria-hidden="true" />
            <strong>
              {item.recommendation_text.length > 60
                ? item.recommendation_text.slice(0, 57) + "..."
                : item.recommendation_text}
            </strong>
          </div>

          <p>{item.recommendation_text}</p>

          <span className="status-pill">{statusLabel(item.status)}</span>

          {item.parameter_suggestions &&
            Object.keys(item.parameter_suggestions).length > 0 && (
              <div
                style={{
                  borderTop: "1px solid var(--line)",
                  paddingTop: 10,
                  marginTop: 4,
                }}
              >
                <p
                  style={{
                    margin: "0 0 6px",
                    color: "var(--muted)",
                    fontSize: "0.82rem",
                  }}
                >
                  Справочные параметры (только для просмотра):
                </p>
                <dl style={{ margin: 0, fontSize: "0.9rem" }}>
                  {Object.entries(item.parameter_suggestions).map(([k, v]) => (
                    <div key={k}>
                      <dt style={{ color: "var(--muted)" }}>{k}</dt>
                      <dd style={{ margin: 0, textAlign: "right" }}>{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

          {item.status === "requires_human_review" && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" onClick={() => void onReview(item, "accepted")}>
                Принять
              </button>
              <button type="button" onClick={() => void onReview(item, "rejected")}>
                Отклонить
              </button>
              <button type="button" onClick={() => void onReview(item, "reviewed")}>
                Ознакомлен
              </button>
            </div>
          )}

          {item.reviewed_at && (
            <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
              Проверено: {new Date(item.reviewed_at).toLocaleString("ru-RU")}
            </span>
          )}
        </article>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Admin — static (read-only display from audit/user info)
// ---------------------------------------------------------------------------

function AdminPage() {
  return (
    <section className="content-grid two">
      <div className="data-panel">
        <PanelTitle icon={Users} title="Управление доступом" />
        <p style={{ color: "var(--muted)", margin: 0 }}>
          Управление пользователями и ролями выполняется в Keycloak Admin Console на порту 8080.
        </p>
      </div>
      <div className="data-panel">
        <PanelTitle icon={Settings} title="Журнал аудита" />
        <p style={{ color: "var(--muted)", margin: 0 }}>
          Просмотр журнала аудита доступен через API: <code>/api/v1/admin/audit-log</code>
        </p>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

function QuarrySelect({
  quarries,
  value,
  onChange,
  className,
}: {
  quarries: Quarry[];
  value: string | null;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <select
      className={className ? `control-select ${className}` : "control-select"}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={quarries.length === 0}
      aria-label="Выберите карьер"
    >
      <option value="" disabled>
        Выберите карьер
      </option>
      {quarries.map((q) => (
        <option key={q.id} value={q.id}>
          {q.name}
        </option>
      ))}
    </select>
  );
}

function PanelTitle({ icon: Icon, title }: { icon: NavItem["icon"]; title: string }) {
  return (
    <div className="panel-title">
      <Icon aria-hidden="true" />
      <h2>{title}</h2>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: NavItem["icon"];
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <Icon aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function Histogram({ fractions }: { fractions: Fraction[] }) {
  return (
    <div className="histogram">
      {fractions.map((fraction) => (
        <div className="bar-row" key={fraction.label}>
          <span>{fraction.label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${fraction.percent}%` }} />
          </div>
          <strong>{fraction.percent}%</strong>
        </div>
      ))}
    </div>
  );
}

type SectionSortKey = "name" | "block_number" | "description";

function SectionTable({ rows }: { rows: SiteSection[] }) {
  const [sortKey, setSortKey] = useState<SectionSortKey>("name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    return [...rows].sort((a, b) => {
      const left = String(a[sortKey] ?? "").toLowerCase();
      const right = String(b[sortKey] ?? "").toLowerCase();
      const result = left.localeCompare(right, "ru", { numeric: true });
      return sortDirection === "asc" ? result : -result;
    });
  }, [rows, sortDirection, sortKey]);

  const toggleSort = (key: SectionSortKey) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection("asc");
  };

  const sortLabel = (key: SectionSortKey) =>
    sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : "";

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={MapPinned}
        title="Участки не найдены"
        description="Добавьте первый участок для выбранного карьера или измените поисковый запрос."
      />
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <button className="table-sort" type="button" onClick={() => toggleSort("name")}>
                Участок{sortLabel("name")}
              </button>
            </th>
            <th>
              <button
                className="table-sort"
                type="button"
                onClick={() => toggleSort("block_number")}
              >
                Блок{sortLabel("block_number")}
              </button>
            </th>
            <th>
              <button
                className="table-sort"
                type="button"
                onClick={() => toggleSort("description")}
              >
                Описание{sortLabel("description")}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((sec) => (
            <tr key={sec.id}>
              <td data-label="Участок">{sec.name}</td>
              <td data-label="Блок">{sec.block_number ?? "—"}</td>
              <td data-label="Описание">{sec.description ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RoleBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="role-badge">
      <UserRound aria-hidden="true" />
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function priorityClass(status: string): string {
  if (status === "requires_human_review") return "priority-high";
  if (status === "reviewed") return "priority-medium";
  return "priority-low";
}

function statusLabel(status: string): string {
  switch (status) {
    case "requires_human_review":
      return "требует проверки";
    case "reviewed":
      return "ознакомлен";
    case "accepted":
      return "принято";
    case "rejected":
      return "отклонено";
    default:
      return status;
  }
}
