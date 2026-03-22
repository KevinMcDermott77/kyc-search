import clsx from 'clsx';

interface Props {
  children: React.ReactNode;
  variant?: 'green' | 'red' | 'yellow' | 'gray' | 'blue';
  className?: string;
}

const VARIANTS = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  gray: 'bg-gray-100 text-gray-700',
  blue: 'bg-blue-100 text-blue-800',
};

export default function Badge({ children, variant = 'gray', className }: Props) {
  return (
    <span className={clsx('badge', VARIANTS[variant], className)}>
      {children}
    </span>
  );
}
