'use client';

import { useState } from 'react';
import {
  getOfficers, getPscs, getFilings, getScreening,
  type CompanyDetail, type Officer, type Psc, type Filing, type ScreeningResult,
} from '@/lib/api';
import { toTitleCase, formatDate, formatJurisdiction, formatCompanyType, formatRole, formatKind } from '@/lib/format';

function controlLabel(s: string): string {
  return s.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function riskColor(label: string | undefined): string {
  if (label === 'HIGH') return '#c62828';
  if (label === 'MEDIUM') return '#f57f17';
  return '#2e7d32';
}

function buildScreeningSection(s: ScreeningResult | null): string {
  if (!s) return '';

  const sanctionsHits = s.sanctions.filter(r => r.match);
  const sanctionsSummary = sanctionsHits.length > 0
    ? sanctionsHits.map(r => `<span class="risk">HIT: ${toTitleCase(r.name)}</span>`).join(' ')
    : `<span style="color:#2e7d32">✓ No matches (${s.screened_names} names checked)</span>`;

  const pepSummary = s.pep_indicators.length > 0
    ? s.pep_indicators.map(p => `${toTitleCase(p.name)} (${p.role ?? p.type})`).join(', ')
    : '<span style="color:#2e7d32">✓ None detected</span>';

  const countrySummary = s.country_risks.length > 0
    ? s.country_risks.map(c => `${toTitleCase(c.country)} [${c.risk === 'high' ? 'High Risk' : 'Elevated'}]`).join(', ')
    : '<span style="color:#2e7d32">✓ None</span>';

  const topSectorRisk = s.sector_risks.find(r => r.risk === 'high') ?? s.sector_risks.find(r => r.risk === 'medium');
  const sectorSummary = topSectorRisk
    ? `${topSectorRisk.risk.toUpperCase()}: ${s.sector_risks.map(r => r.sector_label).join(', ')}`
    : '<span style="color:#2e7d32">✓ Low risk sectors</span>';

  const articles = s.adverse_media?.articles ?? [];
  const mediaSummary = articles.length > 0
    ? `${articles.length} article${articles.length > 1 ? 's' : ''} indexed: ${articles.slice(0, 3).map(a => a.title).join(' | ')}`
    : '<span style="color:#2e7d32">✓ No articles indexed (past 12 months)</span>';

  return `
<h2>Compliance Screening</h2>
<div class="card" style="margin-bottom:16px;border-left:4px solid ${riskColor(s.overall_label)}">
  <div style="display:flex;align-items:center;gap:16px">
    <div>
      <div class="label">Overall Risk</div>
      <div style="font-size:18pt;font-weight:700;color:${riskColor(s.overall_label)}">${s.overall_label}</div>
    </div>
    <div style="width:52px;height:52px;border-radius:50%;background:${riskColor(s.overall_label)}20;border:2px solid ${riskColor(s.overall_label)};display:flex;align-items:center;justify-content:center;font-weight:700;color:${riskColor(s.overall_label)}">
      ${s.overall_score}
    </div>
  </div>
</div>
<table>
  <tbody>
    <tr><th style="width:160px;background:#f9fafb">Sanctions</th><td>${sanctionsSummary}</td></tr>
    <tr><th style="background:#f9fafb">PEP Indicators</th><td>${pepSummary}</td></tr>
    <tr><th style="background:#f9fafb">Country Risk</th><td>${countrySummary}</td></tr>
    <tr><th style="background:#f9fafb">Sector Risk</th><td>${sectorSummary}</td></tr>
    <tr><th style="background:#f9fafb">Adverse Media</th><td>${mediaSummary}</td></tr>
  </tbody>
</table>
<p style="font-size:8.5pt;color:#999;margin-top:4px">
  Sanctions: ${s.sanctions_api_source} &nbsp;·&nbsp;
  Country: ${s.country_source} &nbsp;·&nbsp;
  Sector: ${s.sector_source}
</p>`;
}

function buildPrintHtml(
  company: CompanyDetail,
  officers: Officer[],
  pscs: Psc[],
  filings: Filing[],
  screening: ScreeningResult | null,
): string {
  const addr = company.registered_office_address;
  const addrLine = addr ? Object.values(addr).filter(Boolean).join(', ') : '—';
  const activeOfficers = officers.filter(o => !o.resigned_on);
  const resignedOfficers = officers.filter(o => o.resigned_on);
  const activePs = pscs.filter(p => !p.ceased_on);
  const ceasedPs = pscs.filter(p => p.ceased_on);
  const generatedAt = new Date().toLocaleString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>KYC Report — ${toTitleCase(company.company_name)}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11pt; color: #111; line-height: 1.5; padding: 24px; }
    .confidential { font-size: 8.5pt; color: #aaa; text-align: right; letter-spacing: 0.1em; margin-bottom: 8px; }
    h1 { font-size: 18pt; margin-bottom: 4px; }
    h2 { font-size: 13pt; margin: 20px 0 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
    h3 { font-size: 11pt; margin: 12px 0 4px; color: #555; }
    .meta { color: #555; font-size: 10pt; margin-bottom: 4px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    .card { border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; }
    .label { font-size: 9pt; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
    .value { font-size: 11pt; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
    th { text-align: left; font-size: 9pt; color: #666; border-bottom: 1px solid #e0e0e0; padding: 4px 8px; }
    td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; font-size: 10pt; vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    .badge { display: inline-block; background: #e8f4fd; color: #1565c0; border-radius: 12px; padding: 1px 8px; font-size: 8.5pt; margin: 1px; }
    .faded { color: #999; }
    .risk { background: #fdecea; color: #c62828; border: 1px solid #f5c6c6; border-radius: 12px; padding: 1px 8px; font-size: 8.5pt; margin: 1px; display: inline-block; }
    .footer { margin-top: 24px; font-size: 8.5pt; color: #999; border-top: 1px solid #e0e0e0; padding-top: 8px; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>

<p class="confidential">CONFIDENTIAL — FOR COMPLIANCE USE ONLY</p>

<h1>${toTitleCase(company.company_name)}</h1>
<p class="meta">Company No: ${company.company_number} &nbsp;|&nbsp; ${formatCompanyType(company.company_type)} &nbsp;|&nbsp; ${toTitleCase(company.company_status ?? '—')}</p>
<p class="meta">${addrLine}</p>
${company.risk_flags && company.risk_flags.length > 0
  ? `<p style="margin-top:8px">${company.risk_flags.map(f => `<span class="risk">⚠ ${f}</span>`).join(' ')}</p>`
  : ''}

<div class="grid" style="margin-top:16px">
  <div class="card"><div class="label">Incorporated</div><div class="value">${formatDate(company.date_of_creation)}</div></div>
  <div class="card"><div class="label">Jurisdiction</div><div class="value">${formatJurisdiction(company.jurisdiction)}</div></div>
  <div class="card"><div class="label">Officers</div><div class="value">${company.total_officers}</div></div>
  <div class="card"><div class="label">PSCs</div><div class="value">${company.total_pscs}</div></div>
</div>

${company.accounts_overdue || company.confirmation_statement_overdue || company.has_charges || company.has_insolvency_history ? `
<div class="grid">
  ${company.accounts_overdue ? '<div class="card"><div class="label">Accounts</div><div style="color:#c62828;font-weight:600">OVERDUE</div></div>' : ''}
  ${company.confirmation_statement_overdue ? '<div class="card"><div class="label">Confirmation Statement</div><div style="color:#c62828;font-weight:600">OVERDUE</div></div>' : ''}
  ${company.has_charges ? '<div class="card"><div class="label">Charges</div><div style="color:#c62828;font-weight:600">Yes</div></div>' : ''}
  ${company.has_insolvency_history ? '<div class="card"><div class="label">Insolvency History</div><div style="color:#c62828;font-weight:600">Yes</div></div>' : ''}
</div>` : ''}

${company.sic_codes && company.sic_codes.length > 0 ? `<p class="meta">SIC Codes: ${company.sic_codes.join(', ')}</p>` : ''}

${buildScreeningSection(screening)}

<h2>Officers (${officers.length})</h2>
${activeOfficers.length > 0 ? `
<table>
  <thead><tr><th>Name</th><th>Role</th><th>Appointed</th><th>Nationality</th></tr></thead>
  <tbody>
    ${activeOfficers.map(o => `<tr>
      <td>${toTitleCase(o.name)}</td>
      <td>${formatRole(o.role)}</td>
      <td>${formatDate(o.appointed_on)}</td>
      <td>${toTitleCase(o.nationality ?? '—')}</td>
    </tr>`).join('')}
  </tbody>
</table>` : '<p class="faded" style="font-size:10pt">No active officers.</p>'}

${resignedOfficers.length > 0 ? `
<h3 class="faded">Resigned (${resignedOfficers.length})</h3>
<table>
  <thead><tr><th>Name</th><th>Role</th><th>Appointed</th><th>Resigned</th></tr></thead>
  <tbody>
    ${resignedOfficers.map(o => `<tr class="faded">
      <td>${toTitleCase(o.name)}</td>
      <td>${formatRole(o.role)}</td>
      <td>${formatDate(o.appointed_on)}</td>
      <td>${formatDate(o.resigned_on)}</td>
    </tr>`).join('')}
  </tbody>
</table>` : ''}

<h2>Persons with Significant Control (${pscs.length})</h2>
${activePs.length > 0 ? `
<table>
  <thead><tr><th>Name</th><th>Kind</th><th>Notified</th><th>Control</th></tr></thead>
  <tbody>
    ${activePs.map(p => `<tr>
      <td>${toTitleCase(p.name)}${p.linked_company_number ? ` <span class="meta">(${p.linked_company_number})</span>` : ''}</td>
      <td>${formatKind(p.kind)}</td>
      <td>${formatDate(p.notified_on)}</td>
      <td>${(p.natures_of_control ?? []).map(n => `<span class="badge">${controlLabel(n)}</span>`).join(' ')}</td>
    </tr>`).join('')}
  </tbody>
</table>` : '<p class="faded" style="font-size:10pt">No active PSCs.</p>'}

${ceasedPs.length > 0 ? `
<h3 class="faded">Ceased (${ceasedPs.length})</h3>
<table>
  <thead><tr><th>Name</th><th>Kind</th><th>Notified</th><th>Ceased</th></tr></thead>
  <tbody>
    ${ceasedPs.map(p => `<tr class="faded">
      <td>${toTitleCase(p.name)}</td>
      <td>${formatKind(p.kind)}</td>
      <td>${formatDate(p.notified_on)}</td>
      <td>${formatDate(p.ceased_on)}</td>
    </tr>`).join('')}
  </tbody>
</table>` : ''}

<h2>Filing History (${filings.length})</h2>
${filings.length > 0 ? `
<table>
  <thead><tr><th>Date</th><th>Description</th><th>Type</th></tr></thead>
  <tbody>
    ${filings.map(f => `<tr>
      <td style="white-space:nowrap">${formatDate(f.date)}</td>
      <td>${toTitleCase(f.description ?? f.type ?? '')}</td>
      <td><span style="font-size:9pt;color:#555">${f.type ?? ''}</span></td>
    </tr>`).join('')}
  </tbody>
</table>` : '<p class="faded" style="font-size:10pt">No filings found.</p>'}

<div class="footer">
  Generated by KYC Search &nbsp;|&nbsp; ${generatedAt}
  &nbsp;|&nbsp; Source: <a href="https://find-and-update.company-information.service.gov.uk/company/${company.company_number}">Companies House</a>
</div>

</body>
</html>`;
}

export default function PdfExportButton({ company }: { company: CompanyDetail }) {
  const [loading, setLoading] = useState(false);

  async function handleExport() {
    setLoading(true);
    try {
      const [officers, pscs, filings, screening] = await Promise.all([
        getOfficers(company.company_number),
        getPscs(company.company_number),
        getFilings(company.company_number),
        getScreening(company.company_number).catch(() => null),
      ]);

      const html = buildPrintHtml(company, officers, pscs, filings, screening);
      const win = window.open('', '_blank');
      if (!win) return;
      win.document.write(html);
      win.document.close();
      win.focus();
      setTimeout(() => win.print(), 400);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="btn-secondary text-sm flex items-center gap-1.5"
    >
      {loading ? (
        <>
          <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Preparing...
        </>
      ) : (
        <>
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v3a1 1 0 001 1h16a1 1 0 001-1v-3M3 7l9-4 9 4M3 7v10M21 7v10" />
          </svg>
          Export PDF
        </>
      )}
    </button>
  );
}
