"use client";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  FileText,
  HeartHandshake,
  Leaf,
  LockKeyhole,
  Menu,
  Plus,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  Volume2,
  X,
} from "lucide-react";
import {
  api,
  Assessment,
  Doc,
  Fact,
  Overview,
  Profile,
  Proposal,
  Result,
  ResearchAnswer,
  ResearchScheme,
  ResearchStatus,
  Scheme,
  User,
} from "./api";
import { Lang, text } from "./i18n";

type Page =
  | "home"
  | "login"
  | "profiles"
  | "consent"
  | "documents"
  | "review"
  | "results"
  | "history"
  | "privacy"
  | "schemes"
  | "admin";
export default function FormFlow() {
  const [lang, setLang] = useState<Lang>("en"),
    [page, setPage] = useState<Page>("home"),
    [user, setUser] = useState<User | null>(null),
    [profiles, setProfiles] = useState<Profile[]>([]),
    [profile, setProfile] = useState<Profile | null>(null),
    [consented, setConsented] = useState(false),
    [docs, setDocs] = useState<Doc[]>([]),
    [facts, setFacts] = useState<Fact[]>([]),
    [assessment, setAssessment] = useState<Assessment | null>(null),
    [history, setHistory] = useState<Assessment[]>([]),
    [registry, setRegistry] = useState<Scheme[]>([]),
    [researchSchemes, setResearchSchemes] = useState<ResearchScheme[]>([]),
    [researchQuestion, setResearchQuestion] = useState(""),
    [researchAnswer, setResearchAnswer] = useState<ResearchAnswer | null>(null),
    [researchScheme, setResearchScheme] = useState<string>(""),
    [researchStatus, setResearchStatus] = useState<ResearchStatus | null>(null),
    [overview, setOverview] = useState<Overview | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [contrast, setContrast] = useState(false),
    [larger, setLarger] = useState(false),
    [role, setRole] = useState<User["role"]>("citizen"),
    [handle, setHandle] = useState(""),
    [adminAccess, setAdminAccess] = useState(""),
    [challenge, setChallenge] = useState<{
      challenge_id: string;
      development_code: string;
    } | null>(null),
    [code, setCode] = useState(""),
    [name, setName] = useState(""),
    [authorized, setAuthorized] = useState(false),
    [agree, setAgree] = useState(false),
    [category, setCategory] = useState("age_proof"),
    [demoCase, setDemoCase] = useState("A"),
    [filter, setFilter] = useState("all"),
    [query, setQuery] = useState(""),
    [searchResults, setSearchResults] = useState<
      { id: string; text: string }[]
    >([]),
    [metrics, setMetrics] = useState<Record<string, unknown> | null>(null),
    [preview, setPreview] = useState<Doc | null>(null),
    [mobileMenu, setMobileMenu] = useState(false);
  const t = useCallback((key: string) => text(lang, key), [lang]);
  useEffect(() => {
    if (!preview) return;
    const previous = document.activeElement as HTMLElement | null;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPreview(null);
      if (event.key !== "Tab") return;
      const elements = document
        .querySelector(".preview-modal")
        ?.querySelectorAll<HTMLElement>(
          'button, a[href], input, iframe, [tabindex="0"]',
        );
      if (!elements?.length) return;
      const first = elements[0],
        last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [preview]);
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const go = (p: Page) => {
    setPage(p);
    setError("");
    setMessage("");
    setMobileMenu(false);
    window.scrollTo(0, 0);
  };
  const loadProfiles = async () => {
    setProfiles(await api<Profile[]>("/profiles"));
  };
  const refresh = useCallback(async (id: string) => {
    const [d, f, c] = await Promise.all([
      api<Doc[]>(`/profiles/${id}/documents`),
      api<Fact[]>(`/profiles/${id}/facts`),
      api<{ accepted: boolean }>(`/profiles/${id}/consent`),
    ]);
    setDocs(d);
    setFacts(f);
    setConsented(c.accepted);
  }, []);
  useEffect(() => {
    const saved = localStorage.getItem("formflow-language") as Lang | null;
    if (saved === "en" || saved === "kn") setLang(saved);
    api<User>("/auth/me")
      .then((u) => {
        setUser(u);
        setPage(u.role === "admin" ? "admin" : "profiles");
      })
      .catch(() => {});
    api<Scheme[]>("/schemes")
      .then(setRegistry)
      .catch(() => {});
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("formflow-language", lang);
  }, [lang]);
  useEffect(() => {
    if (user && page === "profiles")
      api<Profile[]>("/profiles")
        .then(setProfiles)
        .catch((e) => setError(e.message));
    if (page === "schemes")
      api<ResearchScheme[]>("/research/schemes")
        .then(setResearchSchemes)
        .catch((e) => setError(e.message));
    if (user && page === "admin")
      api<Overview>("/admin/overview")
        .then(setOverview)
        .catch((e) => setError(e.message));
    if (user?.role === "admin" && page === "admin")
      api<ResearchStatus>("/admin/research")
        .then(setResearchStatus)
        .catch((e) => setError(e.message));
    if (profile && page === "history")
      api<Assessment[]>(`/profiles/${profile.id}/evaluations`)
        .then(setHistory)
        .catch((e) => setError(e.message));
  }, [user, page, profile]);
  useEffect(() => {
    if (!profile || !["documents", "review"].includes(page)) return;
    refresh(profile.id).catch((e) => setError(e.message));
    const timer = setInterval(() => refresh(profile.id).catch(() => {}), 2500);
    return () => clearInterval(timer);
  }, [profile, page, refresh]);
  const choose = async (p: Profile) => {
    setProfile(p);
    if (/^Fictional profile [ABC]$/.test(p.name)) setDemoCase(p.name.slice(-1));
    setAssessment(null);
    const c = await api<{ accepted: boolean }>(`/profiles/${p.id}/consent`);
    setConsented(c.accepted);
    setAgree(false);
    await refresh(p.id);
    go(c.accepted ? "documents" : "consent");
  };
  const create = async (label: string, fictionalCase?: string) => {
    const p = await api<Profile>("/profiles", "POST", {
      name: label,
      language: lang,
      authorized:
        role === "caregiver" || user?.role === "caregiver" ? authorized : false,
    });
    if (fictionalCase) setDemoCase(fictionalCase);
    await loadProfiles();
    await choose(p);
  };
  const uploadFiles = async (files: File[]) => {
    if (!profile) return;
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      await api(
        `/profiles/${profile.id}/documents?category=${category}`,
        "POST",
        form,
      );
    }
    await refresh(profile.id);
  };
  const loadFixtures = async () => {
    if (!profile) return;
    for (const type of demoCase === "B"
      ? ["age_proof", "residence"]
      : ["age_proof", "residence", "income"]) {
      const response = await fetch(`/api/v1/demo/document/${demoCase}/${type}`);
      if (!response.ok) throw new Error("Fixture download failed");
      const form = new FormData();
      form.append(
        "file",
        await response.blob(),
        `FICTIONAL-${demoCase}-${type}.pdf`,
      );
      await api(
        `/profiles/${profile.id}/documents?category=${type}`,
        "POST",
        form,
      );
    }
    await refresh(profile.id);
  };
  const reviewFact = async (f: Fact, action: string, value?: string) => {
    await api(`/facts/${f.id}/review`, "POST", {
      action,
      ...(value !== undefined ? { value } : {}),
    });
    if (profile) await refresh(profile.id);
  };
  const assess = async () => {
    if (!profile) return;
    const result = await api<Assessment>(
      `/profiles/${profile.id}/evaluations`,
      "POST",
    );
    setAssessment(result);
    setFilter("all");
    go("results");
  };
  const localRead = () => {
    const voices = window.speechSynthesis
      ?.getVoices()
      .filter(
        (v) =>
          v.localService &&
          v.lang.toLowerCase().startsWith(lang === "kn" ? "kn" : "en"),
      );
    if (!voices?.length) {
      setMessage(t("noVoice"));
      return;
    }
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(
      document.querySelector("main")?.innerText.slice(0, 5000) || "",
    );
    utterance.voice = voices[0];
    utterance.lang = voices[0].lang;
    speechSynthesis.speak(utterance);
  };
  const status = (v: string) =>
    t(
      v === "LIKELY_ELIGIBLE"
        ? "likely"
        : v === "NEEDS_EVIDENCE"
          ? "needs"
          : "notEligible",
    );
  const badgeClass = (v: string) =>
    v === "LIKELY_ELIGIBLE"
      ? "success"
      : v === "NEEDS_EVIDENCE"
        ? "warning"
        : "neutral";
  const activeStep = { consent: 0, documents: 1, review: 2, results: 3 }[
    page as "consent" | "documents" | "review" | "results"
  ];
  return (
    <div
      className={`${contrast ? "high-contrast " : ""}${larger ? "large-text" : ""}`}
    >
      <a className="skip" href="#main">
        {t("next")}
      </a>
      <div className="topline">
        <span>
          <span className="live-dot" />
          {t("demo")}
        </span>
        <span>
          {t("bilingual")}
          <span className="top-separator"> / </span>
          {t("private")}
        </span>
      </div>
      <header>
        <button
          className="brand"
          onClick={() => go("home")}
          aria-label="FormFlow home"
        >
          <span className="brand-mark">
            <Leaf size={25} />
          </span>
          <span>
            FormFlow<span className="ai"> AI</span>
          </span>
        </button>
        <nav
          aria-label="Main navigation"
          className={mobileMenu ? "mobile-open" : ""}
        >
          <button
            onClick={() => go("schemes")}
            className={page === "schemes" ? "active" : ""}
          >
            {t("schemes")}
          </button>
          <button
            onClick={() => {
              go("home");
              setTimeout(
                () =>
                  document
                    .getElementById("how")
                    ?.scrollIntoView({ behavior: "smooth" }),
                100,
              );
            }}
          >
            {t("how")}
          </button>
          <button onClick={() => go("privacy")}>{t("privacy")}</button>
          {user && (
            <button
              onClick={() => go(user.role === "admin" ? "admin" : "profiles")}
            >
              {t(user.role === "admin" ? "adminAccess" : "profiles")}
            </button>
          )}
        </nav>
        <div className="header-actions">
          <button
            className="language"
            aria-label={t("language")}
            onClick={() => {
              setLang(lang === "en" ? "kn" : "en");
              setResearchAnswer(null);
            }}
          >
            {lang === "en" ? "ಕನ್ನಡ" : "English"}
            <span>↔</span>
          </button>
          {user ? (
            <button
              className="small-link signout"
              onClick={() =>
                run(async () => {
                  await api("/auth/logout", "POST");
                  setUser(null);
                  setProfile(null);
                  setChallenge(null);
                  go("home");
                })
              }
            >
              {t("signOut")}
            </button>
          ) : (
            <button
              className="btn small header-cta"
              onClick={() => {
                setRole("citizen");
                go("login");
              }}
            >
              {t("find")}
              <ArrowUpRight size={16} />
            </button>
          )}
          <button
            className="icon-btn hamburger"
            aria-label="Menu"
            onClick={() => setMobileMenu(!mobileMenu)}
          >
            <Menu />
          </button>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {error && (
          <div className="alert error" role="alert">
            <strong>{t("error")}</strong>
            <p>{error}</p>
            <button
              className="icon-btn"
              aria-label={t("close")}
              onClick={() => setError("")}
            >
              <X size={18} />
            </button>
          </div>
        )}
        {message && (
          <div className="alert" role="status">
            {message}
          </div>
        )}
        {busy && (
          <div className="busy" role="status">
            {t("loading")}
          </div>
        )}
        {page === "home" && (
          <>
            <section className="hero">
              <div className="hero-copy">
                <div className="eyebrow">
                  <span className="little-line" />
                  {t("region")}
                </div>
                <h1>
                  {t("hero")
                    .split("\n")
                    .map((line, i) => (
                      <span
                        key={line}
                        className={i === 1 ? "serif accent" : ""}
                      >
                        {line}
                        <br />
                      </span>
                    ))}
                </h1>
                <p className="hero-intro">{t("intro")}</p>
                <div className="hero-actions">
                  <button
                    className="btn"
                    onClick={() => {
                      setRole("citizen");
                      go(user ? "profiles" : "login");
                    }}
                  >
                    {t("find")}
                    <ArrowRight size={20} />
                  </button>
                  <button
                    className="text-action"
                    onClick={() => {
                      setRole("caregiver");
                      go(user ? "profiles" : "login");
                    }}
                  >
                    <Users size={19} />
                    {t("caregiver")}
                    <ChevronRight size={17} />
                  </button>
                </div>
                <p className="privacy-promise">
                  <LockKeyhole size={14} />
                  {t("private")}
                </p>
              </div>
              <div className="hero-art" aria-label={t("guidance")}>
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <span className="art-label">
                  <Sparkles size={15} /> {t("guidance")}
                </span>
                <div className="art-file back-file">
                  <div className="file-top">
                    <FileText size={25} />
                    <span className="tag">{t("demoOnly")}</span>
                  </div>
                  <div className="file-rule" />
                  <div className="file-rule short" />
                  <div className="file-rule" />
                  <div className="file-rule medium" />
                </div>
                <div className="art-file front-file">
                  <div className="file-top">
                    <span className="file-icon">
                      <ClipboardCheck size={24} />
                    </span>
                    <span className="tag light">{t("flow4")}</span>
                  </div>
                  <h3>{t("step3")}</h3>
                  <p>{t("step3d")}</p>
                  <div className="art-check">
                    <CheckCircle2 size={17} />
                    {t("evidence")}
                  </div>
                  <div className="art-check">
                    <CheckCircle2 size={17} />
                    {t("checklist")}
                  </div>
                  <div className="file-bottom">
                    <span>{t("fictional").split(".")[0]}</span>
                    <ArrowUpRight size={19} />
                  </div>
                </div>
                <div className="floating-shield">
                  <ShieldCheck size={25} />
                  <div>
                    <strong>{t("private")}</strong>
                    <span>{t("demo")}</span>
                  </div>
                </div>
                <div className="leaf-drawing">
                  <Leaf size={88} strokeWidth={0.8} />
                </div>
                <span className="art-dot dot-one" />
                <span className="art-dot dot-two" />
              </div>
            </section>
            <div className="trust-strip">
              <span>
                <ShieldCheck />
                {t("private")}
              </span>
              <span>
                <FileCheck2 />
                {t("guidance")}
              </span>
              <span>
                <HeartHandshake />
                {t("bilingual")}
              </span>
            </div>
            <section className="how-section" id="how">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">01 / {t("how")}</p>
                  <h2>{t("begin")}</h2>
                </div>
                <p>{t("guidanceText")}</p>
              </div>
              <div className="steps">
                {[
                  { icon: Users, title: "step1", desc: "step1d" },
                  { icon: Upload, title: "step2", desc: "step2d" },
                  { icon: ClipboardCheck, title: "step3", desc: "step3d" },
                ].map((s, i) => (
                  <article key={s.title}>
                    <div className="step-head">
                      <s.icon size={26} strokeWidth={1.5} />
                      <span>0{i + 1}</span>
                    </div>
                    <h3>{t(s.title)}</h3>
                    <p>{t(s.desc)}</p>
                  </article>
                ))}
              </div>
            </section>
            <section className="demo-note">
              <div className="note-icon">
                <Leaf size={30} />
              </div>
              <div>
                <p className="eyebrow">{t("demo")}</p>
                <h3>{t("fictional")}</h3>
                <p>{t("disclaimer")}</p>
              </div>
              <button className="text-action" onClick={() => go("schemes")}>
                {t("schemes")}
                <ArrowUpRight size={19} />
              </button>
            </section>
          </>
        )}
        {page === "login" && (
          <section className="narrow section-pad">
            <p className="eyebrow">{t("demo")}</p>
            <h1 className="page-title">{t("begin")}</h1>
            <p className="muted">{t("beginText")}</p>
            <form
              className="panel form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                run(async () => {
                  if (!challenge) {
                    setChallenge(
                      await api("/auth/request-otp", "POST", {
                        handle,
                        role,
                        admin_access: adminAccess,
                      }),
                    );
                  } else {
                    const u = await api<User>("/auth/verify-otp", "POST", {
                      challenge_id: challenge.challenge_id,
                      code,
                    });
                    setUser(u);
                    setChallenge(null);
                    go(u.role === "admin" ? "admin" : "profiles");
                  }
                });
              }}
            >
              {!challenge ? (
                <>
                  <label>
                    {t("username")}
                    <input
                      required
                      minLength={3}
                      pattern="[a-zA-Z0-9_.@-]+"
                      autoComplete="username"
                      value={handle}
                      onChange={(e) => setHandle(e.target.value)}
                    />
                  </label>
                  <label>
                    {t("role")}
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value as User["role"])}
                    >
                      <option value="citizen">{t("citizen")}</option>
                      <option value="caregiver">{t("careRole")}</option>
                      <option value="admin">{t("administrator")}</option>
                    </select>
                  </label>
                  {role === "admin" && (
                    <label>
                      {t("adminKey")}
                      <input
                        type="password"
                        value={adminAccess}
                        onChange={(e) => setAdminAccess(e.target.value)}
                        required
                      />
                      <small>{t("adminHint")}</small>
                    </label>
                  )}
                </>
              ) : (
                <>
                  <div className="local-code">
                    <strong>{t("devChannel")}</strong>
                    <code data-testid="development-code">
                      {challenge.development_code}
                    </code>
                  </div>
                  <label>
                    {t("code")}
                    <input
                      required
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                    />
                  </label>
                </>
              )}
              <button className="btn" disabled={busy}>
                {t(challenge ? "signIn" : "requestCode")}
                <ArrowRight size={18} />
              </button>
            </form>
          </section>
        )}
        {user && page !== "home" && page !== "login" && page !== "schemes" && (
          <div className="workspace-bar">
            <span>
              <span className="live-dot" />
              {t("workspace")}
              <span className="bar-divider">/</span>
              {t(
                user.role === "caregiver"
                  ? "careRole"
                  : user.role === "admin"
                    ? "administrator"
                    : "citizen",
              )}
            </span>
            {profile && user.role !== "admin" && (
              <>
                <button onClick={() => go("profiles")}>
                  {profile.name}
                  <ChevronRight size={15} />
                </button>
                <div className="workspace-links">
                  <button onClick={() => go("history")}>{t("history")}</button>
                  <button onClick={() => go("privacy")}>{t("privacy")}</button>
                </div>
              </>
            )}
          </div>
        )}
        {activeStep !== undefined && profile && (
          <ol className="progress">
            {["flow1", "flow2", "flow3", "flow4"].map((s, i) => (
              <li
                className={
                  i === activeStep
                    ? "current"
                    : i < activeStep
                      ? "complete"
                      : ""
                }
                key={s}
              >
                <button
                  onClick={() =>
                    go(
                      (["consent", "documents", "review", "results"] as Page[])[
                        i
                      ],
                    )
                  }
                >
                  <span>{i < activeStep ? <Check size={14} /> : i + 1}</span>
                  {t(s)}
                </button>
              </li>
            ))}
          </ol>
        )}
        {page === "profiles" && user && (
          <section className="content section-pad">
            <p className="eyebrow">{t("workspace")}</p>
            <h1 className="page-title">{t("welcome")}</h1>
            <p className="muted">{t("choose")}</p>
            <div className="profile-grid">
              {profiles.map((p) => (
                <button
                  className="profile-card"
                  key={p.id}
                  onClick={() => run(() => choose(p))}
                >
                  <span className="avatar">
                    <Users />
                  </span>
                  <strong>{p.name}</strong>
                  <span className="tag">{t("demoOnly")}</span>
                  <ArrowRight size={19} />
                </button>
              ))}
            </div>
            <div className="split-panels">
              <form
                className="panel form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(() => create(name));
                }}
              >
                <h2>{t("createProfile")}</h2>
                <label>
                  {t("profileName")}
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    maxLength={80}
                  />
                </label>
                {user.role === "caregiver" && (
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={authorized}
                      onChange={(e) => setAuthorized(e.target.checked)}
                    />
                    {t("authorization")}
                  </label>
                )}
                <button
                  disabled={busy || (user.role === "caregiver" && !authorized)}
                  className="btn"
                >
                  {t("create")}
                  <Plus size={18} />
                </button>
              </form>
              <div className="panel sample-panel">
                <p className="eyebrow">{t("demo")}</p>
                <h2>{t("samples")}</h2>
                <p>{t("sampleHint")}</p>
                {["A", "B", "C"].map((c) => (
                  <button
                    className="sample-button"
                    key={c}
                    disabled={
                      busy || (user.role === "caregiver" && !authorized)
                    }
                    onClick={() =>
                      run(() => create(`Fictional profile ${c}`, c))
                    }
                  >
                    <span>{t("sample" + c)}</span>
                    <ArrowRight size={18} />
                  </button>
                ))}
              </div>
            </div>
          </section>
        )}
        {page === "consent" && profile && (
          <section className="narrow section-pad">
            <ShieldCheck size={38} className="accent" />
            <h1 className="page-title">{t("consent")}</h1>
            <div className="panel consent-panel">
              <p>{t("consentText")}</p>
              <small>{t("version")}: 2026-11-v1</small>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={agree}
                  onChange={(e) => setAgree(e.target.checked)}
                />
                {t("agree")}
              </label>
              <button
                className="btn"
                disabled={!agree || busy}
                onClick={() =>
                  run(async () => {
                    await api(`/profiles/${profile.id}/consent`, "POST", {
                      accepted: true,
                      notice_version: "2026-11-v1",
                    });
                    setConsented(true);
                    go("documents");
                  })
                }
              >
                {t("consentButton")}
                <ArrowRight size={18} />
              </button>
            </div>
          </section>
        )}
        {page === "documents" && profile && (
          <section className="content section-pad">
            <div className="section-heading">
              <div>
                <p className="eyebrow">02 / {t("flow2")}</p>
                <h1 className="page-title">{t("documents")}</h1>
                <p className="muted">{t("uploadHint")}</p>
              </div>
            </div>
            {!consented ? (
              <button className="btn" onClick={() => go("consent")}>
                {t("consent")}
              </button>
            ) : (
              <>
                <div className="upload-grid">
                  <div className="upload-zone">
                    <Upload size={35} strokeWidth={1.5} />
                    <label className="category-label">
                      {t("category")}
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                      >
                        {[
                          "age_proof",
                          "income",
                          "residence",
                          "identity",
                          "disability",
                          "pension",
                          "other",
                        ].map((c) => (
                          <option key={c} value={c}>
                            {t(c)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="btn upload-button">
                      {t("upload")}
                      <input
                        type="file"
                        multiple
                        accept="application/pdf,image/jpeg,image/png"
                        disabled={busy}
                        onChange={(e) => {
                          const fs = Array.from(e.target.files || []);
                          run(() => uploadFiles(fs));
                          e.target.value = "";
                        }}
                      />
                    </label>
                    <label className="text-action camera-input">
                      {t("camera")}
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        onChange={(e) => {
                          run(() =>
                            uploadFiles(Array.from(e.target.files || [])),
                          );
                          e.target.value = "";
                        }}
                      />
                    </label>
                    <p>{t("retake")}</p>
                  </div>
                  <aside className="panel fixture-panel">
                    <span className="tag">{t("demo")}</span>
                    <h2>{t("fixtures")}</h2>
                    <p>{t("fixtureHint")}</p>
                    <select
                      aria-label={t("samples")}
                      value={demoCase}
                      onChange={(e) => setDemoCase(e.target.value)}
                    >
                      {["A", "B", "C"].map((c) => (
                        <option value={c} key={c}>
                          {t("sample" + c)}
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn secondary"
                      disabled={busy}
                      onClick={() => run(loadFixtures)}
                    >
                      {t("fixtures")}
                      <Plus size={17} />
                    </button>
                    <a
                      href="/api/v1/demo/document/A/age_proof?format=png&language=en"
                      download
                    >
                      {t("englishScan")}
                      <ArrowUpRight size={14} />
                    </a>
                    <a
                      href="/api/v1/demo/document/A/age_proof?format=png&language=kn"
                      download
                    >
                      {t("kannadaScan")}
                      <ArrowUpRight size={14} />
                    </a>
                  </aside>
                </div>
                <div className="document-list">
                  {docs.map((d, i) => (
                    <article className="document-row" key={d.id}>
                      <span className="doc-icon">
                        <FileText />
                      </span>
                      <div>
                        <strong>
                          {t(d.category)} <span className="muted">{i + 1}</span>
                        </strong>
                        <span
                          className={
                            "document-status " +
                            (d.status === "ready" ? "success-text" : "")
                          }
                        >
                          {t(
                            d.status === "ready"
                              ? "ready"
                              : d.status === "failed"
                                ? "failed"
                                : d.status === "processing"
                                  ? "processing"
                                  : "queued",
                          )}
                        </span>
                        {d.error && <p className="error-text">{d.error}</p>}
                        {d.quality.pages
                          ?.flatMap((p) => p.warnings)
                          .map((w, i) => (
                            <p className="error-text" key={i}>
                              {w} · {t("retake")}
                            </p>
                          ))}
                      </div>
                      <button
                        className="small-link"
                        onClick={() => setPreview(d)}
                      >
                        {t("preview")}
                      </button>
                      <button
                        className="small-link danger-text"
                        onClick={() =>
                          run(async () => {
                            await api(`/documents/${d.id}`, "DELETE");
                            await refresh(profile.id);
                          })
                        }
                      >
                        {t("replace")}
                      </button>
                    </article>
                  ))}
                </div>
                <div className="action-footer">
                  <span className="muted">
                    <LockKeyhole size={15} />
                    {t("private")}
                  </span>
                  <button
                    className="btn"
                    disabled={
                      busy ||
                      docs.some((d) =>
                        ["queued", "processing"].includes(d.status),
                      )
                    }
                    onClick={() => go("review")}
                  >
                    {t("flow3")}
                    <ArrowRight size={18} />
                  </button>
                </div>
              </>
            )}
          </section>
        )}
        {page === "review" && profile && (
          <section className="content section-pad">
            <p className="eyebrow">03 / {t("flow3")}</p>
            <h1 className="page-title">{t("review")}</h1>
            <p className="muted max-width">{t("reviewHint")}</p>
            <div className="review-toolbar">
              <button
                className="btn secondary"
                disabled={
                  busy || !facts.some((f) => f.review === "unconfirmed")
                }
                onClick={() =>
                  run(async () => {
                    for (const f of facts.filter(
                      (f) =>
                        f.review === "unconfirmed" && f.value === f.original,
                    ))
                      await api(`/facts/${f.id}/review`, "POST", {
                        action: "confirmed",
                      });
                    await refresh(profile.id);
                  })
                }
              >
                {t("confirmAll")}
                <Check size={17} />
              </button>
            </div>
            {facts
              .filter((f) => f.review !== "removed")
              .map((f) => (
                <FactCard
                  key={f.id}
                  fact={f}
                  t={t}
                  busy={busy}
                  onReview={(action, value) =>
                    run(() => reviewFact(f, action, value))
                  }
                  onPreview={() =>
                    setPreview(docs.find((d) => d.id === f.document_id) || null)
                  }
                />
              ))}
            {!facts.length && <div className="empty panel">{t("noFacts")}</div>}
            <div className="action-footer">
              <button className="text-action" onClick={() => go("documents")}>
                {t("back")}
              </button>
              <button
                className="btn"
                disabled={busy}
                onClick={() => run(assess)}
              >
                {t("evaluate")}
                <ArrowRight size={18} />
              </button>
            </div>
          </section>
        )}
        {page === "results" && profile && (
          <section className="content section-pad">
            <div className="section-heading">
              <div>
                <p className="eyebrow">04 / {t("flow4")}</p>
                <h1 className="page-title">{t("results")}</h1>
                <p className="muted max-width">{t("resultsHint")}</p>
              </div>
              {assessment && (
                <a
                  className="btn secondary"
                  href={`/api/v1/evaluations/${assessment.id}/report?language=${lang}`}
                  download
                >
                  {t("export")}
                  <ArrowUpRight size={18} />
                </a>
              )}
            </div>
            <div className="notice">
              <ShieldCheck size={19} />
              {t("fictional")}
            </div>
            {assessment?.rules_changed && (
              <div className="alert">{t("oldRules")}</div>
            )}
            {assessment ? (
              <>
                <div className="filter-row">
                  <label>
                    {t("all")}
                    <select
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    >
                      <option value="all">{t("all")}</option>
                      {[
                        "LIKELY_ELIGIBLE",
                        "NEEDS_EVIDENCE",
                        "NOT_ELIGIBLE",
                      ].map((v) => (
                        <option value={v} key={v}>
                          {status(v)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <small>
                    {t("assessed")}{" "}
                    {new Date(assessment.created_at).toLocaleDateString(
                      lang === "kn" ? "kn-IN" : "en-IN",
                    )}
                  </small>
                </div>
                {assessment.results
                  .filter((r) => filter === "all" || r.verdict === filter)
                  .map((r) => (
                    <ResultCard
                      key={r.scheme_id}
                      result={r}
                      lang={lang}
                      t={t}
                      status={status}
                      badgeClass={badgeClass}
                      onEvidence={(id) =>
                        setPreview(docs.find((d) => d.id === id) || null)
                      }
                    />
                  ))}
                <p className="muted">{t("registryText")}</p>
                <button className="text-action" onClick={() => go("schemes")}>
                  {t("schemes")}
                  <ArrowRight size={18} />
                </button>
              </>
            ) : (
              <div className="panel empty">
                <p>{t("noResults")}</p>
                <button className="btn" onClick={() => run(assess)}>
                  {t("evaluate")}
                </button>
              </div>
            )}
          </section>
        )}
        {page === "history" && profile && (
          <section className="content section-pad">
            <h1 className="page-title">{t("history")}</h1>
            {history.length ? (
              history.map((a) => (
                <article className="panel history-row" key={a.id}>
                  <div>
                    <strong>
                      {new Date(a.created_at).toLocaleString(
                        lang === "kn" ? "kn-IN" : "en-IN",
                      )}
                    </strong>
                    <p>{a.results.map((r) => status(r.verdict)).join(" · ")}</p>
                    {a.rules_changed && (
                      <p className="error-text">{t("oldRules")}</p>
                    )}
                  </div>
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setAssessment(a);
                      go("results");
                    }}
                  >
                    {t("view")}
                    <ArrowRight size={18} />
                  </button>
                </article>
              ))
            ) : (
              <p>{t("emptyHistory")}</p>
            )}
          </section>
        )}
        {page === "privacy" && (
          <section className="narrow section-pad">
            <LockKeyhole size={36} />
            <h1 className="page-title">{t("data")}</h1>
            <div className="panel form-stack">
              <p>{t("dataText")}</p>
              <p>{t("consentText")}</p>
              {profile && (
                <>
                  <strong>{profile.name}</strong>
                  <p>
                    {t("consentState")}: {t(consented ? "yes" : "no")}
                  </p>
                  <button
                    className="btn secondary"
                    disabled={!consented || busy}
                    onClick={() =>
                      run(async () => {
                        await api(
                          `/profiles/${profile.id}/consent/revoke`,
                          "POST",
                        );
                        setConsented(false);
                        setMessage(t("done"));
                      })
                    }
                  >
                    {t("revoke")}
                  </button>
                  <button
                    className="btn danger"
                    disabled={busy}
                    onClick={() => {
                      if (window.confirm(t("deleteConfirm")))
                        run(async () => {
                          await api(`/profiles/${profile.id}`, "DELETE");
                          setProfile(null);
                          setDocs([]);
                          setFacts([]);
                          setAssessment(null);
                          go("profiles");
                        });
                    }}
                  >
                    {t("deleteProfile")}
                  </button>
                </>
              )}
            </div>
          </section>
        )}
        {page === "schemes" && (
          <section className="content section-pad">
            <p className="eyebrow">{t("region")}</p>
            <h1 className="page-title">{t("registry")}</h1>
            <p className="muted max-width">{t("registryText")}</p>
            <div className="research-intro">
              <span className="tag">
                {lang === "kn" ? "ಸರ್ಕಾರಿ ಮೂಲಗಳು" : "OFFICIAL SOURCE RESEARCH"}
              </span>
              <h2>
                {lang === "kn"
                  ? "ಪಿಂಚಣಿ ಯೋಜನೆಗಳ ಮಾಹಿತಿ"
                  : "Explore source linked pension guidance"}
              </h2>
              <p>
                {lang === "kn"
                  ? "ನಿಯಮಗಳು ಸ್ವತಂತ್ರ ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿವೆ. ವೈಯಕ್ತಿಕ ಅರ್ಹತಾ ನಿರ್ಧಾರ ಲಭ್ಯವಿಲ್ಲ."
                  : "These government pages are archived and linked below. Rule versions and government orders still need independent review before personal eligibility assessment."}
              </p>
            </div>
            <div className="registry-grid">
              {researchSchemes.map((s) => (
                <article
                  className="panel registry-card research-card"
                  key={s.id}
                >
                  <span className="tag light">
                    {lang === "kn" ? "ಪರಿಶೀಲನೆ ಬಾಕಿ" : "Rule review pending"}
                  </span>
                  <h2>{lang === "kn" ? s.name_kn : s.name}</h2>
                  <details>
                    <summary>
                      {lang === "kn"
                        ? "ಅರ್ಹತೆ ಮತ್ತು ಹೊರತಾಗಿರುವವರು"
                        : "Eligibility and exceptions"}
                    </summary>
                    <ul>
                      {[...s.eligibility, ...s.exceptions].map((f, i) => (
                        <li key={i}>
                          {lang === "kn" ? f.value_kn || f.value : f.value}
                        </li>
                      ))}
                    </ul>
                  </details>
                  <details>
                    <summary>
                      {lang === "kn"
                        ? "ಪ್ರಯೋಜನ ಮತ್ತು ಅರ್ಜಿ"
                        : "Benefits and application"}
                    </summary>
                    <ul>
                      {[...s.benefits, ...s.application].map((f, i) => (
                        <li key={i}>
                          {lang === "kn" ? f.value_kn || f.value : f.value}
                        </li>
                      ))}
                    </ul>
                  </details>
                  <details>
                    <summary>
                      {lang === "kn"
                        ? "ಅರ್ಜಿಗೆ ಬೇಕಾದ ದಾಖಲೆಗಳು"
                        : "Application documents"}
                    </summary>
                    <ul>
                      {s.application_documents.map((f, i) => (
                        <li key={i}>
                          {lang === "kn" ? f.value_kn || f.value : f.value}
                        </li>
                      ))}
                    </ul>
                  </details>
                  <p className="review-note">
                    {lang === "kn"
                      ? "ಸರ್ಕಾರಿ ಆದೇಶಗಳು ಮತ್ತು ಅರ್ಹತಾ ನಿಯಮಗಳ ಸ್ವತಂತ್ರ ಪರಿಶೀಲನೆ ಬಾಕಿ ಇದೆ."
                      : `${s.review_status}. ${s.unresolved.join(" ")}`}
                  </p>
                  <a
                    className="text-action"
                    href={s.primary_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {lang === "kn" ? "ಅಧಿಕೃತ ಮೂಲ" : "Read official page"}{" "}
                    <ArrowUpRight size={17} />
                  </a>
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setResearchScheme(s.id);
                      setResearchAnswer(null);
                      setResearchQuestion(
                        lang === "kn"
                          ? `${s.name_kn} ಅರ್ಹತೆ ಏನು?`
                          : `What are the eligibility conditions for ${s.name}?`,
                      );
                      document.getElementById("research-question")?.focus();
                    }}
                  >
                    {lang === "kn"
                      ? "ಈ ಯೋಜನೆಯ ಬಗ್ಗೆ ಕೇಳಿ"
                      : "Ask about this scheme"}
                  </button>
                </article>
              ))}
            </div>
            <form
              className="panel form-stack research-ask"
              onSubmit={(e) => {
                e.preventDefault();
                run(async () =>
                  setResearchAnswer(
                    await api<ResearchAnswer>(
                      `/research/ask?q=${encodeURIComponent(researchQuestion)}${researchScheme ? `&scheme_id=${encodeURIComponent(researchScheme)}` : ""}`,
                    ),
                  ),
                );
              }}
            >
              <h2>
                {lang === "kn"
                  ? "ಮೂಲಗಳ ಆಧಾರದ ಮೇಲೆ ಪ್ರಶ್ನೆ ಕೇಳಿ"
                  : "Ask a question about official sources"}
              </h2>
              <label htmlFor="research-scheme">
                {lang === "kn" ? "ಯೋಜನೆ" : "Scheme"}
              </label>
              <select
                id="research-scheme"
                value={researchScheme}
                onChange={(e) => {
                  setResearchScheme(e.target.value);
                  setResearchAnswer(null);
                }}
              >
                <option value="">
                  {lang === "kn" ? "ಎಲ್ಲಾ ಯೋಜನೆಗಳು" : "All schemes"}
                </option>
                {researchSchemes.map((s) => (
                  <option value={s.id} key={s.id}>
                    {lang === "kn" ? s.name_kn : s.name}
                  </option>
                ))}
              </select>
              <label htmlFor="research-question">
                {lang === "kn" ? "ನಿಮ್ಮ ಪ್ರಶ್ನೆ" : "Your question"}
              </label>
              <input
                id="research-question"
                value={researchQuestion}
                onChange={(e) => {
                  setResearchQuestion(e.target.value);
                  setResearchAnswer(null);
                }}
                minLength={3}
                maxLength={500}
                required
                placeholder={
                  lang === "kn"
                    ? "ವಯಸ್ಸಿನ ಅರ್ಹತೆ ಏನು?"
                    : "What is the age requirement?"
                }
              />
              <button className="btn" disabled={busy}>
                {busy
                  ? lang === "kn"
                    ? "ಹುಡುಕುತ್ತಿದೆ…"
                    : "Searching…"
                  : lang === "kn"
                    ? "ಉತ್ತರ ಹುಡುಕಿ"
                    : "Find answer"}
              </button>
              {researchAnswer && (
                <div className="answer-panel" aria-live="polite">
                  <strong>
                    {lang === "kn" ? "ಮೂಲದ ಮಾಹಿತಿ" : "Source linked guidance"}
                  </strong>
                  <p>{researchAnswer.answer}</p>
                  <small>
                    {lang === "kn"
                      ? "ಮೂಲ ಉಲ್ಲೇಖಗಳನ್ನು ಪರಿಶೀಲಿಸಿ; ವೈಯಕ್ತಿಕ ಅರ್ಹತಾ ನಿರ್ಧಾರವಲ್ಲ."
                      : researchAnswer.model_status}
                  </small>
                  {researchAnswer.citations.map((c) => (
                    <blockquote key={c.id}>
                      <a href={c.url} target="_blank" rel="noreferrer">
                        {c.section}
                        {c.page ? ` · page ${c.page}` : ""} · {c.source_version}{" "}
                        <ArrowUpRight size={13} />
                      </a>
                      <p lang="kn">{c.text}</p>
                    </blockquote>
                  ))}
                </div>
              )}
            </form>
            <h2 className="demo-list-title">
              {lang === "kn"
                ? "ಕಾಲ್ಪನಿಕ ಮೌಲ್ಯಮಾಪನ ಮಾದರಿಗಳು"
                : "Fictional assessment examples"}
            </h2>
            <div className="registry-grid">
              {registry
                .filter((s) => s.mode === "DEMO")
                .map((s) => (
                  <article className="panel registry-card" key={s.id}>
                    <span
                      className={"tag " + (s.mode === "DEMO" ? "light" : "")}
                    >
                      {s.mode === "DEMO" ? t("demoOnly") : t("unavailable")}
                    </span>
                    <h2>{lang === "kn" ? s.name_kn : s.name}</h2>
                    <p>{lang === "kn" ? t("registryText") : s.description}</p>
                    <small>
                      {s.department} · {s.category}
                    </small>
                    {s.source_url && (
                      <a
                        className="text-action"
                        href={s.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t("official")}
                        <ArrowUpRight size={17} />
                      </a>
                    )}
                  </article>
                ))}
            </div>
            <form
              className="panel form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                run(async () =>
                  setSearchResults(
                    await api(`/search?q=${encodeURIComponent(query)}`),
                  ),
                );
              }}
            >
              <h2>{t("search")}</h2>
              <label>
                {t("search")}
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("searchPlaceholder")}
                />
              </label>
              <button className="btn">{t("search")}</button>
              {searchResults.map((c) => (
                <blockquote key={c.id}>
                  <strong>{c.id}</strong>
                  <p>{c.text}</p>
                </blockquote>
              ))}
            </form>
          </section>
        )}
        {page === "admin" && user?.role === "admin" && (
          <section className="content section-pad">
            <p className="eyebrow">{t("adminAccess")}</p>
            <h1 className="page-title">{t("adminTitle")}</h1>
            <p className="muted max-width">{t("adminText")}</p>
            <details className="panel research-admin" open>
              <summary>
                Official research corpus ·{" "}
                {researchStatus?.sources.filter((s) => s.status === "fetched")
                  .length ?? 0}{" "}
                fetched / {researchStatus?.sources.length ?? 0} sources
              </summary>
              <p>
                Passages: {researchStatus?.passage_count ?? 0}. Dense model:{" "}
                {researchStatus?.dense_model || "not configured"}. Reranker:{" "}
                {researchStatus?.reranker_model || "not configured"}.
              </p>
              {researchStatus?.model_error && (
                <p className="error-text">{researchStatus.model_error}</p>
              )}
              {researchStatus?.sources.map((source) => (
                <div className="source-row" key={source.id}>
                  <strong>{source.title}</strong>
                  <p>
                    {source.status} · retrieved{" "}
                    {new Date(source.retrieved_at).toLocaleString()} · version{" "}
                    {source.content_hash?.slice(0, 12) || "unavailable"}
                  </p>
                  {source.error && <p className="error-text">{source.error}</p>}
                  {source.extraction_note && (
                    <p className="error-text">{source.extraction_note}</p>
                  )}
                  <a href={source.url} target="_blank" rel="noreferrer">
                    Official source <ArrowUpRight size={13} />
                  </a>
                </div>
              ))}
              {researchStatus?.evaluation && (
                <pre>
                  {JSON.stringify(researchStatus.evaluation.results, null, 2)}
                </pre>
              )}
              <p>
                To collect new versions, run{" "}
                <code>python scripts/ingest_official.py</code>, inspect changed
                passages, then rebuild reviewed annotations. Source changes
                never activate rules automatically.
              </p>
            </details>
            <div className="admin-actions">
              {[
                ["simulate", "/admin/simulate-change"],
                ["monitor", "/admin/monitor"],
                ["cleanup", "/admin/cleanup"],
              ].map(([label, path]) => (
                <button
                  className="btn secondary"
                  disabled={busy}
                  key={label}
                  onClick={() =>
                    run(async () => {
                      await api(path, "POST");
                      setOverview(await api("/admin/overview"));
                      setMessage(t("done"));
                    })
                  }
                >
                  {t(label)}
                </button>
              ))}
              <button
                className="btn"
                onClick={() =>
                  run(async () => setMetrics(await api("/admin/evaluation")))
                }
              >
                {t("metrics")}
              </button>
              <label className="btn secondary upload-button">
                {t("importLabels")}
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file)
                      run(async () => {
                        const form = new FormData();
                        form.append("file", file);
                        setMetrics(
                          await api("/admin/human-labels", "POST", form),
                        );
                      });
                  }}
                />
              </label>
            </div>
            {metrics && (
              <details className="panel" open>
                <summary>{t("metrics")}</summary>
                <pre>{JSON.stringify(metrics, null, 2)}</pre>
              </details>
            )}
            <h2>{t("proposals")}</h2>
            {overview?.proposals.length ? (
              overview.proposals.map((p) => (
                <ProposalCard
                  key={p.id}
                  proposal={p}
                  t={t}
                  busy={busy}
                  onAction={(action) =>
                    run(async () => {
                      await api(`/admin/proposals/${p.id}/${action}`, "POST");
                      setOverview(await api("/admin/overview"));
                    })
                  }
                  onEdit={(rule, cases) =>
                    run(async () => {
                      await api(`/admin/proposals/${p.id}`, "PATCH", {
                        proposed_rule: JSON.parse(rule),
                        regression_cases: JSON.parse(cases),
                      });
                      setOverview(await api("/admin/overview"));
                    })
                  }
                />
              ))
            ) : (
              <div className="panel empty">{t("pending")} · 0</div>
            )}
            <SourceManager
              overview={overview}
              t={t}
              busy={busy}
              onSave={(body) =>
                run(async () => {
                  await api("/admin/sources", "POST", body);
                  setOverview(await api("/admin/overview"));
                  setMessage(t("done"));
                })
              }
            />
            <details className="panel">
              <summary>{t("rules")}</summary>
              {overview?.versions.map((v) => (
                <div className="source-row" key={v.id}>
                  <strong>{v.id}</strong>
                  <p>
                    {v.approved_by} · {new Date(v.created_at).toLocaleString()}
                  </p>
                  <pre>{JSON.stringify(v.rule, null, 2)}</pre>
                </div>
              ))}
            </details>
            <details className="panel">
              <summary>{t("audit")}</summary>
              {overview?.audit.map((a) => (
                <p key={a.id}>
                  <strong>{a.action}</strong> · {a.target_id} · {a.created_at}
                </p>
              ))}
            </details>
          </section>
        )}
      </main>
      {preview && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => setPreview(null)}
        >
          <section
            className="preview-modal"
            role="dialog"
            aria-modal="true"
            aria-label={t("preview")}
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h2>{t(preview.category)}</h2>
              <button
                autoFocus
                className="icon-btn"
                aria-label={t("close")}
                onClick={() => setPreview(null)}
              >
                <X />
              </button>
            </div>
            <DocumentPages key={preview.id} doc={preview} t={t} />
            <p>{t("reviewHint")}</p>
          </section>
        </div>
      )}
      <footer>
        <div>
          <span className="brand footer-brand">
            <span className="brand-mark">
              <Leaf size={21} />
            </span>
            FormFlow<span className="ai"> AI</span>
          </span>
          <p>{t("help")}</p>
        </div>
        <div className="footer-note">
          <strong>{t("demo")}</strong>
          <p>{t("fictional")}</p>
        </div>
        <div className="accessibility">
          <button
            onClick={() => setContrast(!contrast)}
            aria-pressed={contrast}
          >
            {t("contrast")}
          </button>
          <button onClick={() => setLarger(!larger)} aria-pressed={larger}>
            {t("bigger")}
          </button>
          <button onClick={localRead}>
            <Volume2 size={16} />
            {t("read")}
          </button>
        </div>
      </footer>
    </div>
  );
}

