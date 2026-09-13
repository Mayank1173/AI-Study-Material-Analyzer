function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="flex items-center justify-between px-8 py-6">
        <h1 className="text-2xl font-bold text-blue-400">StudyAI</h1>

        <div className="flex gap-4">
          <a href="/login" className="px-4 py-2 text-slate-300 hover:text-white">
            Login
          </a>

          <a
            href="/register"
            className="rounded-lg bg-blue-600 px-5 py-2 font-semibold hover:bg-blue-700"
          >
            Get Started
          </a>
        </div>
      </nav>

      <main className="mx-auto flex max-w-6xl flex-col items-center px-6 py-24 text-center">
        <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-blue-400">
          AI-Powered Learning Assistant
        </p>

        <h2 className="max-w-4xl text-5xl font-bold leading-tight md:text-6xl">
          Turn Your Study Materials Into
          <span className="text-blue-400"> Smart Answers</span>
        </h2>

        <p className="mt-6 max-w-2xl text-lg text-slate-300">
          Upload notes, PDFs, PPTs, handwritten materials, question banks,
          previous-year papers, and videos. StudyAI analyzes everything and
          helps you learn faster.
        </p>

        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <a
            href="/register"
            className="rounded-xl bg-blue-600 px-8 py-4 font-semibold hover:bg-blue-700"
          >
            Start Learning
          </a>

          <a
            href="/dashboard"
            className="rounded-xl border border-slate-700 px-8 py-4 font-semibold text-slate-200 hover:bg-slate-900"
          >
            Explore Dashboard
          </a>
        </div>

        <div className="mt-20 grid w-full gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">Upload Anything</h3>
            <p className="mt-3 text-slate-400">
              Add PDFs, PPTs, images, handwritten notes, and videos.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">Ask Questions</h3>
            <p className="mt-3 text-slate-400">
              Get answers generated from your uploaded study materials.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">Learn Smarter</h3>
            <p className="mt-3 text-slate-400">
              Find important topics, summaries, and exam-focused insights.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Home