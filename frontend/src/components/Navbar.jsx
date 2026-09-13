function Navbar() {
  return (
    <nav className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-8 py-5">
      <a href="/" className="text-2xl font-bold text-blue-400">
        StudyAI
      </a>

      <div className="flex gap-6">
        <a href="/dashboard" className="text-slate-300 hover:text-white">
          Dashboard
        </a>

        <a href="/upload" className="text-slate-300 hover:text-white">
          Upload Materials
        </a>

        <a href="/chat" className="text-slate-300 hover:text-white">
          AI Chat
        </a>
      </div>
    </nav>
  )
}

export default Navbar