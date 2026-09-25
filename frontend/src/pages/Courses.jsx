import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Bell,
  Plus,
  BookOpen,
  CheckCircle,
  Clock,
  Layers,
  Upload,
  MessageSquare,
  Sparkles,
  FileQuestion,
  Calendar as CalendarIcon,
  Settings,
  ChevronRight,
  GraduationCap,
  Home as HomeIcon,
  Zap,
  HelpCircle,
  FileText,
  Eye,
  MoreHorizontal,
  Code,
  ShieldAlert,
  Leaf,
  Network,
  X
} from 'lucide-react';

export default function Courses() {
  const [showNotifications, setShowNotifications] = useState(false);
  
  // Dynamic States for Activity and Deadlines
  const [recentActivity, setRecentActivity] = useState([]);
  const [upcomingDeadlines, setUpcomingDeadlines] = useState([]);

  const [coursesList, setCoursesList] = useState([
    {
      id: 1,
      title: 'Data Computer and Computer Network (DCCN)',
      code: '4CSGC2062',
      semester: 'Semester 5',
      instructor: 'Dr Arokia Jesu L Prabhu',
      progress: 0,
      modules: 12,
      assignments: 4,
      color: 'bg-blue-500',
      lightBg: 'bg-blue-50 text-blue-600',
      icon: <Network className="w-5 h-5 text-white" />
    },
    {
      id: 2,
      title: 'Environment and Sustainability (E&S)',
      code: 'CKHM1011',
      semester: 'Semester 5',
      instructor: 'Prof. Manohar K M',
      progress: 0,
      modules: 10,
      assignments: 3,
      color: 'bg-emerald-500',
      lightBg: 'bg-emerald-50 text-emerald-600',
      icon: <Leaf className="w-5 h-5 text-white" />
    },
    {
      id: 3,
      title: 'Full Stack Development (FSD)',
      code: '4CSPL2021',
      semester: 'Semester 5',
      instructor: 'Prof. Rohith Kumar',
      progress: 0,
      modules: 14,
      assignments: 5,
      color: 'bg-purple-500',
      lightBg: 'bg-purple-50 text-purple-600',
      icon: <Code className="w-5 h-5 text-white" />
    },
    {
      id: 4,
      title: 'Ethical Hacking',
      code: '4CSGC3221',
      semester: 'Semester 5',
      instructor: 'Prof. Rohith Kumar',
      progress: 0,
      modules: 12,
      assignments: 3,
      color: 'bg-amber-500',
      lightBg: 'bg-amber-50 text-amber-600',
      icon: <ShieldAlert className="w-5 h-5 text-white" />
    }
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCourse, setNewCourse] = useState({
    title: '',
    code: '',
    semester: 'Semester 1',
    instructor: '',
    modules: 10,
    assignments: 2
  });

  const handleAddCourse = (e) => {
    e.preventDefault();
    if (!newCourse.title.trim()) return;

    const colors = [
      { color: 'bg-blue-500', lightBg: 'bg-blue-50 text-blue-600', icon: <BookOpen className="w-5 h-5 text-white" /> },
      { color: 'bg-indigo-500', lightBg: 'bg-indigo-50 text-indigo-600', icon: <Layers className="w-5 h-5 text-white" /> },
      { color: 'bg-emerald-500', lightBg: 'bg-emerald-50 text-emerald-600', icon: <Leaf className="w-5 h-5 text-white" /> },
      { color: 'bg-purple-500', lightBg: 'bg-purple-50 text-purple-600', icon: <Code className="w-5 h-5 text-white" /> },
    ];

    const randomTheme = colors[Math.floor(Math.random() * colors.length)];

    const createdCourse = {
      id: Date.now(),
      title: newCourse.title,
      code: newCourse.code || 'CS101',
      semester: newCourse.semester,
      instructor: newCourse.instructor || 'Prof. Unassigned',
      progress: 0,
      modules: Number(newCourse.modules) || 8,
      assignments: Number(newCourse.assignments) || 2,
      ...randomTheme
    };

    setCoursesList([createdCourse, ...coursesList]);
    
    // Dynamically log this action in Recent Activity
    setRecentActivity([
      { 
        text: `Enrolled in ${newCourse.title}`, 
        time: 'Just now', 
        icon: <Plus className="w-4 h-4 text-blue-500" /> 
      },
      ...recentActivity
    ]);

    setIsModalOpen(false);
    setNewCourse({
      title: '',
      code: '',
      semester: 'Semester 1',
      instructor: '',
      modules: 10,
      assignments: 2
    });
  };

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" />, active: true },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  const quickActions = [
    { title: 'Upload Materials', desc: 'Add notes, PDFs, PPTs, images, etc.', icon: <Upload className="w-4 h-4 text-blue-500" />, route: '/upload' },
    { title: 'Ask a Question', desc: 'Get instant answers', icon: <MessageSquare className="w-4 h-4 text-purple-500" />, route: '/chat' },
    { title: 'Generate Study Plan', desc: 'Create a personalized plan', icon: <CalendarIcon className="w-4 h-4 text-indigo-500" />, route: '/calendar' },
    { title: 'Create Quiz', desc: 'Test your knowledge', icon: <HelpCircle className="w-4 h-4 text-pink-500" />, route: '/chat' },
    { title: 'Generate Flashcards', desc: 'Revise smarter', icon: <Zap className="w-4 h-4 text-amber-500" />, route: '/chat' },
  ];

  const inProgressCount = coursesList.filter(c => c.progress < 100).length;
  const completedCount = coursesList.filter(c => c.progress === 100).length;

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-[#0F172A] text-slate-300 flex flex-col justify-between p-4 shrink-0">
        <div>
          <Link to="/dashboard" className="flex items-center gap-3 px-2 py-3 mb-6">
            <div className="bg-blue-600 text-white p-2 rounded-xl">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-white tracking-wide text-base">CampusLearn AI</h1>
              <p className="text-xs text-slate-400">Learn • Analyze • Grow</p>
            </div>
          </Link>

          <nav className="space-y-1">
            {sidebarNavItems.map((item, idx) => (
              <Link
                key={idx}
                to={item.path}
                className={`flex items-center gap-3 w-full px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  item.active
                    ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/30'
                    : 'hover:bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center justify-between p-3 bg-slate-800/60 rounded-xl border border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center font-semibold justify-center text-sm">
              M
            </div>
            <div>
              <p className="text-sm font-medium text-white">Mayank</p>
              <p className="text-xs text-slate-400">Student</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <div className="relative w-1/3">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search your materials, courses, or ask anything..."
              className="w-full pl-9 pr-12 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
            <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs text-slate-400 font-medium border border-slate-200 px-1.5 py-0.5 rounded bg-white">
              Ctrl + K
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <button 
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 text-slate-500 hover:bg-slate-100 rounded-full relative cursor-pointer"
              >
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-amber-500 rounded-full"></span>
              </button>

              {showNotifications && (
                <div className="absolute right-0 top-12 z-50 w-72 rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
                  <h3 className="mb-2 text-sm font-semibold text-slate-800">Notifications</h3>
                  <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                    You have no new notifications.
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-sm">
                M
              </div>
              <div className="text-left leading-tight">
                <p className="text-sm font-semibold text-slate-700">Mayank</p>
                <p className="text-xs text-slate-400">Student</p>
              </div>
            </div>
          </div>
        </header>

        {/* Courses Page Body Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
          {/* Main Content Area (Left 8 Cols) */}
          <div className="col-span-12 lg:col-span-8 space-y-6">
            
            {/* Header Title with Add Course Button */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-md shadow-blue-500/20">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">My Courses</h2>
                  <p className="text-xs text-slate-500">Access all your enrolled courses and manage your learning progress.</p>
                </div>
              </div>

              {/* Add Course Trigger Button */}
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl flex items-center gap-2 shadow-md shadow-blue-600/20 transition-all"
              >
                <Plus className="w-4 h-4" /> Add Course
              </button>
            </div>

            {/* Banner Section */}
            <div className="bg-gradient-to-r from-blue-50/80 via-indigo-50/50 to-purple-50/80 rounded-2xl p-6 border border-blue-100/80 flex items-center justify-between relative overflow-hidden">
              <div className="max-w-md">
                <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  Continue Your Learning Journey 🚀
                </h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                  Add your subjects and organize all your study materials in one place with CampusLearn AI.
                </p>
              </div>

              {/* Illustration graphic placeholder */}
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
                <GraduationCap className="w-12 h-12 text-white" />
              </div>
            </div>

            {/* Stats Summary Cards */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-3 bg-blue-100/80 text-blue-600 rounded-xl">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Courses</p>
                  <p className="text-2xl font-bold text-blue-600 mt-0.5">{coursesList.length}</p>
                </div>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-3 bg-emerald-100/80 text-emerald-600 rounded-xl">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">In Progress</p>
                  <p className="text-2xl font-bold text-emerald-600 mt-0.5">{inProgressCount}</p>
                </div>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-3 bg-purple-100/80 text-purple-600 rounded-xl">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Completed</p>
                  <p className="text-2xl font-bold text-purple-600 mt-0.5">{completedCount}</p>
                </div>
              </div>
            </div>

            {/* Course List Header */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-800">My Courses ({coursesList.length})</h3>
                  <p className="text-xs text-slate-500">Select a course to manage its materials and progress.</p>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span>Sort by:</span>
                  <select className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 font-medium outline-none focus:border-blue-500">
                    <option>Latest</option>
                    <option>Progress</option>
                    <option>Name</option>
                  </select>
                </div>
              </div>

              {/* Courses 2x2 Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {coursesList.map((course) => (
                  <div
                    key={course.id}
                    className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow space-y-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-3 rounded-2xl ${course.color} shrink-0`}>
                          {course.icon}
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-slate-800 leading-snug">{course.title}</h4>
                          <p className="text-[11px] text-slate-400 mt-0.5">{course.code} • {course.semester}</p>
                          <p className="text-[11px] text-slate-500">Instructor: {course.instructor}</p>
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-400">Progress</span>
                        <span className="font-bold text-slate-700">{course.progress}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-1.5 rounded-full transition-all duration-500 ease-in-out ${course.color}`}
                          style={{ width: `${course.progress}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Card Footer Actions */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                      <div className="flex items-center gap-3 text-slate-500 font-medium text-[11px]">
                        <span className="flex items-center gap-1">
                          <Layers className="w-3.5 h-3.5" /> {course.modules} Modules
                        </span>
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" /> {course.assignments} Assignments
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <Link
                          to="/materials"
                          className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs transition-colors"
                        >
                          View Materials
                        </Link>
                        <button className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Right Sidebar Columns (4 Cols) */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            
            {/* Quick Actions Panel */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-blue-600" />
                Quick Actions
              </h3>
              <div className="space-y-2">
                {quickActions.map((action, idx) => (
                  <Link
                    key={idx}
                    to={action.route}
                    className="flex items-center justify-between p-2.5 hover:bg-slate-50 rounded-xl cursor-pointer border border-transparent hover:border-slate-100 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-slate-100 group-hover:bg-white group-hover:shadow-sm">
                        {action.icon}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-slate-800">{action.title}</p>
                        <p className="text-[11px] text-slate-400">{action.desc}</p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500" />
                  </Link>
                ))}
              </div>
            </div>

            {/* Recent Activity Panel */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-slate-500" />
                  Recent Activity
                </h3>
                <span className="text-[11px] font-semibold text-blue-600 cursor-pointer hover:underline">View All</span>
              </div>

              <div className="space-y-3">
                {recentActivity.length > 0 ? (
                  recentActivity.map((act, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-xs animate-in fade-in slide-in-from-top-2">
                      <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100 mt-0.5">
                        {act.icon}
                      </div>
                      <div>
                        <p className="font-medium text-slate-700">{act.text}</p>
                        <p className="text-[10px] text-slate-400">{act.time}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-4">No recent activity yet.</p>
                )}
              </div>
            </div>

            {/* Upcoming Deadlines */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <CalendarIcon className="w-3.5 h-3.5 text-indigo-500" />
                  Upcoming Deadlines
                </h3>
                <Link to="/calendar" className="text-[11px] font-semibold text-blue-600 hover:underline">View Calendar</Link>
              </div>

              <div className="space-y-2.5">
                {upcomingDeadlines.length > 0 ? (
                  upcomingDeadlines.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50/80 border border-slate-100 animate-in fade-in slide-in-from-top-2">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-2 h-2 rounded-full ${item.color}`}></div>
                        <div>
                          <p className="text-xs font-bold text-slate-800">{item.name}</p>
                          <p className="text-[10px] text-slate-400">{item.date}</p>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-rose-50 text-rose-600">
                        {item.days}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-4">No upcoming deadlines.</p>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* Add Course Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4 relative animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-600" /> Add New Course
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddCourse} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Course Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Data Structures and Algorithms"
                  value={newCourse.title}
                  onChange={(e) => setNewCourse({ ...newCourse, title: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Course Code</label>
                  <input
                    type="text"
                    placeholder="e.g. CS202"
                    value={newCourse.code}
                    onChange={(e) => setNewCourse({ ...newCourse, code: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Semester</label>
                  <select
                    value={newCourse.semester}
                    onChange={(e) => setNewCourse({ ...newCourse, semester: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
                  >
                    <option>Semester 1</option>
                    <option>Semester 2</option>
                    <option>Semester 3</option>
                    <option>Semester 4</option>
                    <option>Semester 5</option>
                    <option>Semester 6</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Instructor Name</label>
                <input
                  type="text"
                  placeholder="e.g. Dr. A. K. Sharma"
                  value={newCourse.instructor}
                  onChange={(e) => setNewCourse({ ...newCourse, instructor: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Number of Modules</label>
                  <input
                    type="number"
                    min="1"
                    value={newCourse.modules}
                    onChange={(e) => setNewCourse({ ...newCourse, modules: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Assignments</label>
                  <input
                    type="number"
                    min="0"
                    value={newCourse.assignments}
                    onChange={(e) => setNewCourse({ ...newCourse, assignments: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 rounded-xl text-slate-600 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold shadow-md shadow-blue-600/20"
                >
                  Create Course
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}