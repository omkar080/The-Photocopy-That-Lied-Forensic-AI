import hashlib
import json
import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image as PILImage
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config import settings, BASE_DIR
from app.database import init_db, check_database_connection, engine, active_db_type, get_db
from app.models.claim import Claim
from app.models.image import ClaimImage
from app.models.forensic import ForensicAnalysis, ForensicModuleResult
from app.models.fairness import FairnessResult
from app.models.baseline import DeviceBaseline
from app.models.review import Review
from app.models.audit import AuditLog
from app.services.forensic_service import ForensicAnalysisEngine, classify_image

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("forensic_ai.main")


def seed_device_baselines(db: Session):
    """Seed calibrated smartphone camera device baselines if table is empty."""
    count = db.query(DeviceBaseline).count()
    if count == 0:
        baselines = [
            DeviceBaseline(
                device_make="Xiaomi",
                device_model="Redmi Note 12 (Budget)",
                sensor_type="Samsung JN1 (50MP ISOCELL)",
                typical_prnu_variance=0.024,
                typical_compression_quality=85,
                standard_noise_floor=0.035,
                sample_count=100,
                notes="Aggressive sharpening and high chroma noise reduction typical of entry-level ISP.",
            ),
            DeviceBaseline(
                device_make="Realme",
                device_model="Realme 10 Pro (Budget)",
                sensor_type="Samsung HM6 (108MP)",
                typical_prnu_variance=0.022,
                typical_compression_quality=88,
                standard_noise_floor=0.030,
                sample_count=80,
                notes="Standard AI-scene HDR enhancement; strong edge contrast on foliage.",
            ),
            DeviceBaseline(
                device_make="Samsung",
                device_model="Galaxy A34 (Mid-range)",
                sensor_type="Sony IMX582 (48MP)",
                typical_prnu_variance=0.016,
                typical_compression_quality=92,
                standard_noise_floor=0.020,
                sample_count=120,
                notes="Balanced ISP processing with moderate noise suppression.",
            ),
            DeviceBaseline(
                device_make="Apple",
                device_model="iPhone 13/14 (Flagship)",
                sensor_type="Sony Custom CMOS (12MP)",
                typical_prnu_variance=0.010,
                typical_compression_quality=95,
                standard_noise_floor=0.015,
                sample_count=150,
                notes="Deep Fusion neural noise reduction and fine spatial coherence.",
            ),
        ]
        db.add_all(baselines)
        db.commit()
        logger.info("Default device baselines seeded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Starting up Forensic AI application...")
    try:
        init_db()
        # Seed initial baselines
        from app.database import SessionLocal
        with SessionLocal() as db:
            seed_device_baselines(db)
        logger.info("Database tables and baselines verified/created successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize database tables: {exc}")

    yield

    logger.info("Shutting down Forensic AI application...")
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Insurance Claim Forensic Analysis & Tampering Detection Platform",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and uploaded files
static_path = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

uploads_path = Path(settings.upload_path)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Template configuration
templates_path = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# =============================================================================
# FRONTEND JINJA2 ROUTES (Web User Interface)
# =============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def view_dashboard(request: Request, db: Session = Depends(get_db)):
    """Render the main forensic investigation dashboard."""
    total_claims = db.query(Claim).count()
    analyzed_claims = db.query(ForensicAnalysis).filter(ForensicAnalysis.status == "completed").count()
    review_required = db.query(Claim).filter(Claim.status.in_(["in_review", "flagged"])).count()
    strong_evidence = db.query(ForensicAnalysis).filter(ForensicAnalysis.overall_risk_score >= 60.0).count()

    stats = {
        "total_claims": total_claims,
        "analyzed_claims": analyzed_claims,
        "review_required": review_required,
        "flagged_claims": strong_evidence,
    }

    # Fetch recent claims with their latest analysis if available
    claims_records = db.query(Claim).order_by(desc(Claim.created_at)).limit(10).all()
    claims_list = []
    for c in claims_records:
        first_img = db.query(ClaimImage).filter(ClaimImage.claim_id == c.id).first()
        analysis = None
        classification = None
        if first_img:
            analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == first_img.id).first()
            if analysis:
                classification = classify_image(analysis.overall_risk_score)
        claims_list.append({
            "claim": c,
            "image": first_img,
            "analysis": analysis,
            "classification": classification,
        })

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "stats": stats,
            "claims": claims_list,
            "db_type": active_db_type,
        },
    )


