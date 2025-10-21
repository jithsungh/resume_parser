import { useState } from "react";
import { Brain, Loader2, Search, TrendingUp } from "lucide-react";
import { extractEntities } from "../api";

function NERExtractor() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleExtract = async () => {
    if (!text || text.length < 10) {
      setError("Please enter at least 10 characters");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await extractEntities(text);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to extract entities");
    } finally {
      setLoading(false);
    }
  };

  const entityColors = {
    COMPANY: "blue",
    ROLE: "purple",
    DATE: "green",
    TECHNOLOGY: "orange",
    SKILL: "pink",
  };

  const getEntityStats = () => {
    if (!result?.entities) return {};

    const stats = {};
    result.entities.forEach((entity) => {
      stats[entity.entity_group] = (stats[entity.entity_group] || 0) + 1;
    });
    return stats;
  };

  const stats = getEntityStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
          <Brain className="w-8 h-8 text-purple-600" />
          Named Entity Recognition (NER)
        </h2>
        <p className="text-gray-600">
          Extract structured entities from resume text using deep learning NER
          models. Identifies companies, roles, dates, technologies, and skills
          with confidence scores.
        </p>
      </div>

      {/* Input Area */}
      <div className="card">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Resume Text
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="input-field font-mono text-sm min-h-[300px] resize-y"
          placeholder="Paste resume text here...

Example:
John Doe
Senior Software Engineer at Google Inc.
Experience: 5 years with Python, JavaScript, React
Worked on AWS cloud infrastructure from Jan 2020 to Present
Previously at Microsoft as Backend Developer"
        />
        <div className="flex items-center justify-between mt-3">
          <span className="text-sm text-gray-500">
            {text.length} characters
          </span>
          <button
            onClick={handleExtract}
            disabled={loading || text.length < 10}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 inline mr-2 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <Search className="w-5 h-5 inline mr-2" />
                Extract Entities
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-2 border-red-200">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card bg-gradient-to-br from-purple-50 to-purple-100">
              <div className="text-3xl font-bold text-purple-700 mb-1">
                {result.entity_count}
              </div>
              <div className="text-sm text-purple-600 font-medium">
                Total Entities
              </div>
            </div>
            <div className="card bg-gradient-to-br from-blue-50 to-blue-100">
              <div className="text-3xl font-bold text-blue-700 mb-1">
                {stats.COMPANY || 0}
              </div>
              <div className="text-sm text-blue-600 font-medium">Companies</div>
            </div>
            <div className="card bg-gradient-to-br from-green-50 to-green-100">
              <div className="text-3xl font-bold text-green-700 mb-1">
                {stats.ROLE || 0}
              </div>
              <div className="text-sm text-green-600 font-medium">Roles</div>
            </div>
            <div className="card bg-gradient-to-br from-orange-50 to-orange-100">
              <div className="text-3xl font-bold text-orange-700 mb-1">
                {result.processing_time_seconds}s
              </div>
              <div className="text-sm text-orange-600 font-medium">
                Processing Time
              </div>
            </div>
          </div>

          {/* Entity Types Breakdown */}
          <div className="card">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-green-600" />
              Entity Types
            </h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats).map(([type, count]) => (
                <div
                  key={type}
                  className={`badge-${
                    entityColors[type] || "blue"
                  } text-base px-4 py-2`}
                >
                  {type}: {count}
                </div>
              ))}
            </div>
          </div>

          {/* Entities List */}
          <div className="card">
            <h3 className="text-xl font-bold text-gray-800 mb-4">
              Extracted Entities ({result.entities.length})
            </h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {result.entities.map((entity, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 hover:bg-blue-50 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span
                      className={`badge-${
                        entityColors[entity.entity_group] || "blue"
                      } shrink-0`}
                    >
                      {entity.entity_group}
                    </span>
                    <span className="font-semibold text-gray-800 truncate">
                      {entity.word}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {entity.start !== null && entity.end !== null && (
                      <span className="text-xs text-gray-500">
                        {entity.start}-{entity.end}
                      </span>
                    )}
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full"
                          style={{ width: `${entity.score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-gray-700 w-12 text-right">
                        {(entity.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analyzed Text Preview */}
          <div className="card bg-gray-50">
            <h3 className="text-xl font-bold text-gray-800 mb-3">
              Analyzed Text Preview
            </h3>
            <div className="bg-white p-4 rounded-lg border border-gray-200 font-mono text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-y-auto">
              {result.text_analyzed}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default NERExtractor;
