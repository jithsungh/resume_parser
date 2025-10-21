import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { FileSearch, Upload, Loader2, FileText, List } from "lucide-react";
import { segmentSections } from "../api";

function SectionSegmenter() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [inputMode, setInputMode] = useState("file"); // 'file' or 'text'

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

  const handleSegment = async () => {
    setLoading(true);
    setError(null);

    try {
      let data;
      if (inputMode === "file" && file) {
        data = await segmentSections(file);
      } else if (inputMode === "text" && text) {
        data = await segmentSections(null, text);
      } else {
        throw new Error("Please provide a file or text");
      }
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to segment sections"
      );
    } finally {
      setLoading(false);
    }
  };

  const sectionColors = [
    "from-blue-500 to-blue-600",
    "from-purple-500 to-purple-600",
    "from-green-500 to-green-600",
    "from-orange-500 to-orange-600",
    "from-pink-500 to-pink-600",
    "from-indigo-500 to-indigo-600",
    "from-teal-500 to-teal-600",
    "from-red-500 to-red-600",
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
          <FileSearch className="w-8 h-8 text-blue-600" />
          Section Segmentation
        </h2>
        <p className="text-gray-600">
          Automatically identify and extract resume sections like Personal Info,
          Experience, Education, Skills, and more using intelligent pattern
          matching.
        </p>
      </div>

      {/* Input Mode Toggle */}
      <div className="card">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setInputMode("file")}
            className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
              inputMode === "file"
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            <Upload className="w-5 h-5 inline mr-2" />
            Upload File
          </button>
          <button
            onClick={() => setInputMode("text")}
            className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
              inputMode === "text"
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            <FileText className="w-5 h-5 inline mr-2" />
            Paste Text
          </button>
        </div>

        {inputMode === "file" ? (
          <>
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
              <button
                onClick={handleSegment}
                className="btn-primary w-full mt-4"
              >
                <FileSearch className="w-5 h-5 inline mr-2" />
                Segment Sections
              </button>
            )}
          </>
        ) : (
          <>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="input-field font-mono text-sm min-h-[300px] resize-y"
              placeholder="Paste resume text here..."
            />
            <div className="flex items-center justify-between mt-3">
              <span className="text-sm text-gray-500">
                {text.length} characters
              </span>
              <button
                onClick={handleSegment}
                disabled={loading || text.length < 50}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 inline mr-2 animate-spin" />
                    Segmenting...
                  </>
                ) : (
                  <>
                    <FileSearch className="w-5 h-5 inline mr-2" />
                    Segment Sections
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="card text-center animate-pulse">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-lg font-semibold text-gray-700">
            Segmenting sections...
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-2 border-red-200">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card bg-gradient-to-br from-blue-50 to-blue-100">
              <div className="text-3xl font-bold text-blue-700 mb-1">
                {result.total_sections}
              </div>
              <div className="text-sm text-blue-600 font-medium">
                Sections Found
              </div>
            </div>
            <div className="card bg-gradient-to-br from-green-50 to-green-100">
              <div className="text-3xl font-bold text-green-700 mb-1">
                {result.processing_time_seconds}s
              </div>
              <div className="text-sm text-green-600 font-medium">
                Processing Time
              </div>
            </div>
            <div className="card bg-gradient-to-br from-purple-50 to-purple-100">
              <div className="text-xl font-bold text-purple-700 mb-1 truncate">
                {result.filename || "N/A"}
              </div>
              <div className="text-sm text-purple-600 font-medium">
                Filename
              </div>
            </div>
            <div className="card bg-gradient-to-br from-orange-50 to-orange-100">
              <div className="text-3xl font-bold text-orange-700 mb-1">✓</div>
              <div className="text-sm text-orange-600 font-medium">
                Completed
              </div>
            </div>
          </div>

          {/* Sections */}
          <div className="card">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <List className="w-6 h-6 text-blue-600" />
              Identified Sections
            </h3>
            <div className="space-y-4">
              {result.sections.map((section, index) => (
                <div
                  key={index}
                  className="border-2 border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow"
                >
                  <div
                    className={`bg-gradient-to-r ${
                      sectionColors[index % sectionColors.length]
                    } p-4`}
                  >
                    <h4 className="text-xl font-bold text-white flex items-center justify-between">
                      <span>{section.section_name}</span>
                      {section.confidence && (
                        <span className="text-sm bg-white/20 px-3 py-1 rounded-full">
                          {(section.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </h4>
                  </div>
                  <div className="p-4 bg-white">
                    <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {section.content}
                    </div>
                    {(section.start_line !== null ||
                      section.end_line !== null) && (
                      <div className="mt-2 text-xs text-gray-500">
                        Lines: {section.start_line || "N/A"} -{" "}
                        {section.end_line || "N/A"}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SectionSegmenter;
