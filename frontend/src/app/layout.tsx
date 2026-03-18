import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import './globals.css'
import { GraduationCap, User, BarChart3, Map } from 'lucide-react'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SkillBridge Navigator',
  description: 'AI-powered career guidance using knowledge graphs',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="border-b bg-white">
          <div className="container mx-auto flex h-16 items-center justify-between px-4">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl">
              <GraduationCap className="h-8 w-8 text-blue-600" />
              <span>SkillBridge</span>
            </Link>
            <div className="flex items-center gap-6">
              <Link href="/profile" className="flex items-center gap-2 text-sm hover:text-blue-600">
                <User className="h-4 w-4" />
                Profile
              </Link>
              <Link href="/analyze" className="flex items-center gap-2 text-sm hover:text-blue-600">
                <BarChart3 className="h-4 w-4" />
                Analyze
              </Link>
              <Link href="/roadmap" className="flex items-center gap-2 text-sm hover:text-blue-600">
                <Map className="h-4 w-4" />
                Roadmap
              </Link>
            </div>
          </div>
        </nav>
        <main>{children}</main>
        <footer className="border-t bg-white py-6">
          <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
            SkillBridge Navigator - Powered by Knowledge Graphs & AI
          </div>
        </footer>
      </body>
    </html>
  )
}
