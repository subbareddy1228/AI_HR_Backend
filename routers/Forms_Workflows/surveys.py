from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional

from model.Forms_Workflows.survey import Survey, SurveyResponse as SurveyResponseModel
from schema.Forms_Workflows.survey import (
    SurveyCreate,
    SurveyUpdate,
    SurveyResponse,
    SurveyResponseCreate,
    SurveyResponseResponse,
)

router = APIRouter(prefix="/surveys", tags=["Forms & Workflows"])


@router.post("/", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
def create_survey(payload: SurveyCreate, db: Session = Depends(get_db)):
    survey = Survey(**payload.model_dump())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("/", response_model=list[SurveyResponse])
def list_surveys(
    is_active: Optional[bool] = Query(None),
    survey_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(Survey)
    if is_active is not None:
        query = query.where(Survey.is_active == is_active)
    if survey_type:
        query = query.where(Survey.survey_type == survey_type)
    return db.execute(query).scalars().all()


@router.get("/{survey_id}", response_model=SurveyResponse)
def get_survey(survey_id: int, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


@router.put("/{survey_id}", response_model=SurveyResponse)
def update_survey(survey_id: int, payload: SurveyUpdate, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(survey, field, value)
    db.commit()
    db.refresh(survey)
    return survey


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_survey(survey_id: int, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    db.delete(survey)
    db.commit()


@router.post("/{survey_id}/respond", response_model=SurveyResponseResponse, status_code=status.HTTP_201_CREATED)
def submit_response(survey_id: int, payload: SurveyResponseCreate, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if not survey.is_active:
        raise HTTPException(status_code=400, detail="Survey is not active")

    data = payload.model_dump()
    data["survey_id"] = survey_id
    response = SurveyResponseModel(**data)
    db.add(response)
    db.commit()
    db.refresh(response)
    return response


@router.get("/{survey_id}/responses", response_model=list[SurveyResponseResponse])
def list_responses(survey_id: int, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return db.execute(
        select(SurveyResponseModel).where(SurveyResponseModel.survey_id == survey_id)
    ).scalars().all()


@router.get("/{survey_id}/summary")
def survey_summary(survey_id: int, db: Session = Depends(get_db)):
    survey = db.execute(select(Survey).where(Survey.id == survey_id)).scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    all_responses = db.execute(
        select(SurveyResponseModel).where(SurveyResponseModel.survey_id == survey_id)
    ).scalars().all()

    total = len(all_responses)
    questions = survey.questions or []

    # Build per-question answer breakdown
    question_breakdown: dict = {}
    for q in questions:
        qid = str(q.get("id") or q.get("question_id", ""))
        question_breakdown[qid] = {"question": q.get("text", qid), "answers": {}}

    for resp in all_responses:
        for ans in (resp.responses or []):
            qid = str(ans.get("question_id", ""))
            answer = str(ans.get("answer", ""))
            if qid not in question_breakdown:
                question_breakdown[qid] = {"question": qid, "answers": {}}
            bucket = question_breakdown[qid]["answers"]
            bucket[answer] = bucket.get(answer, 0) + 1

    return {
        "survey_id": survey_id,
        "title": survey.title,
        "total_responses": total,
        "question_breakdown": list(question_breakdown.values()),
    }
