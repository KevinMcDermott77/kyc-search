'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getScreening,
  listCases,
  createCase,
  type ScreeningResult,
  type SanctionsResult,
  type PepIndicator,
  type CountryRisk,
  type SectorRisk,
  type AdverseMediaArticle,
  type CaseListItem,
} from '@/lib/api';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import { toTitleCase, formatDate } from '@/lib/format';

// ── Risk colour helpers ──────────────────────────────────────────────────────

const RISK_PALETTE = {
  HIGH:     { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700',    badge: 'bg-red-100 text-red-800',    dot: 'bg-red-500'    },
  MEDIUM:   { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  LOW:      { bg: 'bg-green-50',  border: 'border-green-200',  text: 'text-green-700',  badge: 'bg-green-100 text-green-800',  dot: 'bg-green-500'  },
  elevated: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-800', dot: 'bg-orange-400' },
  high:     { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700',    badge: 'bg-red-100 text-red-800',    dot: 'bg-red-500'    },
  medium:   { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  low:      { bg: 'bg-green-50',  border: 'border-green-200',  text: 'text-green-700',  badge: 'bg-green-100 text-green-800',  dot: 'bg-green-500'  },
} as const;

type PaletteKey = keyof typeof RISK_PALETTE;

function rp(key: string): typeof RISK_PALETTE[PaletteKey] {
  return RISK_PALETTE[key as PaletteKey] ?? RISK_PALETTE.LOW;
}

// ── Sub-components ───────────────────────────────────────────────────────────

function Section({ title, icon, children, count, alert }: {
  title: string;
  icon: string;
  children: React.ReactNode;
  count?: number;
  alert?: boolean;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <span>{icon}</span> {title}
        </h3>
        {count !== undefined && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            alert && count > 0
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-500'
          }`}>
            {count}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function SourceNote({ label }: { label: string }) {
  return (
    <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-gray-100">
      Source: {label}
    </p>
  );
}

function RiskDot({ risk }: { risk: string }) {
  const p = rp(risk);
  return <span className={`inline-block w-2 h-2 rounded-full ${p.dot} flex-shrink-0 mt-1`} />;
}

// ── Overall risk score ───────────────────────────────────────────────────────

export function RiskScoreCard({ result }: { result: ScreeningResult }) {
  const p = rp(result.overall_label);
  const pct = result.overall_score;
  return (
    <div className={`card p-6 border-2 ${p.border}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Overall screening risk</p>
          <p className={`text-3xl font-bold ${p.text}`}>{result.overall_label}</p>
        </div>
        <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold ${p.bg} ${p.text} border-2 ${p.border}`}>
          {pct}
        </div>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2.5 mb-2">
        <div
          className={`h-2.5 rounded-full transition-all ${
            result.overall_label === 'HIGH' ? 'bg-red-500' :
            result.overall_label === 'MEDIUM' ? 'bg-yellow-400' : 'bg-green-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-400">
        Score: {pct}/100 &nbsp;·&nbsp; {result.screened_names} names checked against OFSI sanctions list
      </p>
    </div>
  );
}

// ── Sanctions ────────────────────────────────────────────────────────────────

export function SanctionsSection({ data, source }: { data: SanctionsResult[]; source: string }) {
  const hits = data.filter(d => d.match);
  const clean = data.filter(d => !d.match);

  return (
    <Section title="Sanctions Screening" icon="🔴" count={hits.length} alert={hits.length > 0}>
      {hits.length === 0 && clean.length > 0 && (
        <div className="flex items-center gap-2 text-green-700 text-sm bg-green-50 rounded-lg px-3 py-2 mb-3">
          <span>✓</span>
          <span>No matches found on UK OFSI consolidated sanctions list for any screened name.</span>
        </div>
      )}
      {hits.length > 0 && (
        <div className="space-y-2 mb-3">
          {hits.map((r, i) => (
            <div key={i} className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="font-semibold text-red-800 text-sm">{toTitleCase(r.name)}</p>
              <p className="text-xs text-red-600 mb-2">Type: {r.type}</p>
              {r.hits.map((h, j) => (
                <div key={j} className="text-xs bg-red-100 rounded p-2 mt-1">
                  <p><strong>Regime:</strong> {h.regime}</p>
                  <p><strong>Entity type:</strong> {h.entity_type}</p>
                  <p><strong>Reference:</strong> {h.unique_id}</p>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      <details className="text-xs text-gray-400 cursor-pointer">
        <summary className="hover:text-gray-600">Screened names ({data.length})</summary>
        <ul className="mt-2 space-y-0.5 pl-2">
          {data.map((r, i) => (
            <li key={i} className="flex items-center gap-2">
              <span>{r.match ? '🔴' : '✓'}</span>
              <span>{toTitleCase(r.name)} <span className="text-gray-300">({r.type})</span></span>
            </li>
          ))}
        </ul>
      </details>
      <SourceNote label={source} />
    </Section>
  );
}

// ── PEP ──────────────────────────────────────────────────────────────────────

export function PepSection({ data, source }: { data: PepIndicator[]; source: string }) {
  return (
    <Section title="PEP Indicators" icon="🏛️" count={data.length} alert={data.length > 0}>
      {data.length === 0 ? (
        <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
          ✓ No politically exposed person indicators detected from occupations or roles.
        </p>
      ) : (
        <div className="space-y-2">
          {data.map((p, i) => (
            <div key={i} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="font-semibold text-sm text-gray-800">{toTitleCase(p.name)}</p>
              <p className="text-xs text-gray-500">
                {p.type === 'officer' ? 'Officer' : 'PSC'} &nbsp;·&nbsp;
                Role: {p.role ?? '—'} &nbsp;·&nbsp;
                Occupation: {p.occupation ?? '—'}
              </p>
              {p.nationality && (
                <p className="text-xs text-gray-400 mt-0.5">Nationality: {toTitleCase(p.nationality)}</p>
              )}
            </div>
          ))}
        </div>
      )}
      <p className="text-xs text-gray-400 mt-3">
        Note: PEP detection is keyword-based. Manual verification is required for confirmation.
      </p>
      <SourceNote label={source} />
    </Section>
  );
}

// ── Country risk ─────────────────────────────────────────────────────────────

export function CountryRiskSection({ data, source }: { data: CountryRisk[]; source: string }) {
  return (
    <Section title="Country Risk" icon="🌍" count={data.length} alert={data.length > 0}>
      {data.length === 0 ? (
        <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
          ✓ No officers or PSCs with nationalities or residencies in FATF high-risk or monitored jurisdictions.
        </p>
      ) : (
        <div className="space-y-2">
          {data.map((c, i) => {
            const p = rp(c.risk);
            return (
              <div key={i} className={`rounded-lg p-3 border ${p.bg} ${p.border}`}>
                <div className="flex items-start gap-2">
                  <RiskDot risk={c.risk} />
                  <div>
                    <p className={`font-semibold text-sm ${p.text}`}>{toTitleCase(c.country)}</p>
                    <p className="text-xs text-gray-500">
                      {c.list} &nbsp;·&nbsp;
                      Flagged for: {toTitleCase(c.flagged_for)} ({c.person_type})
                    </p>
                  </div>
                  <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${p.badge}`}>
                    {c.risk === 'high' ? 'High Risk' : 'Elevated'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <SourceNote label={source} />
    </Section>
  );
}

// ── Sector risk dashboard ────────────────────────────────────────────────────

export function SectorRiskSection({ data, source }: { data: SectorRisk[]; source: string }) {
  const highRisk = data.filter(s => s.risk === 'high');
  const mediumRisk = data.filter(s => s.risk === 'medium');
  const topRisk = highRisk.length > 0 ? 'high' : mediumRisk.length > 0 ? 'medium' : 'low';

  return (
    <Section title="Sector Risk Dashboard" icon="📊">
      {data.length === 0 ? (
        <p className="text-sm text-gray-400">No SIC codes registered for this company.</p>
      ) : (
        <>
          <div className={`rounded-lg p-3 mb-4 border ${rp(topRisk).bg} ${rp(topRisk).border}`}>
            <p className={`text-sm font-semibold ${rp(topRisk).text}`}>
              Sector risk level: {topRisk.toUpperCase()}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Based on {data.length} SIC code{data.length !== 1 ? 's' : ''} registered.
              {highRisk.length > 0 && ` ${highRisk.length} high-risk sector${highRisk.length > 1 ? 's' : ''}.`}
              {mediumRisk.length > 0 && ` ${mediumRisk.length} medium-risk sector${mediumRisk.length > 1 ? 's' : ''}.`}
            </p>
          </div>
          <div className="space-y-2">
            {data.map((s, i) => {
              const p = rp(s.risk);
              return (
                <div key={i} className={`rounded-lg border p-3 ${p.bg} ${p.border}`}>
                  <div className="flex items-start gap-3">
                    <RiskDot risk={s.risk} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-sm text-gray-800">{s.sector_label}</p>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${p.badge}`}>
                          {s.risk.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-400 font-mono">SIC {s.sic_code}</span>
                      </div>
                      {s.reason && (
                        <p className="text-xs text-gray-500 mt-1">{s.reason}</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {(highRisk.length > 0 || mediumRisk.length > 0) && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-500">
              <p className="font-medium text-gray-600 mb-1">Why does sector matter?</p>
              <p>
                FATF and the UK National Risk Assessment identify certain sectors as inherently higher risk
                for money laundering and terrorist financing. High-risk sectors warrant enhanced due diligence
                (EDD) and closer scrutiny of the beneficial ownership chain.
              </p>
            </div>
          )}
        </>
      )}
      <SourceNote label={source} />
    </Section>
  );
}

// ── Adverse media ─────────────────────────────────────────────────────────────

export function AdverseMediaSection({
  companyName,
  data,
}: {
  companyName: string;
  data?: { articles: AdverseMediaArticle[]; source: string; error?: string };
}) {
  const searchName = encodeURIComponent(companyName);
  const articles = data?.articles ?? [];

  function formatGdeltDate(raw: string): string {
    // GDELT date format: "20240301T120000Z"
    if (!raw || raw.length < 8) return raw;
    try {
      const y = raw.slice(0, 4);
      const m = raw.slice(4, 6);
      const d = raw.slice(6, 8);
      return formatDate(`${y}-${m}-${d}`);
    } catch {
      return raw;
    }
  }

  return (
    <Section title="Adverse Media" icon="📰" count={articles.length}>
      {data?.error && (
        <p className="text-xs text-yellow-600 bg-yellow-50 rounded px-3 py-2 mb-3">
          News index temporarily unavailable. Use the manual search links below.
        </p>
      )}

      {articles.length > 0 ? (
        <div className="space-y-2 mb-4">
          {articles.map((a, i) => (
            <a
              key={i}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg border border-gray-200 bg-gray-50 hover:bg-white hover:border-brand-300 transition-colors"
            >
              <p className="text-sm font-medium text-gray-800 leading-snug mb-1">{a.title || 'Untitled'}</p>
              <p className="text-xs text-gray-400">
                {a.domain} &nbsp;·&nbsp; {formatGdeltDate(a.date)}
                {a.sourcecountry && ` &nbsp;·&nbsp; ${a.sourcecountry}`}
              </p>
            </a>
          ))}
        </div>
      ) : (
        !data?.error && (
          <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2 mb-4">
            ✓ No news articles indexed for this company name in the past 12 months.
          </p>
        )
      )}

      <p className="text-xs text-gray-400 mb-3">
        {data?.source ? `Sourced from ${data.source} news index.` : ''} Manual verification recommended.
      </p>

      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-gray-400 self-center">Search manually:</span>
        <a href={`https://news.google.com/search?q=${searchName}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-brand-600 hover:underline bg-white border border-gray-200 rounded px-2 py-1">
          Google News ↗
        </a>
        <a href={`https://www.bbc.co.uk/search?q=${searchName}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-brand-600 hover:underline bg-white border border-gray-200 rounded px-2 py-1">
          BBC News ↗
        </a>
        <a href={`https://www.theguardian.com/search?q=${searchName}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-brand-600 hover:underline bg-white border border-gray-200 rounded px-2 py-1">
          The Guardian ↗
        </a>
        <a href={`https://www.ft.com/search?q=${searchName}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-brand-600 hover:underline bg-white border border-gray-200 rounded px-2 py-1">
          Financial Times ↗
        </a>
      </div>
    </Section>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function ScreeningTab({
  companyNumber,
  companyName,
}: {
  companyNumber: string;
  companyName: string;
}) {
  const router = useRouter();
  const [result, setResult] = useState<ScreeningResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [existingCase, setExistingCase] = useState<CaseListItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    Promise.all([
      getScreening(companyNumber),
      listCases(undefined, companyNumber),
    ])
      .then(([screening, cases]) => {
        setResult(screening);
        setExistingCase(cases[0] ?? null);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyNumber]);

  async function handleSaveCase() {
    if (!result) return;
    setSaving(true);
    setSaveError('');
    try {
      const saved = await createCase({
        company_number: companyNumber,
        company_name: companyName,
        risk_score: result.overall_score,
        risk_label: result.overall_label,
        screening_snapshot: result,
      });
      router.push(`/cases/${saved.id}`);
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save case');
      setSaving(false);
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center py-16 gap-3">
      <Spinner />
      <p className="text-sm text-gray-400">Running screening checks — querying OFSI sanctions list…</p>
    </div>
  );
  if (error) return <ErrorBanner message={error} />;
  if (!result) return null;

  return (
    <div className="space-y-4">
      {/* Action bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Screening result for <strong>{companyName}</strong></p>
        <div className="flex items-center gap-3">
          {saveError && <p className="text-xs text-red-600">{saveError}</p>}
          {existingCase ? (
            <a
              href={`/cases/${existingCase.id}`}
              className="text-sm font-medium text-brand-600 hover:underline"
            >
              View Case →
            </a>
          ) : (
            <button
              onClick={handleSaveCase}
              disabled={saving}
              className="btn-primary text-sm px-4 py-2 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save as Case'}
            </button>
          )}
        </div>
      </div>

      <RiskScoreCard result={result} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SanctionsSection data={result.sanctions} source={result.sanctions_api_source} />
        <PepSection data={result.pep_indicators} source={result.pep_source} />
        <CountryRiskSection data={result.country_risks} source={result.country_source} />
        <SectorRiskSection data={result.sector_risks} source={result.sector_source} />
      </div>

      <AdverseMediaSection companyName={companyName} data={result.adverse_media} />

      <p className="text-xs text-gray-400 text-center pt-2">
        Screening is indicative only. Results must be reviewed by a qualified compliance officer before making risk decisions.
        Sanctions data: UK OFSI via Cabinet Office API. FATF lists current as of 2025 Q1.
      </p>
    </div>
  );
}
