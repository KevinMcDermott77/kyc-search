import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kev YC',
  description: 'UK company KYC lookup — powered by Companies House',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