function FactCard({
  fact: f,
  t,
  busy,
  onReview,
  onPreview,
}: {
  fact: Fact;
  t: (k: string) => string;
  busy: boolean;
  onReview: (action: string, value?: string) => void;
  onPreview: () => void;
}) {
  const [value, setValue] = useState(f.value);
  return (
    <article className="panel fact-card">
      <div className="fact-main">
        <p className="eyebrow">{t(f.key)}</p>
        <strong className="fact-value">{f.value}</strong>
        <span className={"tag " + (f.review === "confirmed" ? "light" : "")}>
          {t(
            f.review === "confirmed"
              ? "confirmed"
              : f.review === "corrected"
                ? "corrected"
                : f.review === "unreadable"
                  ? "unreadable"
                  : "unconfirmed",
          )}
        </span>
        <p className="muted">
          {t("original")}: {f.original} · {f.method} · p.{f.page} ·{" "}
          {t("confidence")}: {Math.round(f.confidence * 100)}/100
        </p>
        <details className="evidence-region">
          <summary>{t("source")}</summary>
          <img
            loading="lazy"
            alt={t("source")}
            src={`/api/v1/facts/${f.id}/region`}
          />
        </details>
        <button className="small-link" onClick={onPreview}>
          {t("preview")}
          <ArrowUpRight size={14} />
        </button>
      </div>
      <div className="fact-actions">
        <label>
          {t("value")}
          <input value={value} onChange={(e) => setValue(e.target.value)} />
        </label>
        <div className="button-row">
          <button
            className="btn small"
            disabled={
              busy || f.review === "corrected" || f.review === "confirmed"
            }
            onClick={() => onReview("confirmed")}
          >
            {t("confirm")}
            <Check size={15} />
          </button>
          <button
            className="btn small secondary"
            disabled={busy || value === f.value}
            onClick={() => onReview("corrected", value)}
          >
            {t("saveCorrection")}
          </button>
        </div>
        <div className="button-row">
          <button className="small-link" onClick={() => onReview("unreadable")}>
            {t("unreadable")}
          </button>
          <button
            className="small-link danger-text"
            onClick={() => onReview("removed")}
          >
            {t("remove")}
          </button>
        </div>
      </div>
    </article>
  );
}
function ResultCard({
  result: r,
  lang,
  t,
  status,
  badgeClass,
  onEvidence,
}: {
  result: Result;
  lang: Lang;
  t: (k: string) => string;
  status: (s: string) => string;
  badgeClass: (s: string) => string;
  onEvidence: (id: string) => void;
}) {
  const groups: { [k: string]: string } = {
    provided: "provided",
    required: "missing",
    clarification: "clarification",
    conflicting_or_outdated: "outdated",
    application: "application",
  };
  return (
    <article className="panel result-card" data-testid="scheme-result">
      <div className="result-heading">
        <div>
          <span className="eyebrow">
            {t("demo")} / {r.category}
          </span>
          <h2>{lang === "kn" ? r.name_kn : r.name}</h2>
          <small>
            {t("ruleVersion")} {r.version} · {t("assessed")} {r.date}
          </small>
        </div>
        <span
          className={"verdict " + badgeClass(r.verdict)}
          data-testid="verdict"
        >
          {status(r.verdict)}
        </span>
      </div>
      <details open>
        <summary>{t("conditions")}</summary>
        {r.conditions.map((c) => (
          <div className="condition" key={c.id}>
            <span
              className={
                "condition-dot " +
                (c.status === "SATISFIED"
                  ? "success"
                  : c.status === "NOT_SATISFIED"
                    ? "neutral"
                    : "warning")
              }
            >
              {c.status === "SATISFIED" ? (
                <Check size={16} />
              ) : c.status === "NOT_SATISFIED" ? (
                "×"
              ) : (
                "?"
              )}
            </span>
            <div>
              <h3>{lang === "kn" ? c.description_kn : c.description}</h3>
              <p>{t(c.reason)}</p>
              <small>
                {t("value")}: {c.actual.join(", ") || "—"} /{" "}
                {String(c.expected)} {c.unit}
              </small>
              <blockquote>
                <strong>
                  {t("clause")} {c.clause_id}
                </strong>
                <p>{c.clause_text}</p>
              </blockquote>
              {c.evidence
                .filter((e) => e.document_id)
                .map((e, i) => (
                  <button
                    className="small-link"
                    key={i}
                    onClick={() => onEvidence(e.document_id)}
                  >
                    {t("evidence")} · p.{e.page}
                    <ArrowUpRight size={13} />
                  </button>
                ))}
            </div>
          </div>
        ))}
      </details>
      <details open>
        <summary>{t("checklist")}</summary>
        {r.evidence_guidance &&
          r.evidence_guidance.unresolved_conditions.length > 0 && (
            <div className="notice evidence-guidance">
              <div>
                <strong>
                  {lang === "kn"
                    ? "ಮುಂದಿನ ಸಾಕ್ಷ್ಯ"
                    : "Smallest mapped evidence set"}
                </strong>
                <p>
                  {lang === "kn"
                    ? "ಇವು ಪರಿಶೀಲಿಸದ ಷರತ್ತುಗಳನ್ನು ಸ್ಪಷ್ಟಪಡಿಸಲು ಸಹಾಯ ಮಾಡುವ ದಾಖಲೆಗಳು; ಅರ್ಹತೆಯ ಪುರಾವೆಯಲ್ಲ."
                    : "These document categories could resolve unresolved conditions. They do not establish eligibility by themselves."}
                </p>
                <ul>
                  {r.evidence_guidance.documents.map((item) => (
                    <li key={item.document_type}>
                      {t(item.document_type)} → {item.resolves.join(", ")}
                    </li>
                  ))}
                </ul>
                {r.evidence_guidance.no_sufficient_mapping.length > 0 && (
                  <p>
                    {lang === "kn"
                      ? "ಈ ಷರತ್ತುಗಳಿಗೆ ಸಾಕಷ್ಟು ದಾಖಲೆ ನಕ್ಷೆ ಇಲ್ಲ:"
                      : "No sufficient document mapping for:"}{" "}
                    {r.evidence_guidance.no_sufficient_mapping.join(", ")}
                  </p>
                )}
              </div>
            </div>
          )}
        <div className="checklist-grid">
          {Object.entries(groups).map(([group, key]) => {
            const items = r.checklist.filter((i) => i.group === group);
            return items.length ? (
              <div className="checklist-group" key={group}>
                <h3>{t(key)}</h3>
                {items.map((i) => (
                  <p key={i.document_type}>
                    <FileText size={16} />
                    {t(i.document_type)}
                  </p>
                ))}
              </div>
            ) : null;
          })}
        </div>
        <p className="muted small-text">{t("finalDocs")}</p>
      </details>
    </article>
  );
}
function ProposalCard({
  proposal: p,
  t,
  busy,
  onAction,
  onEdit,
}: {
  proposal: Proposal;
  t: (k: string) => string;
  busy: boolean;
  onAction: (a: string) => void;
  onEdit: (rule: string, cases: string) => void;
}) {
  const [rule, setRule] = useState(JSON.stringify(p.proposed_rule, null, 2)),
    [cases, setCases] = useState(JSON.stringify(p.regression_cases, null, 2));
  return (
    <article className="panel proposal">
      <div className="result-heading">
        <h3>
          {p.scheme_id} · {p.classification}
        </h3>
        <span className="tag">
          {t(p.state === "pending" ? "pending" : p.state)}
        </span>
      </div>
      <div className="diff-grid">
        <div>
          <strong>{t("old")}</strong>
          <pre className="diff-old">{p.old_text}</pre>
        </div>
        <div>
          <strong>{t("updated")}</strong>
          <pre className="diff-new">{p.new_text}</pre>
        </div>
      </div>
      {p.impact && (
        <div className="notice">
          <div>
            <strong>Potential reassessment impact</strong>
            <p>{p.impact.reason}</p>
            <p>
              Conditions: {p.impact.condition_ids.join(", ") || "none mapped"} ·
              Previous assessments: {p.impact.assessment_ids.length}
            </p>
          </div>
        </div>
      )}
      <details>
        <summary>
          {t("rules")} / {t("regression")}
        </summary>
        <label>
          {t("rules")}
          <textarea
            value={rule}
            onChange={(e) => setRule(e.target.value)}
            rows={12}
            disabled={p.state !== "pending"}
          />
        </label>
        <label>
          {t("regression")}
          <textarea
            value={cases}
            onChange={(e) => setCases(e.target.value)}
            rows={8}
            disabled={p.state !== "pending"}
          />
        </label>
        {p.state === "pending" && (
          <button
            className="btn secondary"
            disabled={busy}
            onClick={() => onEdit(rule, cases)}
          >
            {t("saveProposal")}
          </button>
        )}
      </details>
      {p.state === "pending" ? (
        <div className="button-row">
          <button
            className="btn"
            disabled={busy}
            onClick={() => onAction("approve")}
          >
            {t("approve")}
            <Check size={17} />
          </button>
          <button
            className="btn secondary"
            disabled={busy}
            onClick={() => onAction("reject")}
          >
            {t("reject")}
          </button>
        </div>
      ) : (
        <pre>{JSON.stringify(p.validation, null, 2)}</pre>
      )}
    </article>
  );
}

