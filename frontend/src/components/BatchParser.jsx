import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  Loader2,
  CheckCircle,
  XCircle,
  Download,
  RefreshCw,
  Files,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import { batchParseResumes, getBatchStatus } from "../api";

function BatchParser() {
  const [files, setFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [polling, setPolling] = useState(false);

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(acceptedFiles);
    setJobId(null);
    setStatus(null);
    setError(null);
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
    maxFiles: 100,
    multiple: true,
  });

  const handleBatchParse = async () => {
    if (files.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const data = await batchParseResumes(files);
      setJobId(data.job_id);
      setStatus(data);
      setPolling(true);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to start batch processing"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!polling || !jobId) return;

    const interval = setInterval(async () => {
      try {
        const data = await getBatchStatus(jobId);
        setStatus(data);

        if (data.status === "completed" || data.status === "failed") {
          setPolling(false);
        }
      } catch (err) {
        console.error("Failed to fetch status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [polling, jobId]);

  const downloadResults = () => {
    if (!status?.results) return;

    const dataStr = JSON.stringify(status.results, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `batch_results_${jobId}.json`;
    link.click();
  };

  const downloadCSV = () => {
    if (!status?.results) return;

    const headers = [
      "Name",
      "Email",
      "Mobile",
      "Location",
      "Experience (Years)",
      "Primary Role",
      "Filename",
    ];
    const rows = status.results.map((r) => [
      r.name || "",
      r.email || "",
      r.mobile || "",
      r.location || "",
      r.total_experience_years || 0,
      r.primary_role || "",
      r.filename || "",
    ]);

    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${cell}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `batch_results_${jobId}.csv`;
    link.click();
  };

  const reset = () => {
    setFiles([]);
    setJobId(null);
    setStatus(null);
    setError(null);
    setPolling(false);
  };

  const progress = status
    ? (status.processed_files / status.total_files) * 100
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Batch Resume Processing
        </h2>
        <p className="text-gray-600">
          Upload multiple resume files for asynchronous batch processing. Track
          progress in real-time and download results when complete.
        </p>
      </div>

      {/* Upload Area */}
      {!jobId && (
        <div className="card">
          <div
            {...getRootProps()}
            className={`border-3 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
              isDragActive
                ? "border-purple-500 bg-purple-50"
                : "border-gray-300 hover:border-purple-400 hover:bg-gray-50"
            }`}
          >
            <input {...getInputProps()} />
            <Files
              className={`w-16 h-16 mx-auto mb-4 ${
                isDragActive ? "text-purple-500" : "text-gray-400"
              }`}
            />

            {files.length > 0 ? (
              <div className="animate-fade-in">
                <p className="text-lg font-semibold text-gray-800 mb-2">
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </p>
                <p className="text-sm text-gray-500">
                  Total size:{" "}
                  {(files.reduce((acc, f) => acc + f.size, 0) / 1024).toFixed(
                    2
                  )}{" "}
                  KB
                </p>
                <div className="mt-4 max-h-40 overflow-y-auto">
                  <div className="space-y-1">
                    {files.slice(0, 5).map((file, idx) => (
                      <div key={idx} className="text-sm text-gray-600">
                        📄 {file.name}
                      </div>
                    ))}
                    {files.length > 5 && (
                      <div className="text-sm text-gray-500 italic">
                        ... and {files.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <>
                <p className="text-lg font-semibold text-gray-700 mb-2">
                  {isDragActive
                    ? "Drop the files here"
                    : "Drag & drop multiple resume files"}
                </p>
                <p className="text-sm text-gray-500">
                  or click to select files (PDF, DOCX, DOC, TXT) - Max 100 files
                </p>
              </>
            )}
          </div>

          {files.length > 0 && !loading && (
            <button
              onClick={handleBatchParse}
              className="btn-primary w-full mt-4"
            >
              <Upload className="w-5 h-5 inline mr-2" />
              Start Batch Processing ({files.length} files)
            </button>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-2 border-red-200 animate-slide-up">
          <div className="flex items-start gap-3">
            <XCircle className="w-6 h-6 text-red-600 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-800 mb-1">
                Processing Failed
              </h3>
              <p className="text-red-700">{error}</p>
            </div>
            <button onClick={reset} className="btn-secondary">
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Processing Status */}
      {status && (
        <div className="space-y-6 animate-slide-up">
          {/* Status Card */}
          <div
            className={`card ${
              status.status === "completed"
                ? "bg-green-50 border-2 border-green-200"
                : status.status === "failed"
                ? "bg-red-50 border-2 border-red-200"
                : "bg-blue-50 border-2 border-blue-200"
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {status.status === "completed" && (
                  <CheckCircle className="w-8 h-8 text-green-600" />
                )}
                {status.status === "failed" && (
                  <XCircle className="w-8 h-8 text-red-600" />
                )}
                {(status.status === "pending" ||
                  status.status === "processing") && (
                  <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">
                    {status.status === "completed" && "Processing Complete!"}
                    {status.status === "failed" && "Processing Failed"}
                    {status.status === "pending" && "Pending..."}
                    {status.status === "processing" && "Processing Resumes..."}
                  </h3>
                  <p className="text-sm text-gray-600">Job ID: {jobId}</p>
                </div>
              </div>
              {status.status === "completed" && (
                <div className="flex gap-2">
                  <button onClick={downloadResults} className="btn-secondary">
                    <Download className="w-5 h-5 inline mr-2" />
                    JSON
                  </button>
                  <button onClick={downloadCSV} className="btn-primary">
                    <Download className="w-5 h-5 inline mr-2" />
                    CSV
                  </button>
                  <button onClick={reset} className="btn-secondary">
                    <RefreshCw className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Progress</span>
                <span>
                  {status.processed_files} / {status.total_files} files
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white p-3 rounded-lg">
                <div className="text-2xl font-bold text-gray-800">
                  {status.total_files}
                </div>
                <div className="text-xs text-gray-500">Total Files</div>
              </div>
              <div className="bg-white p-3 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {status.processed_files}
                </div>
                <div className="text-xs text-gray-500">Processed</div>
              </div>
              <div className="bg-white p-3 rounded-lg">
                <div className="text-2xl font-bold text-red-600">
                  {status.failed_files}
                </div>
                <div className="text-xs text-gray-500">Failed</div>
              </div>
            </div>
          </div>

          {/* Results Preview */}
          {status.status === "completed" &&
            status.results &&
            status.results.length > 0 && (
              <div className="card">
                <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-6 h-6 text-green-600" />
                  Results Preview
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {status.results.map((result, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 p-4 rounded-lg border border-gray-200 hover:bg-blue-50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h4 className="font-bold text-gray-800">
                            {result.name || "Name not found"}
                          </h4>
                          <p className="text-sm text-gray-600">
                            {result.filename}
                          </p>
                        </div>
                        {result.error ? (
                          <span className="badge bg-red-100 text-red-800 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Error
                          </span>
                        ) : (
                          <span className="badge-green">Parsed</span>
                        )}
                      </div>
                      {!result.error && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-600">
                          <div>📧 {result.email || "N/A"}</div>
                          <div>📱 {result.mobile || "N/A"}</div>
                          <div>📍 {result.location || "N/A"}</div>
                          <div>
                            💼{" "}
                            {result.total_experience_years?.toFixed(1) || "0"}{" "}
                            years
                          </div>
                        </div>
                      )}
                      {result.error && (
                        <p className="text-xs text-red-600 mt-2">
                          {result.error}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default BatchParser;
