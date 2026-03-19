import { Plus_Jakarta_Sans } from 'next/font/google'
import './globals.css'

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta',
  display: 'swap',
})

export const metadata = {
  title: 'AI Counsellor — Career Guidance',
  description: 'AI-powered career guidance for students in Uttarakhand',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={plusJakarta.variable}>
      <body className="font-sans bg-[var(--background)] text-[var(--foreground)]">{children}</body>
    </html>
  )
}
