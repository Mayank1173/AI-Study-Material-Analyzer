import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  Search,
  Bell,
  GraduationCap,
  Home as HomeIcon,
  Layers,
  Upload,
  MessageSquare,
  Sparkles,
  FileQuestion,
  Calendar as CalendarIcon,
  Settings as SettingsIcon,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Plus,
  X,
  FileText,
  CheckCircle2,
  HelpCircle,
  BarChart3,
  GitCompare,
  Target,
  Sliders,
  Sparkle,
  ArrowRight
} from 'lucide-react';

export default function PYQs() {
  const [showNotifications, setShowNotifications] = useState(false);
  const { user } = useUser();

  // State for Uploaded Files
  const [files, setFiles] = useState([
    { id: 1, name: 'DCCN_2023.pdf', size: '1.2 MB', status: 'ready' },
    { id: 2, name: 'DCCN_2024.pdf', size: '1.4 MB', status: 'ready' },
    { id: 3, name: 'DCCN_2025.pdf', size: '1.1 MB', status: 'ready' },
    { id: 4, name: 'DCCN_Model_Paper.pdf', size: '980 KB', status: 'ready' },
  ]);

  // State for Settings
  const [selectedCourse, setSelectedCourse] = useState('Data Communication and Computer Networks (DCCN)');
  const [numQuestions, setNumQuestions] = useState('Top 10');
  const [answerLength, setAnswerLength] = useState('Detailed');
  const [selectedMarks, setSelectedMarks] = useState('10 Marks');
  
  // Style Checkboxes State
  const [styles, setStyles] = useState({
    pointWise: true,
    includeDiagrams: true,
    simpleLanguage: true,
    stepByStep: false,
    paragraphFormat: false,
    includeExamples: false,
    includeDefinitions: false,
    prosAndCons: false,
  });

  // Questions List
  const [expandedQuestionId, setExpandedQuestionId] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const initialQuestions = [
    {
      id: 1,
      question: 'Explain the OSI reference model with a neat diagram.',
      yearsAppeared: '2023, 2024, 2025',
      unit: 'Unit 1',
      marks: 10,
      importance: 'High',
      answer: 'The OSI (Open Systems Interconnection) model defines a networking framework to implement protocols in seven layers: Physical, Data Link, Network, Transport, Session, Presentation, and Application layers.'
    },
    {
      id: 2,
      question: 'Explain TCP and UDP protocols. Compare their differences.',
      yearsAppeared: '2024, 2025',
      unit: 'Unit 2',
      marks: 10,
      importance: 'High',
      answer: 'TCP is connection-oriented, reliable, and byte-stream based with error-checking and flow control. UDP is connectionless, faster, lightweight, and does not guarantee packet delivery.'
    },
    {
      id: 3,
      question: 'What is routing? Explain distance vector routing algorithm.',
      yearsAppeared: '2023, 2024',
      unit: 'Unit 3',
      marks: 10,
      importance: 'High',
      answer: 'Routing is the process of selecting a path for traffic in a network. Distance Vector Routing relies on Bellman-Ford algorithm where routers share distance vectors with immediate neighbors.'
    },
    {
      id: 4,
      question: 'Explain network security threats and their countermeasures.',
      yearsAppeared: '2023, 2025',
      unit: 'Unit 4',
      marks: 10,
      importance: 'High',
      answer: 'Threats include eavesdropping, spoofing, Denial-of-Service (DoS), and malware. Countermeasures involve encryption (AES/RSA), firewalls, intrusion detection systems (IDS), and strong authentication.'
    },
    {
      id: 5,
      question: 'What is congestion control? Explain different techniques.',
      yearsAppeared: '2024',
      unit: 'Unit 3',
      marks: 10,
      importance: 'Medium',
      answer: 'Congestion control regulates traffic entering a telecommunication network to avoid link overload. Open-loop mechanisms prevent congestion, while closed-loop mechanisms detect and resolve it dynamically.'
    },
  ];

  const [questions, setQuestions] = useState(initialQuestions);

  // Toggle Checkbox
  const handleStyleChange = (key) => {
    setStyles((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Add Dummy File
  const handleFileUpload = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    if (uploadedFiles.length > 0) {
      const newFileItems = uploadedFiles.map((file, idx) => ({
        id: Date.now() + idx,
        name: file.name,
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        status: 'ready'
      }));
      setFiles((prev) => [...prev, ...newFileItems]);
    }
  };

  // Remove File
  const handleRemoveFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Trigger Analysis
  const handleAnalyze = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
    }, 1000);
  };

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" />, active: true },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <SettingsIcon className="w-4 h-4" /> },
  ];

  const initialLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'M';

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

        {/* User Badge */}
        <div className="flex items-center justify-between p-3 bg-slate-800/60 rounded-xl border border-slate-700/50">
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
            </div>
          </div>
        </header>

        {/* Scrollable Dashboard Body */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
          {/* Main Content Area (Left 8 Cols) */}
          <div className="col-span-12 lg:col-span-8 space-y-6">
            
            {/* Banner Section */}
            <div className="bg-gradient-to-r from-blue-50/90 via-indigo-50/60 to-purple-50/90 rounded-2xl p-6 border border-blue-100 flex items-center justify-between relative overflow-hidden">
              <div className="flex items-center gap-4">
                <div className="p-3.5 bg-blue-600 text-white rounded-2xl shadow-lg shadow-blue-500/20">
                  <FileQuestion className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">PYQ Analyzer</h2>
                  <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">
                    Upload previous-year question papers, identify important questions, and generate exam-ready answers using your study materials.
                  </p>
                </div>
              </div>

              <button className="text-xs font-semibold text-slate-600 hover:text-blue-600 flex items-center gap-1 bg-white/80 px-3 py-1.5 rounded-full border border-slate-200/80 shadow-sm">
                <HelpCircle className="w-3.5 h-3.5" /> How it works?
              </button>
            </div>

            {/* Upload Area & Uploaded Files Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Upload Dropzone */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-bold text-slate-800">Upload Question Papers</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">Upload PDF, images, or DOC/DOCX files. You can add multiple files.</p>
                  
                  {/* Supported File Badge Chips */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className="px-2 py-0.5 bg-rose-50 text-rose-600 text-[10px] font-bold rounded border border-rose-100 flex items-center gap-1">
                      <FileText className="w-3 h-3" /> PDF
                    </span>
                    <span className="px-2 py-0.5 bg-purple-50 text-purple-600 text-[10px] font-bold rounded border border-purple-100">
                      Image
                    </span>
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-bold rounded border border-blue-100">
                      DOC/DOCX
                    </span>
                  </div>
                </div>

                <div className="mt-6 flex items-center gap-3">
                  <label className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl cursor-pointer flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition-all">
                    <Plus className="w-4 h-4" /> Add Files
                    <input type="file" multiple onChange={handleFileUpload} className="hidden" />
                  </label>
                  <span className="text-xs text-slate-400 font-medium">or Drag & Drop</span>
                </div>
              </div>

              {/* Uploaded Files List */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
                <h3 className="text-xs font-bold text-slate-800 mb-3">Uploaded Files ({files.length})</h3>
                
                <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                  {files.map((file) => (
                    <div key={file.id} className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <div className="flex items-center gap-2.5 truncate">
                        <span className="p-1.5 bg-rose-100 text-rose-600 rounded-lg">
                          <FileText className="w-3.5 h-3.5" />
                        </span>
                        <div className="truncate">
                          <p className="font-semibold text-slate-700 truncate">{file.name}</p>
                          <p className="text-[10px] text-slate-400">{file.size}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        <button onClick={() => handleRemoveFile(file.id)} className="text-slate-400 hover:text-rose-500 p-1">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Feature Highlights Row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-xl shrink-0">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">AI-Powered Analysis</h4>
                  <p className="text-[10px] text-slate-400 leading-tight">Finds repeated, important & trending questions</p>
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl shrink-0">
                  <GitCompare className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Cross-Year Comparison</h4>
                  <p className="text-[10px] text-slate-400 leading-tight">Compares questions across different years</p>
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-purple-50 text-purple-600 rounded-xl shrink-0">
                  <Target className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Smart Ranking</h4>
                  <p className="text-[10px] text-slate-400 leading-tight">Ranks questions by importance, frequency & marks</p>
                </div>
              </div>
            </div>

            {/* Top 10 Important Questions Table */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Sparkle className="w-4 h-4 text-blue-600 fill-blue-600" />
                  Top 10 Important Questions
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Based on analysis of 4 question papers • 86 total questions</p>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 text-[11px] font-semibold">
                      <th className="py-2.5 px-2">#</th>
                      <th className="py-2.5 px-2">Question</th>
                      <th className="py-2.5 px-2">Years Appeared</th>
                      <th className="py-2.5 px-2">Unit</th>
                      <th className="py-2.5 px-2">Marks</th>
                      <th className="py-2.5 px-2">Importance</th>
                      <th className="py-2.5 px-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {questions.map((q) => (
                      <React.Fragment key={q.id}>
                        <tr className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-2 font-bold text-slate-500">{q.id}</td>
                          <td className="py-3 px-2 font-semibold text-slate-800 max-w-xs">{q.question}</td>
                          <td className="py-3 px-2 text-slate-500 font-medium">{q.yearsAppeared}</td>
                          <td className="py-3 px-2 text-slate-500 font-medium">{q.unit}</td>
                          <td className="py-3 px-2 font-bold text-slate-800">{q.marks}</td>
                          <td className="py-3 px-2">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              q.importance === 'High' ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-amber-50 text-amber-600 border border-amber-100'
                            }`}>
                              {q.importance}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-right">
                            <button
                              onClick={() => setExpandedQuestionId(expandedQuestionId === q.id ? null : q.id)}
                              className="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 font-semibold rounded-lg text-[11px] inline-flex items-center gap-1 transition-colors"
                            >
                              View Answer
                              {expandedQuestionId === q.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          </td>
                        </tr>

                        {/* Answer Expanded Row */}
                        {expandedQuestionId === q.id && (
                          <tr>
                            <td colSpan="7" className="p-4 bg-slate-50/90 rounded-xl">
                              <div className="text-xs text-slate-700 space-y-1">
                                <p className="font-bold text-blue-600">AI-Generated Answer:</p>
                                <p className="leading-relaxed bg-white p-3 rounded-xl border border-slate-200">{q.answer}</p>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Table Footer */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                <span className="text-slate-400">Showing 5 of 10 important questions</span>
                <button className="text-blue-600 font-semibold hover:underline flex items-center gap-1">
                  View All 10 Questions <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

          </div>

          {/* Right Sidebar Columns (4 Cols - Analysis Settings) */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            
            {/* Analysis Settings Widget */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-5">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-blue-600" />
                Analysis Settings
              </h3>

              {/* Select Course Dropdown */}
              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-slate-700">Select Course</label>
                <select
                  value={selectedCourse}
                  onChange={(e) => setSelectedCourse(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 font-medium outline-none focus:border-blue-500"
                >
                  <option>Data Communication and Computer Networks (DCCN)</option>
                  <option>Operating Systems (OS)</option>
                  <option>Full Stack Development (FSD)</option>
                  <option>Environment and Sustainability (E&S)</option>
                </select>
              </div>

              {/* Number of Questions Pills */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-700">Number of Questions</label>
                <div className="flex flex-wrap gap-1.5">
                  {['Top 5', 'Top 10', 'Top 15', 'Top 20', 'Custom'].map((item) => (
                    <button
                      key={item}
                      onClick={() => setNumQuestions(item)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
                        numQuestions === item
                          ? 'bg-blue-50 border-blue-500 text-blue-600'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>

              {/* Answer Format - Answer Length */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-700">Answer Format</label>
                <p className="text-[10px] text-slate-400">Answer Length</p>
                <div className="flex flex-wrap gap-1.5">
                  {['Very Short', 'Short', 'Medium', 'Detailed', 'Exam-Oriented'].map((item) => (
                    <button
                      key={item}
                      onClick={() => setAnswerLength(item)}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all ${
                        answerLength === item
                          ? 'bg-blue-50 border-blue-500 text-blue-600'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>

              {/* Answer Style Checkboxes */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-700">Answer Style</label>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.pointWise} onChange={() => handleStyleChange('pointWise')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Point-wise format</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.paragraphFormat} onChange={() => handleStyleChange('paragraphFormat')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Paragraph format</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.includeDiagrams} onChange={() => handleStyleChange('includeDiagrams')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Include diagrams</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.includeExamples} onChange={() => handleStyleChange('includeExamples')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Include examples</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.simpleLanguage} onChange={() => handleStyleChange('simpleLanguage')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Simple language</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.includeDefinitions} onChange={() => handleStyleChange('includeDefinitions')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Include definitions</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.stepByStep} onChange={() => handleStyleChange('stepByStep')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Step-by-step explanation</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={styles.prosAndCons} onChange={() => handleStyleChange('prosAndCons')} className="rounded text-blue-600" />
                    <span className="text-[11px]">Pros & Cons</span>
                  </label>
                </div>
              </div>

              {/* Marks Filter */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-700">Marks</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {['2 Marks', '5 Marks', '10 Marks', '15 Marks'].map((m) => (
                    <button
                      key={m}
                      onClick={() => setSelectedMarks(m)}
                      className={`py-1 rounded-lg text-xs font-semibold border transition-all ${
                        selectedMarks === m
                          ? 'bg-blue-50 border-blue-500 text-blue-600'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              {/* Analyze PYQs Primary Action Button */}
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-blue-500/20 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                {isAnalyzing ? 'Analyzing Question Papers...' : 'Analyze PYQs'}
              </button>
            </div>

            {/* Analysis Summary Box */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-blue-600" />
                Analysis Summary
              </h3>

              {/* Stat Counters Row */}
              <div className="grid grid-cols-4 gap-2 text-center">
                <div className="bg-blue-50/60 p-2 rounded-xl border border-blue-100">
                  <p className="text-[9px] font-semibold text-slate-400">Papers Analyzed</p>
                  <p className="text-base font-bold text-blue-600 mt-0.5">{files.length}</p>
                </div>
                <div className="bg-emerald-50/60 p-2 rounded-xl border border-emerald-100">
                  <p className="text-[9px] font-semibold text-slate-400">Total Questions</p>
                  <p className="text-base font-bold text-emerald-600 mt-0.5">86</p>
                </div>
                <div className="bg-purple-50/60 p-2 rounded-xl border border-purple-100">
                  <p className="text-[9px] font-semibold text-slate-400">Repeated</p>
                  <p className="text-base font-bold text-purple-600 mt-0.5">24</p>
                </div>
                <div className="bg-amber-50/60 p-2 rounded-xl border border-amber-100">
                  <p className="text-[9px] font-semibold text-slate-400">Top Priority</p>
                  <p className="text-base font-bold text-amber-600 mt-0.5">12</p>
                </div>
              </div>

              {/* Most Repeated Topics List */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <h4 className="text-[11px] font-bold text-slate-700">Most Repeated Topics</h4>
                <ol className="space-y-1.5 text-xs text-slate-600">
                  <li className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center">1</span>
                    1. OSI Model
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center">2</span>
                    2. TCP/IP
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center">3</span>
                    3. Routing Algorithms
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center">4</span>
                    4. Network Security
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center">5</span>
                    5. Error Detection
                  </li>
                </ol>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}