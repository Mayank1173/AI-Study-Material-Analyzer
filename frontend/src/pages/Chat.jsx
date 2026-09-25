import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  Search,
  Bell,
  Sparkles,
  Upload,
  MessageSquare,
  Calendar as CalendarIcon,
  BookOpen,
  FileText,
  Zap,
  Layers,
  ChevronRight,
  GraduationCap,
  Home as HomeIcon,
  Settings,
  FileQuestion,
  History,
  Share2,
  Info,
  Clock,
  Plus,
  Camera,
  Image as ImageIcon,
  ChevronLeft,
  Mic,
  ArrowUp,
  Brain,
  Puzzle,
  UserCheck,
  Compass,
  X
} from 'lucide-react';

export default function Chat() {
  const [showHistory, setShowHistory] = useState(false);
  const [showAttachmentMenu, setShowAttachmentMenu] = useState(false);
  const [inputPrompt, setInputPrompt] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const navigate = useNavigate();
  const { user } = useUser();
  const initialLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'M';

  const handleSend = (e) => {
    e.preventDefault();
    if (inputPrompt.trim()) {
      setChatMessages((prev) => [...prev, { role: 'user', text: inputPrompt }]);
      setInputPrompt('');
    }
  };

  const handleNewChat = () => {
    setChatMessages([]);
  };

  const promptSuggestions = [
    { text: 'What is this study set about?', icon: <Brain className="w-4 h-4 text-blue-500" /> },
    { text: 'How do these topics connect?', icon: <Brain className="w-4 h-4 text-purple-500" /> },
    { text: 'Create a study plan for me', icon: <BookOpen className="w-4 h-4 text-emerald-500" /> },
    { text: 'Quiz me on this study set', icon: <BookOpen className="w-4 h-4 text-emerald-500" /> },
    { text: 'Generate flashcards for this set', icon: <Zap className="w-4 h-4 text-amber-500" /> },
    { text: 'Create a study summary', icon: <Zap className="w-4 h-4 text-amber-500" /> },
  ];

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" />, active: true },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <div className="flex h-screen bg-[#F6F5F2] text-slate-800 font-sans overflow-hidden">
      {/* Dark Sidebar */}
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
              <p className="text-sm font-medium text-white truncate">{user?.name || 'Mayank'}</p>
              <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </Link>
      </aside>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#F6F5F2]">
        
        {/* Top Header Bar */}
        <header className="h-14 bg-[#F6F5F2] flex items-center justify-between px-6 border-b border-slate-200/60 shrink-0">
          
          {/* Left Breadcrumb & Actions */}
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span className="font-medium text-slate-500">My First Study Set</span>
            <ChevronRight className="w-4 h-4 text-slate-400" />
            
            {/* New Chat Button */}
            <button 
              onClick={handleNewChat} 
              className="flex items-center gap-1.5 text-slate-600 hover:text-blue-600 transition-colors font-medium px-2 py-1 rounded-lg hover:bg-slate-200/50"
            >
              <MessageSquare className="w-4 h-4" /> New Chat
            </button>

            {/* History Button */}
            <button 
              onClick={() => setShowHistory(!showHistory)} 
              className={`flex items-center gap-1.5 transition-colors font-medium px-2 py-1 rounded-lg ${
                showHistory ? 'text-blue-600 bg-blue-50' : 'text-slate-600 hover:text-blue-600 hover:bg-slate-200/50'
              }`}
            >
              <History className="w-4 h-4" /> History
            </button>
          </div>

          {/* Right Top Bar Actions */}
          <div className="flex items-center gap-3">
            <button className="px-3 py-1.5 bg-emerald-100/70 hover:bg-emerald-200/70 text-emerald-800 text-xs font-semibold rounded-full flex items-center gap-1.5 transition-colors">
              <ArrowUp className="w-3.5 h-3.5" /> Upgrade
            </button>
            <button className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-full hover:bg-slate-50 flex items-center gap-1.5 transition-colors">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
            <button className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-full hover:bg-slate-50 flex items-center gap-1.5 transition-colors">
              <Info className="w-3.5 h-3.5" /> Feedback
            </button>

          

            {/* Profile Circle */}
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt="Avatar" className="w-8 h-8 ml-1 rounded-full object-cover" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-xs ml-1">
                {initialLetter}
              </div>
            )}
          </div>
        </header>

        {/* Content Wrapper for Chat + Sidebar */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Center Chat Area */}
          <div className="flex-1 overflow-y-auto px-6 py-8 flex flex-col items-center justify-between">
            
            {/* Conditional Rendering: Empty State vs Chat Messages */}
            {chatMessages.length === 0 ? (
              <div className="w-full max-w-3xl flex flex-col items-center space-y-6 my-auto animate-in fade-in">
                {/* Mascot Avatar */}
                <div className="w-20 h-20 rounded-full bg-pink-100 flex items-center justify-center shadow-sm relative">
                  <Sparkles className="w-10 h-10 text-pink-500" />
                </div>

                {/* Title */}
                <h2 className="text-2xl font-serif text-slate-800">How can I help?</h2>

                {/* Prompt Chips Grid */}
                <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
                  {promptSuggestions.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputPrompt(item.text)}
                      className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200/80 rounded-full text-xs font-medium text-slate-700 shadow-sm transition-all"
                    >
                      {item.icon}
                      {item.text}
                    </button>
                  ))}
                </div>

                {/* View More Button */}
                <button className="text-xs text-slate-500 hover:text-slate-700 font-medium">
                  View More
                </button>

                {/* Filter Mode Buttons */}
                <div className="flex items-center justify-center gap-2 pt-2">
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors">
                    <UserCheck className="w-3.5 h-3.5" /> Characters
                  </button>
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors">
                    <Puzzle className="w-3.5 h-3.5" /> Plugins
                  </button>
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors">
                    <Sparkles className="w-3.5 h-3.5" /> Scenarios
                  </button>
                </div>

                {/* Guided Session Banner */}
                <div className="w-full max-w-lg bg-[#EFECE6]/80 rounded-2xl p-4 flex items-center justify-between border border-slate-200/60 shadow-sm">
                  <div>
                    <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">NEW</span>
                    <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5 mt-0.5">
                      <Compass className="w-4 h-4 text-slate-700" />
                      Start a Guided Session
                    </h4>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Sparky will navigate you across StudyFetch while you learn.
                    </p>
                  </div>
                  <button className="p-2.5 bg-white hover:bg-slate-100 rounded-xl shadow-sm border border-slate-200 transition-colors">
                    <ChevronRight className="w-4 h-4 text-slate-700" />
                  </button>
                </div>
              </div>
            ) : (
              /* Active Chat Messages */
              <div className="w-full max-w-3xl flex flex-col space-y-4 mb-auto">
                {chatMessages.map((msg, index) => (
                  <div key={index} className="flex flex-col items-end animate-in fade-in slide-in-from-bottom-2">
                    <div className="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm text-sm shadow-sm max-w-[80%]">
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Bottom Floating Chat Input Area */}
            <div className="w-full max-w-2xl mt-6 shrink-0 sticky bottom-0">
              <form onSubmit={handleSend} className="bg-white rounded-3xl border border-slate-200 p-3 shadow-sm space-y-3">
                <input
                  type="text"
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  placeholder="Ask your AI tutor anything..."
                  className="w-full text-sm outline-none text-slate-700 placeholder-slate-400 bg-transparent px-2"
                />

                <div className="flex items-center justify-between pt-1">
                  {/* Left tools: Upload & Guided dropdown */}
                  <div className="flex items-center gap-3 text-slate-500 px-1">
                    <div className="relative flex items-center">
                      <button
                        type="button"
                        onClick={() => setShowAttachmentMenu(!showAttachmentMenu)}
                        className="hover:text-slate-800 transition-colors cursor-pointer"
                      >
                        <Plus className="w-4 h-4" />
                      </button>

                      {/* Attachment Pop-up Menu */}
                      {showAttachmentMenu && (
                        <div className="absolute bottom-full left-0 mb-3 w-48 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95">
                          <div className="flex flex-col py-1.5">
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left"
                            >
                              <Upload className="w-4 h-4 text-blue-500" />
                              Upload files
                            </button>
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left"
                            >
                              <Camera className="w-4 h-4 text-emerald-500" />
                              Camera
                            </button>
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left"
                            >
                              <ImageIcon className="w-4 h-4 text-purple-500" />
                              Photos
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                    <button type="button" className="flex items-center gap-1 text-xs font-medium hover:text-slate-800">
                      <Compass className="w-3.5 h-3.5" />
                      Guided
                    </button>
                  </div>

                  {/* Right tools: Mic & Submit */}
                  <div className="flex items-center gap-2">
                    <button type="button" className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100">
                      <Mic className="w-4 h-4" />
                    </button>
                    <button
                      type="submit"
                      className="p-2.5 bg-black hover:bg-slate-800 text-white rounded-xl transition-all shadow-md"
                    >
                      <ArrowUp className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>

          {/* Slide-out History Panel */}
          {showHistory && (
            <div className="w-72 bg-white border-l border-slate-200/60 flex flex-col shadow-xl z-10 shrink-0 animate-in slide-in-from-right-4 duration-300">
              <div className="h-14 border-b border-slate-100 flex items-center justify-between px-4 shrink-0">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-600" /> Chat History
                </h3>
                <button onClick={() => setShowHistory(false)} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="p-4 flex-1 overflow-y-auto">
                <div className="bg-slate-50 border border-slate-100 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-2 mt-4">
                  <History className="w-6 h-6 text-slate-300" />
                  <p className="text-xs text-slate-500">No previous chats found for this study set.</p>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}