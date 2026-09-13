function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-8 py-5">
        <h1 className="text-2xl font-bold text-blue-400">StudyAI</h1>

        <div className="flex items-center gap-4">
          <a href="/upload" className="text-slate-300 hover:text-white">
            Upload Materials
          </a>

          <a
            href="/chat"
            className="rounded-lg bg-blue-600 px-5 py-2 font-semibold hover:bg-blue-700"
          >
            Ask AI
          </a>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <h2 className="text-3xl font-bold">Welcome to StudyAI</h2>

        <p className="mt-2 text-slate-400">
          Organize your study materials and learn smarter.
        </p>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Total Courses</p>
            <h3 className="mt-3 text-4xl font-bold text-blue-400">0</h3>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Study Materials</p>
            <h3 className="mt-3 text-4xl font-bold text-blue-400">0</h3>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Questions Asked</p>
            <h3 className="mt-3 text-4xl font-bold text-blue-400">0</h3>
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-10 text-center">
          <h3 className="text-2xl font-semibold">
            Start Building Your Study Library
          </h3>

          <p className="mx-auto mt-3 max-w-xl text-slate-400">
            Upload your notes, PDFs, PPTs, handwritten materials, and question
            papers to begin.
          </p>

          <a
            href="/upload"
            className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700"
          >
            Upload Your First Material
          </a>
        </div>
      </main>
    </div>
  )
}

export default Dashboard
