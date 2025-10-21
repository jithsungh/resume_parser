import { useState, useEffect } from "react";
import {
  FileText,
  Users,
  Brain,
  FileSearch,
  Contact2,
  Activity,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import Header from "./components/Header";
import SingleParser from "./components/SingleParser";
import BatchParser from "./components/BatchParser";
import NERExtractor from "./components/NERExtractor";
import SectionSegmenter from "./components/SectionSegmenter";
import ContactExtractor from "./components/ContactExtractor";
import Dashboard from "./components/Dashboard";
import { healthCheck } from "./api";

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [healthStatus, setHealthStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const health = await healthCheck();
      setHealthStatus(health);
      setLoading(false);
    } catch (error) {
      console.error("Health check failed:", error);
      setHealthStatus({ status: "unhealthy" });
      setLoading(false);
    }
  };

  const tabs = [
    { id: "dashboard", name: "Dashboard", icon: Activity },
    { id: "single", name: "Single Resume", icon: FileText },
    { id: "batch", name: "Batch Processing", icon: Users },
    { id: "ner", name: "NER Extraction", icon: Brain },
    { id: "sections", name: "Section Segmentation", icon: FileSearch },
    { id: "contact", name: "Contact Info", icon: Contact2 },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-xl text-gray-600">Initializing Resume Parser...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header healthStatus={healthStatus} />

      {/* Status Banner */}
      {healthStatus && (
        <div
          className={`py-2 px-4 text-center text-sm ${
            healthStatus.status === "healthy"
              ? "bg-green-50 text-green-800"
              : "bg-red-50 text-red-800"
          }`}
        >
          {healthStatus.status === "healthy" ? (
            <div className="flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>
                System Operational - Model Loaded:{" "}
                {healthStatus.model_loaded ? "Yes" : "No"}
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <XCircle className="w-4 h-4" />
              <span>System Initializing - Please Wait</span>
            </div>
          )}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="bg-white shadow-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex space-x-1 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 font-medium text-sm whitespace-nowrap border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-600 hover:text-blue-600 hover:border-gray-300"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content Area */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-fade-in">
          {activeTab === "dashboard" && <Dashboard />}
          {activeTab === "single" && <SingleParser />}
          {activeTab === "batch" && <BatchParser />}
          {activeTab === "ner" && <NERExtractor />}
          {activeTab === "sections" && <SectionSegmenter />}
          {activeTab === "contact" && <ContactExtractor />}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          <p>© 2025 Resume Parser API - AI-Powered Resume Analysis</p>
          <p className="mt-2">Built with FastAPI, Transformers, and React</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
