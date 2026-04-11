"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useCallback } from "react";

/* ================================================================== */
/*  HEMERA INTELLIGENCE — Landing Page                                 */
/*  Aesthetic: Dawn-light luminous, science-forward, collaborative     */
/* ================================================================== */

// ── Smooth counter animation ──
function useCountUp(target: number, duration = 2000, start = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number;
    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return value;
}

// ── Intersection observer hook ──
function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setInView(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

/* ================================================================== */
/*  HERO — Radiant dawn with floating particles                        */
/* ================================================================== */

function Hero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const particles: { x: number; y: number; vx: number; vy: number; r: number; a: number; speed: number }[] = [];
    const PARTICLE_COUNT = 80;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 2 + 0.5,
        a: Math.random() * 0.4 + 0.1,
        speed: Math.random() * 0.5 + 0.2,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      particles.forEach((p) => {
        // Gentle attraction toward mouse
        if (mx && my) {
          const dx = mx - p.x;
          const dy = my - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 300) {
            p.vx += (dx / dist) * 0.02;
            p.vy += (dy / dist) * 0.02;
          }
        }

        p.x += p.vx * p.speed;
        p.y += p.vy * p.speed;
        p.vx *= 0.99;
        p.vy *= 0.99;

        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(13, 148, 136, ${p.a})`;
        ctx.fill();
      });

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(13, 148, 136, ${0.08 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animId = requestAnimationFrame(draw);
    };
    draw();

    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", handleMouse);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMouse);
    };
  }, []);

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Luminous dawn gradient background */}
      <div className="absolute inset-0" style={{
        background: `
          radial-gradient(ellipse 80% 60% at 50% 0%, rgba(13, 148, 136, 0.08) 0%, transparent 60%),
          radial-gradient(ellipse 60% 50% at 70% 20%, rgba(245, 158, 11, 0.04) 0%, transparent 50%),
          radial-gradient(ellipse 50% 40% at 30% 80%, rgba(13, 148, 136, 0.03) 0%, transparent 50%),
          linear-gradient(180deg, #FAFDF9 0%, #F5F5F0 40%, #F0F0EB 100%)
        `,
      }} />

      {/* Particle canvas */}
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />

      {/* Subtle grid pattern */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: `
          linear-gradient(rgba(30, 41, 59, 0.3) 1px, transparent 1px),
          linear-gradient(90deg, rgba(30, 41, 59, 0.3) 1px, transparent 1px)
        `,
        backgroundSize: "60px 60px",
      }} />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        {/* Wordmark */}
        <div className="inline-flex items-center gap-2 mb-8 animate-[fadeInDown_0.8s_ease-out]">
          <div className="w-2 h-2 rounded-full bg-teal animate-pulse" />
          <span className="text-teal text-[11px] font-bold uppercase tracking-[4px]">
            Hemera Intelligence
          </span>
          <div className="w-2 h-2 rounded-full bg-teal animate-pulse" />
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-slate leading-[1.05] tracking-tight animate-[fadeInUp_1s_ease-out]">
          Supply chains
          <br />
          <span className="relative">
            <span className="relative z-10">made transparent</span>
            <span className="absolute bottom-1 left-0 right-0 h-3 bg-teal/10 -skew-x-2 rounded" />
          </span>
        </h1>

        {/* Subheadline */}
        <p className="mt-6 text-lg sm:text-xl text-muted max-w-2xl mx-auto leading-relaxed animate-[fadeInUp_1s_ease-out_0.2s_both]">
          Carbon intelligence, supplier ESG analysis, and data uncertainty quantification —
          all statistically verified to academic standards. At a price and pace that makes
          sustainability accessible to everyone.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center mt-10 animate-[fadeInUp_1s_ease-out_0.4s_both]">
          <Link
            href="#demo"
            className="group relative px-8 py-4 bg-teal text-white rounded-xl font-semibold text-sm overflow-hidden transition-all hover:shadow-lg hover:shadow-teal/20 hover:-translate-y-0.5"
          >
            <span className="relative z-10">Book a Demo</span>
            <div className="absolute inset-0 bg-gradient-to-r from-teal to-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link
            href="#video"
            className="group flex items-center justify-center gap-2 px-8 py-4 border border-slate/15 text-slate rounded-xl font-semibold text-sm hover:border-teal/30 hover:bg-teal/3 transition-all"
          >
            <svg className="w-5 h-5 text-teal group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
            </svg>
            Watch the Video
          </Link>
        </div>

        {/* Trust signals */}
        <div className="mt-16 flex items-center justify-center gap-8 text-muted text-xs animate-[fadeInUp_1s_ease-out_0.6s_both]">
          <span className="flex items-center gap-1.5">
            <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            GHG Protocol Aligned
          </span>
          <span className="w-px h-4 bg-slate/10" />
          <span className="flex items-center gap-1.5">
            <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            ISO 19011 QC Standards
          </span>
          <span className="w-px h-4 bg-slate/10" />
          <span className="flex items-center gap-1.5">
            <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
            </svg>
            59 Public Data Sources
          </span>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 rounded-full border-2 border-slate/20 flex items-start justify-center pt-2">
          <div className="w-1.5 h-3 rounded-full bg-teal/40 animate-[scrollDot_2s_ease-in-out_infinite]" />
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  STATS — Animated counter section                                   */
/* ================================================================== */

function Stats() {
  const { ref, inView } = useInView(0.3);
  const sources = useCountUp(59, 2000, inView);
  const fields = useCountUp(80, 2200, inView);
  const layers = useCountUp(13, 1500, inView);
  const accuracy = useCountUp(95, 1800, inView);

  return (
    <section ref={ref} className="relative py-24 overflow-hidden">
      <div className="absolute inset-0 bg-slate" />
      {/* Subtle diagonal lines */}
      <div className="absolute inset-0 opacity-[0.04]" style={{
        backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 40px, rgba(255,255,255,0.1) 40px, rgba(255,255,255,0.1) 41px)`,
      }} />

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {[
            { value: sources, suffix: "", label: "Public Data Sources", desc: "Government registries, certifications, regulators" },
            { value: fields, suffix: "+", label: "Data Fields Analysed", desc: "Per supplier, across every ESG domain" },
            { value: layers, suffix: "", label: "Intelligence Layers", desc: "From corporate identity to social value" },
            { value: accuracy, suffix: "%", label: "Confidence Level", desc: "Statistical sampling to ISO 19011" },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className="text-center"
              style={{
                opacity: inView ? 1 : 0,
                transform: inView ? "translateY(0)" : "translateY(20px)",
                transition: `all 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${i * 0.1}s`,
              }}
            >
              <div className="text-4xl md:text-5xl font-extrabold text-white tabular-nums">
                {stat.value}{stat.suffix}
              </div>
              <div className="text-teal text-sm font-semibold mt-2">{stat.label}</div>
              <div className="text-white/40 text-xs mt-1">{stat.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  HEMERASCOPE — Product section with bento grid                      */
/* ================================================================== */

function HemeraScope() {
  const { ref, inView } = useInView(0.1);

  const cards = [
    {
      tag: "Carbon Intelligence",
      title: "Scope 1, 2 & 3 emissions calculated from your spend data",
      desc: "Upload your accounting data. Our AI classifies every transaction, matches suppliers, and calculates emissions using DEFRA-verified factors. Full GHG Protocol compliance with uncertainty quantification on every number.",
      color: "from-teal/5 to-teal/10",
      border: "border-teal/15",
      tagColor: "bg-teal/10 text-teal",
      span: "md:col-span-2",
      icon: (
        <svg className="w-8 h-8 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
      ),
    },
    {
      tag: "Data Uncertainty",
      title: "Every number comes with a confidence interval",
      desc: "Pedigree matrix scoring across 5 dimensions. Monte Carlo uncertainty propagation. You'll know exactly how reliable each figure is — and where to invest in better data.",
      color: "from-amber/5 to-amber/10",
      border: "border-amber/15",
      tagColor: "bg-amber/10 text-amber-700",
      span: "",
      icon: (
        <svg className="w-8 h-8 text-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
        </svg>
      ),
    },
    {
      tag: "Supplier ESG",
      title: "59 sources. One Hemera Score per supplier",
      desc: "We check Companies House, Environment Agency, HSE, SBTi, CDP, and 50+ more databases. Every finding is traceable to a public source. AI analysis verifies and challenges the automated results.",
      color: "from-emerald-500/5 to-emerald-500/10",
      border: "border-emerald-500/15",
      tagColor: "bg-emerald-50 text-emerald-700",
      span: "",
      icon: (
        <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
        </svg>
      ),
    },
    {
      tag: "Supplier Engagement",
      title: "We don't just flag problems — we help fix them",
      desc: "Hemera works directly with your suppliers to close ESG gaps. Modern slavery statements, SBTi commitments, environmental compliance — we facilitate the conversations and track progress. Suppliers who meet our standards earn the Hemera Verified badge.",
      color: "from-violet-500/5 to-violet-500/10",
      border: "border-violet-500/15",
      tagColor: "bg-violet-50 text-violet-700",
      span: "md:col-span-2",
      icon: (
        <svg className="w-8 h-8 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
        </svg>
      ),
    },
  ];

  return (
    <section ref={ref} className="py-28 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-teal/8 border border-teal/15 mb-6"
            style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(10px)", transition: "all 0.6s ease-out" }}>
            <div className="w-1.5 h-1.5 rounded-full bg-teal" />
            <span className="text-teal text-[11px] font-bold uppercase tracking-[2px]">HemeraScope</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate leading-tight"
            style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s" }}>
            One report. Complete clarity.
          </h2>
          <p className="mt-4 text-muted text-lg max-w-2xl mx-auto"
            style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s" }}>
            HemeraScope combines carbon footprint analysis, supplier ESG intelligence, and statistical uncertainty
            into a single, auditable deliverable.
          </p>
        </div>

        {/* Bento grid */}
        <div className="grid md:grid-cols-3 gap-4">
          {cards.map((card, i) => (
            <div
              key={card.tag}
              className={`group relative bg-gradient-to-br ${card.color} border ${card.border} rounded-2xl p-8 hover:shadow-lg transition-all duration-500 hover:-translate-y-1 ${card.span}`}
              style={{
                opacity: inView ? 1 : 0,
                transform: inView ? "translateY(0)" : "translateY(30px)",
                transition: `all 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${0.1 + i * 0.1}s`,
              }}
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 mt-1">{card.icon}</div>
                <div>
                  <span className={`inline-block text-[10px] font-bold uppercase tracking-[1.5px] px-2.5 py-1 rounded-full ${card.tagColor} mb-3`}>
                    {card.tag}
                  </span>
                  <h3 className="text-lg font-bold text-slate leading-snug">{card.title}</h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">{card.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  APPROACH — How we work (collaborative, not auditing)               */
/* ================================================================== */

function Approach() {
  const { ref, inView } = useInView(0.1);

  const steps = [
    {
      num: "01",
      title: "Upload your spend data",
      desc: "A simple CSV or Excel file. We handle the complexity — AI classifies every transaction into GHG Protocol scopes and categories.",
      detail: "Keyword matching + Claude AI for ambiguous items. Every classification is auditable.",
    },
    {
      num: "02",
      title: "We analyse your supply chain",
      desc: "59 public data sources checked per supplier. Companies House, Environment Agency, HSE, SBTi, and more. No paid databases needed.",
      detail: "13 intelligence layers with deterministic scoring + AI verification.",
    },
    {
      num: "03",
      title: "Expert review with full transparency",
      desc: "Every finding is reviewed by an analyst who can include, skip, or challenge it. AI-generated insights are verified against real-world knowledge.",
      detail: "Statistical sampling to ISO 19011 standards. Nothing goes to the client unchecked.",
    },
    {
      num: "04",
      title: "We engage with your suppliers",
      desc: "We don't just flag problems — we contact your suppliers, facilitate conversations, and help them improve. Suppliers who meet our standards earn the Hemera Verified badge.",
      detail: "Collaboration, not auditing. Making sustainability accessible.",
    },
    {
      num: "05",
      title: "You receive your HemeraScope report",
      desc: "Carbon footprint, supplier ESG profiles, uncertainty analysis, and recommended actions — all in one beautifully designed, interactive report.",
      detail: "Dashboard + branded PDF. Every number traceable to its source.",
    },
  ];

  return (
    <section ref={ref} className="py-28 px-6 relative overflow-hidden">
      {/* Soft background gradient */}
      <div className="absolute inset-0" style={{
        background: "linear-gradient(180deg, #F5F5F0 0%, #FAFDF9 50%, #F5F5F0 100%)",
      }} />

      <div className="relative z-10 max-w-5xl mx-auto">
        <div className="text-center mb-20">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate"
            style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out" }}>
            How it works
          </h2>
          <p className="mt-4 text-muted text-lg max-w-xl mx-auto"
            style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.1s" }}>
            From upload to insight in days, not months. Collaboration at every step.
          </p>
        </div>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[27px] md:left-1/2 md:-translate-x-px top-0 bottom-0 w-[2px] bg-gradient-to-b from-teal/30 via-teal/15 to-transparent" />

          {steps.map((step, i) => (
            <div
              key={step.num}
              className={`relative flex items-start gap-6 md:gap-12 mb-16 last:mb-0 ${i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"}`}
              style={{
                opacity: inView ? 1 : 0,
                transform: inView ? "translateY(0)" : "translateY(30px)",
                transition: `all 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${i * 0.15}s`,
              }}
            >
              {/* Number circle */}
              <div className="flex-shrink-0 w-14 h-14 rounded-full bg-white border-2 border-teal/20 flex items-center justify-center shadow-sm z-10 md:absolute md:left-1/2 md:-translate-x-1/2">
                <span className="text-teal text-sm font-bold">{step.num}</span>
              </div>

              {/* Content */}
              <div className={`flex-1 bg-white rounded-2xl border border-slate/8 p-6 shadow-sm hover:shadow-md transition-shadow ${i % 2 === 0 ? "md:mr-[calc(50%+2rem)]" : "md:ml-[calc(50%+2rem)]"}`}>
                <h3 className="text-lg font-bold text-slate">{step.title}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">{step.desc}</p>
                <p className="mt-2 text-xs text-teal/70 font-medium">{step.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  VIDEO — Placeholder section                                        */
/* ================================================================== */

function Video() {
  const { ref, inView } = useInView(0.2);

  return (
    <section ref={ref} id="video" className="py-28 px-6 bg-slate relative overflow-hidden">
      {/* Subtle animated gradient */}
      <div className="absolute inset-0 opacity-30" style={{
        background: "radial-gradient(ellipse 80% 50% at 50% 50%, rgba(13, 148, 136, 0.15), transparent)",
      }} />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out" }}>
          See HemeraScope in action
        </h2>
        <p className="text-white/50 text-lg mb-12"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.1s" }}>
          Watch how we turn your spend data into actionable supply chain intelligence.
        </p>

        {/* Video placeholder */}
        <div
          className="relative aspect-video bg-white/5 border border-white/10 rounded-2xl overflow-hidden group cursor-pointer hover:border-teal/30 transition-colors"
          style={{
            opacity: inView ? 1 : 0,
            transform: inView ? "translateY(0) scale(1)" : "translateY(30px) scale(0.97)",
            transition: "all 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s",
          }}
        >
          {/* Placeholder pattern */}
          <div className="absolute inset-0 opacity-5" style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
            backgroundSize: "24px 24px",
          }} />

          {/* Play button */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-20 h-20 rounded-full bg-teal/90 flex items-center justify-center group-hover:scale-110 group-hover:bg-teal transition-all duration-300 shadow-2xl shadow-teal/30">
              <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 20 20">
                <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
              </svg>
            </div>
          </div>

          {/* Duration badge */}
          <div className="absolute bottom-4 right-4 px-3 py-1 rounded-lg bg-black/40 backdrop-blur-sm text-white text-xs font-medium">
            3:24
          </div>
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  SCIENCE — Academic rigor section                                   */
/* ================================================================== */

function Science() {
  const { ref, inView } = useInView(0.1);

  const standards = [
    { name: "GHG Protocol", desc: "Corporate Standard & Scope 3 calculation methodology", category: "Carbon" },
    { name: "DEFRA", desc: "UK Government emission factors (annually updated)", category: "Carbon" },
    { name: "ISO 19011", desc: "Statistical sampling for quality control audits", category: "Quality" },
    { name: "SBTi", desc: "Science Based Targets initiative alignment", category: "Targets" },
    { name: "Pedigree Matrix", desc: "5-dimension data quality scoring (Weidema et al.)", category: "Uncertainty" },
    { name: "Monte Carlo", desc: "Uncertainty propagation with confidence intervals", category: "Uncertainty" },
  ];

  return (
    <section ref={ref} className="py-28 px-6 relative">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          {/* Left — copy */}
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate/5 border border-slate/10 mb-6"
              style={{ opacity: inView ? 1 : 0, transition: "all 0.6s ease-out" }}>
              <span className="text-slate text-[11px] font-bold uppercase tracking-[2px]">Academic Standards</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate leading-tight"
              style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.1s" }}>
              Rigorous by design.
              <br />
              <span className="text-teal">Not by accident.</span>
            </h2>
            <p className="mt-6 text-muted leading-relaxed"
              style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.2s" }}>
              Every carbon figure comes with a confidence interval. Every supplier finding is traceable
              to a public registry. Every quality control check follows ISO 19011 sampling standards.
            </p>
            <p className="mt-4 text-muted leading-relaxed"
              style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.3s" }}>
              We believe sustainability data should be as trustworthy as financial data.
              That&apos;s why we quantify uncertainty instead of hiding it — and why our reports
              stand up to boardroom scrutiny.
            </p>
          </div>

          {/* Right — standards grid */}
          <div className="grid grid-cols-2 gap-3">
            {standards.map((std, i) => (
              <div
                key={std.name}
                className="group bg-white border border-slate/8 rounded-xl p-5 hover:border-teal/20 hover:shadow-md transition-all duration-300"
                style={{
                  opacity: inView ? 1 : 0,
                  transform: inView ? "translateY(0)" : "translateY(20px)",
                  transition: `all 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${0.2 + i * 0.08}s`,
                }}
              >
                <span className="text-[9px] font-bold uppercase tracking-[1px] text-teal bg-teal/8 px-2 py-0.5 rounded-full">
                  {std.category}
                </span>
                <h4 className="text-sm font-bold text-slate mt-2">{std.name}</h4>
                <p className="text-xs text-muted mt-1 leading-relaxed">{std.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  COLLABORATION — Not auditing                                       */
/* ================================================================== */

function Collaboration() {
  const { ref, inView } = useInView(0.2);

  return (
    <section ref={ref} className="py-28 px-6 relative overflow-hidden">
      <div className="absolute inset-0" style={{
        background: "linear-gradient(135deg, rgba(13, 148, 136, 0.03) 0%, rgba(245, 158, 11, 0.02) 50%, rgba(13, 148, 136, 0.03) 100%)",
      }} />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate leading-tight"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out" }}>
          Collaboration, not auditing.
        </h2>
        <p className="mt-6 text-muted text-lg leading-relaxed max-w-2xl mx-auto"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.1s" }}>
          Every supply chain has areas for improvement. Our job isn&apos;t to judge — it&apos;s to help.
          When we find a gap, we don&apos;t just flag it. We reach out to your suppliers, facilitate the conversation,
          and work together toward a solution.
        </p>

        <div className="grid sm:grid-cols-3 gap-6 mt-16">
          {[
            {
              title: "For your business",
              items: ["Full Scope 1, 2 & 3 footprint", "Boardroom-ready reports", "Reduction roadmap with ROI", "SBTi-aligned target setting"],
              accent: "teal",
            },
            {
              title: "For your suppliers",
              items: ["Free ESG assessment", "Guided improvement pathway", "Hemera Verified badge", "Access to sustainability resources"],
              accent: "emerald",
            },
            {
              title: "For the planet",
              items: ["Measurable emissions reduction", "Supply chain transparency", "Evidence-based sustainability", "Accessible to all organisations"],
              accent: "amber",
            },
          ].map((col, i) => (
            <div
              key={col.title}
              className="text-left bg-white rounded-2xl border border-slate/8 p-8 hover:shadow-lg transition-all duration-300"
              style={{
                opacity: inView ? 1 : 0,
                transform: inView ? "translateY(0)" : "translateY(30px)",
                transition: `all 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${0.2 + i * 0.1}s`,
              }}
            >
              <h3 className="text-lg font-bold text-slate mb-4">{col.title}</h3>
              <ul className="space-y-3">
                {col.items.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-muted">
                    <svg className={`w-4 h-4 flex-shrink-0 mt-0.5 ${col.accent === "teal" ? "text-teal" : col.accent === "emerald" ? "text-emerald-500" : "text-amber"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  ABOUT — Who we are                                                 */
/* ================================================================== */

function About() {
  const { ref, inView } = useInView(0.2);

  return (
    <section ref={ref} className="py-28 px-6 bg-slate relative overflow-hidden">
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
        backgroundSize: "32px 32px",
      }} />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-6"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out" }}>
          About Hemera Intelligence
        </h2>
        <p className="text-white/60 text-lg leading-relaxed max-w-2xl mx-auto"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.1s" }}>
          Named after the Greek goddess of daylight, Hemera Intelligence was founded on a simple belief:
          supply chain sustainability should be transparent, rigorous, and accessible to all.
        </p>
        <p className="text-white/40 text-base leading-relaxed max-w-2xl mx-auto mt-4"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.2s" }}>
          We combine academic rigour with cutting-edge technology to deliver supply chain intelligence
          that stands up to scrutiny. Our approach is collaborative — we work with your suppliers,
          not against them — because real sustainability happens through partnership.
        </p>

        <div className="flex items-center justify-center gap-6 mt-12"
          style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease-out 0.3s" }}>
          <Link
            href="#demo"
            className="px-8 py-4 bg-teal text-white rounded-xl font-semibold text-sm hover:bg-teal/90 transition-colors"
          >
            Get in Touch
          </Link>
          <Link
            href="/sign-up"
            className="px-8 py-4 border border-white/20 text-white rounded-xl font-semibold text-sm hover:bg-white/5 transition-colors"
          >
            Create Account
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  CTA — Final call to action                                         */
/* ================================================================== */

function CTA() {
  const { ref, inView } = useInView(0.3);

  return (
    <section ref={ref} id="demo" className="py-28 px-6 relative">
      <div className="absolute inset-0" style={{
        background: "radial-gradient(ellipse 70% 50% at 50% 50%, rgba(13, 148, 136, 0.06), transparent)",
      }} />

      <div className="relative z-10 max-w-3xl mx-auto text-center"
        style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0) scale(1)" : "translateY(20px) scale(0.98)", transition: "all 0.8s cubic-bezier(0.16, 1, 0.3, 1)" }}>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate leading-tight">
          Ready to bring daylight
          <br />
          to your supply chain?
        </h2>
        <p className="mt-6 text-muted text-lg max-w-xl mx-auto">
          Book a 20-minute demo and see how HemeraScope can transform your supply chain sustainability.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mt-10">
          <Link
            href="mailto:hello@hemera.earth"
            className="group relative px-10 py-4 bg-teal text-white rounded-xl font-semibold text-sm overflow-hidden transition-all hover:shadow-xl hover:shadow-teal/20 hover:-translate-y-0.5"
          >
            <span className="relative z-10">Book a Demo</span>
            <div className="absolute inset-0 bg-gradient-to-r from-teal to-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link
            href="/sign-up"
            className="px-10 py-4 border border-slate/15 text-slate rounded-xl font-semibold text-sm hover:border-teal/30 hover:bg-teal/3 transition-all"
          >
            Start Free
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ================================================================== */
/*  NAV — Sticky navigation bar                                        */
/* ================================================================== */

function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? "bg-white/80 backdrop-blur-xl border-b border-slate/8 shadow-sm" : "bg-transparent"
    }`}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-teal" />
          <span className="text-slate text-sm font-bold tracking-wide">Hemera</span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm text-muted">
          <a href="#video" className="hover:text-slate transition-colors">Product</a>
          <a href="#demo" className="hover:text-slate transition-colors">About</a>
          <Link href="/sign-in" className="hover:text-slate transition-colors">Sign In</Link>
          <Link
            href="#demo"
            className="px-5 py-2 bg-teal text-white rounded-lg font-semibold text-xs hover:bg-teal/90 transition-colors"
          >
            Book a Demo
          </Link>
        </div>
      </div>
    </nav>
  );
}

/* ================================================================== */
/*  FOOTER                                                             */
/* ================================================================== */

function Footer() {
  return (
    <footer className="border-t border-slate/8 py-12 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-teal" />
          <span className="text-slate text-sm font-bold">Hemera Intelligence</span>
        </div>

        <div className="flex items-center gap-6 text-xs text-muted">
          <span>Helping organisations build transparent, resilient supply chains.</span>
        </div>

        <div className="text-xs text-muted">
          © 2026 Hemera Intelligence Ltd
        </div>
      </div>
    </footer>
  );
}

/* ================================================================== */
/*  PAGE                                                               */
/* ================================================================== */

export default function LandingPage() {
  // Custom cursor glow
  const glowRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (glowRef.current) {
      glowRef.current.style.left = `${e.clientX}px`;
      glowRef.current.style.top = `${e.clientY}px`;
    }
  }, []);

  return (
    <div className="relative overflow-hidden bg-paper" onMouseMove={handleMouseMove}>
      {/* Mouse glow effect */}
      <div
        ref={glowRef}
        className="pointer-events-none fixed w-[500px] h-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full z-[1] opacity-[0.04]"
        style={{
          background: "radial-gradient(circle, rgba(13, 148, 136, 0.8), transparent 70%)",
          transition: "left 0.3s ease-out, top 0.3s ease-out",
        }}
      />

      <Nav />
      <Hero />
      <Stats />
      <HemeraScope />
      <Approach />
      <Video />
      <Science />
      <Collaboration />
      <About />
      <CTA />
      <Footer />

      {/* Global animation keyframes */}
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes scrollDot {
          0%, 100% { transform: translateY(0); opacity: 0.4; }
          50% { transform: translateY(6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
