import { NavLink } from 'react-router-dom'

const navigationItems = [
  { name: 'Home', path: '/dashboard', icon: '⌂' },
  { name: 'My Courses', path: '/courses', icon: '▣' },
  { name: 'Materials', path: '/materials', icon: '↥' },
  { name: 'AI Chat', path: '/chat', icon: '◌' },
  { name: 'AI Agent', path: '/agent', icon: '✦' },
  { name: 'PYQs', path: '/pyqs', icon: '▤' },
  { name: 'Calendar', path: '/calendar', icon: '📅' },
  { name: 'Study Plan', path: '/study-plan', icon: '□' },
  { name: 'Settings', path: '/settings', icon: '⚙' },
]

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 flex-col bg-[#17233b] text-white md:flex">
      <div className="flex items-center gap-3 border-b border-white/10 px-6 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500 text-2xl">
          🎓
        </div>

        <div>
          <h1 className="text-lg font-bold">CampusLearn AI</h1>
          <p className="text-xs text-slate-400">Learn • Analyze • Grow</p>
        </div>
      </div>

      <nav className="flex-1 space-y-2 px-4 py-6">
        {navigationItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-4 rounded-xl px-4 py-3 text-sm font-medium transition ${
                isActive
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
                  : 'text-slate-300 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <span className="w-5 text-center text-lg">{item.icon}</span>
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500 font-semibold">
            M
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">Mayank</p>
            <p className="text-xs text-slate-400">Student</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar