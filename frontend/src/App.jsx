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

  const toggleAllergy = (allergen) => {
    setAllergies((current) =>
      current.includes(allergen)
        ? current.filter((item) => item !== allergen)
        : [...current, allergen]
    );
  };

  // ==========================================
  // ANALYZE PRODUCT
  // ==========================================

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    // Check image
    if (!selectedFile) {
      setError("Please select a food image first.");
      return;
    }

    // Check allergies
    if (allergies.length === 0) {
      setError("Please select at least one allergy.");
      return;
    }

    setLoading(true);

    try {
      // Create form data
      const formData = new FormData();

      formData.append("file", selectedFile);

      // Convert selected allergies to comma-separated string
      const allergyString = allergies.join(",");

      // Send request to FastAPI
      const response = await fetch(
        `http://127.0.0.1:8000/api/analyze?allergies=${encodeURIComponent(
          allergyString
        )}&severity=HIGH`,
        {
          method: "POST",
          body: formData,
        }
      );

      // Convert response to JSON
      const data = await response.json();

      // Handle backend errors
      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }

      // Store result
      setResult(data);
    } catch (err) {
      console.error(err);
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">

      {/* ==========================================
          HEADER
      ========================================== */}

      <header className="header">
        <div>
          <h1>AllergyGuard</h1>
          <p>Packaged Food Allergen Detection</p>
        </div>
      </header>


      <main className="container">

        {/* ==========================================
            IMAGE UPLOAD
        ========================================== */}

        <section className="card">

          <h2>Analyze a Food Product</h2>

          <p className="description">
            Upload a clear image of the ingredient label to detect
            potential allergens.
          </p>

          <div className="upload-box">

            <input
              type="file"
              accept="image/*"
              onChange={(event) => {
                setSelectedFile(event.target.files[0]);
                setResult(null);
                setError("");
              }}
            />

            {selectedFile && (
              <p className="file-name">
                Selected: {selectedFile.name}
              </p>
            )}

          </div>

        </section>


        {/* ==========================================
            ALLERGIES
        ========================================== */}

        <section className="card">

          <h2>My Allergies</h2>

          <p className="description">
            Select the allergens you want AllergyGuard to check.
          </p>

          <div className="allergy-grid">

            {availableAllergies.map((allergen) => (

              <label
                key={allergen}
                className="allergy-item"
              >

                <input
                  type="checkbox"
                  checked={allergies.includes(allergen)}
                  onChange={() => toggleAllergy(allergen)}
                />

                <span>{allergen}</span>

              </label>

            ))}

          </div>

        </section>


        {/* ==========================================
            ERROR MESSAGE
        ========================================== */}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}


        {/* ==========================================
            ANALYZE BUTTON
        ========================================== */}

        <button
          className="analyze-button"
          onClick={handleAnalyze}
          disabled={loading}
        >

          {loading ? "Analyzing..." : "Analyze Product"}

        </button>


        {/* ==========================================
            RESULTS
        ========================================== */}

        {result && (

          <section className="results-section">

            <h2>Analysis Results</h2>


            {/* OCR */}

            <div className="card">

              <h3>OCR Information</h3>

              <p>
                <strong>OCR Confidence:</strong>{" "}
                {(result.ocr.confidence * 100).toFixed(1)}%
              </p>

              <p>
                <strong>Text Regions:</strong>{" "}
                {result.ocr.regions}
              </p>

            </div>


            {/* RISK */}

            {result.risk && (

              <div className="card">

                <h3>Personalized Risk</h3>

                <div className="risk-box">

                  <strong>
                    {result.risk.level}
                  </strong>

                  <p>
                    {result.risk.message}
                  </p>

                </div>

              </div>

            )}


            {/* ALLERGEN RESULTS */}

            <div className="card">

              <h3>Allergen Analysis</h3>

              {result.allergens.map((item) => (

                <div
                  className="allergen-result"
                  key={item.allergen}
                >

                  <div className="allergen-header">

                    <strong>
                      {item.allergen}
                    </strong>

                    <span>
                      {item.status}
                    </span>

                  </div>

                  <p>
                    Confidence:{" "}
                    {(item.confidence * 100).toFixed(1)}%
                  </p>

                  <p>
                    {item.explanation}
                  </p>


                  {/* Evidence */}

                  {item.evidence &&
                    item.evidence.length > 0 && (

                      <div className="evidence">

                        <strong>
                          Evidence:
                        </strong>

                        {item.evidence.map(
                          (evidence, index) => (

                            <div
                              key={index}
                              className="evidence-item"
                            >

                              <p>
                                <strong>
                                  Type:
                                </strong>{" "}
                                {evidence.type}
                              </p>

                              <p>
                                <strong>
                                  Ingredient:
                                </strong>{" "}
                                {evidence.ingredient}
                              </p>

                              <p>
                                <strong>
                                  Source:
                                </strong>{" "}
                                {evidence.text}
                              </p>

                              <p>
                                <strong>
                                  Confidence:
                                </strong>{" "}
                                {(
                                  evidence.confidence * 100
                                ).toFixed(1)}
                                %
                              </p>

                            </div>

                          )
                        )}

                      </div>

                    )}

                </div>

              ))}

            </div>


            {/* INGREDIENTS */}

            <div className="card">

              <h3>Extracted Ingredients</h3>

              <div className="ingredients-list">

                {result.ingredients.map(
                  (ingredient, index) => (

                    <span
                      className="ingredient-tag"
                      key={index}
                    >
                      {ingredient}
                    </span>

                  )
                )}

              </div>

            </div>

          </section>

        )}

      </main>

    </div>
  );
}

export default App;