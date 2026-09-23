from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile

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
        normalized_results = []

        for item in normalized:
            normalized_results.append(
                {
                    "raw_term": item.raw_term,
                    "cleaned_term": item.cleaned_term,
                    "normalized_term": item.normalized_term,
                    "canonical_concept": item.canonical_concept,
                    "allergen": item.allergen,
                    "match_type": item.match_type,
                    "status": item.status,
                    "confidence": round(item.confidence, 4),
                }
            )

        # Convert allergen evidence
        evidence_results = []

        for evidence in allergen_evidence:
            evidence_results.append(
                {
                    "allergen": evidence.allergen,
                    "ingredient": evidence.ingredient,
                    "evidence_type": evidence.evidence_type,
                    "status": evidence.status,
                    "confidence": round(evidence.confidence, 4),
                    "supporting_text": evidence.supporting_text,
                }
            )

        # Convert allergen assessments
        assessment_results = []

        for assessment in allergen_assessments:
            assessment_results.append(
                {
                    "allergen": assessment.allergen,
                    "status": assessment.status,
                    "confidence": round(assessment.confidence, 4),
                    "explanation": assessment.explanation,
                }
            )

        # Convert personalized risk
        risk_result = None

        if product_risk is not None:
            risk_result = {
                "overall_risk": product_risk.overall_risk,
                "explanation": product_risk.explanation,
                "warnings": product_risk.warnings,
                "allergen_results": [
                    {
                        "allergen": result.allergen,
                        "risk_level": result.risk_level,
                        "reason": result.reason,
                    }
                    for result in product_risk.allergen_results
                ],
            }

        return {
            "success": True,

            "image": {
                "filename": file.filename,
                "content_type": file.content_type,
            },

            "ocr": {
                "text": ocr_text,
                "average_confidence": ocr_summary["avg_confidence"],
                "region_count": ocr_summary["region_count"],
            },

            "ingredients": ingredients,

            "normalization": normalized_results,

            "allergen_evidence": evidence_results,

            "allergen_assessments": assessment_results,

            "personalized_risk": risk_result,
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