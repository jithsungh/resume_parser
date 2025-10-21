import { FileText, Sparkles } from "lucide-react";

function Header({ healthStatus }) {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-xl">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="bg-white/20 p-3 rounded-xl backdrop-blur-sm">
              <FileText className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">
                Resume Parser
                <Sparkles className="w-6 h-6 text-yellow-300" />
              </h1>
              <p className="text-blue-100 text-sm mt-1">
                AI-Powered Resume Analysis & Extraction
              </p>
            </div>
          </div>

          {healthStatus && (
            <div className="hidden md:block">
              <div className="bg-white/10 px-4 py-2 rounded-lg backdrop-blur-sm">
                <div className="text-xs text-blue-100 mb-1">Version</div>
                <div className="font-semibold">
                  {healthStatus.version || "1.0.0"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
