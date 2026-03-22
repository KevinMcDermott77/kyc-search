export function toTitleCase(str: string): string {
  if (!str) return '';
  return str.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

export function formatJurisdiction(j: string | null | undefined): string {
  if (!j) return '—';
  const map: Record<string, string> = {
    'england-wales': 'England & Wales',
    'northern-ireland': 'Northern Ireland',
    'scotland': 'Scotland',
    'wales': 'Wales',
    'england': 'England',
    'united-kingdom': 'United Kingdom',
  };
  return map[j.toLowerCase()] ?? toTitleCase(j.replace(/-/g, ' '));
}

export function formatCompanyType(type: string | null | undefined): string {
  if (!type) return '—';
  const map: Record<string, string> = {
    'ltd': 'Private Ltd',
    'plc': 'Public Ltd (PLC)',
    'llp': 'LLP',
    'private-limited-company': 'Private Ltd',
    'public-limited-company': 'Public Ltd (PLC)',
    'limited-liability-partnership': 'LLP',
    'community-interest-company': 'CIC',
    'charitable-incorporated-organisation': 'CIO',
    'registered-society-non-jurisdictional': 'Registered Society',
    'northern-ireland': 'Northern Ireland company',
    'royal-charter': 'Royal Charter',
  };
  return map[type.toLowerCase()] ?? toTitleCase(type.replace(/-/g, ' '));
}

export function formatRole(role: string | null | undefined): string {
  if (!role) return '—';
  return toTitleCase(role.replace(/-/g, ' '));
}

export function formatKind(kind: string | null | undefined): string {
  if (!kind) return '—';
  return toTitleCase(kind.replace(/-/g, ' '));
}