@app.get("/claims", response_class=HTMLResponse, tags=["Web UI"])
def view_claims(request: Request, db: Session = Depends(get_db)):
    """Render the full insurance claims registry."""
    claims_records = db.query(Claim).order_by(desc(Claim.created_at)).all()
    claims_list = []
    for c in claims_records:
        first_img = db.query(ClaimImage).filter(ClaimImage.claim_id == c.id).first()
        analysis = None
        classification = None
        if first_img:
            analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == first_img.id).first()
            if analysis:
                classification = classify_image(analysis.overall_risk_score)
        claims_list.append({
            "claim": c,
            "image": first_img,
            "analysis": analysis,
            "classification": classification,
        })

    return templates.TemplateResponse(
        request,
        "claims.html",
        {
            "active_page": "claims",
            "claims": claims_list,
            "db_type": active_db_type,
        },
    )


@app.get("/claims/new", response_class=HTMLResponse, tags=["Web UI"])
def view_new_claim(request: Request):
    """Render the new claim submission form."""
    random_suffix = uuid.uuid4().hex[:6].upper()
    default_number = f"CLM-{datetime.now().strftime('%Y%m%d')}-{random_suffix}"
    return templates.TemplateResponse(
        request,
        "new_claim.html",
        {
            "active_page": "new_claim",
            "default_claim_number": default_number,
            "db_type": active_db_type,
        },
    )


@app.post("/claims/create", tags=["Web UI"])
async def create_claim_form(
    claim_number: str = Form(...),
    policy_number: str = Form(...),
    claimant_name: str = Form(...),
    claim_type: str = Form(...),
    incident_date: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    action: str = Form("analyze_now"),
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Process claim creation form with image upload and optional immediate analysis."""
    # 1. Validate and save image file
    filename_ext = Path(image_file.filename).suffix.lower() if image_file.filename else ".jpg"
    if filename_ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, or PNG images are supported.")

    unique_filename = f"{uuid.uuid4().hex}{filename_ext}"
    dest_path = settings.upload_path / unique_filename

    content = await image_file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with open(dest_path, "wb") as f:
        f.write(content)

    # 2. Compute cryptographic hashes
    sha256_hash = hashlib.sha256(content).hexdigest()
    md5_hash = hashlib.md5(content).hexdigest()

    # 3. Read image dimensions & EXIF metadata safely
    width, height = None, None
    exif_json_str = None
    try:
        with PILImage.open(dest_path) as pil_img:
            width, height = pil_img.size
            raw_exif = pil_img._getexif()
            if raw_exif:
                clean_exif = {}
                for k, v in raw_exif.items():
                    if isinstance(v, (str, int, float)):
                        clean_exif[str(k)] = v
                if clean_exif:
                    exif_json_str = json.dumps(clean_exif)
    except Exception as e:
        logger.warning(f"Failed to parse EXIF metadata: {e}")

    # 4. Parse date
    parsed_date = None
    if incident_date:
        try:
            parsed_date = datetime.strptime(incident_date, "%Y-%m-%d")
        except Exception:
            pass

    full_notes = notes or ""
    if location:
        full_notes = f"[Location: {location}] {full_notes}".strip()

    # 5. Insert Claim record
    claim = Claim(
        claim_number=claim_number.strip(),
        policy_number=policy_number.strip(),
        claimant_name=claimant_name.strip(),
        claim_type=claim_type,
        incident_date=parsed_date,
        status="submitted",
        notes=full_notes,
    )
    db.add(claim)
    db.flush()

    # 6. Insert ClaimImage record
    image_record = ClaimImage(
        claim_id=claim.id,
        filename=unique_filename,
        original_filename=image_file.filename or "claim_photo.jpg",
        file_path=str(dest_path),
        file_size_bytes=len(content),
        mime_type=image_file.content_type or "image/jpeg",
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        width=width,
        height=height,
        metadata_json=exif_json_str,
    )
    db.add(image_record)

    # Audit log
    audit = AuditLog(
        claim_id=claim.id,
        action="CLAIM_CREATED",
        details=f"Claim {claim.claim_number} created with photo {image_file.filename} ({len(content)} bytes).",
    )
    db.add(audit)
    db.commit()
    db.refresh(claim)
    db.refresh(image_record)

    # 7. Execute analysis immediately if requested
    if action == "analyze_now":
        engine_service = ForensicAnalysisEngine(db)
        engine_service.analyze_claim_image(claim, image_record)

    return RedirectResponse(url=f"/claims/{claim.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/claims/{claim_id}", response_class=HTMLResponse, tags=["Web UI"])
def view_claim_analysis(claim_id: int, request: Request, db: Session = Depends(get_db)):
    """Render the forensic examination and analysis result view for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    image = db.query(ClaimImage).filter(ClaimImage.claim_id == claim.id).first()
    analysis = None
    modules = []
    fairness = None
    findings = []
    classification = None
    existing_review = db.query(Review).filter(Review.claim_id == claim.id).order_by(desc(Review.created_at)).first()
    audit_logs = db.query(AuditLog).filter(AuditLog.claim_id == claim.id).order_by(AuditLog.created_at).all()

    if image:
        analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == image.id).first()
        if analysis:
            modules = db.query(ForensicModuleResult).filter(ForensicModuleResult.analysis_id == analysis.id).all()
            fairness = db.query(FairnessResult).filter(FairnessResult.analysis_id == analysis.id).first()
            classification = classify_image(analysis.overall_risk_score)
            if analysis.summary_notes:
                try:
                    findings = json.loads(analysis.summary_notes)
                except Exception:
                    findings = [analysis.summary_notes]

    return templates.TemplateResponse(
        request,
        "analysis.html",
        {
            "active_page": "claims",
            "claim": claim,
            "image": image,
            "analysis": analysis,
            "modules": modules,
            "fairness": fairness,
            "findings": findings,
            "classification": classification,
            "existing_review": existing_review,
            "audit_logs": audit_logs,
            "db_type": active_db_type,
        },
    )


