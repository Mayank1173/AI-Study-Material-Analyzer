import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  Search,
  Bell,
  ArrowRight,
  Sparkles,
  Upload,
  MessageSquare,
  Calendar as CalendarIcon,
  BookOpen,
  FileText,
  Zap,
  CheckCircle,
  Layers,
  ChevronRight,
  GraduationCap,
  Home as HomeIcon,
  Settings as SettingsIcon,
  FileQuestion,
  MoreVertical,
  Crown,
  Flame,
  Megaphone,
  Video,
  Cpu,
  Database,
  Network,
  X,
  Check
} from 'lucide-react';

export default function Dashboard() {
  const [showNotifications, setShowNotifications] = useState(false);
  const { user } = useUser();
  const navigate = useNavigate();

  // Time-based greeting helper
  const currentHour = new Date().getHours();
  const timeGreeting = currentHour < 12 ? 'Good morning' : currentHour < 17 ? 'Good afternoon' : 'Good evening';

  const [askInput, setAskInput] = useState('');
  const [globalSearch, setGlobalSearch] = useState('');
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('monthly');

  // Dynamic Streak Management with localStorage
  const [streakCount, setStreakCount] = useState(() => {
    const lastLogin = localStorage.getItem('last_login_date');
    const currentStreak = parseInt(localStorage.getItem('streak_count'), 10) || 1;
    
    const today = new Date().toDateString();

    if (!lastLogin) {
      localStorage.setItem('last_login_date', today);
      localStorage.setItem('streak_count', '1');
      return 1;
    }

    const lastLoginDate = new Date(lastLogin);
    const currentDate = new Date(today);
    
    const diffTime = currentDate - lastLoginDate;
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return currentStreak;
    } else if (diffDays === 1) {
      const newStreak = currentStreak + 1;
      localStorage.setItem('last_login_date', today);
      localStorage.setItem('streak_count', newStreak.toString());
      return newStreak;
    } else {
      localStorage.setItem('last_login_date', today);
      localStorage.setItem('streak_count', '1');
      return 1;
    }
  });

  // Dynamic Recent Materials (Starts empty by default)
  const [recentMaterialsList, setRecentMaterialsList] = useState(() => {
    const saved = localStorage.getItem('recently_viewed_materials');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Error parsing recent materials', e);
      }
    }
    return []; // Start completely empty if nothing is saved
  });

  // RESTORED COURSES ARRAY
  const courses = [
    {
      title: 'Data Computer and Computer Network(DCCN)',
      materials: '12 materials',
      topicsLeft: '3 topics left',
      progress: 0,
      icon: <Network className="w-5 h-5 text-blue-500" />,
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Environment and Sustainability(E&S)',
      materials: '8 materials',
      topicsLeft: '2 topics left',
      progress: 0,
      icon: <Cpu className="w-5 h-5 text-purple-500" />,
      bgColor: 'bg-purple-50',
    },
    {
      title: 'Full Stack Development(FSD)',
      materials: '10 materials',
      topicsLeft: '4 topics left',
      progress: 0,
      icon: <Database className="w-5 h-5 text-sky-500" />,
      bgColor: 'bg-sky-50',
    },
  ];

  // Helper to get tag icon
  const getTagIcon = (tag) => {
    switch (tag) {
      case 'PDF':
        return <FileText className="w-3.5 h-3.5 text-rose-500" />;
      case 'PPT':
        return <Layers className="w-3.5 h-3.5 text-amber-500" />;
      case 'Video':
        return <Video className="w-3.5 h-3.5 text-purple-500" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 text-blue-500" />;
    }
  };

  const handleAskSubmit = (e) => {
    e.preventDefault();
    if (askInput.trim()) {
      navigate('/chat', { state: { initialPrompt: askInput } });
    }
  };

  // Handle Global Search Submit & Add to Recent
  const handleSearchSubmit = (e) => {
    if (e.key === 'Enter' && globalSearch.trim()) {
      const newItem = {
        id: `search-${Date.now()}`,
        title: globalSearch,
        tag: 'Search',
        tagBg: 'bg-slate-100 text-slate-600 border-slate-200',
        time: 'Just now',
        course: 'General Search',
        size: '-'
      };
      const newList = [newItem, ...recentMaterialsList].slice(0, 4);
      setRecentMaterialsList(newList);
      localStorage.setItem('recently_viewed_materials', JSON.stringify(newList));
      navigate('/chat', { state: { initialPrompt: `Search materials for: ${globalSearch}` } });
    }
  };

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" />, active: true },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <SettingsIcon className="w-4 h-4" /> },
  ];

  const initialLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'M';

  return (
    <>
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

          <Link to="/settings" className="flex items-center justify-between p-3 bg-slate-800/60 hover:bg-slate-800 transition-colors rounded-xl border border-slate-700/50">
            <div className="flex items-center gap-3">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt="Avatar" className="w-8 h-8 rounded-full object-cover" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center font-semibold justify-center text-sm">
                  {initialLetter}
                </div>
              )}
              <div className="truncate max-w-[120px]">
                <p className="text-sm font-medium text-white truncate">{user?.name || 'Student'}</p>
                <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-400" />
          </Link>
        </aside>

        {/* Main Container */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Header */}
          <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
            <div className="relative w-1/3">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                onKeyDown={handleSearchSubmit}
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

              <Link to="/settings" className="flex items-center gap-3 pl-2 border-l border-slate-200 hover:opacity-80 transition-opacity">
                {user?.avatarUrl ? (
                  <img src={user.avatarUrl} alt="Avatar" className="w-8 h-8 rounded-full object-cover" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-sm">
                    {initialLetter}
                  </div>
                )}
                <div className="text-left leading-tight">
                  <p className="text-sm font-semibold text-slate-700">{user?.name || 'Student'}</p>
                  <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
                </div>
              </Link>
            </div>
          </header>

          {/* Dashboard Body Scrollable */}
          <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
            
            {/* Main Content Area (Left 8 Cols) */}
            <div className="col-span-12 lg:col-span-8 space-y-6">
              
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">
                    {timeGreeting}, <span className="text-blue-600">{user?.name || 'Student'}</span>
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">Ready to ace your next exam?</p>
                </div>
                {/* Bot Avatar Illustration */}
                <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
              </div>

              {/* 3 Action Cards Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Continue Learning */}
                <div className="bg-gradient-to-br from-blue-50/60 to-indigo-50/60 rounded-2xl p-5 border border-blue-100 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 bg-blue-100/80 rounded-xl text-blue-600">
                        <BookOpen className="w-5 h-5" />
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    </div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Continue Learning</h4>
                    <h3 className="text-sm font-bold text-slate-800 mt-1">Computer Networks</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">12 materials • 3 topics left</p>
                  </div>
                  <Link
                    to="/courses"
                    className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold text-center flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                  >
                    Go to Course <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                {/* Ask AI Anything */}
                <div className="bg-gradient-to-br from-purple-50/60 to-pink-50/60 rounded-2xl p-5 border border-purple-100 flex flex-col justify-between">
                  <div>
                    <div className="p-2 bg-purple-100/80 rounded-xl text-purple-600 w-fit mb-3">
                      <MessageSquare className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-800">Ask AI Anything</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                      Get instant answers from your study materials.
                    </p>
                  </div>
                  <form onSubmit={handleAskSubmit} className="mt-4 relative">
                    <input
                      type="text"
                      value={askInput}
                      onChange={(e) => setAskInput(e.target.value)}
                      placeholder="Ask a question..."
                      className="w-full pl-3 pr-8 py-2 text-xs bg-white rounded-xl border border-purple-200 outline-none focus:ring-2 focus:ring-purple-400/20 text-slate-700"
                    />
                    <button type="submit" className="absolute right-2 top-1/2 transform -translate-y-1/2 text-purple-600 hover:text-purple-800">
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </form>
                </div>

                {/* AI Agent */}
                <div className="bg-gradient-to-br from-emerald-50/60 to-teal-50/60 rounded-2xl p-5 border border-emerald-100 flex flex-col justify-between">
                  <div>
                    <div className="p-2 bg-emerald-100/80 rounded-xl text-emerald-600 w-fit mb-3">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-800">AI Agent</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                      Your personal study assistant. Summarize, explain, generate quizzes and more.
                    </p>
                  </div>
                  <Link
                    to="/agent"
                    className="mt-4 px-4 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200/60 rounded-xl text-xs font-semibold text-center flex items-center justify-center gap-1.5 transition-colors"
                  >
                    Explore Agent <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              {/* Dynamic Recent Materials Section */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-800">Recent Materials</h3>
                    <p className="text-xs text-slate-500">Your recent searches and materials.</p>
                  </div>
                  {recentMaterialsList.length > 0 && (
                    <button 
                      onClick={() => {
                        setRecentMaterialsList([]);
                        localStorage.removeItem('recently_viewed_materials');
                      }} 
                      className="text-xs font-semibold text-rose-600 hover:underline"
                    >
                      Clear All
                    </button>
                  )}
                </div>

                {recentMaterialsList.length === 0 ? (
                  <div className="bg-white border-2 border-slate-200/80 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center">
                    <Search className="w-8 h-8 text-slate-300 mb-3" />
                    <p className="text-sm font-semibold text-slate-700">No recent materials</p>
                    <p className="text-xs text-slate-500 mt-1">Use the search bar above to find and add materials here.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {recentMaterialsList.map((item) => (
                      <div
                        key={item.id}
                        className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-all group hover:border-blue-300 relative"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border flex items-center gap-1 ${item.tagBg || 'bg-blue-50 text-blue-600 border-blue-100'}`}>
                              {getTagIcon(item.tag)}
                              {item.tag}
                            </span>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                const newList = recentMaterialsList.filter(m => m.id !== item.id);
                                setRecentMaterialsList(newList);
                                localStorage.setItem('recently_viewed_materials', JSON.stringify(newList));
                              }}
                              className="text-slate-300 hover:text-rose-500 p-1 rounded-md hover:bg-rose-50 transition-colors"
                              title="Remove"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                          <h4 className="text-xs font-bold text-slate-800 group-hover:text-blue-600 transition-colors line-clamp-2">
                            {item.title}
                          </h4>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-4">{item.time}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Your Courses Section */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-800">Your Courses</h3>
                    <p className="text-xs text-slate-500">Continue learning from your enrolled courses.</p>
                  </div>
                  <Link to="/courses" className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1">
                    View all <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {courses.map((course, idx) => (
                    <Link
                      key={idx}
                      to="/courses"
                      className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm space-y-3 hover:shadow-md transition-shadow block"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-xl ${course.bgColor}`}>
                          {course.icon}
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-slate-800">{course.title}</h4>
                          <p className="text-[10px] text-slate-400">{course.materials} • {course.topicsLeft}</p>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-blue-600 h-1.5 rounded-full transition-all"
                            style={{ width: `${course.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-[10px] text-slate-400 text-right font-medium">{course.progress}%</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Sidebar Widget Column (4 Cols) */}
            <div className="col-span-12 lg:col-span-4 space-y-6">

              {/* Upgrade to Premium Widget */}
              <div className="bg-gradient-to-br from-indigo-50/70 via-blue-50/50 to-purple-50/70 rounded-2xl p-5 border border-indigo-100 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Crown className="w-5 h-5 text-amber-500 fill-amber-500" />
                  <h3 className="text-sm font-bold text-slate-800">Upgrade to Premium</h3>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Unlock advanced features, unlimited uploads, and priority AI access.
                </p>

                <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    Unlimited material uploads
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    Advanced AI capabilities
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    Priority support
                  </li>
                </ul>

                <button
                  onClick={() => setIsUpgradeModalOpen(true)}
                  className="mt-4 w-full py-2.5 bg-[#0F172A] hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-md"
                >
                  Upgrade Now <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Upcoming Exam Widget */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-3">
                <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                  <CalendarIcon className="w-4 h-4 text-blue-600" />
                  Upcoming
                </div>
                <p className="text-xs text-slate-500">
                  Set your exam date to generate personalized study sessions.
                </p>
                <Link
                  to="/calendar"
                  className="w-full py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-center transition-colors"
                >
                  Add exam date
                </Link>
              </div>

              {/* Streak Widget */}
              <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-amber-50 rounded-xl text-amber-500">
                    <Flame className="w-5 h-5 fill-amber-500" />
                  </div>
                  <span className="text-xs font-bold text-slate-800">{streakCount} {streakCount === 1 ? 'day' : 'days'} streak!</span>
                </div>
                <Link to="/calendar" className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1">
                  View Calendar <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Announcements Widget */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-3">
                <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                  <Megaphone className="w-4 h-4 text-purple-600" />
                  Announcements
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
                    <p className="text-xs font-bold text-slate-800">New Feature: AI Agent</p>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-normal pl-3">
                    Generate summaries, mind maps, or quiz sets directly from your study materials.
                  </p>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      {/* Upgrade Modal */}
      {isUpgradeModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 relative animate-in fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Crown className="w-6 h-6 text-amber-500 fill-amber-500" />
                <h3 className="text-base font-bold text-slate-800">Choose Your CampusLearn Plan</h3>
              </div>
              <button
                onClick={() => setIsUpgradeModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex items-center justify-center bg-slate-100 p-1 rounded-full w-fit mx-auto text-xs font-semibold">
              <button
                onClick={() => setSelectedPlan('monthly')}
                className={`px-4 py-1.5 rounded-full transition-all ${
                  selectedPlan === 'monthly' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setSelectedPlan('annual')}
                className={`px-4 py-1.5 rounded-full transition-all ${
                  selectedPlan === 'annual' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
                }`}
              >
                Annual <span className="text-[10px] text-emerald-600 font-bold ml-1">Save 20%</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col justify-between space-y-3">
                <div>
                  <h4 className="text-sm font-bold text-slate-800">Free Tier</h4>
                  <p className="text-[11px] text-slate-500">Essential tools to get started</p>
                  <div className="mt-2">
                    <span className="text-xl font-bold text-slate-800">₹0</span>
                    <span className="text-xs text-slate-400">/forever</span>
                  </div>
                </div>

                <ul className="space-y-1.5 text-[11px] text-slate-600 pt-2 border-t border-slate-200">
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-slate-400" /> Up to 5 document uploads</li>
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-slate-400" /> Standard AI chat responses</li>
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-slate-400" /> Basic study plan calendar</li>
                </ul>

                <button
                  onClick={() => {
                    alert('You are currently on the Free plan.');
                    setIsUpgradeModalOpen(false);
                  }}
                  className="w-full py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold transition-colors"
                >
                  Current Plan
                </button>
              </div>

              <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50/50 border-2 border-blue-500 flex flex-col justify-between space-y-3 relative shadow-sm">
                <span className="absolute -top-2.5 right-4 bg-blue-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                  Popular
                </span>
                <div>
                  <h4 className="text-sm font-bold text-slate-800">Pro Student Pass</h4>
                  <p className="text-[11px] text-slate-500">Everything you need for exams</p>
                  <div className="mt-2">
                    <span className="text-xl font-bold text-slate-800">{selectedPlan === 'monthly' ? '₹799' : '₹8999'}</span>
                    <span className="text-xs text-slate-400">/{selectedPlan === 'monthly' ? 'mo' : 'yr'}</span>
                  </div>
                </div>

                <ul className="space-y-1.5 text-[11px] text-slate-600 pt-2 border-t border-blue-100">
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-emerald-500" /> Unlimited OCR & Uploads</li>
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-emerald-500" /> Advanced RAG & Long-Context</li>
                  <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-emerald-500" /> Fast PYQ & Quiz Generation</li>
                </ul>

                <button
                  onClick={() => {
                    alert('Thank you for choosing Pro! Proceeding to checkout...');
                    setIsUpgradeModalOpen(false);
                  }}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-500/20 transition-colors"
                >
                  Upgrade to Pro
                </button>
              </div>
            </div>
            
            <div className="flex items-center justify-end pt-1">
              <button
                onClick={() => setIsUpgradeModalOpen(false)}
                className="text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Material Detail Modal */}
      {selectedMaterial && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4 relative animate-in fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                  {getTagIcon(selectedMaterial.tag)}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">{selectedMaterial.title}</h3>
                  <p className="text-[10px] text-slate-400">{selectedMaterial.tag} • {selectedMaterial.time}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedMaterial(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-600">
              <p><strong>Course:</strong> {selectedMaterial.course || 'Computer Networks'}</p>
              <p><strong>Size:</strong> {selectedMaterial.size || '3.2 MB'}</p>
              <p className="text-[11px] text-slate-500 pt-1">
                What would you like to do with this study material?
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <button
                onClick={() => {
                  setSelectedMaterial(null);
                  navigate('/chat', { state: { initialPrompt: `Analyze and explain ${selectedMaterial.title}` } });
                }}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors flex items-center justify-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" /> Analyze with AI
              </button>
              <button
                onClick={() => {
                  setSelectedMaterial(null);
                  navigate('/agent', { state: { material: selectedMaterial } });
                }}
                className="px-3 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                <BookOpen className="w-3.5 h-3.5" /> Summarize
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}