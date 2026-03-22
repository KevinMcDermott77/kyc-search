import Link from 'next/link';
import type { OwnershipNode as NodeData } from '@/lib/api';
import Badge from '@/components/ui/Badge';
import { toTitleCase } from '@/lib/format';

const CH_BASE = 'https://find-and-update.company-information.service.gov.uk/company';

function statusVariant(status: string | null): 'green' | 'red' | 'gray' {
  if (!status) return 'gray';
  if (status === 'active') return 'green';
  if (['dissolved', 'liquidation', 'receivership'].includes(status)) return 'red';
  return 'gray';
}

interface Props {
  node: NodeData;
  isRoot?: boolean;
}

export default function OwnershipNodeCard({ node, isRoot }: Props) {
  const pscUrl = `${CH_BASE}/${node.company_number}/persons-with-significant-control`;

  return (
    <div className={`bg-white rounded-lg border-2 px-4 py-3 min-w-[200px] max-w-[240px] shadow-sm text-left ${isRoot ? 'border-brand-500' : 'border-gray-200'}`}>
      <Link href={`/company/${node.company_number}`} className="block hover:text-brand-600 transition-colors">
        <p className="font-semibold text-sm text-gray-900 leading-tight">{toTitleCase(node.company_name)}</p>
        <p className="text-xs text-gray-400 mt-0.5 font-mono">{node.company_number}</p>
      </Link>
      <div className="flex items-center gap-1 mt-2 flex-wrap">
        <Badge variant={statusVariant(node.company_status)}>{toTitleCase(node.company_status ?? 'unknown')}</Badge>
        {node.percentage_label && (
          <span className="text-xs text-gray-500">{node.percentage_label}</span>
        )}
      </div>
      <div className="mt-2 flex flex-col gap-0.5">
        <a
          href={node.ch_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-brand-500 hover:text-brand-700 hover:underline"
        >
          Profile ↗
        </a>
        <a
          href={pscUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-400 hover:text-brand-600 hover:underline"
        >
          PSC register ↗
        </a>
      </div>
    </div>
  );
}
