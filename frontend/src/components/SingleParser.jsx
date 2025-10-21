import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle,
  XCircle,
  Download,
  User,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  Clock,
  AlertCircle,
} from "lucide-react";
import { parseSingleResume } from "../api";

function SingleParser() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "application/msword": [".doc"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
  });

  const handleParse = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const data = await parseSingleResume(file);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to parse resume");
    } finally {
      setLoading(false);
    }
  };

  const downloadJSON = () => {
    const dataStr = JSON.stringify(result, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.filename || "resume"}_parsed.json`;
    link.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Single Resume Parser
        </h2>
        <p className="text-gray-600">
          Upload a single resume file to extract structured information
          including contact details, work experience, skills, and more.
        </p>
      </div>

      {/* Upload Area */}
      <div className="card">
        <div
          {...getRootProps()}
          className={`border-3 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragActive
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
          }`}
        >
          <input {...getInputProps()} />
          <Upload
            className={`w-16 h-16 mx-auto mb-4 ${
              isDragActive ? "text-blue-500" : "text-gray-400"
            }`}
          />

          {file ? (
            <div className="animate-fade-in">
              <div className="flex items-center justify-center gap-3 text-lg font-semibold text-gray-800 mb-2">
                <FileText className="w-6 h-6 text-blue-600" />
                {file.name}
              </div>
              <p className="text-sm text-gray-500">
                {(file.size / 1024).toFixed(2)} KB
              </p>
            </div>
          ) : (
            <>
              <p className="text-lg font-semibold text-gray-700 mb-2">
                {isDragActive
                  ? "Drop the file here"
                  : "Drag & drop a resume file"}
              </p>
              <p className="text-sm text-gray-500">
                or click to select a file (PDF, DOCX, DOC, TXT)
              </p>
            </>
          )}
        </div>

        {file && !loading && !result && (
          <button onClick={handleParse} className="btn-primary w-full mt-4">
            <FileText className="w-5 h-5 inline mr-2" />
            Parse Resume
          </button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="card text-center animate-pulse">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-lg font-semibold text-gray-700">
            Parsing resume...
          </p>
          <p className="text-sm text-gray-500 mt-2">
            This may take a few seconds
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-2 border-red-200 animate-slide-up">
          <div className="flex items-start gap-3">
            <XCircle className="w-6 h-6 text-red-600 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-semibold text-red-800 mb-1">
                Parsing Failed
              </h3>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Success Banner */}
          <div className="card bg-green-50 border-2 border-green-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-8 h-8 text-green-600" />
                <div>
                  <h3 className="text-lg font-semibold text-green-800">
                    Parsing Successful!
                  </h3>
                  <p className="text-sm text-green-700">
                    Processed in {result.processing_time_seconds}s
                  </p>
                </div>
              </div>
              <button onClick={downloadJSON} className="btn-secondary">
                <Download className="w-5 h-5 inline mr-2" />
                Download JSON
              </button>
            </div>
          </div>

          {/* Contact Information */}
          <div className="card">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <User className="w-6 h-6 text-blue-600" />
              Contact Information
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <InfoItem icon={User} label="Name" value={result.name} />
              <InfoItem icon={Mail} label="Email" value={result.email} />
              <InfoItem icon={Phone} label="Mobile" value={result.mobile} />
              <InfoItem
                icon={MapPin}
                label="Location"
                value={result.location}
              />
            </div>
          </div>

          {/* Professional Summary */}
          <div className="card">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <Briefcase className="w-6 h-6 text-purple-600" />
              Professional Summary
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
                <div className="text-3xl font-bold text-purple-700 mb-1">
                  {result.total_experience_years.toFixed(1)} years
                </div>
                <div className="text-sm text-purple-600 font-medium">
                  Total Experience
                </div>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
                <div className="text-xl font-bold text-blue-700 mb-1">
                  {result.primary_role || "Not specified"}
                </div>
                <div className="text-sm text-blue-600 font-medium">
                  Primary Role
                </div>
              </div>
            </div>
          </div>

          {/* Work Experience */}
          {result.experiences && result.experiences.length > 0 && (
            <div className="card">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Clock className="w-6 h-6 text-orange-600" />
                Work Experience ({result.experiences.length})
              </h3>
              <div className="space-y-4">
                {result.experiences.map((exp, index) => (
                  <ExperienceCard key={index} experience={exp} />
                ))}
              </div>
            </div>
          )}

          {result.experiences && result.experiences.length === 0 && (
            <div className="card bg-yellow-50 border-2 border-yellow-200">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-6 h-6 text-yellow-600" />
                <p className="text-yellow-800">
                  No work experience entries found in the resume.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <Icon className="w-5 h-5 text-gray-500 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-xs text-gray-500 font-medium mb-1">{label}</div>
        <div className="text-sm text-gray-800 font-semibold truncate">
          {value || "Not found"}
        </div>
      </div>
    </div>
  );
}

function ExperienceCard({ experience }) {
  return (
    <div className="bg-gradient-to-r from-gray-50 to-blue-50 p-4 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="text-lg font-bold text-gray-800">
            {experience.role || "Role not specified"}
          </h4>
          <p className="text-blue-600 font-semibold">
            {experience.company_name || "Company not specified"}
          </p>
        </div>
        {experience.duration_months && (
          <div className="bg-purple-100 px-3 py-1 rounded-full text-purple-700 font-semibold text-sm">
            {experience.duration_months} months
          </div>
        )}
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
        <span>📅 {experience.from_date || "N/A"}</span>
        <span>→</span>
        <span>{experience.to_date || "Present"}</span>
      </div>

      {experience.skills && experience.skills.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 font-medium mb-2">
            Skills & Technologies:
          </div>
          <div className="flex flex-wrap gap-2">
            {experience.skills.map((skill, idx) => (
              <span key={idx} className="badge-blue text-xs">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SingleParser;
