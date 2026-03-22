'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AuthGuard from '@/components/layout/AuthGuard';
import { getCompany, type CompanyDetail } from '@/lib/api';
import { toTitleCase, formatDate, formatJurisdiction, formatCompanyType } from '@/lib/format';
import CompanyHeader from '@/components/company/CompanyHeader';
import PdfExportButton from '@/components/company/PdfExportButton';
import OfficersTab from '@/components/company/tabs/OfficersTab';
import PscsTab from '@/components/company/tabs/PscsTab';
import FilingsTab from '@/components/company/tabs/FilingsTab';
import ScreeningTab from '@/components/company/tabs/ScreeningTab';
import OwnershipChart from '@/components/ownership/OwnershipChart';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import clsx from 'clsx';

type Tab = 'overview' | 'officers' | 'pscs' | 'filings' | 'ownership' | 'screening';

const TABS: { id: Tab; label: string; alert?: boolean }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'officers', label: 'Officers' },
  { id: 'pscs', label: 'PSCs' },
  { id: 'filings', label: 'Filings' },
  { id: 'ownership', label: 'Ownership' },
  { id: 'screening', label: '🔍 Screening' },
];

export default function CompanyPage() {
  const { number } = useParams<{ number: string }>();
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('overview');

  useEffect(() => {
    getCompany(number)
      .then(setCompany)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [number]);

  return (
    <AuthGuard>
      {loading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
      {error && <ErrorBanner message={error} />}
      {company && (
        <>
          <CompanyHeader company={company} />

          {/* Actions */}
          <div className="flex justify-end mb-4">
            <PdfExportButton company={company} />
          </div>

          {/* Tab bar */}
          <div className="flex gap-1 border-b border-gray-200 mb-6 overflow-x-auto">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={clsx(
                  'px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px',
                  tab === t.id
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {tab === 'overview' && <OverviewTab company={company} />}
          {tab === 'officers' && <OfficersTab companyNumber={number} />}
          {tab === 'pscs' && <PscsTab companyNumber={number} />}
          {tab === 'filings' && <FilingsTab companyNumber={number} />}
          {tab === 'ownership' && <OwnershipChart companyNumber={number} />}
          {tab === 'screening' && (
            <ScreeningTab companyNumber={number} companyName={company.company_name} />
          )}
        </>
      )}
    </AuthGuard>
  );
}

function OverviewTab({ company }: { company: CompanyDetail }) {
  const addr = company.registered_office_address;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <InfoCard title="Registered Address">
        {addr ? (
          <address className="not-italic text-sm text-gray-700 leading-relaxed">
            {Object.values(addr).filter(Boolean).join(', ')}
          </address>
        ) : <p className="text-sm text-gray-400">Not available</p>}
      </InfoCard>

      <InfoCard title="Status">
        <div className="space-y-1 text-sm">
          <p>Status: <strong>{toTitleCase(company.company_status ?? '—')}</strong></p>
          <p>Type: <strong>{formatCompanyType(company.company_type)}</strong></p>
          <p>Jurisdiction: <strong>{formatJurisdiction(company.jurisdiction)}</strong></p>
          {company.date_of_creation && <p>Incorporated: <strong>{formatDate(company.date_of_creation)}</strong></p>}
          {company.date_of_cessation && <p>Dissolved: <strong>{formatDate(company.date_of_cessation)}</strong></p>}
        </div>
      </InfoCard>

      {company.sic_codes && company.sic_codes.length > 0 && (
        <InfoCard title="SIC Codes">
          <div className="flex flex-wrap gap-2">
            {company.sic_codes.map(c => (
              <span key={c} className="badge badge-gray">{c}</span>
            ))}
          </div>
        </InfoCard>
      )}

      <InfoCard title="Incorporation Documents">
        <div className="space-y-2 text-sm">
          <a
            href={`https://find-and-update.company-information.service.gov.uk/company/${company.company_number}/filing-history?type=incorporation`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-brand-600 hover:underline"
          >
            View incorporation filing on Companies House
          </a>
          <a
            href={`https://find-and-update.company-information.service.gov.uk/company/${company.company_number}/filing-history`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-brand-600 hover:underline"
          >
            Full filing history
          </a>
        </div>
      </InfoCard>
    </div>
  );
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">{title}</h3>
      {children}
    </div>
  );
}