@app.post("/claims/{claim_id}/analyze", tags=["Web UI"])
def trigger_analysis(claim_id: int, db: Session = Depends(get_db)):
    """Trigger or re-run the forensic analysis pipeline for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    image = db.query(ClaimImage).filter(ClaimImage.claim_id == claim.id).first()
    if not image:
        raise HTTPException(status_code=400, detail="No evidence image attached to this claim.")

    engine_service = ForensicAnalysisEngine(db)
    engine_service.analyze_claim_image(claim, image)

    return RedirectResponse(url=f"/claims/{claim.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/claims/{claim_id}/review", tags=["Web UI"])
def submit_human_review(
    claim_id: int,
    decision: str = Form(...),
    reviewer_name: str = Form("Certified Adjuster"),
    comments: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Record an adjuster's human review decision on a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    image = db.query(ClaimImage).filter(ClaimImage.claim_id == claim.id).first()
    analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == image.id).first() if image else None

    # Update claim status based on decision
    if decision == "approved":
        claim.status = "verified"
    elif decision == "manual_audit_required":
        claim.status = "in_review"
    elif decision == "flagged_for_investigation":
        claim.status = "flagged"

    review = Review(
        claim_id=claim.id,
        analysis_id=analysis.id if analysis else None,
        decision=decision,
        comments=comments,
        is_final=True,
    )
    db.add(review)

    audit = AuditLog(
        claim_id=claim.id,
        action="HUMAN_REVIEW_RECORDED",
        details=f"Decision '{decision}' logged by {reviewer_name}. Comments: {comments or 'None'}",
    )
    db.add(audit)

    db.commit()
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/claims/{claim_id}/report", response_class=HTMLResponse, tags=["Web UI"])
def view_investigation_report(claim_id: int, request: Request, db: Session = Depends(get_db)):
    """Render a printable forensic investigation report for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    image = db.query(ClaimImage).filter(ClaimImage.claim_id == claim.id).first()
    analysis = None
    modules = []
    fairness = None
    findings = []
    classification = None
    existing_review = db.query(Review).filter(Review.claim_id == claim.id).order_by(desc(Review.created_at)).first()
    audit_logs = db.query(AuditLog).filter(AuditLog.claim_id == claim.id).order_by(AuditLog.created_at).all()

    if image:
        analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == image.id).first()
        if analysis:
            modules = db.query(ForensicModuleResult).filter(ForensicModuleResult.analysis_id == analysis.id).all()
            fairness = db.query(FairnessResult).filter(FairnessResult.analysis_id == analysis.id).first()
            classification = classify_image(analysis.overall_risk_score)
            if analysis.summary_notes:
                try:
                    findings = json.loads(analysis.summary_notes)
                except Exception:
                    findings = [analysis.summary_notes]

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "claim": claim,
            "image": image,
            "analysis": analysis,
            "modules": modules,
            "fairness": fairness,
            "findings": findings,
            "classification": classification,
            "existing_review": existing_review,
            "audit_logs": audit_logs,
            "db_type": active_db_type,
        },
    )

@app.get("/evidence", response_class=HTMLResponse, tags=["Web UI"])
def view_evidence_gallery(request: Request, db: Session = Depends(get_db)):
    """Render the forensic artifact evidence gallery across all analyzed claims."""
    module_results = db.query(ForensicModuleResult).order_by(desc(ForensicModuleResult.created_at)).all()
    return templates.TemplateResponse(
        request,
        "evidence.html",
        {
            "active_page": "evidence",
            "module_results": module_results,
            "db_type": active_db_type,
        },
    )


