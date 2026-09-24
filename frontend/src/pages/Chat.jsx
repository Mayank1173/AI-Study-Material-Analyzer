import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUser } from '../hooks/useUser';
import { api, ApiError } from '../api/client';

const makeConversationId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};
import {
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
  Mic,
  ArrowUp,
  Brain,
  Puzzle,
  UserCheck,
  Compass,
  X,
  Loader2,
  AlertCircle,
  ChevronDown,
  FileSearch
} from 'lucide-react';

export default function Chat() {
  const location = useLocation();
  const { user, logout } = useUser();

  const [showHistory, setShowHistory] = useState(false);
  const [showAttachmentMenu, setShowAttachmentMenu] = useState(false);
  const [inputPrompt, setInputPrompt] = useState(() => {
    const state = location.state;
    if (!state) return '';
    const prompt = state.initialPrompt || state.action;
    if (prompt && typeof prompt === 'string' && prompt.trim()) return prompt.trim();
    return '';
  });
  const [chatMessages, setChatMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [conversationId, setConversationId] = useState(makeConversationId);
  const [courses, setCourses] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState(() => location.state?.courseId || '');
  const [selectedMaterialId, setSelectedMaterialId] = useState('');
  const [showCourseDropdown, setShowCourseDropdown] = useState(false);
  const [showMaterialDropdown, setShowMaterialDropdown] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const initialLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'U';

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, isLoading, scrollToBottom]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.get('/courses/mine?page=1&page_size=100');
        if (!cancelled) setCourses(data?.items || []);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          if (!cancelled) logout();
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [logout]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const params = new URLSearchParams();
        params.set('page', '1');
        params.set('page_size', '100');
        if (selectedCourseId) params.set('course_id', selectedCourseId);
        const data = await api.get(`/materials?${params.toString()}`);
        if (!cancelled) setMaterials(data?.items || []);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          if (!cancelled) logout();
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [selectedCourseId, logout]);

  const handleSend = useCallback(async (e) => {
    if (e) e.preventDefault();
    const question = inputPrompt.trim();
    if (!question || isLoading) return;

    setError('');
    setIsLoading(true);

    setChatMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInputPrompt('');

    try {
      const body = { message: question };
      if (conversationId) body.conversation_id = conversationId;
      if (selectedCourseId) body.course_id = selectedCourseId;
      if (selectedMaterialId) body.material_id = selectedMaterialId;

      const data = await api.post('/chat', { body });

      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer || 'No answer generated.',
          sources: data.sources || [],
          hasContext: data.has_context,
        },
      ]);
    } catch (err) {
      let msg = 'Something went wrong. Please try again.';
      if (err instanceof ApiError) {
        if (err.status === 401) {
          msg = 'Your session has expired. Please log in again.';
          logout();
        } else if (err.status === 404) {
          msg = 'The chat service could not be found. Please try again later.';
        } else if (err.status === 503) {
          msg = 'The AI service is temporarily unavailable. Please try again in a moment.';
        } else if (err.status >= 500) {
          msg = 'The server encountered an error. Please try again later.';
        } else {
          msg = err.message || msg;
        }
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        msg = 'Unable to connect to the server. Please check your connection.';
      }
      setError(msg);
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Error: ${msg}`, isError: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [inputPrompt, isLoading, selectedCourseId, selectedMaterialId, conversationId, logout]);

  const handleNewChat = () => {
    setChatMessages([]);
    setInputPrompt('');
    setError('');
    setIsLoading(false);
    setConversationId(makeConversationId());
    setSelectedCourseId('');
    setSelectedMaterialId('');
  };

  const handlePromptSuggestion = (text) => {
    setInputPrompt(text);
    if (inputRef.current) inputRef.current.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const promptSuggestions = [
    { text: 'What is this study set about?', icon: <Brain className="w-4 h-4 text-blue-500" /> },
    { text: 'How do these topics connect?', icon: <Brain className="w-4 h-4 text-purple-500" /> },
    { text: 'Create a study plan for me', icon: <BookOpen className="w-4 h-4 text-emerald-500" /> },
    { text: 'Quiz me on this study set', icon: <BookOpen className="w-4 h-4 text-emerald-500" /> },
    { text: 'Generate flashcards for this set', icon: <Zap className="w-4 h-4 text-amber-500" /> },
    { text: 'Create a study summary', icon: <Zap className="w-4 h-4 text-amber-500" /> },
  ];

  const filteredMaterials = selectedCourseId
    ? materials.filter((m) => m.course_id === selectedCourseId)
    : materials;

  const selectedCourseName = courses.find((c) => c.id === selectedCourseId)?.name || 'All Courses';
  const selectedMaterialTitle = filteredMaterials.find((m) => m.id === selectedMaterialId)?.title
    || filteredMaterials.find((m) => m.id === selectedMaterialId)?.file_name
    || 'All Materials';

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" />, active: true },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  const formatScore = (score) => {
    if (!score && score !== 0) return null;
    return `${Math.round(score * 100)}%`;
  };

  return (
    <div className="flex h-screen bg-[#F6F5F2] dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-sans overflow-hidden">
      {/* Dark Sidebar */}
      <aside className="w-64 bg-[#0F172A] dark:bg-[#111318] text-slate-300 flex flex-col justify-between p-4 shrink-0">
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
              {initialLetter}
            </div>
            <div>
              <p className="text-sm font-medium text-white">{user?.name}</p>
              <p className="text-xs text-slate-400">{user?.email}</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </aside>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#F6F5F2] dark:bg-slate-900">
        
        {/* Top Header Bar */}
        <header className="h-14 bg-[#F6F5F2] dark:bg-[#121417] flex items-center justify-between px-6 border-b border-slate-200/60 dark:border-slate-700 shrink-0">
          
          {/* Left Breadcrumb & Actions */}
          <div className="flex items-center gap-3 text-sm text-slate-600">
            {/* Course Filter */}
            <div className="relative">
              <button
                onClick={() => { setShowCourseDropdown(!showCourseDropdown); setShowMaterialDropdown(false); }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors max-w-[180px] dark:bg-slate-700 dark:border-slate-600 dark:text-slate-200"
              >
                <BookOpen className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span className="truncate">{selectedCourseName}</span>
                <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
              </button>
              {showCourseDropdown && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 dark:bg-slate-800 dark:border-slate-700">
                  <div className="py-1">
                    <button
                      onClick={() => { setSelectedCourseId(''); setSelectedMaterialId(''); setShowCourseDropdown(false); }}
                      className={`w-full text-left px-4 py-2 text-xs font-medium transition-colors ${!selectedCourseId ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700'}`}
                    >
                      All Courses
                    </button>
                    {courses.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => { setSelectedCourseId(c.id); setSelectedMaterialId(''); setShowCourseDropdown(false); }}
                        className={`w-full text-left px-4 py-2 text-xs font-medium transition-colors ${selectedCourseId === c.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700'}`}
                      >
                        {c.name}
                      </button>
                    ))}
                    {courses.length === 0 && (
                      <p className="px-4 py-2 text-xs text-slate-400">No courses yet</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            <ChevronRight className="w-4 h-4 text-slate-400" />

            {/* Material Filter */}
            <div className="relative">
              <button
                onClick={() => { setShowMaterialDropdown(!showMaterialDropdown); setShowCourseDropdown(false); }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors max-w-[180px] dark:bg-slate-700 dark:border-slate-600 dark:text-slate-200"
              >
                <FileText className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span className="truncate">{selectedMaterialTitle}</span>
                <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
              </button>
              {showMaterialDropdown && (
                <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 dark:bg-slate-800 dark:border-slate-700">
                  <div className="py-1 max-h-60 overflow-y-auto">
                    <button
                      onClick={() => { setSelectedMaterialId(''); setShowMaterialDropdown(false); }}
                      className={`w-full text-left px-4 py-2 text-xs font-medium transition-colors ${!selectedMaterialId ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700'}`}
                    >
                      All Materials
                    </button>
                    {filteredMaterials.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => { setSelectedMaterialId(m.id); setShowMaterialDropdown(false); }}
                        className={`w-full text-left px-4 py-2 text-xs font-medium transition-colors ${selectedMaterialId === m.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700'}`}
                      >
                        {m.title || m.file_name || 'Untitled'}
                      </button>
                    ))}
                    {filteredMaterials.length === 0 && (
                      <p className="px-4 py-2 text-xs text-slate-400">No materials found</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* New Chat Button */}
            <button 
              onClick={handleNewChat} 
              className="flex items-center gap-1.5 text-slate-600 hover:text-blue-600 transition-colors font-medium px-2 py-1 rounded-lg hover:bg-slate-200/50 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <MessageSquare className="w-4 h-4" /> New Chat
            </button>

            {/* History Button */}
            <button 
              onClick={() => setShowHistory(!showHistory)} 
              className={`flex items-center gap-1.5 transition-colors font-medium px-2 py-1 rounded-lg ${
                showHistory ? 'text-blue-600 bg-blue-50' : 'text-slate-600 hover:text-blue-600 hover:bg-slate-200/50 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              <History className="w-4 h-4" /> History
            </button>
          </div>

          {/* Right Top Bar Actions */}
          <div className="flex items-center gap-3">
            <button className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-full hover:bg-slate-50 flex items-center gap-1.5 transition-colors dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
            <button className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-full hover:bg-slate-50 flex items-center gap-1.5 transition-colors dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300">
              <Info className="w-3.5 h-3.5" /> Feedback
            </button>

            {/* Timer Badge */}
            <div className="flex items-center gap-1 px-3 py-1.5 bg-amber-100/80 dark:bg-amber-900/30 dark:text-amber-200 text-amber-900 rounded-full text-xs font-semibold">
              <Clock className="w-3.5 h-3.5" /> 25m
            </div>

            {/* Profile Circle */}
            <div className="w-8 h-8 rounded-full bg-blue-700 text-white font-semibold flex items-center justify-center text-xs ml-1">
              {initialLetter}
            </div>
          </div>
        </header>

        {/* Content Wrapper for Chat + Sidebar */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Click-away handler for dropdowns */}
          {(showCourseDropdown || showMaterialDropdown) && (
            <div
              className="fixed inset-0 z-40"
              onClick={() => { setShowCourseDropdown(false); setShowMaterialDropdown(false); }}
            />
          )}

          {/* Center Chat Area */}
          <div className="flex-1 overflow-y-auto px-6 py-8 flex flex-col items-center justify-between">
            
            {/* Error Banner */}
            {error && (
              <div className="w-full max-w-3xl mb-4">
                <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs dark:bg-red-900/30 dark:border-red-800 dark:text-red-300">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                  <button onClick={() => setError('')} className="ml-auto p-0.5 hover:bg-red-100 rounded">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}

            {/* Conditional Rendering: Empty State vs Chat Messages */}
            {chatMessages.length === 0 ? (
              <div className="w-full max-w-3xl flex flex-col items-center space-y-6 my-auto animate-in fade-in">
                {/* Mascot Avatar */}
                <div className="w-20 h-20 rounded-full bg-pink-100 flex items-center justify-center shadow-sm relative dark:bg-pink-900/30">
                  <Sparkles className="w-10 h-10 text-pink-500" />
                </div>

                {/* Title */}
                <h2 className="text-2xl font-serif text-slate-800 dark:text-slate-100">How can I help?</h2>

                {/* Prompt Chips Grid */}
                <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
                  {promptSuggestions.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => handlePromptSuggestion(item.text)}
                      className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200/80 rounded-full text-xs font-medium text-slate-700 shadow-sm transition-all dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300"
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
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors dark:bg-slate-700 dark:text-slate-300">
                    <UserCheck className="w-3.5 h-3.5" /> Characters
                  </button>
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors dark:bg-slate-700 dark:text-slate-300">
                    <Puzzle className="w-3.5 h-3.5" /> Plugins
                  </button>
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-[#EFECE6] hover:bg-slate-200 text-slate-700 rounded-full text-xs font-medium transition-colors dark:bg-slate-700 dark:text-slate-300">
                    <Sparkles className="w-3.5 h-3.5" /> Scenarios
                  </button>
                </div>

                {/* Guided Session Banner */}
                <div className="w-full max-w-lg bg-[#EFECE6]/80 rounded-2xl p-4 flex items-center justify-between border border-slate-200/60 shadow-sm dark:bg-slate-800 dark:border-slate-700">
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
                  <div key={index} className={`animate-in fade-in slide-in-from-bottom-2 ${msg.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}>
                    {/* User Message */}
                    {msg.role === 'user' && (
                      <div className="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm text-sm shadow-sm max-w-[80%]">
                        {msg.text}
                      </div>
                    )}

                    {/* Assistant Message */}
                    {msg.role === 'assistant' && (
                      <div className={`flex flex-col gap-2 max-w-[85%] ${msg.isError ? 'w-full' : ''}`}>
                        <div className={`px-4 py-3 rounded-2xl rounded-tl-sm text-sm shadow-sm ${
                          msg.isError
                            ? 'bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
                            : 'bg-white border border-slate-200 text-slate-700 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200'
                        }`}>
                          <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>

                          {/* No Context Indicator */}
                          {msg.hasContext === false && !msg.isError && (
                            <div className="mt-2 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg px-2.5 py-1.5">
                              <FileSearch className="w-3.5 h-3.5 shrink-0" />
                              This answer was generated without matching study materials.
                            </div>
                          )}
                        </div>

                        {/* Sources */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="flex flex-col gap-1.5">
                            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-1">
                              Sources
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.sources.map((src, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300"
                                >
                                  <FileText className="w-3 h-3 text-blue-500 shrink-0" />
                                  <span className="font-medium text-slate-700 truncate max-w-[200px]">
                                    {src.original_filename || src.material_title || 'Material'}
                                  </span>
                                  {src.source_location && (
                                    <>
                                      <span className="text-slate-300">|</span>
                                      <span className="text-slate-500 truncate max-w-[120px]">{src.source_location}</span>
                                    </>
                                  )}
                                  {formatScore(src.score) && (
                                    <>
                                      <span className="text-slate-300">|</span>
                                      <span className="text-emerald-600 font-semibold">{formatScore(src.score)}</span>
                                    </>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Loading / Typing Indicator */}
                {isLoading && (
                  <div className="flex flex-col items-start animate-in fade-in slide-in-from-bottom-2">
                    <div className="bg-white border border-slate-200 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm dark:bg-slate-800 dark:border-slate-700">
                      <div className="flex items-center gap-2 text-slate-500">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                        <span className="text-xs font-medium">Thinking...</span>
                        <div className="flex gap-1">
                          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}

            {/* Bottom Floating Chat Input Area */}
            <div className="w-full max-w-2xl mt-6 shrink-0 sticky bottom-0">
              <form onSubmit={handleSend} className="bg-white rounded-3xl border border-slate-200 p-3 shadow-sm space-y-3 dark:bg-slate-800 dark:border-slate-700">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask your AI tutor anything..."
                  disabled={isLoading}
                  className="w-full text-sm outline-none text-slate-700 placeholder-slate-400 bg-transparent px-2 disabled:opacity-50 dark:text-slate-200 dark:placeholder-slate-400"
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
                        <div className="absolute bottom-full left-0 mb-3 w-48 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 dark:bg-slate-800 dark:border-slate-700">
                          <div className="flex flex-col py-1.5">
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left dark:text-slate-300 dark:hover:bg-slate-700"
                            >
                              <Upload className="w-4 h-4 text-blue-500" />
                              Upload files
                            </button>
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left dark:text-slate-300 dark:hover:bg-slate-700"
                            >
                              <Camera className="w-4 h-4 text-emerald-500" />
                              Camera
                            </button>
                            <button 
                              type="button"
                              onClick={() => setShowAttachmentMenu(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors w-full text-left dark:text-slate-300 dark:hover:bg-slate-700"
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
                      disabled={isLoading || !inputPrompt.trim()}
                      className="p-2.5 bg-black hover:bg-slate-800 text-white rounded-xl transition-all shadow-md disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-black"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <ArrowUp className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>

          {/* Slide-out History Panel */}
          {showHistory && (
            <div className="w-72 bg-white border-l border-slate-200/60 flex flex-col shadow-xl z-10 shrink-0 animate-in slide-in-from-right-4 duration-300 dark:bg-slate-800 dark:border-slate-700">
              <div className="h-14 border-b border-slate-100 flex items-center justify-between px-4 shrink-0">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 dark:text-slate-100">
                  <History className="w-4 h-4 text-blue-600" /> Chat History
                </h3>
                <button onClick={() => setShowHistory(false)} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="p-4 flex-1 overflow-y-auto">
                {chatMessages.length > 0 ? (
                  <div className="space-y-2">
                    {chatMessages.filter((m) => m.role === 'user').map((msg, idx) => (
                      <button
                        key={idx}
                        onClick={() => setInputPrompt(msg.text)}
                        className="w-full text-left px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-100 rounded-xl text-xs text-slate-600 truncate transition-colors dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300"
                      >
                        {msg.text}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-100 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-2 mt-4 dark:bg-slate-700 dark:border-slate-600">
                    <History className="w-6 h-6 text-slate-300" />
                    <p className="text-xs text-slate-500">No previous chats found for this session.</p>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
