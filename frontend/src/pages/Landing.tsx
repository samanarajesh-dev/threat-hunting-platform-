import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { ErrorBox } from "../ui";

export default function Landing() {
  const { login } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [username, setU] = useState("admin");
  const [password, setP] = useState("admin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [contactSent, setContactSent] = useState(false);

  async function handleLogin(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function quickLogin(role: string) {
    setU(role);
    setP(role);
    setBusy(true);
    setError(null);
    login(role, role).catch((err) => {
      setError((err as Error).message);
      setBusy(false);
    });
  }

  function handleContactSubmit(e: FormEvent) {
    e.preventDefault();
    setContactSent(true);
    setTimeout(() => setContactSent(false), 5000);
  }

  return (
    <div className="landing-page">
      {/* 1. Top Navbar */}
      <header className="landing-nav">
        <div className="landing-brand">
          <svg className="landing-logo-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="14" stroke="#ffffff" strokeWidth="2.5" />
            <polygon points="16,6 24,22 8,22" stroke="#38bdf8" strokeWidth="2" fill="none" />
            <circle cx="16" cy="17" r="3" fill="#6366f1" />
          </svg>
          <span className="brand-text">THREAT-HUNTING</span>
        </div>

        {/* Clean Menu with Products, Services, About Us, Contact Us */}
        <nav className="landing-menu" aria-label="Platform navigation">
          <a href="#products">Products</a>
          <a href="#services">Services</a>
          <a href="#about-us">About Us</a>
          <a href="#contact-us">Contact Us</a>
        </nav>

        {/* Right actions */}
        <div className="landing-actions">
          <button className="link-action" onClick={() => setShowLogin(true)}>Report an incident</button>
          <button className="icon-search-btn" aria-label="Search" onClick={() => setShowLogin(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </button>
          <button className="btn-signin" onClick={() => setShowLogin(true)}>
            Sign in
          </button>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="landing-hero">
        <div className="hero-content">
          <p className="hero-kicker">Cybersecurity Products and Services</p>
          <h1 className="hero-title">
            Fight against<br />cybercrime
          </h1>
          <p className="hero-desc">
            Our cybersecurity, anti-fraud and brand protection solutions are powered by intelligence-driven technologies and the exceptional human proficiency of our experts.
          </p>

          <div className="hero-cta-group">
            <button className="btn-primary" onClick={() => setShowLogin(true)}>
              Find your product
            </button>
          </div>
        </div>

        {/* Futuristic 3D Cyber Core Visual */}
        <div className="hero-visual" aria-hidden="true">
          <div className="cyber-glow-bg"></div>
          
          <div className="laser-beam laser-vertical"></div>
          <div className="laser-beam laser-diagonal"></div>

          <svg className="cyber-scene" viewBox="0 0 500 500">
            <defs>
              <radialGradient id="sphereGrad1" cx="35%" cy="35%" r="65%">
                <stop offset="0%" stopColor="#7dd3fc" />
                <stop offset="45%" stopColor="#0284c7" />
                <stop offset="100%" stopColor="#050e24" />
              </radialGradient>
              <radialGradient id="sphereGrad2" cx="30%" cy="30%" r="70%">
                <stop offset="0%" stopColor="#ffffff" />
                <stop offset="25%" stopColor="#38bdf8" />
                <stop offset="70%" stopColor="#1e3a8a" />
                <stop offset="100%" stopColor="#060b1c" />
              </radialGradient>
              <radialGradient id="indigoGrad" cx="35%" cy="35%" r="65%">
                <stop offset="0%" stopColor="#c7d2fe" />
                <stop offset="50%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#1e1b4b" />
              </radialGradient>
              <radialGradient id="redGlow" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stopColor="#ff99a4" />
                <stop offset="50%" stopColor="#ff334b" />
                <stop offset="100%" stopColor="#50000a" />
              </radialGradient>
              <filter id="laserGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Connecting Lattice Lines */}
            <g stroke="#38bdf8" strokeWidth="1" opacity="0.38">
              <line x1="250" y1="250" x2="160" y2="180" />
              <line x1="250" y1="250" x2="340" y2="170" />
              <line x1="250" y1="250" x2="380" y2="290" />
              <line x1="250" y1="250" x2="150" y2="330" />
              <line x1="250" y1="250" x2="250" y2="100" />
              <line x1="160" y1="180" x2="250" y2="100" />
              <line x1="340" y1="170" x2="250" y2="100" />
              <line x1="340" y1="170" x2="380" y2="290" />
              <line x1="150" y1="330" x2="160" y2="180" />
              <line x1="150" y1="330" x2="280" y2="380" />
              <line x1="380" y1="290" x2="280" y2="380" />
            </g>

            {/* Central Dark Faceted Core Cube */}
            <polygon points="250,170 330,215 250,265 170,215" fill="#0f1738" stroke="#38bdf8" strokeWidth="1.5" />
            <polygon points="170,215 250,265 250,355 170,305" fill="#0a1029" stroke="#6366f1" strokeWidth="1.5" />
            <polygon points="330,215 250,265 250,355 330,305" fill="#070c20" stroke="#4338ca" strokeWidth="1.5" />

            {/* Floating Glossy Telemetry Spheres */}
            <circle cx="250" cy="100" r="24" fill="url(#sphereGrad2)" />
            <circle cx="160" cy="180" r="18" fill="url(#indigoGrad)" />
            <circle cx="340" cy="170" r="22" fill="url(#sphereGrad2)" />
            <circle cx="380" cy="290" r="26" fill="url(#sphereGrad1)" />
            <circle cx="150" cy="330" r="20" fill="url(#sphereGrad2)" />
            <circle cx="280" cy="380" r="16" fill="url(#indigoGrad)" />

            {/* Glowing Threat & Alert Nodes */}
            <circle cx="340" cy="245" r="8" fill="url(#redGlow)" filter="url(#laserGlow)" />
            <circle cx="195" cy="310" r="7" fill="url(#redGlow)" filter="url(#laserGlow)" />
            <circle cx="215" cy="140" r="9" fill="url(#sphereGrad2)" filter="url(#laserGlow)" />
            <circle cx="370" cy="130" r="6" fill="#38bdf8" filter="url(#laserGlow)" />

            {/* High Power Laser Beams in SVG */}
            <line x1="250" y1="0" x2="250" y2="500" stroke="#38bdf8" strokeWidth="3" filter="url(#laserGlow)" />
            <line x1="0" y1="360" x2="500" y2="180" stroke="#6366f1" strokeWidth="2.5" filter="url(#laserGlow)" opacity="0.85" />
          </svg>
        </div>
      </section>

      {/* 3. Products Section */}
      <section id="products" className="landing-section">
        <div className="section-container">
          <div className="section-head">
            <span className="section-badge">OUR PORTFOLIO</span>
            <h2 className="section-title">Engineered for Proactive Threat Hunting</h2>
            <p className="section-desc">Unified security tools designed to outmaneuver advanced adversaries across endpoints, networks, and cloud infrastructure.</p>
          </div>

          <div className="cards-grid">
            <div className="feature-card">
              <div className="card-icon blue-glow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  <path d="m9 12 2 2 4-4"/>
                </svg>
              </div>
              <h3>Automated Detection Engine</h3>
              <p>Execute YAML-based detection rules every 60 seconds with thresholding and multi-event aggregation over normalized Elasticsearch logs.</p>
              <ul className="feature-list">
                <li>10 built-in rules targeting MITRE ATT&CK</li>
                <li>Retro-hunting capability up to 7 days</li>
                <li>False-positive suppression controls</li>
              </ul>
            </div>

            <div className="feature-card">
              <div className="card-icon red-glow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </div>
              <h3>Incident Correlation Matrix</h3>
              <p>Automatically merges related alerts sharing entities (IP, host, user, domain, hash) into unified kill-chain incidents with 0–100 risk scoring.</p>
              <ul className="feature-list">
                <li>Automatic multi-stage attack escalation</li>
                <li>Noisy entity filtering & suppression</li>
                <li>Incident timelines with MITRE mapping</li>
              </ul>
            </div>

            <div className="feature-card">
              <div className="card-icon amber-glow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  <path d="M11 8v6M8 11h6"/>
                </svg>
              </div>
              <h3>Log Search & Indicator Pivot</h3>
              <p>High-velocity log hunting across millions of events with instant pivoting on IPs, domains, URLs, and hashes with automated un-defanging.</p>
              <ul className="feature-list">
                <li>Sub-second query performance</li>
                <li>Dynamic multi-bucket time series</li>
                <li>Single-click evidence attachment to cases</li>
              </ul>
            </div>

            <div className="feature-card">
              <div className="card-icon purple-glow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
              </div>
              <h3>Tamper-Proof Case Management</h3>
              <p>Manage security investigations with append-only evidence tracking, cryptographic SHA-256 integrity hashing, and executive report exports.</p>
              <ul className="feature-list">
                <li>SHA-256 chain of custody for all artifacts</li>
                <li>One-click PDF and Markdown case reports</li>
                <li>Full audit logging on all analyst actions</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Services Section */}
      <section id="services" className="landing-section dark-alt">
        <div className="section-container">
          <div className="section-head">
            <span className="section-badge">CAPABILITIES & SERVICES</span>
            <h2 className="section-title">Comprehensive Security Operations</h2>
            <p className="section-desc">Delivering frontline defensive capabilities from automated alert triage to multi-source threat intelligence enrichment.</p>
          </div>

          <div className="services-grid">
            <div className="service-row">
              <div className="service-num">01</div>
              <div className="service-body">
                <h3>Threat Intelligence Enrichment & In-Memory Cache</h3>
                <p>Real-time querying against VirusTotal, AbuseIPDB, and AlienVault OTX with 24-hour smart caching to protect API quotas. Continuous background monitoring against active local watchlists.</p>
              </div>
              <div className="service-meta">
                <span className="pill">VirusTotal</span>
                <span className="pill">AbuseIPDB</span>
                <span className="pill">OTX</span>
              </div>
            </div>

            <div className="service-row">
              <div className="service-num">02</div>
              <div className="service-body">
                <h3>Log Normalization & Ingest Pipeline</h3>
                <p>Collect raw telemetry via Filebeat or Winlogbeat, mapped through our <code>thp-normalize</code> Elasticsearch pipeline strictly following the Elastic Common Schema (ECS) Data Contract.</p>
              </div>
              <div className="service-meta">
                <span className="pill">ECS Schema</span>
                <span className="pill">Sysmon</span>
                <span className="pill">Linux Syslog</span>
              </div>
            </div>

            <div className="service-row">
              <div className="service-num">03</div>
              <div className="service-body">
                <h3>24/7 Managed Alert Triage & Incident Escalation</h3>
                <p>Role-governed console workflow separating Viewers, Analysts, and Administrators with full state transition audits, evidence attachment, and incident retrospectives.</p>
              </div>
              <div className="service-meta">
                <span className="pill">RBAC Gated</span>
                <span className="pill">Audit Trail</span>
                <span className="pill">FastAPI</span>
              </div>
            </div>

            <div className="service-row">
              <div className="service-num">04</div>
              <div className="service-body">
                <h3>Digital Forensics & Incident Response Reporting</h3>
                <p>Export auditable compliance reports in PDF and Markdown formats with verified verdicts, indicator timelines, and findings for stakeholders and regulators.</p>
              </div>
              <div className="service-meta">
                <span className="pill">PDF Generator</span>
                <span className="pill">Markdown</span>
                <span className="pill">Chain-of-Custody</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. About Us Section */}
      <section id="about-us" className="landing-section">
        <div className="section-container">
          <div className="about-grid">
            <div className="about-info">
              <span className="section-badge">ABOUT OUR PLATFORM</span>
              <h2 className="section-title">Built for Modern Security Operations Centers</h2>
              <p className="about-p">
                The Threat Hunting Platform was architected by defensive engineers who understand that modern attackers bypass basic signature alerts. Threat actors employ living-off-the-land techniques, encoded scripts, and credential dumping.
              </p>
              <p className="about-p">
                Our mission is to eliminate analyst fatigue by providing a single-pane web console that stitches together log ingestion, statistical detection, threat-intel lookups, and incident case files in a single unified workflow.
              </p>

              <div className="stats-strip">
                <div className="stat-block">
                  <div className="stat-value">10+</div>
                  <div className="stat-label">Built-in Attack Rules</div>
                </div>
                <div className="stat-block">
                  <div className="stat-value">100%</div>
                  <div className="stat-label">Append-Only Evidence</div>
                </div>
                <div className="stat-block">
                  <div className="stat-value">&lt; 1s</div>
                  <div className="stat-label">Query Search Speed</div>
                </div>
                <div className="stat-block">
                  <div className="stat-value">24h</div>
                  <div className="stat-label">IOC Cache Window</div>
                </div>
              </div>
            </div>

            <div className="about-tech-box">
              <h3>Enterprise Technology Stack</h3>
              <div className="tech-item">
                <span className="tech-name">FastAPI Backend</span>
                <span className="tech-detail">Python 3.12, SQLAlchemy 2, Pydantic 2, JWT Auth</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">Elasticsearch Engine</span>
                <span className="tech-detail">ECS Event Indexing, Ingest Pipeline Normalization</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">PostgreSQL Relational DB</span>
                <span className="tech-detail">Alerts, Incidents, Cases, Evidence, Audit Logs</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">React 19 + TypeScript</span>
                <span className="tech-detail">Vite, Strict Types, Recharts, Accessible Dark SOC Theme</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Contact Us Section */}
      <section id="contact-us" className="landing-section dark-alt">
        <div className="section-container">
          <div className="section-head">
            <span className="section-badge">GET IN TOUCH</span>
            <h2 className="section-title">Connect with Security Operations</h2>
            <p className="section-desc">Have questions about deploying the Threat Hunting Platform or need urgent incident consultation? Send our engineers a message.</p>
          </div>

          <div className="contact-grid">
            <div className="contact-details">
              <div className="contact-card">
                <div className="contact-icon">📍</div>
                <div>
                  <h4>Operations Center</h4>
                  <p className="muted">Global SOC HQ & Security Engineering Lab</p>
                </div>
              </div>

              <div className="contact-card">
                <div className="contact-icon">🚨</div>
                <div>
                  <h4>Emergency Incident Reporting</h4>
                  <p className="muted">hotline@threat-hunting.local (24/7/365)</p>
                </div>
              </div>

              <div className="contact-card">
                <div className="contact-icon">🔒</div>
                <div>
                  <h4>Encrypted Key Exchange</h4>
                  <p className="muted">PGP Fingerprint: 4E92 B21C 8901 AA4F 3910</p>
                </div>
              </div>

              <div className="contact-card">
                <div className="contact-icon">💻</div>
                <div>
                  <h4>Platform Console Access</h4>
                  <p className="muted">Authorized analysts can sign in directly above</p>
                </div>
              </div>
            </div>

            <div className="contact-form-box">
              {contactSent ? (
                <div className="contact-success">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="9 12 12 15 16 10" />
                  </svg>
                  <h3>Message Dispatched to SOC Team</h3>
                  <p className="muted">A security operations engineer will review your request shortly.</p>
                </div>
              ) : (
                <form onSubmit={handleContactSubmit}>
                  <h3>Send a Request to the SOC Team</h3>
                  <label>
                    Full Name
                    <input placeholder="Analyst or Team Lead" required />
                  </label>
                  <label>
                    Work Email
                    <input type="email" placeholder="name@organization.com" required />
                  </label>
                  <label>
                    Subject
                    <input placeholder="Threat Intel Inquiry / Incident Support" required />
                  </label>
                  <label>
                    Message / Incident Brief
                    <textarea rows={4} placeholder="Describe your deployment requirements or threat scenario..." required />
                  </label>
                  <button type="submit" className="btn-primary" style={{ width: "100%", marginTop: "0.8rem" }}>
                    Dispatch Message
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-left">
            <span className="brand-text">THREAT-HUNTING PLATFORM</span>
            <p className="muted small">Intelligence-driven detection, log hunting, and incident forensics.</p>
          </div>
          <div className="footer-links">
            <a href="#products">Products</a>
            <a href="#services">Services</a>
            <a href="#about-us">About Us</a>
            <a href="#contact-us">Contact Us</a>
            <button className="link" onClick={() => setShowLogin(true)}>Console Sign In</button>
          </div>
        </div>
        <div className="footer-bottom">
          <small className="muted">© 2026 Threat Hunting Platform. Built for Security Operations Centers. All rights reserved.</small>
        </div>
      </footer>

      {/* Login Modal Overlay */}
      {showLogin && (
        <div className="login-modal-overlay" onClick={() => setShowLogin(false)}>
          <div className="login-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>SOC Platform Access</h2>
              <button className="modal-close" onClick={() => setShowLogin(false)} aria-label="Close modal">✕</button>
            </div>
            <p className="modal-subtitle">Sign in to open the Threat Hunting Console</p>

            {/* Quick Demo Login Buttons */}
            <div className="quick-demo-box">
              <span className="small muted">One-Click Quick Sign In:</span>
              <div className="demo-buttons">
                <button type="button" className="demo-chip" onClick={() => quickLogin("admin")}>
                  Admin (Full Access)
                </button>
                <button type="button" className="demo-chip" onClick={() => quickLogin("analyst")}>
                  Analyst (Hunting & Cases)
                </button>
                <button type="button" className="demo-chip" onClick={() => quickLogin("viewer")}>
                  Viewer (Read-Only)
                </button>
              </div>
            </div>

            <form onSubmit={handleLogin}>
              <label>
                Username
                <input
                  value={username}
                  onChange={(e) => setU(e.target.value)}
                  autoComplete="username"
                  required
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setP(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>
              <ErrorBox error={error} />
              <button className="btn-modal-signin" disabled={busy}>
                {busy ? "Authenticating…" : "Sign In to Console"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
