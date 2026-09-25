import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  GraduationCap,
  Home as HomeIcon,
  Layers,
  Upload,
  MessageSquare,
  Sparkles,
  FileQuestion,
  Calendar as CalendarIcon,
  Settings,
  ChevronRight,
  ChevronLeft,
  ArrowUp,
  Share2,
  Info,
  Clock,
  Plus,
  Sliders,
  UploadCloud
} from 'lucide-react';

export default function Calendar() {
  const { user } = useUser();
  const initialLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'U';

  // --- STATE ---
  const [viewMode, setViewMode] = useState('Week');
  const [currentDate, setCurrentDate] = useState(new Date()); 
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [syllabusName, setSyllabusName] = useState('My First Study Set');

  // --- NAVIGATION ---
  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" />, active: true },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  const timeSlots = [
    '7 AM', '8 AM', '9 AM', '10 AM', '11 AM', '12 PM',
    '1 PM', '2 PM', '3 PM', '4 PM', '5 PM', '6 PM'
  ];

  const monthNames = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
  ];

  // --- DATE MATH ---
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();

  const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();
  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();

  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDayOfMonth = getFirstDayOfMonth(currentYear, currentMonth);

  const miniCalendarBlanks = Array.from({ length: firstDayOfMonth }, () => null);
  const miniCalendarDays = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const allMiniCalendarSlots = [...miniCalendarBlanks, ...miniCalendarDays];

  const generateGridDays = () => {
    const start = new Date(selectedDate);
    
    if (viewMode === 'Day') {
      return [{
        name: ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][start.getDay()],
        date: start.getDate(),
        fullDate: start,
        isToday: start.toDateString() === new Date().toDateString(),
        isSelected: true
      }];
    }
    
    start.setDate(start.getDate() - start.getDay());
    
    return Array.from({ length: 7 }).map((_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return {
        name: ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][d.getDay()],
        date: d.getDate(),
        fullDate: d,
        isToday: d.toDateString() === new Date().toDateString(),
        isSelected: d.toDateString() === selectedDate.toDateString()
      };
    });
  };

  const gridDays = generateGridDays();

  const formatHeaderRange = () => {
    if (viewMode === 'Day') {
      return `${monthNames[selectedDate.getMonth()].substring(0, 3)} ${selectedDate.getDate()}, ${selectedDate.getFullYear()}`;
    }
    
    const start = gridDays[0].fullDate;
    const end = gridDays[gridDays.length - 1].fullDate;
    const startMonth = monthNames[start.getMonth()].substring(0, 3);
    const endMonth = monthNames[end.getMonth()].substring(0, 3);
    
    if (start.getMonth() === end.getMonth()) {
      return `${startMonth} ${start.getDate()} – ${end.getDate()}, ${end.getFullYear()}`;
    }
    return `${startMonth} ${start.getDate()} – ${endMonth} ${end.getDate()}, ${end.getFullYear()}`;
  };

  // --- HANDLERS ---
  const prevMonth = () => setCurrentDate(new Date(currentYear, currentMonth - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(currentYear, currentMonth + 1, 1));
  
  const handleMiniDayClick = (day) => {
    const newSelection = new Date(currentYear, currentMonth, day);
    setSelectedDate(newSelection);
  };

  const goToday = () => {
    const today = new Date();
    setCurrentDate(today);
    setSelectedDate(today);
    setViewMode('Week'); 
  };

  const handleMainPrev = () => {
    const newDate = new Date(selectedDate);
    if (viewMode === 'Day') newDate.setDate(newDate.getDate() - 1);
    if (viewMode === 'Week') newDate.setDate(newDate.getDate() - 7);
    if (viewMode === 'Month') newDate.setMonth(newDate.getMonth() - 1);
    setSelectedDate(newDate);
    setCurrentDate(newDate); 
  };

  const handleMainNext = () => {
    const newDate = new Date(selectedDate);
    if (viewMode === 'Day') newDate.setDate(newDate.getDate() + 1);
    if (viewMode === 'Week') newDate.setDate(newDate.getDate() + 7);
    if (viewMode === 'Month') newDate.setMonth(newDate.getMonth() + 1);
    setSelectedDate(newDate);
    setCurrentDate(newDate);
  };

  return (
    <div className="flex h-screen bg-[#F6F5F2] text-slate-800 font-sans overflow-hidden">
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

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#F6F5F2]">
        
        {/* Top Header Bar */}
        <header className="h-14 bg-[#F6F5F2] flex items-center justify-between px-6 border-b border-slate-200/60 shrink-0">
          <h1 className="font-serif text-lg text-slate-800">Calendar</h1>

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

        {/* Calendar Control Header */}
        <div className="h-14 px-6 flex items-center justify-between border-b border-slate-200/60 shrink-0">
          <div className="flex items-center gap-4">
            <button onClick={goToday} className="px-4 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-full text-xs font-medium shadow-sm hover:bg-slate-50 transition-colors">
              Today
            </button>
            <div className="flex items-center gap-1">
              <button onClick={handleMainPrev} className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 rounded-full transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button onClick={handleMainNext} className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 rounded-full transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <h2 className="text-base font-serif text-slate-800 min-w-[160px]">{formatHeaderRange()}</h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-[#EFECE6] p-1 rounded-full flex items-center text-xs font-medium">
              {['Day', 'Week', 'Month'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1 rounded-full transition-all ${
                    viewMode === mode ? 'bg-white text-slate-800 shadow-sm font-semibold' : 'text-slate-600 hover:text-slate-800'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>

            <button className="px-4 py-1.5 bg-black hover:bg-slate-800 text-white text-xs font-medium rounded-full flex items-center gap-1.5 shadow-sm transition-colors">
              <Plus className="w-4 h-4" /> Add
            </button>
            <button className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 rounded-full transition-colors">
              <Sliders className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Calendar Grid Body */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Mini Calendar */}
          <div className="w-64 border-r border-slate-200/60 p-4 space-y-6 overflow-y-auto shrink-0 bg-[#F6F5F2]">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800">{monthNames[currentMonth]} {currentYear}</h3>
                <div className="flex items-center gap-1">
                  <button onClick={prevMonth} className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 rounded transition-colors"><ChevronLeft className="w-3.5 h-3.5" /></button>
                  <button onClick={nextMonth} className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 rounded transition-colors"><ChevronRight className="w-3.5 h-3.5" /></button>
                </div>
              </div>

              <div className="grid grid-cols-7 text-center text-[11px] font-semibold text-slate-400 mb-1">
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => <span key={i}>{d}</span>)}
              </div>

              <div className="grid grid-cols-7 text-center text-xs gap-y-1">
                {allMiniCalendarSlots.map((day, index) => {
                  if (!day) return <span key={`blank-${index}`} className="w-6 h-6 mx-auto"></span>;
                  
                  const isDaySelected = selectedDate.getDate() === day && selectedDate.getMonth() === currentMonth && selectedDate.getFullYear() === currentYear;
                  const isDayToday = new Date().getDate() === day && new Date().getMonth() === currentMonth && new Date().getFullYear() === currentYear;

                  return (
                    <button
                      key={day}
                      onClick={() => handleMiniDayClick(day)}
                      className={`w-6 h-6 mx-auto flex items-center justify-center rounded-full text-[11px] font-medium transition-colors ${
                        isDaySelected ? 'bg-black text-white font-bold shadow-sm' : 
                        isDayToday ? 'bg-blue-100 text-blue-700 font-bold' : 
                        'text-slate-700 hover:bg-slate-200/80'
                      }`}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Syllabus Upload Card */}
            <div className="bg-[#EFECE6]/80 rounded-2xl p-4 border border-slate-200/60 space-y-3">
              <h3 className="text-sm font-serif font-bold text-slate-800">Upload your syllabus</h3>
              <p className="text-[11px] text-slate-500 leading-normal">
                We'll auto-fill your exam dates and tell you what to study.
              </p>

              <div className="bg-white rounded-xl p-2.5 border border-slate-200/80 flex items-center justify-between overflow-hidden">
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg shrink-0">
                    <Layers className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-semibold text-slate-800 truncate max-w-[120px]" title={syllabusName}>
                    {syllabusName}
                  </span>
                </div>
                
                {/* Hidden file input handling the upload */}
                <input 
                  type="file" 
                  id="syllabus-upload" 
                  className="hidden" 
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSyllabusName(e.target.files[0].name);
                    }
                  }}
                />
                <label htmlFor="syllabus-upload">
                  <UploadCloud className="w-4 h-4 text-slate-400 cursor-pointer hover:text-blue-500 transition-colors" />
                </label>
              </div>

              <label 
                htmlFor="syllabus-upload"
                className="w-full py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 flex items-center justify-center gap-1 shadow-sm transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" /> New Set
              </label>
            </div>
          </div>

          {/* Right Main Grid */}
          <div className="flex-1 overflow-y-auto flex flex-col bg-[#F6F5F2]">
            <div className={`grid border-b border-slate-200/60 sticky top-0 bg-[#F6F5F2] z-10 ${viewMode === 'Day' ? 'grid-cols-2' : 'grid-cols-8'}`}>
              <div className="p-2 text-[10px] text-slate-400 font-medium border-r border-slate-200/60 flex items-end justify-center">
                GMT+5:30
              </div>
              
              {gridDays.map((day, i) => (
                <div key={i} className="p-3 text-center border-r border-slate-200/60">
                  <p className="text-[10px] font-semibold text-slate-500 tracking-wider">{day.name}</p>
                  <p className={`text-base font-bold mt-0.5 inline-flex items-center justify-center transition-colors ${
                    day.isSelected ? 'w-8 h-8 rounded-full bg-black text-white shadow-sm' : 
                    day.isToday ? 'w-8 h-8 rounded-full bg-blue-100 text-blue-700' : 'text-slate-800'
                  }`}>
                    {day.date}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex-1">
              {timeSlots.map((slot, idx) => (
                <div key={idx} className={`grid h-16 border-b border-slate-200/60 ${viewMode === 'Day' ? 'grid-cols-2' : 'grid-cols-8'}`}>
                  <div className="text-[10px] text-slate-400 font-medium pr-2 pt-1 text-right border-r border-slate-200/60">
                    {slot}
                  </div>
                  {Array.from({ length: viewMode === 'Day' ? 1 : 7 }).map((_, colIdx) => (
                    <div
                      key={colIdx}
                      className={`relative border-r border-slate-200/60 transition-colors ${
                        gridDays[colIdx]?.isToday ? 'bg-amber-50/10' : ''
                      }`}
                    >
                      <input
                        type="text"
                        className="absolute inset-0 w-full h-full bg-transparent px-2 text-[11px] font-medium text-slate-700 outline-none hover:bg-slate-100/60 focus:bg-white focus:ring-1 focus:ring-blue-400 focus:z-10"
                        placeholder=""
                      />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* Right Drawer */}
          <div className="w-12 border-l border-slate-200/60 bg-[#F6F5F2] flex flex-col items-center pt-6 space-y-4 shrink-0">
            <button className="p-2 hover:bg-slate-200/60 rounded-xl flex flex-col items-center text-[10px] text-slate-600 font-medium transition-colors">
              <div className="w-6 h-6 rounded-full bg-pink-100 text-pink-500 flex items-center justify-center mb-1">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              Chat
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}