from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from normalization.run_image_pipeline import process_fresh_image
from normalization.pipeline import DEMO_PROFILE
from normalization.user_profile import (
    AllergySeverity,
    UserAllergy,
    UserProfile,
)

def create_user_profile(
    allergies: list[str] | None = None,
    severity: str = "HIGH",
) -> UserProfile:
    """
    Build a UserProfile from allergen names supplied by the API client.
    """

    if not allergies:
        return UserProfile([])

    user_allergies = []

    for allergen in allergies:
        allergen = allergen.strip().upper()

        if not allergen:
            continue

        user_allergies.append(
            UserAllergy(
                allergen=allergen,
                severity=AllergySeverity(severity.upper()),
                avoidance_required=True,
            )
        )

    return UserProfile(user_allergies)

app = FastAPI(
    title="AllergyGuard API",
    description="Multimodal packaged-food allergen detection and risk assessment API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "application": "AllergyGuard",
        "status": "running",
        "message": "AllergyGuard API is working",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AllergyGuard API",
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...),
    allergies: str = "",
    severity: str = "HIGH",):
    """
    Analyze a packaged-food image through the complete AllergyGuard pipeline.
    """

    # Check that a file was actually uploaded
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No image file provided.",
        )

    # Basic image-file validation
    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format: {extension}",
        )

    temp_path = None

    try:
        # Read uploaded image
        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty.",
            )

        # Save temporarily
        with NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        # Run existing AllergyGuard pipeline
        allergy_list = [
            item.strip().upper()
            for item in allergies.split(",")
            if item.strip()
        ]

        user_profile = create_user_profile(
            allergy_list,
            severity,
        )
        
        (
            image_path,
            ocr_text,
            ocr_summary,
            ingredients,
            normalized,
            allergen_evidence,
            allergen_assessments,
            product_risk,
        ) = process_fresh_image(
            temp_path,
            user_profile,
        )

        # Convert normalization results to JSON-safe dictionaries
                # ==========================================
        # BUILD FRONTEND-FRIENDLY RESPONSE
        # ==========================================

        # ------------------------------------------
        # Allergen results
        # ------------------------------------------
        #
        # IMPORTANT:
        # The internal pipeline may assess the complete
        # allergen ontology.
        #
        # The API must return ONLY the allergens selected
        # by the current user.
        #
        # Example:
        #   Image contains MILK + SOY + WHEAT
        #   User selected PEANUT
        #
        # API must return:
        #   PEANUT -> NOT_DETECTED
        #
        # It must NOT return MILK/SOY/WHEAT as user results,
        # because those are not part of this user's profile.
        
        # ------------------------------------------
        # Allergen results
        # ------------------------------------------
        #
        # IMPORTANT:
        # Return results ONLY for allergens selected
        # by the current user.
        #
        # If the selected allergen has no evidence:
        #   - with usable ingredient text -> NOT_DETECTED
        #   - without usable ingredient text -> INSUFFICIENT_EVIDENCE
        # ------------------------------------------

        selected_allergen_set = {
            allergen.upper()
            for allergen in allergy_list
        }

        # First index the assessments produced by the pipeline
        assessment_map = {
            assessment.allergen.upper(): assessment
            for assessment in allergen_assessments
        }

        allergen_results = []

        for selected_allergen in selected_allergen_set:

            # ------------------------------------------
            # Case 1: Pipeline already produced an
            # assessment for this allergen
            # ------------------------------------------

            assessment = assessment_map.get(selected_allergen)

            if assessment is not None:

                supporting_evidence = []

                for evidence in allergen_evidence:
                    if evidence.allergen.upper() == selected_allergen:
                        supporting_evidence.append(
                            {
                                "type": evidence.evidence_type,
                                "ingredient": evidence.ingredient,
                                "text": evidence.supporting_text,
                                "confidence": round(evidence.confidence, 4),
                            }
                        )

                allergen_results.append(
                    {
                        "allergen": assessment.allergen,
                        "status": assessment.status,
                        "confidence": round(assessment.confidence, 4),
                        "explanation": assessment.explanation,
                        "evidence": supporting_evidence,
                    }
                )

                continue

            # ------------------------------------------
            # Case 2: Selected allergen was NOT found
            # in the pipeline assessments
            #
            # If we have usable ingredient information,
            # we can say NOT_DETECTED.
            #
            # Otherwise we cannot determine it.
            # ------------------------------------------

            if ingredients:

                allergen_results.append(
                    {
                        "allergen": selected_allergen,
                        "status": "NOT_DETECTED",
                        "confidence": 1.0,
                        "explanation": (
                            f"{selected_allergen} was not found in the "
                            "available ingredient evidence."
                        ),
                        "evidence": [],
                    }
                )

            else:

                allergen_results.append(
                    {
                        "allergen": selected_allergen,
                        "status": "INSUFFICIENT_EVIDENCE",
                        "confidence": 0.0,
                        "explanation": (
                            f"There is insufficient ingredient evidence "
                            f"to determine whether {selected_allergen} is present."
                        ),
                        "evidence": [],
                    }
                )

        # ------------------------------------------
        # Personalized risk result
        # ------------------------------------------
        #
        # IMPORTANT:
        # Risk must be based ONLY on the allergens
        # selected by the current user.
        #
        # We should NOT use product_risk here because
        # product_risk is based on the broader product
        # allergen assessment.
        # ------------------------------------------

        risk_allergens = []

        for result in allergen_results:

            status = str(result["status"]).upper()

            if status == "DETECTED":

                risk_level = "ALLERGEN_FOUND"

                reason = (
                    f"{result['allergen']} was detected in the "
                    "available allergen evidence."
                )

            elif status == "POTENTIAL":

                risk_level = "POSSIBLE_ALLERGEN"

                reason = (
                    f"There is potential evidence for "
                    f"{result['allergen']} in the available evidence."
                )

            elif status == "NOT_DETECTED":

                risk_level = "NO_MATCH"

                reason = (
                    f"{result['allergen']} was not found in the "
                    "available ingredient evidence."
                )

            else:

                risk_level = "INSUFFICIENT_EVIDENCE"

                reason = (
                    f"There is insufficient evidence to determine "
                    f"whether {result['allergen']} is present."
                )

            risk_allergens.append(
                {
                    "allergen": result["allergen"],
                    "risk_level": risk_level,
                    "reason": reason,
                }
            )


        # ------------------------------------------
        # Determine overall personalized result
        # ------------------------------------------

        statuses = [
            str(result["status"]).upper()
            for result in allergen_results
        ]


        if "DETECTED" in statuses:

            overall_level = "ALLERGEN_FOUND"

            overall_message = (
                "A selected allergen was detected in the "
                "available product evidence."
            )

            overall_warnings = [
                "This is an evidence-based screening result and "
                "not a medical safety determination."
            ]

        elif "POTENTIAL" in statuses:

            overall_level = "POSSIBLE_ALLERGEN"

            overall_message = (
                "Potential evidence for a selected allergen was found."
            )

            overall_warnings = [
                "The evidence is not conclusive. This is not a "
                "medical safety determination."
            ]

        elif "INSUFFICIENT_EVIDENCE" in statuses:

            overall_level = "INSUFFICIENT_EVIDENCE"

            overall_message = (
                "There is insufficient evidence to determine "
                "whether the selected allergens are present."
            )

            overall_warnings = [
                "The available image or ingredient evidence is insufficient."
            ]

        elif statuses and all(
            status == "NOT_DETECTED"
            for status in statuses
        ):

            overall_level = "NO_MATCH"

            overall_message = (
                "No selected allergen was found in the "
                "available ingredient evidence."
            )

            overall_warnings = [
                "No selected allergen was detected in the available evidence.",
                "This screening result does not guarantee that the product "
                "is medically safe for you."
            ]

        else:

            overall_level = "INSUFFICIENT_EVIDENCE"

            overall_message = (
                "The available evidence was insufficient to "
                "determine the selected allergens."
            )

            overall_warnings = [
                "The screening result is inconclusive."
            ]


        risk_result = {
            "level": overall_level,
            "message": overall_message,
            "warnings": overall_warnings,
            "allergens": risk_allergens,
        }

        # ------------------------------------------
        # Final API response
        # ------------------------------------------

        return {
            "success": True,

            "product": {
                "filename": file.filename,
                "content_type": file.content_type,
            },

            "ocr": {
                "confidence": ocr_summary["avg_confidence"],
                "regions": ocr_summary["region_count"],
            },

            "ingredients": ingredients,

            "allergens": allergen_results,

            "risk": risk_result,
        }
    
    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AllergyGuard processing failed: {exc}",
        )

    finally:
        # Delete temporary uploaded image
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()