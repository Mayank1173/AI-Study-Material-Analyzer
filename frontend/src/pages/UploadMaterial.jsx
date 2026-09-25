import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
  ChevronLeft,
  FileText,
  UploadCloud,
  X,
  Eye,
  Download,
  MoreHorizontal,
  Zap,
  HelpCircle,
  Check,
  Filter,
  Plus,
  BookOpen,
  Image as ImageIcon,
  Video as VideoIcon,
  FileCode,
  FolderPlus
} from 'lucide-react';

export default function UploadMaterial() {
  const [showNotifications, setShowNotifications] = useState(false);
  const { user } = useUser();
  const navigate = useNavigate();
  // Calculate actual storage used based on uploaded materials
const [storageInfo] = useState(() => {
  try {
    const saved = localStorage.getItem('recently_viewed_materials');
    const list = saved ? JSON.parse(saved) : [];
    const count = list.length || 12; // Fallback to your default file count if empty
    const sizeMB = (count * 0.8).toFixed(1);
    const percent = Math.min(Math.round((sizeMB / 1000) * 100), 100);
    return { sizeMB, percent, count };
  } catch (e) {
    return { sizeMB: '9.6', percent: 1, count: 12 };
  }
});

  // Initial Materials List
  const initialMaterials = [
    { id: 1, name: 'DCCN_2024.pdf', sub: 'Previous Year Question Paper', type: 'PDF', course: 'DCCN', uploadedOn: '12 Sep 2026, 10:24 AM', size: '1.4 MB' },
    { id: 2, name: 'DCCN_Lectures.pptx', sub: 'Lecture Slides', type: 'PPT', course: 'DCCN', uploadedOn: '10 Sep 2026, 03:12 PM', size: '8.6 MB' },
    { id: 3, name: 'E&S_Notes.docx', sub: 'Class Notes', type: 'DOCX', course: 'E&S', uploadedOn: '8 Sep 2026, 11:45 AM', size: '2.3 MB' },
    { id: 4, name: 'Network_Diagram.png', sub: 'Network Topology', type: 'Image', course: 'DCCN', uploadedOn: '6 Sep 2026, 04:32 PM', size: '1.1 MB' },
    { id: 5, name: 'FSD_Lecture.mp4', sub: 'Full Stack Development', type: 'Video', course: 'FSD', uploadedOn: '4 Sep 2026, 09:18 AM', size: '45.2 MB' },
    { id: 6, name: 'Ethical_Hacking_Notes.pdf', sub: 'Study Material', type: 'PDF', course: 'Ethical Hacking', uploadedOn: '2 Sep 2026, 02:27 PM', size: '3.8 MB' },
  ];

  const [materials, setMaterials] = useState(initialMaterials);
  const [activeTab, setActiveTab] = useState('All Materials');
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Search & Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('All Types');
  const [courseFilter, setCourseFilter] = useState('All Courses');
  const [sortBy, setSortBy] = useState('Recently Added');
  const [onlyMyUploads, setOnlyMyUploads] = useState(false);

  // Modal State for Viewing Material
  const [viewingItem, setViewingItem] = useState(null);

  // File Upload Handler
  const handleFileUpload = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    if (uploadedFiles.length > 0) {
      const newItems = uploadedFiles.map((file, idx) => ({
        id: Date.now() + idx,
        name: file.name,
        sub: 'Uploaded Resource',
        type: file.name.endsWith('.pdf') ? 'PDF' : file.name.endsWith('.pptx') ? 'PPT' : file.name.endsWith('.mp4') ? 'Video' : 'DOCX',
        course: 'DCCN',
        uploadedOn: new Date().toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`
      }));
      setMaterials((prev) => [...newItems, ...prev]);
    }
  };

  // Toggle Row Checkbox
  const toggleSelectRow = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Toggle Select All
  const toggleSelectAll = () => {
    if (selectedIds.length === filteredMaterials.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredMaterials.map((m) => m.id));
    }
  };

  // Clear Filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setTypeFilter('All Types');
    setCourseFilter('All Courses');
    setSortBy('Recently Added');
    setOnlyMyUploads(false);
  };

  // Delete Selected
  const handleDeleteSelected = () => {
    setMaterials((prev) => prev.filter((m) => !selectedIds.includes(m.id)));
    setSelectedIds([]);
  };

  // Filter Logic
  const filteredMaterials = materials.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) || item.sub.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === 'All Types' || item.type === typeFilter;
    const matchesCourse = courseFilter === 'All Courses' || item.course === courseFilter;
    
    let matchesTab = true;
    if (activeTab === 'Notes') matchesTab = item.type === 'DOCX' || item.sub.includes('Notes');
    else if (activeTab === 'PPTs (2)') matchesTab = item.type === 'PPT';
    else if (activeTab === 'PDFs (3)') matchesTab = item.type === 'PDF';
    else if (activeTab === 'Videos (1)') matchesTab = item.type === 'Video';
    else if (activeTab === 'Images (1)') matchesTab = item.type === 'Image';

    return matchesSearch && matchesType && matchesCourse && matchesTab;
  });

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/upload', icon: <Upload className="w-4 h-4" />, active: true },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <SettingsIcon className="w-4 h-4" /> },
  ];

  const quickActions = [
    { title: 'Upload Material', desc: 'Add notes, PDFs, PPTs, images, etc.', icon: <Upload className="w-4 h-4 text-blue-500" />, action: () => document.getElementById('file-input').click() },
    { title: 'Create Notes', desc: 'Generate AI notes from your materials', icon: <FileText className="w-4 h-4 text-emerald-500" />, action: () => navigate('/chat') },
    { title: 'Summarize Content', desc: 'Get key points and summaries', icon: <BookOpen className="w-4 h-4 text-indigo-500" />, action: () => navigate('/agent') },
    { title: 'Generate Flashcards', desc: 'Convert notes to flashcards', icon: <Zap className="w-4 h-4 text-amber-500" />, action: () => navigate('/chat') },
    { title: 'Search Materials', desc: 'Find what you need instantly', icon: <Search className="w-4 h-4 text-purple-500" />, action: () => document.getElementById('search-input').focus() },
  ];

  const aiFeatures = [
    'Extract key concepts from your materials',
    'Detect important topics',
    'Find repeated questions (PYQs)',
    'Generate study notes',
    'Provide source references for answers'
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

        {/* User Sidebar Bottom Badge */}
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
              <p className="text-sm font-medium text-white truncate">{user?.name || 'Mayank'}</p>
              <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <div className="relative w-1/3">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              id="search-input"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
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
                <p className="text-sm font-semibold text-slate-700">{user?.name || 'Mayank'}</p>
                <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
          {/* Main Content Area (Left 8 Cols) */}
          <div className="col-span-12 lg:col-span-8 space-y-6">
            
            {/* Header Banner */}
            <div className="bg-gradient-to-r from-blue-50/90 via-indigo-50/60 to-purple-50/90 rounded-2xl p-6 border border-blue-100 flex items-center justify-between relative overflow-hidden">
              <div className="flex items-center gap-4">
                <div className="p-3.5 bg-blue-600 text-white rounded-2xl shadow-lg shadow-blue-500/20">
                  <FolderPlus className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">Study Materials</h2>
                  <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">
                    Upload and manage all your study materials. Our AI will analyze them together and help you get better insights, notes, and answers.
                  </p>
                </div>
              </div>
            </div>

            {/* Filter Toolbar Card */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm space-y-3">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search for notes, PDFs, PPTs, or anything..."
                  className="w-full pl-9 pr-10 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
                <button className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1.5 bg-blue-600 text-white rounded-lg">
                  <Search className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Filter Select Controls */}
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                    className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl font-medium text-slate-700 outline-none"
                  >
                    <option>All Types</option>
                    <option>PDF</option>
                    <option>PPT</option>
                    <option>DOCX</option>
                    <option>Video</option>
                    <option>Image</option>
                  </select>

                  <select
                    value={courseFilter}
                    onChange={(e) => setCourseFilter(e.target.value)}
                    className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl font-medium text-slate-700 outline-none"
                  >
                    <option>All Courses</option>
                    <option>DCCN</option>
                    <option>E&S</option>
                    <option>FSD</option>
                    <option>Ethical Hacking</option>
                  </select>

                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl font-medium text-slate-700 outline-none"
                  >
                    <option>Recently Added</option>
                    <option>Name (A-Z)</option>
                    <option>Size</option>
                  </select>

                  <label className="flex items-center gap-2 cursor-pointer text-slate-600 pl-2">
                    <input
                      type="checkbox"
                      checked={onlyMyUploads}
                      onChange={() => setOnlyMyUploads(!onlyMyUploads)}
                      className="rounded text-blue-600"
                    />
                    <span className="text-[11px] font-medium">Show only my uploads</span>
                  </label>
                </div>

                <button
                  onClick={handleClearFilters}
                  className="text-blue-600 hover:underline font-semibold text-xs flex items-center gap-1"
                >
                  <X className="w-3.5 h-3.5" /> Clear Filters
                </button>
              </div>
            </div>

            {/* Drag & Drop Upload Zone */}
            <div className="bg-white rounded-2xl p-8 border-2 border-dashed border-slate-200 text-center space-y-4 hover:border-blue-400 transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                <UploadCloud className="w-6 h-6" />
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-800">Drag & drop files here or click to upload</h3>
                <p className="text-[11px] text-slate-400 mt-1">Supports PDF, PPT, DOC, DOCX, Images, Videos (MP4, MOV, etc.)</p>
              </div>

              <div>
                <label className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl cursor-pointer inline-flex items-center gap-2 shadow-md shadow-blue-500/20 transition-all">
                  <Upload className="w-4 h-4" /> Choose Files
                  <input id="file-input" type="file" multiple onChange={handleFileUpload} className="hidden" />
                </label>
              </div>

              {/* Supported File Type Badges */}
              <div className="flex items-center justify-center gap-4 pt-2">
                <div className="flex flex-col items-center gap-1">
                  <span className="p-2 bg-rose-100 text-rose-600 rounded-xl"><FileText className="w-4 h-4" /></span>
                  <span className="text-[10px] text-slate-500 font-medium">PDF Files</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="p-2 bg-amber-100 text-amber-600 rounded-xl"><Layers className="w-4 h-4" /></span>
                  <span className="text-[10px] text-slate-500 font-medium">PPT Files</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="p-2 bg-blue-100 text-blue-600 rounded-xl"><BookOpen className="w-4 h-4" /></span>
                  <span className="text-[10px] text-slate-500 font-medium">DOC/DOCX</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="p-2 bg-purple-100 text-purple-600 rounded-xl"><ImageIcon className="w-4 h-4" /></span>
                  <span className="text-[10px] text-slate-500 font-medium">Images</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="p-2 bg-emerald-100 text-emerald-600 rounded-xl"><VideoIcon className="w-4 h-4" /></span>
                  <span className="text-[10px] text-slate-500 font-medium">Videos</span>
                </div>
              </div>
            </div>

            {/* Materials Table & Tabs */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-4">
              
              {/* Category Tabs */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-4 text-xs font-semibold text-slate-500 overflow-x-auto">
                  {['All Materials (12)', 'Notes (4)', 'PPTs (2)', 'PDFs (3)', 'Videos (1)', 'Images (1)', 'Others (1)'].map((tab) => {
                    const tabName = tab.split(' ')[0];
                    const isActive = activeTab.startsWith(tabName);
                    return (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-1 transition-colors whitespace-nowrap ${
                          isActive ? 'text-blue-600 border-b-2 border-blue-600 font-bold' : 'hover:text-slate-800'
                        }`}
                      >
                        {tab}
                      </button>
                    );
                  })}
                </div>

                {selectedIds.length > 0 && (
                  <button
                    onClick={handleDeleteSelected}
                    className="px-3 py-1 bg-rose-50 text-rose-600 border border-rose-200 rounded-lg text-xs font-semibold hover:bg-rose-100"
                  >
                    Delete Selected ({selectedIds.length})
                  </button>
                )}
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 text-[11px] font-semibold">
                      <th className="py-2.5 px-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.length === filteredMaterials.length && filteredMaterials.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded text-blue-600"
                        />
                      </th>
                      <th className="py-2.5 px-2">Name</th>
                      <th className="py-2.5 px-2">Type</th>
                      <th className="py-2.5 px-2">Course</th>
                      <th className="py-2.5 px-2">Uploaded On</th>
                      <th className="py-2.5 px-2">Size</th>
                      <th className="py-2.5 px-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredMaterials.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-2">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(item.id)}
                            onChange={() => toggleSelectRow(item.id)}
                            className="rounded text-blue-600"
                          />
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-2.5">
                            <span className={`p-1.5 rounded-lg text-[10px] font-bold ${
                              item.type === 'PDF' ? 'bg-rose-100 text-rose-600' : item.type === 'PPT' ? 'bg-amber-100 text-amber-600' : item.type === 'Video' ? 'bg-emerald-100 text-emerald-600' : 'bg-blue-100 text-blue-600'
                            }`}>
                              {item.type}
                            </span>
                            <div>
                              <p className="font-semibold text-slate-800">{item.name}</p>
                              <p className="text-[10px] text-slate-400">{item.sub}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                            {item.type}
                          </span>
                        </td>
                        <td className="py-3 px-2 font-semibold text-blue-600">{item.course}</td>
                        <td className="py-3 px-2 text-slate-400 text-[11px]">{item.uploadedOn}</td>
                        <td className="py-3 px-2 text-slate-500 font-medium">{item.size}</td>
                        <td className="py-3 px-2 text-right">
                          <div className="flex items-center justify-end gap-2 text-slate-400">
                            <button onClick={() => alert(`Downloading ${item.name}`)} className="hover:text-blue-600 p-1">
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => setViewingItem(item)} className="hover:text-blue-600 p-1">
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button className="hover:text-slate-600 p-1">
                              <MoreHorizontal className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Table Footer & Pagination */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs text-slate-400">
                <span>Showing {filteredMaterials.length} of {materials.length} materials</span>
                <div className="flex items-center gap-1">
                  <button className="p-1 rounded hover:bg-slate-100"><ChevronLeft className="w-4 h-4" /></button>
                  <button className="w-6 h-6 bg-blue-600 text-white font-bold rounded-lg text-xs">1</button>
                  <button className="w-6 h-6 hover:bg-slate-100 text-slate-600 rounded-lg text-xs">2</button>
                  <button className="p-1 rounded hover:bg-slate-100"><ChevronRight className="w-4 h-4" /></button>
                </div>
              </div>
            </div>

          </div>

          {/* Right Sidebar Columns (4 Cols - Storage & Actions) */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
           {/* Dynamic Storage Usage Widget */}
<div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
  <div className="flex items-center justify-between">
    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Storage Usage</span>
    <button className="text-xs font-semibold text-blue-600 hover:underline">Upgrade</button>
  </div>
  <div>
    <div className="flex justify-between text-xs text-slate-600 mb-1 font-medium">
      <span>{storageInfo.sizeMB} MB of 2 GB used</span>
      <span>{storageInfo.percent}%</span>
    </div>
    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
      <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${Math.max(storageInfo.percent, 2)}%` }}></div>
    </div>
  </div>
</div>

            {/* Quick Actions Panel */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-blue-600" />
                Quick Actions
              </h3>
              <div className="space-y-2">
                {quickActions.map((action, idx) => (
                  <div
                    key={idx}
                    onClick={action.action}
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
                  </div>
                ))}
              </div>
            </div>

            {/* AI Features Checklist */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm space-y-3">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                AI Features
              </h3>

              <div className="space-y-2 text-xs text-slate-600">
                {aiFeatures.map((feature, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-50 transition-colors">
                    <span className="flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                      {feature}
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* View Material Modal Overlay */}
      {viewingItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 space-y-4 relative">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" /> Material Details
              </h3>
              <button onClick={() => setViewingItem(null)} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-700">
              <p><strong>File Name:</strong> {viewingItem.name}</p>
              <p><strong>Description:</strong> {viewingItem.sub}</p>
              <p><strong>Type:</strong> {viewingItem.type}</p>
              <p><strong>Course:</strong> {viewingItem.course}</p>
              <p><strong>Uploaded On:</strong> {viewingItem.uploadedOn}</p>
              <p><strong>File Size:</strong> {viewingItem.size}</p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button onClick={() => setViewingItem(null)} className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold">
                Close
              </button>
              <button onClick={() => navigate('/chat')} className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-500/20">
                Analyze with AI
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}