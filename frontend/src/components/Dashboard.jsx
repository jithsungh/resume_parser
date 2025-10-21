import {
  FileText,
  Users,
  Brain,
  FileSearch,
  TrendingUp,
  Clock,
  CheckCircle,
  Zap,
} from "lucide-react";

function Dashboard() {
  const features = [
    {
      icon: FileText,
      title: "Single Resume Parsing",
      description:
        "Upload and parse individual resumes with complete information extraction",
      color: "blue",
      stats: "Supports PDF, DOCX, TXT",
    },
    {
      icon: Users,
      title: "Batch Processing",
      description:
        "Process multiple resumes simultaneously with async job tracking",
      color: "purple",
      stats: "Up to 100 files per batch",
    },
    {
      icon: Brain,
      title: "NER Extraction",
      description:
        "Extract named entities like companies, roles, dates, and technologies",
      color: "green",
      stats: "Deep learning powered",
    },
    {
      icon: FileSearch,
      title: "Section Segmentation",
      description: "Automatically identify and extract resume sections",
      color: "orange",
      stats: "8+ section types",
    },
  ];

  const capabilities = [
    "Contact Information (Name, Email, Phone, Location)",
    "Work Experience with Company & Role details",
    "Total Years of Experience calculation",
    "Primary Role identification",
    "Skills extraction per experience",
    "Date parsing (From/To dates)",
    "Employment duration calculation",
    "Entity recognition with confidence scores",
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="card bg-gradient-to-br from-blue-600 to-blue-800 text-white">
        <div className="grid md:grid-cols-2 gap-8 items-center">
          <div>
            <h2 className="text-4xl font-bold mb-4">
              Welcome to Resume Parser
            </h2>
            <p className="text-blue-100 text-lg mb-6">
              Advanced AI-powered resume parsing with state-of-the-art NER
              models and intelligent section segmentation. Extract structured
              data from resumes in seconds.
            </p>
            <div className="flex gap-4">
              <div className="bg-white/20 px-4 py-3 rounded-lg backdrop-blur-sm">
                <div className="text-2xl font-bold">99%</div>
                <div className="text-sm text-blue-100">Accuracy</div>
              </div>
              <div className="bg-white/20 px-4 py-3 rounded-lg backdrop-blur-sm">
                <div className="text-2xl font-bold">&lt;2s</div>
                <div className="text-sm text-blue-100">Processing</div>
              </div>
              <div className="bg-white/20 px-4 py-3 rounded-lg backdrop-blur-sm">
                <div className="text-2xl font-bold">3</div>
                <div className="text-sm text-blue-100">Formats</div>
              </div>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="bg-white/10 p-8 rounded-2xl backdrop-blur-sm">
              <FileText className="w-32 h-32 mx-auto text-blue-200 opacity-50" />
            </div>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div>
        <h3 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <Zap className="w-6 h-6 text-yellow-500" />
          Key Features
        </h3>
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const colors = {
              blue: "from-blue-500 to-blue-600",
              purple: "from-purple-500 to-purple-600",
              green: "from-green-500 to-green-600",
              orange: "from-orange-500 to-orange-600",
            };

            return (
              <div
                key={index}
                className="card hover:scale-105 transition-transform duration-300"
              >
                <div
                  className={`inline-block p-3 rounded-xl bg-gradient-to-br ${
                    colors[feature.color]
                  } mb-4`}
                >
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <h4 className="text-xl font-bold text-gray-800 mb-2">
                  {feature.title}
                </h4>
                <p className="text-gray-600 mb-3">{feature.description}</p>
                <div className="text-sm text-gray-500 font-medium">
                  {feature.stats}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Capabilities */}
      <div className="card">
        <h3 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <CheckCircle className="w-6 h-6 text-green-500" />
          What We Extract
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          {capabilities.map((capability, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-blue-50 transition-colors"
            >
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              <span className="text-gray-700">{capability}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Start */}
      <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-200">
        <h3 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-purple-600" />
          Quick Start Guide
        </h3>
        <div className="grid md:grid-cols-3 gap-6 mt-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-3">
              1
            </div>
            <h4 className="font-semibold text-gray-800 mb-2">Choose Feature</h4>
            <p className="text-sm text-gray-600">
              Select from single parsing, batch processing, or specialized
              extraction
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-3">
              2
            </div>
            <h4 className="font-semibold text-gray-800 mb-2">Upload Resume</h4>
            <p className="text-sm text-gray-600">
              Drag & drop or click to upload PDF, DOCX, or TXT files
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-3">
              3
            </div>
            <h4 className="font-semibold text-gray-800 mb-2">Get Results</h4>
            <p className="text-sm text-gray-600">
              View structured data, download JSON, or export to CSV
            </p>
          </div>
        </div>
      </div>

      {/* API Info */}
      <div className="card bg-gray-50">
        <div className="flex items-start gap-4">
          <div className="bg-blue-600 p-3 rounded-xl">
            <Clock className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">
              Powered by Advanced NLP
            </h3>
            <p className="text-gray-600 mb-3">
              Our system uses fine-tuned transformer models for Named Entity
              Recognition and intelligent pattern matching for section
              segmentation. All processing happens in real-time with
              sub-2-second response times.
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="badge-blue">Transformers</span>
              <span className="badge-green">FastAPI</span>
              <span className="badge-purple">Async Processing</span>
              <span className="badge-orange">spaCy</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
