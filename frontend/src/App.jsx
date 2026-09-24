
import { useState } from "react";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [allergies, setAllergies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const availableAllergies = [
    "WHEAT",
    "SOY",
    "MILK",
    "EGG",
    "PEANUT",
    "TREE_NUTS",
  ];

  const allergyLabels = {
    WHEAT: "Wheat",
    SOY: "Soy",
    MILK: "Milk",
    EGG: "Egg",
    PEANUT: "Peanut",
    TREE_NUTS: "Tree Nuts",
  };

  const toggleAllergy = (allergen) => {
    setAllergies((current) =>
      current.includes(allergen)
        ? current.filter((item) => item !== allergen)
        : [...current, allergen]
    );
  };

  const selectedAllergenResults =
    result?.allergens?.filter((item) =>
      allergies.includes(String(item.allergen).toUpperCase())
    ) || [];

  const getStatusClass = (status) => {
    switch (status) {
      case "DETECTED":
        return "status-detected";
      case "POTENTIAL":
        return "status-potential";
      case "NOT_DETECTED":
        return "status-not-detected";
      case "INSUFFICIENT_EVIDENCE":
        return "status-insufficient";
      default:
        return "status-default";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "DETECTED":
        return "🔴";
      case "POTENTIAL":
        return "🟠";
      case "NOT_DETECTED":
        return "🟢";
      case "INSUFFICIENT_EVIDENCE":
        return "⚪";
      default:
        return "⚪";
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case "DETECTED":
        return "ALLERGEN FOUND";
      case "POTENTIAL":
        return "POSSIBLE MATCH";
      case "NOT_DETECTED":
        return "NO KNOWN MATCH";
      case "INSUFFICIENT_EVIDENCE":
        return "CAN'T DETERMINE";
      default:
        return status;
    }
  };

  const getOverallResult = () => {
    if (!result?.allergens?.length) {
      return {
        className: "overall-insufficient",
        icon: "⚪",
        title: "Can't determine",
        message:
          "We could not determine allergen information from the available evidence.",
      };
    }

    if (selectedAllergenResults.some((item) => item.status === "DETECTED")) {
      return {
        className: "overall-danger",
        icon: "🔴",
        title: "Allergen found",
        message:
          "One or more allergens you selected were detected in the available ingredient information.",
      };
    }

    if (selectedAllergenResults.some((item) => item.status === "POTENTIAL")) {
      return {
        className: "overall-warning",
        icon: "🟠",
        title: "Possible allergen",
        message:
          "There is uncertain evidence that may be relevant to one or more of your selected allergies.",
      };
    }

    if (
      selectedAllergenResults.every(
        (item) => item.status === "NOT_DETECTED"
      )
    ) {
      return {
        className: "overall-safe",
        icon: "🟢",
        title: "No known allergen found",
        message:
          "No selected allergen was found in the usable ingredient information. This does not guarantee the product is free of it.",
      };
    }

    return {
      className: "overall-insufficient",
      icon: "⚪",
      title: "Can't determine",
      message:
        "There was not enough reliable ingredient information to determine the result.",
    };
  };

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    if (!selectedFile) {
      setError("Please select a food image first.");
      return;
    }

    if (allergies.length === 0) {
      setError("Please select at least one allergy.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const allergyString = allergies.join(",");

      const response = await fetch(
        `http://127.0.0.1:8000/api/analyze?allergies=${encodeURIComponent(
          allergyString
        )}&severity=HIGH`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }

      setResult(data);
    } catch (err) {
      console.error(err);
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const overallResult = getOverallResult();

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div className="header-inner">
          <div>
            <h1>AllergyGuard</h1>
            <p>Personalized Food Allergen Screening</p>
          </div>
        </div>
      </header>

      <main className="container">
        {/* INTRO */}
        <section className="intro">
          <h2>Can I eat this product?</h2>
          <p>
            Upload a food product image and tell AllergyGuard which allergens
            you need to avoid. The system checks the visible ingredient
            information and provides an evidence-based screening result.
          </p>
        </section>

        {/* IMAGE UPLOAD */}
        <section className="card">
          <div className="section-heading">
            <span className="step-number">1</span>
            <div>
              <h2>Upload Product Image</h2>
              <p className="description">
                For best results, use a clear photo where the ingredient
                information is visible.
              </p>
            </div>
          </div>

          <div className="upload-box">
            <div className="upload-icon">📷</div>

            <p className="upload-title">Choose a food product image</p>

            <p className="upload-description">
              JPG, PNG, WEBP and other image formats are supported.
            </p>

            <input
              id="food-image"
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files[0];
                setSelectedFile(file || null);
                setResult(null);
                setError("");
              }}
            />

            <label htmlFor="food-image" className="choose-file-button">
              Choose Image
            </label>

            {selectedFile && (
              <div className="selected-file">
                <span>📄</span>
                <span>{selectedFile.name}</span>
              </div>
            )}
          </div>
        </section>

        {/* ALLERGIES */}
        <section className="card">
          <div className="section-heading">
            <span className="step-number">2</span>
            <div>
              <h2>My Allergies</h2>
              <p className="description">
                Select the allergens you want AllergyGuard to check.
              </p>
            </div>
          </div>

          <div className="allergy-grid">
            {availableAllergies.map((allergen) => (
              <label
                key={allergen}
                className={`allergy-item ${
                  allergies.includes(allergen) ? "selected" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={allergies.includes(allergen)}
                  onChange={() => toggleAllergy(allergen)}
                />

                <span className="custom-checkbox">
                  {allergies.includes(allergen) ? "✓" : ""}
                </span>

                <span className="allergy-name">
                  {allergyLabels[allergen]}
                </span>
              </label>
            ))}
          </div>

          {allergies.length > 0 && (
            <div className="selected-allergies">
              Checking for:
              <strong>
                {" "}
                {allergies.map((item) => allergyLabels[item]).join(", ")}
              </strong>
            </div>
          )}
        </section>

        {/* ERROR */}
        {error && <div className="error-box">⚠️ {error}</div>}

        {/* ANALYZE */}
        <button
          className="analyze-button"
          onClick={handleAnalyze}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Analyzing image...
            </>
          ) : (
            <>🔍 Analyze Product</>
          )}
        </button>

        {/* RESULTS */}
        {result && (
          <section className="results-section">
            <div className="results-title">
              <h2>Analysis Result</h2>
              <p>
                Based on the ingredient information detected in{" "}
                <strong>{result.product?.filename}</strong>
              </p>
            </div>

            {/* MAIN ANSWER */}
            <div className={`overall-result ${overallResult.className}`}>
              <div className="overall-icon">{overallResult.icon}</div>

              <div className="overall-content">
                <span className="overall-label">SCREENING RESULT</span>
                <h2>{overallResult.title}</h2>
                <p>{overallResult.message}</p>
              </div>
            </div>

            {/* OCR INFO */}
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">OCR CONFIDENCE</span>
                <strong>
                  {(result.ocr.confidence * 100).toFixed(1)}%
                </strong>
              </div>

              <div className="stat-card">
                <span className="stat-label">TEXT REGIONS</span>
                <strong>{result.ocr.regions}</strong>
              </div>

              <div className="stat-card">
                <span className="stat-label">ALLERGIES CHECKED</span>
                <strong>{selectedAllergenResults.length}</strong>
              </div>
            </div>

            {/* ALLERGEN ANALYSIS */}
            <div className="card">
              <div className="result-card-heading">
                <div>
                  <h3>Allergen Analysis</h3>
                  <p className="description">
                    Results for the allergens you selected.
                  </p>
                </div>
              </div>

              <div className="allergen-results">
                {selectedAllergenResults.map((item) => (
                  <div
                    className={`allergen-result ${getStatusClass(
                      item.status
                    )}`}
                    key={item.allergen}
                  >
                    <div className="allergen-header">
                      <div className="allergen-title">
                        <span className="status-icon">
                          {getStatusIcon(item.status)}
                        </span>

                        <strong>
                          {allergyLabels[item.allergen] ||
                            item.allergen
                              .replaceAll("_", " ")
                              .replace(/\b\w/g, (letter) =>
                                letter.toUpperCase()
                              )}
                        </strong>
                      </div>

                      <span className="status-badge">
                        {getStatusLabel(item.status)}
                      </span>
                    </div>

                    <div className="confidence-row">
                      <span>Evidence confidence</span>
                      <strong>
                        {(item.confidence * 100).toFixed(1)}%
                      </strong>
                    </div>

                    <p className="explanation">
                      {item.explanation}
                    </p>

                    {/* EVIDENCE */}
                    {item.evidence && item.evidence.length > 0 && (
                      <div className="evidence">
                        <div className="evidence-title">
                          ✓ Supporting Evidence
                        </div>

                        {item.evidence.map((evidence, index) => (
                          <div className="evidence-item" key={index}>
                            <div className="evidence-row">
                              <span>Type</span>
                              <strong>
                                {evidence.type.replaceAll("_", " ")}
                              </strong>
                            </div>

                            <div className="evidence-row">
                              <span>Ingredient</span>
                              <strong>{evidence.ingredient}</strong>
                            </div>

                            <div className="evidence-row">
                              <span>Source</span>
                              <strong>{evidence.text}</strong>
                            </div>

                            <div className="evidence-row">
                              <span>Confidence</span>
                              <strong>
                                {(evidence.confidence * 100).toFixed(1)}%
                              </strong>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* RISK DETAILS */}
            {result.risk && (
              <div className="card">
                <div className="result-card-heading">
                  <div>
                    <h3>Personalized Assessment</h3>
                    <p className="description">
                      Based on the allergies you selected and the available
                      evidence.
                    </p>
                  </div>

                  <span
                    className={`risk-badge risk-${result.risk.level.toLowerCase()}`}
                  >
                    {result.risk.level}
                  </span>
                </div>

                <div className="risk-message">
                  {result.risk.message}
                </div>

                {result.risk.warnings?.length > 0 && (
                  <div className="warning-list">
                    {result.risk.warnings.map((warning, index) => (
                      <div key={index}>⚠️ {warning}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* INGREDIENTS */}
            <div className="card">
              <div className="result-card-heading">
                <div>
                  <h3>Extracted Ingredients</h3>
                  <p className="description">
                    Ingredient terms identified from the uploaded image.
                  </p>
                </div>
              </div>

              {result.ingredients?.length > 0 ? (
                <div className="ingredients-list">
                  {result.ingredients.map((ingredient, index) => (
                    <span className="ingredient-tag" key={index}>
                      {ingredient}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="no-data">
                  No usable ingredient information was extracted.
                </p>
              )}
            </div>

            {/* DISCLAIMER */}
            <div className="disclaimer">
              <strong>Important:</strong> This result is based only on the
              ingredient information visible in the uploaded image. It is a
              screening aid, not a medical or safety guarantee. When in doubt,
              check the physical product label or contact the manufacturer.
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;

