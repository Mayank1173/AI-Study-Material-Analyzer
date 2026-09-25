import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import {
  Search,
  Bell,
  Save,
  LogOut,
  Camera,
  Mail,
  User as UserIcon,
  Globe,
  Eye,
  ShieldCheck,
  Crown,
  Check,
  Zap,
  Database,
  FileText,
  ChevronRight,
  GraduationCap,
  Home as HomeIcon,
  Layers,
  Upload,
  MessageSquare,
  Sparkles,
  FileQuestion,
  Calendar as CalendarIcon,
  Settings as SettingsIcon,
  CheckCircle,
  X
} from 'lucide-react';

export default function Settings() {
  const [theme, setTheme] = useState('light');
  const [selectedPlan, setSelectedPlan] = useState('monthly');
  const [showNotifications, setShowNotifications] = useState(false);
  const { user, updateUser } = useUser();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('Settings');
  const [formData, setFormData] = useState({
    name: user?.name || '',
    username: user?.username || '',
    email: user?.email || '',
    language: user?.language || 'English (US)',
  });

  const [toastMessage, setToastMessage] = useState('');
  const [avatarPreview, setAvatarPreview] = useState(user?.avatarUrl || '');

  // Calculate actual storage and file count from localStorage
  const [storageData] = useState(() => {
    try {
      const savedMaterials = localStorage.getItem('recently_viewed_materials');
      const parsed = savedMaterials ? JSON.parse(savedMaterials) : [];
      const fileCount = parsed.length;
      const totalSizeMB = parseFloat((fileCount * 0.8).toFixed(1)); 
      return { count: fileCount, size: totalSizeMB };
    } catch (e) {
      return { count: 0, size: 0 };
    }
  });

  const tabs = [
    'Settings',
    'Subscription',
    'Usage',
    'Notifications',
    'Personalization',
    'Privacy & Data',
    'Support',
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSaveChanges = (e) => {
    e.preventDefault();
    updateUser({
      name: formData.name,
      username: formData.username,
      email: formData.email,
      language: formData.language,
      avatarUrl: avatarPreview,
    });

    setToastMessage('Settings saved successfully!');
    setTimeout(() => setToastMessage(''), 3000);
  };

  const handleSignOut = () => {
    localStorage.removeItem('campuslearn_user');
    navigate('/login');
  };

  const sidebarNavItems = [
    { label: 'Home', path: '/dashboard', icon: <HomeIcon className="w-4 h-4" /> },
    { label: 'My Courses', path: '/courses', icon: <Layers className="w-4 h-4" /> },
    { label: 'Materials', path: '/materials', icon: <Upload className="w-4 h-4" /> },
    { label: 'AI Chat', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
    { label: 'AI Agent', path: '/agent', icon: <Sparkles className="w-4 h-4" /> },
    { label: 'PYQs', path: '/pyqs', icon: <FileQuestion className="w-4 h-4" /> },
    { label: 'Study Plan', path: '/calendar', icon: <CalendarIcon className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <SettingsIcon className="w-4 h-4" />, active: true },
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
            {avatarPreview ? (
              <img src={avatarPreview} alt="Profile" className="w-8 h-8 rounded-full object-cover" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center font-semibold justify-center text-sm">
                {initialLetter}
              </div>
            )}
            <div className="truncate max-w-[120px]">
              <p className="text-sm font-medium text-white truncate">{user?.name || 'Mayank TS'}</p>
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
              {avatarPreview ? (
                <img src={avatarPreview} alt="Profile" className="w-8 h-8 rounded-full object-cover" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-sm">
                  {initialLetter}
                </div>
              )}
              <div className="text-left leading-tight">
                <p className="text-sm font-semibold text-slate-700">{user?.name || 'Mayank TS'}</p>
                <p className="text-xs text-slate-400">{user?.role || 'Student'}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Settings Body Scrollable */}
        <div className="flex-1 overflow-y-auto p-8 max-w-6xl w-full mx-auto space-y-6">
          
          {/* Toast Alert */}
          {toastMessage && (
            <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-xs font-semibold shadow-sm animate-in fade-in">
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                {toastMessage}
              </span>
              <button onClick={() => setToastMessage('')}><X className="w-4 h-4" /></button>
            </div>
          )}

          {/* Title Header with Save and Sign Out */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                <SettingsIcon className="w-6 h-6 text-blue-600" /> Settings
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Manage your account, preferences and app settings</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleSaveChanges}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl flex items-center gap-2 shadow-sm transition-colors"
              >
                <Save className="w-4 h-4" /> Save Changes
              </button>
              <button
                onClick={handleSignOut}
                className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl flex items-center gap-2 transition-colors"
              >
                <LogOut className="w-4 h-4 text-slate-500" /> Sign Out
              </button>
            </div>
          </div>

          {/* Tabs Row */}
          <div className="border-b border-slate-200 flex items-center gap-6 text-xs font-medium text-slate-500 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-3 transition-colors whitespace-nowrap relative ${
                  activeTab === tab ? 'text-blue-600 font-bold' : 'hover:text-slate-800'
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"></span>
                )}
              </button>
            ))}
          </div>

          {/* Tab Content Area */}
          <div className="p-8 bg-white rounded-2xl border border-slate-200/80 shadow-sm">
            {activeTab === 'Settings' && (
              <div className="max-w-xl space-y-6 text-left">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Account Settings</h3>
                  <p className="text-xs text-slate-500">Update your profile details and preferences.</p>
                </div>
                
                {/* Profile Picture Card */}
                <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 flex items-center gap-6">
                  <div className="relative group">
                    {avatarPreview ? (
                      <img src={avatarPreview} alt="Avatar" className="w-20 h-20 rounded-full object-cover border-2 border-blue-500" />
                    ) : (
                      <div className="w-20 h-20 rounded-full bg-blue-600 text-white font-bold text-2xl flex items-center justify-center">
                        {initialLetter}
                      </div>
                    )}
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-800">Profile Picture</h4>
                    <p className="text-xs text-slate-400">Upload a profile picture to personalize your account.</p>
                    <label className="inline-block mt-2 px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer transition-colors">
                      Change Photo
                      <input type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
                    </label>
                  </div>
                </div>

                {/* Account Details Form */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                    <input 
                      type="text" 
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Username</label>
                    <input 
                      type="text" 
                      name="username"
                      value={formData.username}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                    <input 
                      type="email" 
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Subscription' && (
              <div className="max-w-4xl mx-auto space-y-6 text-left">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Subscription Plans</h3>
                  <p className="text-xs text-slate-500">Manage your current plan and billing options.</p>
                </div>

                {/* Monthly / Annual Toggle */}
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

                {/* Plans Side-by-Side Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  
                  {/* Free Plan Card */}
                  <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-base font-bold text-slate-800">Free Tier</h4>
                        <span className="text-xs font-semibold px-2.5 py-1 bg-white text-slate-600 border border-slate-200 rounded-full">Active Plan</span>
                      </div>
                      <p className="text-xs text-slate-500">Essential tools to get started with your studies.</p>
                      <div className="mt-4">
                        <span className="text-3xl font-bold text-slate-800">₹0</span>
                        <span className="text-xs text-slate-400">/forever</span>
                      </div>
                    </div>

                    <ul className="space-y-2.5 text-xs text-slate-600 pt-4 border-t border-slate-200">
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-slate-400" /> Up to 5 document uploads</li>
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-slate-400" /> Standard AI chat responses</li>
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-slate-400" /> Basic study plan calendar</li>
                    </ul>

                    <button
                      disabled
                      className="w-full py-2.5 bg-white text-slate-400 border border-slate-200 rounded-xl text-xs font-semibold cursor-not-allowed"
                    >
                      Current Plan
                    </button>
                  </div>

                  {/* Pro Student Pass Card */}
                  <div className="bg-gradient-to-br from-blue-50/70 via-indigo-50/40 to-white p-6 rounded-2xl border-2 border-blue-500 shadow-sm flex flex-col justify-between space-y-4 relative">
                    <span className="absolute -top-3 right-6 bg-blue-600 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-sm">
                      Recommended
                    </span>
                    <div>
                      <div className="mb-2">
                        <h4 className="text-base font-bold text-slate-800 flex items-center gap-2">
                          <Crown className="w-5 h-5 text-amber-500 fill-amber-500" /> Pro Student Pass
                        </h4>
                      </div>
                      <p className="text-xs text-slate-500">Everything you need for comprehensive exam preparation.</p>
                      <div className="mt-4">
                        <span className="text-3xl font-bold text-slate-800">{selectedPlan === 'monthly' ? '₹799' : '₹8999'}</span>
                        <span className="text-xs text-slate-400">/{selectedPlan === 'monthly' ? 'mo' : 'yr'}</span>
                      </div>
                    </div>

                    <ul className="space-y-2.5 text-xs text-slate-600 pt-4 border-t border-blue-100">
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500" /> Unlimited OCR & Document Uploads</li>
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500" /> Advanced RAG & Long-Context AI Reasoning</li>
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500" /> Fast PYQ Analysis & Quiz Generation</li>
                      <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500" /> Priority Processing Speed</li>
                    </ul>

                    <button
                      onClick={() => alert('Proceeding to checkout for Pro Student Pass...')}
                      className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-500/20 transition-colors"
                    >
                      Upgrade to Pro
                    </button>
                  </div>

                </div>
              </div>
            )}

            {activeTab === 'Usage' && (
              <div className="max-w-4xl mx-auto space-y-6 text-left">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Resource Usage</h3>
                  <p className="text-xs text-slate-500">Monitor your plan limits and storage consumption.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Storage */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                        <Database className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Plan Limit</span>
                    </div>
                    <h4 className="text-2xl font-bold text-slate-800">{storageData.size}<span className="text-sm font-medium text-slate-400"> MB / 2 GB</span></h4>
                    <p className="text-xs text-slate-500 mt-1">Storage Used</p>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 mt-4 overflow-hidden">
                      <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.max((storageData.size / 2000) * 100, 2)}%` }}></div>
                    </div>
                  </div>

                  {/* Documents */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                        <FileText className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total</span>
                    </div>
                    <h4 className="text-2xl font-bold text-slate-800">{storageData.count}<span className="text-sm font-medium text-slate-400"> files</span></h4>
                    <p className="text-xs text-slate-500 mt-1">Documents Uploaded / Tracked</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Notifications' && (
              <div className="max-w-3xl mx-auto text-left space-y-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Notifications</h3>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                  <h4 className="text-sm font-semibold text-slate-800 mb-3">Recent Alerts</h4>
                  <div className="rounded-xl bg-white p-4 text-sm text-slate-600 border border-slate-100">
                    You have no new notifications.
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Personalization' && (
              <div className="max-w-3xl mx-auto text-left space-y-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Personalization</h3>
                
                {/* Theme Settings */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                  <h4 className="text-sm font-semibold text-slate-800 mb-3">Theme Preferences</h4>
                  <div className="flex items-center gap-3">
                    <button className="px-4 py-2 bg-blue-50 text-blue-600 border border-blue-200 rounded-xl text-sm font-semibold">
                      Light Mode
                    </button>
                    <button className="px-4 py-2 bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 rounded-xl text-sm font-medium transition-colors">
                      Dark Mode
                    </button>
                    <button className="px-4 py-2 bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 rounded-xl text-sm font-medium transition-colors">
                      System Sync
                    </button>
                  </div>
                </div>

                {/* AI Avatar Settings */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                  <h4 className="text-sm font-semibold text-slate-800 mb-1">Custom AI Avatar</h4>
                  <p className="text-xs text-slate-500 mb-4">Generate a unique profile picture using AI.</p>
                  <div className="flex gap-3">
                    <input 
                      type="text" 
                      placeholder="e.g., Anime style featuring Naruto's headband and Ichigo's sword" 
                      className="flex-1 px-4 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                    />
                    <button className="px-5 py-2 bg-[#0F172A] hover:bg-slate-800 text-white rounded-xl text-sm font-semibold shadow-md transition-colors">
                      Generate
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Privacy & Data' && (
              <div className="max-w-3xl mx-auto text-left space-y-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Privacy & Data</h3>
                
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm space-y-6">
                  {/* Data Export */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800">Export Your Data</h4>
                      <p className="text-xs text-slate-500 mt-1">Download a copy of all your uploaded materials, chats, and quiz history.</p>
                    </div>
                    <button className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-sm font-medium transition-colors whitespace-nowrap">
                      Request Export
                    </button>
                  </div>

                  {/* Activity Tracking */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800">Activity Tracking</h4>
                      <p className="text-xs text-slate-500 mt-1">Allow CampusLearn to use your study patterns to improve AI recommendations.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" defaultChecked />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Delete Account */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
                    <div>
                      <h4 className="text-sm font-semibold text-red-600">Delete Account</h4>
                      <p className="text-xs text-slate-500 mt-1">Permanently remove your account and all associated data. This cannot be undone.</p>
                    </div>
                    <button className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-sm font-medium transition-colors whitespace-nowrap">
                      Delete Account
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Support' && (
              <div className="max-w-3xl mx-auto text-left space-y-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Help & Support</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* FAQ Card */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 shadow-sm hover:shadow-md transition-shadow cursor-pointer group border-l-4 border-l-blue-500">
                    <h4 className="text-sm font-bold text-slate-800 group-hover:text-blue-600 transition-colors">FAQs & Guides</h4>
                    <p className="text-xs text-slate-500 mt-1">Browse tutorials and answers to common questions about CampusLearn.</p>
                  </div>
                  
                  {/* Contact Card */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 shadow-sm hover:shadow-md transition-shadow cursor-pointer group border-l-4 border-l-emerald-500">
                    <h4 className="text-sm font-bold text-slate-800 group-hover:text-emerald-600 transition-colors">Contact Support</h4>
                    <p className="text-xs text-slate-500 mt-1">Need human help? Create a ticket and our team will get back to you.</p>
                  </div>
                </div>

                {/* Bug Report Form */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm mt-6">
                  <h4 className="text-sm font-semibold text-slate-800 mb-1">Report an Issue</h4>
                  <p className="text-xs text-slate-500 mb-4">Found a bug or have a feature request? Let us know below.</p>
                  
                  <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); alert('Report submitted successfully!'); }}>
                    <textarea 
                      rows="4"
                      placeholder="Describe the issue you're facing in detail..."
                      className="w-full px-4 py-3 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                    ></textarea>
                    <div className="flex justify-end">
                      <button type="submit" className="px-5 py-2.5 bg-[#0F172A] hover:bg-slate-800 text-white rounded-xl text-sm font-semibold shadow-md transition-colors">
                        Submit Report
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}