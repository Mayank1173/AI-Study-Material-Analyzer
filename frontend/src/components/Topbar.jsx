import { useState } from 'react';

function Topbar() {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-1 items-center">
          <div className="relative w-full max-w-2xl">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-lg text-slate-400">
              ⌕
            </span>

            <input
              type="text"
              placeholder="Search your materials, courses, or ask anything..."
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-4 text-sm outline-none transition focus:border-blue-400 focus:bg-white"
            />
          </div>
        </div>

        <button className="hidden rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 sm:block">
          Ctrl + K
        </button>

        {/* The Bell Icon with onClick state toggle */}
        <div className="relative hidden md:block">
          <button 
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative h-10 w-10 rounded-full border border-slate-200 bg-white text-lg transition hover:bg-slate-50 cursor-pointer"
          >
            🔔
          </button>

          {/* The Notification Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 top-12 z-50 w-72 rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Notifications</h3>
              <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                You have no new notifications.
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">
            M
          </div>

          <div className="hidden sm:block">
            <p className="text-sm font-semibold text-slate-800">Mayank Test</p>
            <p className="text-xs text-slate-500">Student</p>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Topbar