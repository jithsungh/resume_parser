import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Contact2,
  Upload,
  Loader2,
  FileText,
  User,
  Mail,
  Phone,
  MapPin,
  Zap,
} from "lucide-react";
import { extractContactInfo } from "../api";

function ContactExtractor() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [inputMode, setInputMode] = useState("file");

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

  const handleExtract = async () => {
    setLoading(true);
    setError(null);

    try {
      let data;
      if (inputMode === "file" && file) {
        data = await extractContactInfo(file);
      } else if (inputMode === "text" && text) {
        data = await extractContactInfo(null, text);
      } else {
        throw new Error("Please provide a file or text");
      }
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to extract contact info"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
          <Contact2 className="w-8 h-8 text-green-600" />
          Quick Contact Extraction
        </h2>
        <p className="text-gray-600">
          Fast extraction of essential contact information: name, email, phone
          number, and location. Perfect for quick candidate screening and
          contact database building.
        </p>
      </div>

      {/* Input Mode Toggle */}
      <div className="card">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setInputMode("file")}
            className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
              inputMode === "file"
                ? "bg-green-600 text-white"
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
                ? "bg-green-600 text-white"
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
                  ? "border-green-500 bg-green-50"
                  : "border-gray-300 hover:border-green-400 hover:bg-gray-50"
              }`}
            >
              <input {...getInputProps()} />
              <Upload
                className={`w-16 h-16 mx-auto mb-4 ${
                  isDragActive ? "text-green-500" : "text-gray-400"
                }`}
              />

              {file ? (
                <div className="animate-fade-in">
                  <div className="flex items-center justify-center gap-3 text-lg font-semibold text-gray-800 mb-2">
                    <FileText className="w-6 h-6 text-green-600" />
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
                onClick={handleExtract}
                className="btn-primary w-full mt-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
              >
                <Zap className="w-5 h-5 inline mr-2" />
                Quick Extract
              </button>
            )}
          </>
        ) : (
          <>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="input-field font-mono text-sm min-h-[200px] resize-y"
              placeholder="Paste resume text here...

Example:
John Smith
john.smith@email.com
+1 (555) 123-4567
San Francisco, CA"
            />
            <div className="flex items-center justify-between mt-3">
              <span className="text-sm text-gray-500">
                {text.length} characters
              </span>
              <button
                onClick={handleExtract}
                disabled={loading || text.length < 20}
                className="btn-primary bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 inline mr-2 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5 inline mr-2" />
                    Quick Extract
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
          <Loader2 className="w-12 h-12 text-green-600 animate-spin mx-auto mb-4" />
          <p className="text-lg font-semibold text-gray-700">
            Extracting contact information...
          </p>
          <p className="text-sm text-gray-500 mt-2">This is super fast!</p>
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
          {/* Success Banner */}
          <div className="card bg-green-50 border-2 border-green-200">
            <div className="flex items-center gap-3">
              <Zap className="w-8 h-8 text-green-600" />
              <div>
                <h3 className="text-lg font-semibold text-green-800">
                  Contact Info Extracted!
                </h3>
                <p className="text-sm text-green-700">
                  Lightning fast extraction complete
                </p>
              </div>
            </div>
          </div>

          {/* Contact Cards */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Name Card */}
            <div className="card hover:scale-105 transition-transform duration-300 bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-200">
              <div className="flex items-start gap-4">
                <div className="bg-blue-600 p-4 rounded-xl">
                  <User className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-blue-600 font-semibold mb-1">
                    Full Name
                  </div>
                  <div className="text-2xl font-bold text-gray-800 truncate">
                    {result.name || "Not found"}
                  </div>
                  {!result.name && (
                    <p className="text-sm text-gray-500 mt-1">
                      Unable to detect name in document
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Email Card */}
            <div className="card hover:scale-105 transition-transform duration-300 bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-200">
              <div className="flex items-start gap-4">
                <div className="bg-purple-600 p-4 rounded-xl">
                  <Mail className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-purple-600 font-semibold mb-1">
                    Email Address
                  </div>
                  <div className="text-xl font-bold text-gray-800 truncate">
                    {result.email || "Not found"}
                  </div>
                  {result.email && (
                    <a
                      href={`mailto:${result.email}`}
                      className="text-sm text-purple-600 hover:underline mt-1 inline-block"
                    >
                      Send email →
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Phone Card */}
            <div className="card hover:scale-105 transition-transform duration-300 bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-200">
              <div className="flex items-start gap-4">
                <div className="bg-green-600 p-4 rounded-xl">
                  <Phone className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-green-600 font-semibold mb-1">
                    Phone Number
                  </div>
                  <div className="text-xl font-bold text-gray-800 truncate">
                    {result.mobile || "Not found"}
                  </div>
                  {result.mobile && (
                    <a
                      href={`tel:${result.mobile}`}
                      className="text-sm text-green-600 hover:underline mt-1 inline-block"
                    >
                      Call now →
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Location Card */}
            <div className="card hover:scale-105 transition-transform duration-300 bg-gradient-to-br from-orange-50 to-orange-100 border-2 border-orange-200">
              <div className="flex items-start gap-4">
                <div className="bg-orange-600 p-4 rounded-xl">
                  <MapPin className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-orange-600 font-semibold mb-1">
                    Location
                  </div>
                  <div className="text-xl font-bold text-gray-800 truncate">
                    {result.location || "Not found"}
                  </div>
                  {result.location && (
                    <a
                      href={`https://www.google.com/maps/search/${encodeURIComponent(
                        result.location
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-orange-600 hover:underline mt-1 inline-block"
                    >
                      View on map →
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Summary Card */}
          <div className="card bg-gradient-to-r from-gray-50 to-blue-50">
            <h3 className="text-xl font-bold text-gray-800 mb-4">
              Extraction Summary
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div
                  className={`text-3xl font-bold ${
                    result.name ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {result.name ? "✓" : "✗"}
                </div>
                <div className="text-sm text-gray-600 mt-1">Name</div>
              </div>
              <div className="text-center">
                <div
                  className={`text-3xl font-bold ${
                    result.email ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {result.email ? "✓" : "✗"}
                </div>
                <div className="text-sm text-gray-600 mt-1">Email</div>
              </div>
              <div className="text-center">
                <div
                  className={`text-3xl font-bold ${
                    result.mobile ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {result.mobile ? "✓" : "✗"}
                </div>
                <div className="text-sm text-gray-600 mt-1">Phone</div>
              </div>
              <div className="text-center">
                <div
                  className={`text-3xl font-bold ${
                    result.location ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {result.location ? "✓" : "✗"}
                </div>
                <div className="text-sm text-gray-600 mt-1">Location</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ContactExtractor;