@app.get("/reviews", response_class=HTMLResponse, tags=["Web UI"])
def view_reviews_queue(request: Request, db: Session = Depends(get_db)):
    """Render the human adjuster reviews queue."""
    reviews_list = db.query(Review).order_by(desc(Review.created_at)).all()
    return templates.TemplateResponse(
        request,
        "reviews.html",
        {
            "active_page": "reviews",
            "reviews": reviews_list,
            "db_type": active_db_type,
        },
    )


@app.get("/health", response_class=HTMLResponse, tags=["Web UI"])
def view_health_page(request: Request, db: Session = Depends(get_db)):
    """Render the system health and device baselines page."""
    db_info = check_database_connection()
    baselines = db.query(DeviceBaseline).all()
    return templates.TemplateResponse(
        request,
        "health.html",
        {
            "active_page": "health",
            "db_info": db_info,
            "baselines": baselines,
            "max_upload_mb": settings.MAX_UPLOAD_SIZE_MB,
            "db_type": active_db_type,
        },
    )


# =============================================================================
# REST API ENDPOINTS (Programmatic API / OpenAPI)
# =============================================================================

@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint for monitoring system and database connectivity."""
    db_status = check_database_connection()
    is_healthy = db_status.get("status") == "connected"

    payload = {
        "status": "healthy" if is_healthy else "degraded",
        "version": settings.PROJECT_VERSION,
        "database": db_status,
        "storage": {
            "upload_dir": str(settings.upload_path),
            "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        },
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/info", tags=["System"])
def system_info():
    """Provide configuration and platform metadata."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.APP_ENV,
        "active_database_type": active_db_type,
        "mysql_configured": f"{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}",
        "sqlite_fallback_enabled": settings.SQLITE_FALLBACK,
    }


@app.get("/api/dashboard/stats", tags=["Dashboard API"])
def api_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregated statistics for claims and forensic analyses."""
    total_claims = db.query(Claim).count()
    analyzed_claims = db.query(ForensicAnalysis).filter(ForensicAnalysis.status == "completed").count()
    review_required = db.query(Claim).filter(Claim.status.in_(["in_review", "flagged"])).count()
    strong_evidence = db.query(ForensicAnalysis).filter(ForensicAnalysis.overall_risk_score >= 60.0).count()

    return {
        "total_claims": total_claims,
        "analyzed_claims": analyzed_claims,
        "review_required": review_required,
        "flagged_claims": strong_evidence,
    }


@app.get("/api/claims", tags=["Claims API"])
def api_list_claims(db: Session = Depends(get_db)):
    """List all registered claims and their forensic integrity scores."""
    claims = db.query(Claim).order_by(desc(Claim.created_at)).all()
    results = []
    for c in claims:
        img = db.query(ClaimImage).filter(ClaimImage.claim_id == c.id).first()
        analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == img.id).first() if img else None
        classification = classify_image(analysis.overall_risk_score) if analysis else None
        results.append({
            "id": c.id,
            "claim_number": c.claim_number,
            "claimant_name": c.claimant_name,
            "policy_number": c.policy_number,
            "claim_type": c.claim_type,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "classification": classification,
        })
    return {"claims": results, "count": len(results)}


@app.get("/api/claims/{claim_id}", tags=["Claims API"])
def api_get_claim(claim_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed information, evidence images, and forensic findings for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    image = db.query(ClaimImage).filter(ClaimImage.claim_id == claim.id).first()
    analysis = db.query(ForensicAnalysis).filter(ForensicAnalysis.image_id == image.id).first() if image else None

    modules_data = []
    if analysis:
        modules = db.query(ForensicModuleResult).filter(ForensicModuleResult.analysis_id == analysis.id).all()
        for m in modules:
            modules_data.append({
                "module_name": m.module_name,
                "score": m.score,
                "anomaly_detected": m.anomaly_detected,
                "details": m.details_json,
                "artifact_path": m.artifact_path,
            })

    classification = None
    if analysis:
        classification = classify_image(analysis.overall_risk_score)

    return {
        "claim": {
            "id": claim.id,
            "claim_number": claim.claim_number,
            "claimant_name": claim.claimant_name,
            "policy_number": claim.policy_number,
            "claim_type": claim.claim_type,
            "status": claim.status,
            "incident_date": claim.incident_date.isoformat() if claim.incident_date else None,
            "notes": claim.notes,
        },
        "image": {
            "filename": image.filename if image else None,
            "original_filename": image.original_filename if image else None,
            "sha256": image.sha256_hash if image else None,
            "resolution": f"{image.width}x{image.height}" if (image and image.width) else None,
        } if image else None,
        "analysis": {
            "classification": classification,
            "explanation": analysis.fusion_explanation if analysis else None,
            "modules": modules_data,
        } if analysis else None,
    }
