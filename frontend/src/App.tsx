import { type CSSProperties, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  ClipboardList,
  Download,
  FileText,
  Hammer,
  ImageUp,
  LayoutDashboard,
  LockKeyhole,
  Map,
  MapPinned,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
  Users,
} from "lucide-react";

import { api, checkBackend, downloadWithAuth, kc } from "./api";
import type {
  AnalysisResult,
  AuditLogEntry,
  AuthUser,
  BlastEvent,
  BlastPassport,
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

export default function App() {
  const [active, setActive] = useState<NavKey>("dashboard");
  const [backendOnline, setBackendOnline] = useState(false);

  const [quarries, setQuarries] = useState<Quarry[]>([]);
  const [selectedQuarryId, setSelectedQuarryId] = useState<string | null>(null);
  const [sections, setSections] = useState<SiteSection[]>([]);
  const [passports, setPassports] = useState<BlastPassport[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [latestAnalysisResult, setLatestAnalysisResult] = useState<AnalysisResult | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

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

      api.quarries
        .list()
        .then((qs) => {
          setQuarries(qs);
          if (qs.length > 0) {
            setSelectedQuarryId(qs[0].id);
          }
        })
        .catch(console.error);
    }
  }, []);

  // When quarry selection changes, reload sections, passports, reports
  useEffect(() => {
    if (!selectedQuarryId) return;

    void Promise.allSettled([
      api.sections.list(selectedQuarryId),
      api.passports.list(selectedQuarryId),
      api.reports.list(selectedQuarryId),
    ]).then(([sectsResult, passpsResult, repsResult]) => {
      if (sectsResult.status === "fulfilled") setSections(sectsResult.value);
      else console.error(sectsResult.reason);

      if (passpsResult.status === "fulfilled") setPassports(passpsResult.value);
      else console.error(passpsResult.reason);

      const reps = repsResult.status === "fulfilled" ? repsResult.value : [];
      if (repsResult.status === "rejected") console.error(repsResult.reason);
      setReports(reps);

      if (reps.length > 0) {
        api.analysisResults
          .get(reps[0].analysis_result_id)
          .then(setLatestAnalysisResult)
          .catch(console.error);
      } else {
        setLatestAnalysisResult(null);
      }
    });
  }, [selectedQuarryId]);

  const handleLoadRecommendations = async (reportId: string) => {
    try {
      const recs = await api.recommendations.list(reportId);
      setRecommendations(recs);
      setActive("recommendations");
    } catch (err) {
      console.error(err);
    }
  };

  const handleReviewRecommendation = async (rec: Recommendation, status: string) => {
    try {
      const updated = await api.recommendations.review(rec.report_id, rec.id, status);
      setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Hammer aria-hidden="true" />
          <div>
            <strong>ZMetrics</strong>
            <span>БВР контроль</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Основные разделы">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={active === item.key ? "nav-item active" : "nav-item"}
              type="button"
              title={item.label}
              onClick={() => setActive(item.key)}
            >
              <item.icon aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Смена {new Date().toLocaleDateString("ru-RU")}</span>
            <h1>{navItems.find((item) => item.key === active)?.label}</h1>
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {authUser && (
              <span className="eyebrow">
                {authUser.preferred_username ?? authUser.email ?? ""}
              </span>
            )}
            <div className={backendOnline ? "connection online" : "connection"}>
              <span />
              API {backendOnline ? "онлайн" : "демо"}
            </div>
          </div>
        </header>

        {active === "auth" && <AuthPage authUser={authUser} />}
        {active === "dashboard" && (
          <Dashboard
            quarries={quarries}
            sections={sections}
            reports={reports}
            latestResult={latestAnalysisResult}
          />
        )}
        {active === "quarries" && <QuarriesPage quarries={quarries} />}
        {active === "sites" && (
          <SitesPage
            quarries={quarries}
            selectedQuarryId={selectedQuarryId}
            onSelectQuarry={setSelectedQuarryId}
            sections={sections}
          />
        )}
        {active === "passports" && (
          <PassportsPage
            quarries={quarries}
            sections={sections}
            selectedQuarryId={selectedQuarryId}
            onSelectQuarry={setSelectedQuarryId}
            passports={passports}
            onCreated={(p) => setPassports((prev) => [p, ...prev])}
            onUpdated={(p) => setPassports((prev) => prev.map((x) => (x.id === p.id ? p : x)))}
          />
        )}
        {active === "analyses" && <AnalysesPage />}
        {active === "reports" && (
          <ReportsPage
            quarries={quarries}
            selectedQuarryId={selectedQuarryId}
            onSelectQuarry={setSelectedQuarryId}
            reports={reports}
            onLoadRecommendations={handleLoadRecommendations}
          />
        )}
        {active === "recommendations" && (
          <RecommendationsPage
            recommendations={recommendations}
            onReview={handleReviewRecommendation}
          />
        )}
        {active === "admin" && <AdminPage />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

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
  sections,
  reports,
  latestResult,
}: {
  quarries: Quarry[];
  sections: SiteSection[];
  reports: Report[];
  latestResult: AnalysisResult | null;
}) {
  const fractions: Fraction[] = useMemo(() => {
    if (!latestResult?.size_distribution) return [];
    return latestResult.size_distribution.map((bin) => ({
      label: `${bin.size_mm} мм`,
      percent: bin.cumulative_passing_pct,
    }));
  }, [latestResult]);

  return (
    <div className="stack">
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

      <section className="content-grid two">
        <div className="image-panel">
          <img src="/assets/rock-sample.png" alt="Фрагменты горной массы" />
          {latestResult && (
            <div className="image-stats">
              <span>
                {latestResult.oversize_percent != null
                  ? `Негабарит: ${latestResult.oversize_percent.toFixed(1)}%`
                  : "Последний анализ"}
              </span>
              <strong>
                {latestResult.confidence_score != null
                  ? `Достоверность: ${Math.round(latestResult.confidence_score * 100)}%`
                  : "Нет оценки"}
              </strong>
            </div>
          )}
        </div>
        <div className="data-panel">
          <PanelTitle icon={BarChart3} title="Распределение фракций" />
          {fractions.length > 0 ? (
            <Histogram fractions={fractions} />
          ) : (
            <p style={{ color: "var(--muted)", margin: 0 }}>Нет данных об анализе</p>
          )}
        </div>
      </section>

      <section className="data-panel">
        <PanelTitle icon={ClipboardList} title="Последние участки" />
        <SectionTable rows={sections.slice(0, 8)} />
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quarries
// ---------------------------------------------------------------------------

function QuarriesPage({ quarries }: { quarries: Quarry[] }) {
  if (quarries.length === 0) {
    return (
      <div className="data-panel" style={{ padding: 24 }}>
        <p style={{ color: "var(--muted)", margin: 0 }}>
          Карьеры не найдены. Войдите в систему для загрузки данных.
        </p>
      </div>
    );
  }
  return (
    <section className="list-grid">
      {quarries.map((quarry) => (
        <article className="entity-card" key={quarry.id}>
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
}: {
  quarries: Quarry[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  sections: SiteSection[];
}) {
  const [query, setQuery] = useState("");

  const filteredSections = useMemo(() => {
    const s = query.trim().toLowerCase();
    if (!s) return sections;
    return sections.filter((sec) =>
      `${sec.name} ${sec.block_number ?? ""} ${sec.description ?? ""}`.toLowerCase().includes(s),
    );
  }, [sections, query]);

  return (
    <section className="stack">
      <div className="toolbar">
        <label className="search-box">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск участков"
          />
        </label>
        <QuarrySelect quarries={quarries} value={selectedQuarryId} onChange={onSelectQuarry} />
      </div>
      <div className="data-panel">
        <SectionTable rows={filteredSections} />
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
  DRAFT: { action: "submit", label: "Подать на проверку" },
  SUBMITTED: { action: "approve", label: "Утвердить" },
  APPROVED: { action: "activate", label: "Активировать" },
  ACTIVE: { action: "complete", label: "Завершить" },
};

const STATUS_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  DRAFT: { bg: "#eef2f6", color: "var(--muted)", label: "Черновик" },
  SUBMITTED: { bg: "#fdf0e1", color: "var(--amber)", label: "На проверке" },
  APPROVED: { bg: "#e8f0fe", color: "var(--blue)", label: "Утверждён" },
  ACTIVE: { bg: "#e8f5f2", color: "var(--teal)", label: "Активен" },
  COMPLETED: { bg: "#e7f6ec", color: "var(--green)", label: "Завершён" },
  SUPERSEDED: { bg: "#eef2f6", color: "var(--muted)", label: "Заменён" },
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
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <QuarrySelect
            quarries={quarries}
            value={selectedQuarryId}
            onChange={onSelectQuarry}
            style={{ flex: 1 }}
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
            <p style={{ color: "var(--muted)", margin: 0 }}>Нет паспортов для выбранного карьера</p>
          )}
        </div>
      </div>

      {detailId !== null ? (
        detailLoading && !detail ? (
          <div className="data-panel">
            <p style={{ color: "var(--muted)", margin: 0 }}>Загрузка…</p>
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
        <div className="data-panel" style={{ display: "grid", gap: 14, alignContent: "start" }}>
          <p style={{ color: "var(--muted)", margin: 0 }}>
            Выберите паспорт из списка или создайте новый.
          </p>
          <button
            className="primary"
            type="button"
            onClick={openCreate}
            style={{ justifySelf: "start" }}
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
  const showBlastSection = passport.status === "APPROVED" || passport.status === "ACTIVE";

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
          <dt>Сетка (ЛНС × расст.)</dt>
          <dd>{`${passport.burden_m ?? "—"} × ${passport.spacing_m ?? "—"} м`}</dd>
        </div>
        <div>
          <dt>Масса ВВ</dt>
          <dd>{passport.total_explosive_kg != null ? `${passport.total_explosive_kg} кг` : "—"}</dd>
        </div>
        <div>
          <dt>Цель P80</dt>
          <dd>{passport.target_p80_mm != null ? `${passport.target_p80_mm} мм` : "не задан"}</dd>
        </div>
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
        ) : passport.status === "COMPLETED" ? (
          <p style={{ color: "var(--green)", margin: 0 }}>Паспорт завершён</p>
        ) : passport.status === "SUPERSEDED" ? (
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
                    <td>{new Date(entry.occurred_at).toLocaleString("ru-RU")}</td>
                    <td>{entry.action}</td>
                    <td>{entry.old_value ? JSON.stringify(entry.old_value) : "—"}</td>
                    <td>{entry.new_value ? JSON.stringify(entry.new_value) : "—"}</td>
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
  const [form, setForm] = useState({
    site_section_id: "",
    hole_diameter_mm: "",
    hole_depth_m: "",
    total_explosive_kg: "",
    target_p80_mm: "",
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!selectedQuarryId || !form.site_section_id) {
      setSaveError("Выберите карьер и участок");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const body = {
        site_section_id: form.site_section_id,
        hole_diameter_mm: form.hole_diameter_mm ? parseFloat(form.hole_diameter_mm) : null,
        hole_depth_m: form.hole_depth_m ? parseFloat(form.hole_depth_m) : null,
        total_explosive_kg: form.total_explosive_kg
          ? parseFloat(form.total_explosive_kg)
          : null,
        target_p80_mm: form.target_p80_mm ? parseFloat(form.target_p80_mm) : null,
      };
      const created = await api.passports.create(selectedQuarryId, body);
      onCreated(created);
      setForm({
        site_section_id: "",
        hole_diameter_mm: "",
        hole_depth_m: "",
        total_explosive_kg: "",
        target_p80_mm: "",
      });
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
        Диаметр скв., мм
        <input
          type="number"
          value={form.hole_diameter_mm}
          onChange={(e) => setForm((prev) => ({ ...prev, hole_diameter_mm: e.target.value }))}
          placeholder="215"
        />
      </label>
      <label>
        Средняя глубина, м
        <input
          type="number"
          value={form.hole_depth_m}
          onChange={(e) => setForm((prev) => ({ ...prev, hole_depth_m: e.target.value }))}
          placeholder="15.2"
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
// Analyses — mobile-only placeholder
// ---------------------------------------------------------------------------

function AnalysesPage() {
  return (
    <section className="data-panel">
      <PanelTitle icon={BarChart3} title="Анализ изображений" />
      <div
        style={{
          padding: "48px 0",
          textAlign: "center",
          color: "var(--muted)",
          display: "grid",
          gap: 12,
          justifyItems: "center",
        }}
      >
        <ImageUp style={{ width: 48, height: 48, opacity: 0.4 }} aria-hidden="true" />
        <p style={{ margin: 0, fontSize: "1.05rem", color: "var(--ink)" }}>
          Запуск анализа выполняется через мобильное приложение ZMetrics.
        </p>
        <p style={{ margin: 0 }}>Результаты появятся в разделе «Отчёты» после завершения.</p>
      </div>
    </section>
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
}: {
  quarries: Quarry[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  reports: Report[];
  onLoadRecommendations: (reportId: string) => Promise<void>;
}) {
  const handleDownload = async (report: Report) => {
    try {
      await downloadWithAuth(
        api.reports.exportUrl(report.id),
        `report-${report.id.slice(-8)}.json`,
      );
    } catch (err) {
      console.error("Download failed:", err);
    }
  };

  return (
    <section className="data-panel">
      <PanelTitle icon={FileText} title="Сформированные отчеты" />
      <div style={{ marginBottom: 14 }}>
        <QuarrySelect quarries={quarries} value={selectedQuarryId} onChange={onSelectQuarry} />
      </div>
      <div className="report-list">
        {reports.map((report) => (
          <article className="report-row" key={report.id}>
            <div>
              <strong>{report.title}</strong>
              <span>{report.report_type}</span>
              {report.analysis_method === "mock" && (
                <span
                  style={{
                    background: "#fff1f2",
                    color: "var(--rose)",
                    borderRadius: 6,
                    padding: "2px 8px",
                    fontSize: "0.78rem",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  ⚠ Синтетические данные
                </span>
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
        {reports.length === 0 && (
          <p style={{ color: "var(--muted)", margin: 0 }}>Нет отчетов для выбранного карьера</p>
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
      <div className="data-panel" style={{ padding: 24, color: "var(--muted)" }}>
        Выберите отчет в разделе «Отчёты» и нажмите «Рекомендации» для загрузки.
      </div>
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
  style,
}: {
  quarries: Quarry[];
  value: string | null;
  onChange: (id: string) => void;
  style?: CSSProperties;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      style={{
        minHeight: 38,
        border: "1px solid var(--line)",
        borderRadius: 8,
        padding: "0 12px",
        background: "white",
        color: "var(--ink)",
        font: "inherit",
        ...style,
      }}
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

function PanelTitle({ icon: Icon, title }: { icon: typeof Activity; title: string }) {
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
  icon: typeof Activity;
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

function SectionTable({ rows }: { rows: SiteSection[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Участок</th>
            <th>Блок</th>
            <th>Описание</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((sec) => (
            <tr key={sec.id}>
              <td>{sec.name}</td>
              <td>{sec.block_number ?? "—"}</td>
              <td>{sec.description ?? "—"}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={3} style={{ color: "var(--muted)", textAlign: "center" }}>
                Нет данных
              </td>
            </tr>
          )}
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