function DocumentPages({ doc, t }: { doc: Doc; t: (key: string) => string }) {
  const [page, setPage] = useState(1);
  const total = doc.quality.page_count || 1;
  return (
    <>
      <img
        alt={t("source")}
        src={`/api/v1/documents/${doc.id}/preview/${page}`}
      />
      <div className="button-row">
        <button
          className="btn secondary small"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          {t("back")}
        </button>
        <span>
          {page} / {total}
        </span>
        <button
          className="btn secondary small"
          disabled={page >= total}
          onClick={() => setPage(page + 1)}
        >
          {t("next")}
        </button>
        <a
          className="small-link"
          href={`/api/v1/documents/${doc.id}/content`}
          target="_blank"
          rel="noreferrer"
        >
          {t("preview")}
          <ArrowUpRight size={14} />
        </a>
      </div>
    </>
  );
}

function SourceManager({
  overview,
  t,
  busy,
  onSave,
}: {
  overview: Overview | null;
  t: (key: string) => string;
  busy: boolean;
  onSave: (body: { id: string; scheme_id: string; url: string }) => void;
}) {
  const [id, setId] = useState(""),
    [scheme, setScheme] = useState("ka-sandhya"),
    [url, setUrl] = useState(""),
    [snapshot, setSnapshot] = useState<{ id: string; text: string } | null>(
      null,
    ),
    [error, setError] = useState("");
  return (
    <details className="panel">
      <summary>{t("sources")}</summary>
      {overview?.sources.map((s) => (
        <div className="source-row" key={s.id}>
          <strong>{s.id}</strong>
          <p>{s.url}</p>
          {s.last_error && <p className="error-text">{s.last_error}</p>}
          {s.snapshots.map((x) => (
            <div key={x.id}>
              <small>
                {x.created_at} · SHA256 {x.content_hash}
              </small>
              <button
                className="small-link"
                onClick={async () => {
                  try {
                    setSnapshot(await api("/admin/snapshots/" + x.id));
                    setError("");
                  } catch (e) {
                    setError(String(e));
                  }
                }}
              >
                {t("view")}
              </button>
              {snapshot?.id === x.id && <pre>{snapshot.text}</pre>}
            </div>
          ))}
        </div>
      ))}
      {error && <p role="alert">{error}</p>}
      <form
        className="form-stack source-form"
        onSubmit={(e) => {
          e.preventDefault();
          onSave({ id, scheme_id: scheme, url });
        }}
      >
        <h3>{t("saveSource")}</h3>
        <p className="muted">{t("allowlisted")}</p>
        <label>
          {t("sourceId")}
          <input
            required
            pattern="[a-zA-Z0-9_-]+"
            minLength={3}
            value={id}
            onChange={(e) => setId(e.target.value)}
          />
        </label>
        <label>
          {t("schemeId")}
          <select value={scheme} onChange={(e) => setScheme(e.target.value)}>
            <option value="ka-sandhya">Sandhya Suraksha Yojana</option>
            <option value="ka-ignoaps">
              Indira Gandhi National Old Age Pension Scheme
            </option>
          </select>
        </label>
        <label>
          {t("sourceUrl")}
          <input
            type="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <button className="btn secondary" disabled={busy}>
          {t("saveSource")}
        </button>
      </form>
    </details>
  );
}
