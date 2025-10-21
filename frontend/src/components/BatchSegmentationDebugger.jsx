import React, { useState, useEffect } from "react";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Download,
  RefreshCw,
  BarChart3,
  Layers,
} from "lucide-react";
import {
  batchSegmentSections,
  getBatchSegmentationStatus,
  downloadBatchSegmentationResults,
} from "../api";

const BatchSegmentationDebugger = () => {
  const [files, setFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [includeFullContent, setIncludeFullContent] = useState(true);
  const [includeTextPreview, setIncludeTextPreview] = useState(true);
  const [error, setError] = useState(null);

  // Poll for status updates
  useEffect(() => {
    let interval;
    if (jobId && polling) {
      interval = setInterval(async () => {
        try {
          const statusData = await getBatchSegmentationStatus(jobId);
          setStatus(statusData);

          if (
            statusData.status === "completed" ||
            statusData.status === "failed"
          ) {
            setPolling(false);
          }
        } catch (err) {
          console.error("Error polling status:", err);
          setPolling(false);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, polling]);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setError(null);
  };

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError("Please select at least one file");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await batchSegmentSections(
        files,
        includeFullContent,
        includeTextPreview
      );

      setJobId(result.job_id);
      setStatus(result);
      setPolling(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Error processing files");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format) => {
    try {
      await downloadBatchSegmentationResults(jobId, format);
    } catch (err) {
      setError(`Error downloading ${format.toUpperCase()}: ${err.message}`);
    }
  };

  const getStatusColor = (statusValue) => {
    switch (statusValue) {
      case "completed":
        return "text-green-600";
      case "processing":
        return "text-blue-600";
      case "failed":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getStatusIcon = (statusValue) => {
    switch (statusValue) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case "processing":
        return <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Layers className="w-8 h-8 text-purple-600" />
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              Batch Segmentation Debugger
            </h2>
            <p className="text-gray-600">
              Debug section segmentation issues by analyzing multiple resumes
            </p>
          </div>
        </div>

        {/* File Upload Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload Resumes
          </label>
          <div className="flex items-center gap-4">
            <label className="flex-1 flex items-center justify-center px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-purple-500 transition-colors">
              <div className="text-center">
                <Upload className="mx-auto w-12 h-12 text-gray-400 mb-2" />
                <span className="text-sm text-gray-600">
                  {files.length > 0
                    ? `${files.length} file(s) selected`
                    : "Click to select resume files (PDF, DOCX, TXT)"}
                </span>
              </div>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          </div>

          {files.length > 0 && (
            <div className="mt-3 text-sm text-gray-600">
              <strong>Selected files:</strong>{" "}
              {files
                .map((f) => f.name)
                .join(", ")
                .substring(0, 100)}
              {files.map((f) => f.name).join(", ").length > 100 && "..."}
            </div>
          )}
        </div>

        {/* Options */}
        <div className="mb-6 space-y-3">
          <h3 className="text-sm font-medium text-gray-700">Options</h3>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeFullContent}
                onChange={(e) => setIncludeFullContent(e.target.checked)}
                className="rounded text-purple-600"
              />
              <span className="text-sm text-gray-700">
                Include full section content
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeTextPreview}
                onChange={(e) => setIncludeTextPreview(e.target.checked)}
                className="rounded text-purple-600"
              />
              <span className="text-sm text-gray-700">
                Include text preview
              </span>
            </label>
          </div>
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={loading || files.length === 0}
          className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
            loading || files.length === 0
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-purple-600 text-white hover:bg-purple-700"
          }`}
        >
          {loading ? "Starting Process..." : "Start Batch Segmentation"}
        </button>

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-800">
              <XCircle className="w-5 h-5" />
              <span className="font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* Status Display */}
        {status && (
          <div className="mt-6 space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {getStatusIcon(status.status)}
                  <span
                    className={`font-medium ${getStatusColor(status.status)}`}
                  >
                    {status.status.toUpperCase()}
                  </span>
                </div>
                <span className="text-sm text-gray-600">
                  Job ID: {jobId?.substring(0, 8)}...
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>Progress</span>
                  <span>
                    {status.processed_files} / {status.total_files}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${
                        (status.processed_files / status.total_files) * 100
                      }%`,
                    }}
                  />
                </div>
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded p-3">
                  <div className="text-2xl font-bold text-gray-800">
                    {status.total_files}
                  </div>
                  <div className="text-xs text-gray-600">Total Files</div>
                </div>
                <div className="bg-white rounded p-3">
                  <div className="text-2xl font-bold text-green-600">
                    {status.processed_files -
                      status.failed_files -
                      status.empty_files}
                  </div>
                  <div className="text-xs text-gray-600">Successful</div>
                </div>
                <div className="bg-white rounded p-3">
                  <div className="text-2xl font-bold text-red-600">
                    {status.failed_files}
                  </div>
                  <div className="text-xs text-gray-600">Errors</div>
                </div>
                <div className="bg-white rounded p-3">
                  <div className="text-2xl font-bold text-yellow-600">
                    {status.empty_files}
                  </div>
                  <div className="text-xs text-gray-600">Empty</div>
                </div>
              </div>

              {/* Statistics Summary */}
              {status.status === "completed" && status.statistics && (
                <div className="mt-4 bg-white rounded-lg p-4">
                  <h4 className="font-medium text-gray-800 mb-3 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Segmentation Analysis
                  </h4>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">
                        Files with no sections:
                      </span>
                      <span className="font-medium text-gray-800">
                        {status.statistics.no_sections_detected}
                      </span>
                    </div>

                    {status.statistics.most_common_sections &&
                      status.statistics.most_common_sections.length > 0 && (
                        <div className="mt-4">
                          <div className="text-gray-700 font-medium mb-2">
                            Most Common Sections:
                          </div>
                          <div className="space-y-1">
                            {status.statistics.most_common_sections
                              .slice(0, 5)
                              .map(([section, count]) => (
                                <div
                                  key={section}
                                  className="flex justify-between items-center"
                                >
                                  <span className="text-gray-600">
                                    {section}
                                  </span>
                                  <div className="flex items-center gap-2">
                                    <div className="w-24 bg-gray-200 rounded-full h-2">
                                      <div
                                        className="bg-purple-500 h-2 rounded-full"
                                        style={{
                                          width: `${
                                            (count / status.total_files) * 100
                                          }%`,
                                        }}
                                      />
                                    </div>
                                    <span className="text-gray-800 font-medium w-12 text-right">
                                      {count}
                                    </span>
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                  </div>
                </div>
              )}

              {/* Download Buttons */}
              {status.status === "completed" && (
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => handleDownload("json")}
                    className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download JSON
                  </button>
                  <button
                    onClick={() => handleDownload("csv")}
                    className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download CSV
                  </button>
                </div>
              )}

              {/* Error Message */}
              {status.error_message && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                  <strong>Error:</strong> {status.error_message}
                </div>
              )}
            </div>

            {/* Results Preview */}
            {status.results && status.results.length > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-3">
                  Results Preview (first 5 files)
                </h4>
                <div className="space-y-3">
                  {status.results.slice(0, 5).map((result, idx) => (
                    <div
                      key={idx}
                      className="bg-white rounded-lg p-3 border border-gray-200"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-800">
                            {result.filename}
                          </span>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            result.status === "success"
                              ? "bg-green-100 text-green-700"
                              : result.status === "empty"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {result.status}
                        </span>
                      </div>

                      {result.status === "success" && (
                        <div className="text-xs text-gray-600 space-y-1">
                          <div>
                            Text Length: {result.text_length?.toLocaleString()}{" "}
                            chars
                          </div>
                          <div>Sections Found: {result.section_count}</div>
                          {result.sections_found &&
                            result.sections_found.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {result.sections_found.map((section) => (
                                  <span
                                    key={section}
                                    className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs"
                                  >
                                    {section}
                                  </span>
                                ))}
                              </div>
                            )}
                        </div>
                      )}

                      {result.error && (
                        <div className="text-xs text-red-600 mt-1">
                          Error: {result.error}
                        </div>
                      )}
                    </div>
                  ))}

                  {status.results.length > 5 && (
                    <div className="text-sm text-gray-600 text-center">
                      ... and {status.results.length - 5} more. Download results
                      to view all.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">
            How to use this debugger:
          </h4>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Upload multiple resume files (PDF, DOCX, TXT)</li>
            <li>Process them to see how sections are detected</li>
            <li>Download JSON for detailed section content</li>
            <li>Download CSV for a quick summary</li>
            <li>Check which files have no sections detected</li>
            <li>Compare segmentation results with NER parsing results</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default BatchSegmentationDebugger;
