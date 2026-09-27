import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  Search,
  Bell,
  Paperclip,
  ArrowRight,
  Sparkles,
  Upload,
  MessageSquare,
  Calendar as CalendarIcon,
  HelpCircle,
  BookOpen,
  FileText,
  Zap,
  CheckCircle,
  Layers,
  Cpu,
  Eye,
  ChevronRight,
  GraduationCap,
  Home,
  Settings,
  FileQuestion
} from 'lucide-react';

export default function Agent() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [prompt, setPrompt] = useState('');
  const navigate = useNavigate();
  const { user } = useUser();
  const displayName = user?.name || 'Student';
  const initial = user?.name ? user.name.charAt(0).toUpperCase() : 'S';
  const firstName = user?.name ? user.name.split(' ')[0] : 'there';

  const handlePromptSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      // Navigate to chat with prompt state or execute agent logic
      navigate('/chat', { state: { initialPrompt: prompt } });
    }
  };

  const capabilities = [
    {
      title: 'Analyze Materials',
      desc: 'Find key concepts, common topics and important points from all your resources.',
      icon: <FileText className="w-5 h-5 text-blue-500" />,
      bgColor: 'bg-blue-50 hover:bg-blue-100/80',
    },
    {
      title: 'Summarize Content',
      desc: 'Get short, unit-wise or last-minute revision notes.',
      icon: <BookOpen className="w-5 h-5 text-emerald-500" />,
      bgColor: 'bg-emerald-50 hover:bg-emerald-100/80',
    },
    {
      title: 'Answer Questions',
      desc: 'Get accurate answers with source references.',
      icon: <MessageSquare className="w-5 h-5 text-purple-500" />,
      bgColor: 'bg-purple-50 hover:bg-purple-100/80',
    },
    {
      title: 'Create Quizzes',
      desc: 'Generate MCQs, true/false, short & descriptive questions.',
      icon: <HelpCircle className="w-5 h-5 text-pink-500" />,
      bgColor: 'bg-pink-50 hover:bg-pink-100/80',
    },
    {
      title: 'Generate Flashcards',
      desc: 'Convert your notes into smart flashcards.',
      icon: <Zap className="w-5 h-5 text-amber-500" />,
      bgColor: 'bg-amber-50 hover:bg-amber-100/80',
    },
    {
      title: 'Create Study Plan',
      desc: 'Get a personalized study plan based on your exam dates.',
      icon: <CalendarIcon className="w-5 h-5 text-indigo-500" />,
      bgColor: 'bg-indigo-50 hover:bg-indigo-100/80',
    },
    {
      title: 'Visual Explanations',
      desc: 'Get diagrams, flowcharts, mind maps and concept visuals.',
      icon: <Layers className="w-5 h-5 text-cyan-500" />,
      bgColor: 'bg-cyan-50 hover:bg-cyan-100/80',
    },
    {
      title: 'Video & Resource Suggestions',
      desc: 'Find relevant videos and external resources for better learning.',
      icon: <Cpu className="w-5 h-5 text-blue-600" />,
      bgColor: 'bg-sky-50 hover:bg-sky-100/80',
    },
  ];

  const quickActions = [
    { title: 'Upload Materials', desc: 'Add notes, PDFs, PPTs, images, etc.', icon: <Upload className="w-4 h-4 text-blue-500" />, route: '/upload' },
    { title: 'Ask a Question', desc: 'Get instant answers', icon: <MessageSquare className="w-4 h-4 text-purple-500" />, route: '/chat' },
    { title: 'Generate Study Plan', desc: 'Create a personalized plan', icon: <CalendarIcon className="w-4 h-4 text-indigo-500" />, route: '/calendar' },
    { title: 'Create Quiz', desc: 'Test your knowledge', icon: <HelpCircle className="w-4 h-4 text-pink-500" />, route: '/chat' },
    { title: 'Generate Flashcards', desc: 'Revise smarter', icon: <Zap className="w-4 h-4 text-amber-500" />, route: '/chat' },
  ];

  const recentActivity = [
    { text: 'Analyzed study materials', time: '2 hours ago', icon: <FileText className="w-4 h-4 text-blue-500" /> },
    { text: 'Created a quiz', time: '4 hours ago', icon: <HelpCircle className="w-4 h-4 text-pink-500" /> },
    { text: 'Generated study plan', time: '6 hours ago', icon: <CalendarIcon className="w-4 h-4 text-indigo-500" /> },
    { text: 'Generated a summary', time: '8 hours ago', icon: <CheckCircle className="w-4 h-4 text-emerald-500" /> },
  ];

  const upcomingExams = [
    { name: 'Data Structures', date: '12 Sep 2026', days: '5 days left', badgeBg: 'bg-blue-50 text-blue-600' },
    { name: 'Database Management Systems', date: '18 Sep 2026', days: '11 days left', badgeBg: 'bg-amber-50 text-amber-600' },
    { name: 'Operating Systems', date: '25 Sep 2026', days: '18 days left', badgeBg: 'bg-emerald-50 text-emerald-600' },
  ];

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <Home className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" />, active: true },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden">
      {/* Sidebar matching App.jsx routes */}
      <aside className="w-64 bg-[#0F172A] text-slate-300 flex flex-col justify-between p-4 shrink-0">
        <div>
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-3 px-2 py-3 mb-6">
            <div className="bg-blue-600 text-white p-2 rounded-xl">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-white tracking-wide text-base">CampusLearn AI</h1>
              <p className="text-xs text-slate-400">Learn • Analyze • Grow</p>
            </div>
          </Link>

          {/* Navigation Links */}
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

        {/* User Profile */}
        <div className="flex items-center justify-between p-3 bg-slate-800/60 rounded-xl border border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center font-semibold justify-center text-sm">
              {initial}
            </div>
            <div>
              <p className="text-sm font-medium text-white">{displayName}</p>
              <p className="text-xs text-slate-400">Student</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
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
                {initial}
              </div>
              <div className="text-left leading-tight">
                <p className="text-sm font-semibold text-slate-700">{displayName}</p>
                <p className="text-xs text-slate-400">Student</p>
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
          {/* Main Workspace (Left 8 Cols) */}
          <div className="col-span-12 lg:col-span-8 space-y-6">
            {/* Banner Section */}
            <div className="bg-gradient-to-r from-indigo-50/70 via-blue-50/50 to-purple-50/70 rounded-2xl p-6 border border-indigo-100 relative overflow-hidden">
              <div className="flex items-start gap-4 relative z-10">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
                  <Sparkles className="w-10 h-10 text-white animate-pulse" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                    Hi {firstName}! <span>👋</span>
                  </h2>
                  <h3 className="text-xl font-bold text-blue-600 mt-0.5">I'm your AI Study Agent</h3>
                  <p className="text-xs text-slate-600 mt-2 max-w-xl leading-relaxed">
                    Upload your handwritten notes, lecture notes, PDFs, PPTs, question banks, PYQs, and other resources.
                    I'll analyze everything together and help you get accurate, relevant, and unified answers.
                  </p>

                  <div className="flex flex-wrap gap-2 mt-4">
                    {['Notes', 'PDFs', 'PPTs', 'Images', 'PYQs', 'Videos'].map((tag, i) => (
                      <span key={i} className="px-3 py-1 bg-white/80 border border-slate-200/60 rounded-full text-xs font-medium text-slate-600 shadow-sm flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Prompt Box */}
            <form onSubmit={handlePromptSubmit} className="bg-white rounded-2xl border border-slate-200 p-3 shadow-sm space-y-3">
              <div className="flex items-center gap-2 px-2">
               {/* Hidden native file input */}
        <input 
          type="file" 
          id="agent-file-upload" 
          className="hidden" 
          multiple
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              console.log("File selected:", e.target.files[0].name);
            }
          }}
        />
        
        {/* The clickable icon wrapper */}
        <label 
          htmlFor="agent-file-upload" 
          title="Upload Materials"
          className="text-slate-400 hover:text-blue-600 p-1 transition-colors cursor-pointer flex items-center justify-center"
        >
          <Paperclip className="w-5 h-5" /> 
        </label>
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Upload files or type your question..."
                  className="w-full text-sm outline-none text-slate-700 placeholder-slate-400 bg-transparent"
                />
                <button
                  type="submit"
                  className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-md transition-all"
                >
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {/* Action Chips */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
                {[
                  'Explain this topic using all my notes',
                  'Give me a short summary',
                  'Create a study plan',
                  'Generate a quiz',
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setPrompt(chip)}
                    className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs rounded-lg border border-slate-200 transition-colors"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </form>

            {/* Capability Cards */}
            <div>
              <div className="mb-4">
                <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  What I can do for you
                </h3>
                <p className="text-xs text-slate-500">Choose an action or ask me anything. I'll use all your uploaded materials to help you.</p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {capabilities.map((cap, idx) => (
                  <div
                    key={idx}
                    onClick={() => navigate('/chat', { state: { action: cap.title } })}
                    className={`p-4 rounded-xl border border-slate-100 ${cap.bgColor} transition-all cursor-pointer flex flex-col justify-between group`}
                  >
                    <div>
                      <div className="p-2 rounded-lg bg-white shadow-sm w-fit mb-3">
                        {cap.icon}
                      </div>
                      <h4 className="text-xs font-bold text-slate-800 mb-1">{cap.title}</h4>
                      <p className="text-[11px] text-slate-500 leading-normal line-clamp-3">{cap.desc}</p>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 mt-3 self-end transition-transform group-hover:translate-x-1" />
                  </div>
                ))}
              </div>
            </div>

            {/* Powered by AI Section */}
            <div className="bg-gradient-to-r from-blue-50/50 via-purple-50/40 to-blue-50/50 rounded-xl p-4 border border-blue-100/60 flex items-center justify-between text-xs text-slate-600">
              <div>
                <p className="font-bold text-slate-800">Powered by Advanced AI</p>
                <p className="text-[11px] text-slate-500">
                  Combining OCR, document understanding, RAG and smart reasoning to give you the best answers.
                </p>
              </div>

              <div className="flex items-center gap-1 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm shrink-0">
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 font-semibold text-[10px] rounded">OCR</span>
                <span className="text-slate-300">→</span>
                <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 font-semibold text-[10px] rounded">RAG</span>
                <span className="text-slate-300">→</span>
                <span className="px-1.5 py-0.5 bg-cyan-100 text-cyan-700 font-semibold text-[10px] rounded">Vector DB</span>
                <span className="text-slate-300">→</span>
                <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 font-semibold text-[10px] rounded">LLM</span>
                <span className="text-slate-300 font-bold mx-1 text-slate-400">=</span>
                <span className="flex items-center gap-1 text-emerald-600 font-bold text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Unified Answer
                </span>
              </div>
            </div>
          </div>

          {/* Right Sidebar Widget Column (4 Cols) */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            {/* Quick Actions */}
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

            {/* Recent Activity */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-slate-500" />
                  Recent Activity
                </h3>
                <span className="text-[11px] font-semibold text-blue-600 cursor-pointer hover:underline">View All</span>
              </div>

              <div className="space-y-3">
                {recentActivity.map((act, idx) => (
                  <div key={idx} className="flex items-start gap-3 text-xs">
                    <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100 mt-0.5">
                      {act.icon}
                    </div>
                    <div>
                      <p className="font-medium text-slate-700">{act.text}</p>
                      <p className="text-[10px] text-slate-400">{act.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Upcoming Exams */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <CalendarIcon className="w-3.5 h-3.5 text-indigo-500" />
                  Upcoming Exams
                </h3>
                <Link to="/calendar" className="text-[11px] font-semibold text-blue-600 hover:underline">
                  View Calendar
                </Link>
              </div>

              <div className="space-y-2.5">
                {upcomingExams.map((exam, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50/80 border border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      <div>
                        <p className="text-xs font-bold text-slate-800">{exam.name}</p>
                        <p className="text-[10px] text-slate-400">{exam.date}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md ${exam.badgeBg}`}>
                      {exam.days}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}