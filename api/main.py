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

        allergen_results = []

        for assessment in allergen_assessments:

            # Find evidence belonging to this allergen
            supporting_evidence = []

            for evidence in allergen_evidence:
                if evidence.allergen == assessment.allergen:
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

        # ------------------------------------------
        # Personalized risk
        # ------------------------------------------

        risk_result = None

        if product_risk is not None:

            risk_result = {
                "level": product_risk.overall_risk,
                "message": product_risk.explanation,
                "warnings": product_risk.warnings,
                "allergens": [
                    {
                        "allergen": result.allergen,
                        "risk_level": result.risk_level,
                        "reason": result.reason,
                    }
                    for result in product_risk.allergen_results
                ],
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