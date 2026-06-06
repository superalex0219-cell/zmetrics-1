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
  AuthUser,
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

    Promise.all([
      api.sections.list(selectedQuarryId),
      api.passports.list(selectedQuarryId),
      api.reports.list(selectedQuarryId),
    ])
      .then(([sects, passps, reps]) => {
        setSections(sects);
        setPassports(passps);
        setReports(reps);
        if (reps.length > 0) {
          api.analysisResults
            .get(reps[0].analysis_result_id)
            .then(setLatestAnalysisResult)
            .catch(console.error);
        } else {
          setLatestAnalysisResult(null);
        }
      })
      .catch(console.error);
  }, [selectedQuarryId]);

  const handleLoadRecommendations = async (reportId: string) => {
    const recs = await api.recommendations.list(reportId);
    setRecommendations(recs);
    setActive("recommendations");
  };

  const handleReviewRecommendation = async (rec: Recommendation, status: string) => {
    const updated = await api.recommendations.review(rec.report_id, rec.id, status);
    setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
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

function PassportsPage({
  quarries,
  sections,
  selectedQuarryId,
  onSelectQuarry,
  passports,
  onCreated,
}: {
  quarries: Quarry[];
  sections: SiteSection[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  passports: BlastPassport[];
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
    <section className="content-grid two">
      <div className="data-panel">
        <PanelTitle icon={ClipboardList} title="Паспорта БВР" />
        <div style={{ marginBottom: 12 }}>
          <QuarrySelect
            quarries={quarries}
            value={selectedQuarryId}
            onChange={onSelectQuarry}
            style={{ width: "100%" }}
          />
        </div>
        <div className="passport-list">
          {passports.map((passport) => (
            <article className="passport-row" key={passport.id}>
              <div>
                <strong>#{passport.id.slice(-8)}</strong>
                <span className="status-pill">{passport.status}</span>
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
            onChange={(e) =>
              setForm((prev) => ({ ...prev, hole_diameter_mm: e.target.value }))
            }
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
            onChange={(e) =>
              setForm((prev) => ({ ...prev, total_explosive_kg: e.target.value }))
            }
            placeholder="4360"
          />
        </label>
        <label>
          Цель P80, мм
          <input
            type="number"
            value={form.target_p80_mm}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, target_p80_mm: e.target.value }))
            }
            placeholder="300"
          />
        </label>
        {saveError && (
          <p style={{ color: "var(--rose)", margin: 0, gridColumn: "1 / -1" }}>{saveError}</p>
        )}
        <button
          className="primary"
          type="submit"
          disabled={saving}
          style={{ gridColumn: "1 / -1" }}
        >
          <ClipboardList aria-hidden="true" />
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
      </form>
    </section>
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
