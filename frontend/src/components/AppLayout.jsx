import Sidebar from './Sidebar'
import Topbar from './Topbar'

function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-[#f7f8fc] text-slate-900">
      <Sidebar />

      <div className="min-h-screen md:ml-64">
        <Topbar />

        <main className="px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  )
}

export default AppLayout