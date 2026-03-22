import type { CompanyDetail } from '@/lib/api';
import Badge from '@/components/ui/Badge';
import RiskBadge from './RiskBadge';
import { toTitleCase, formatDate, formatJurisdiction, formatCompanyType } from '@/lib/format';

const CH_BASE = 'https://find-and-update.company-information.service.gov.uk/company';

function statusVariant(status: string | null): 'green' | 'red' | 'gray' {
  if (!status) return 'gray';
  if (status === 'active') return 'green';
  if (['dissolved', 'liquidation', 'receivership'].includes(status)) return 'red';
  return 'gray';
}

export default function CompanyHeader({ company }: { company: CompanyDetail }) {
  const addr = company.registered_office_address;
  const addrLine = addr
    ? [addr.address_line_1, addr.locality, addr.postal_code, addr.country].filter(Boolean).join(', ')
    : null;

  return (
    <div className="card p-6 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">{toTitleCase(company.company_name)}</h1>
          <p className="text-gray-400 text-sm mt-1 font-mono">{company.company_number}</p>
          {addrLine && <p className="text-gray-600 text-sm mt-1">{toTitleCase(addrLine)}</p>}
        </div>
        <div className="flex flex-col gap-2 sm:items-end flex-shrink-0">
          <div className="flex flex-wrap gap-2">
            <Badge variant={statusVariant(company.company_status)}>
              {toTitleCase(company.company_status ?? 'Unknown')}
            </Badge>
            {company.company_type && <Badge variant="blue">{formatCompanyType(company.company_type)}</Badge>}
          </div>
          <a
            href={`${CH_BASE}/${company.company_number}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-600 hover:text-brand-800 hover:underline font-medium"
          >
            View on Companies House ↗
          </a>
        </div>
      </div>

      {/* Risk flags */}
      {company.risk_flags && company.risk_flags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {company.risk_flags.map(flag => (
            <RiskBadge key={flag} flag={flag} />
          ))}
        </div>
      )}

      {/* Key facts */}
      <div className="mt-5 pt-4 border-t border-gray-100 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <Fact label="Incorporated" value={formatDate(company.date_of_creation)} />
        <Fact label="Officers" value={String(company.total_officers)} />
        <Fact label="PSCs" value={String(company.total_pscs)} />
        <Fact label="Jurisdiction" value={formatJurisdiction(company.jurisdiction)} />
      </div>

      {company.sic_codes && company.sic_codes.length > 0 && (
        <p className="mt-3 text-xs text-gray-400">
          SIC: {company.sic_codes.join(', ')}
        </p>
      )}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className="font-semibold text-gray-800">{value}</p>
    </div>
  );
}
