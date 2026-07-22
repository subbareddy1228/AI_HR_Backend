

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User

from schema.Forms_Workflows.survey import (
    AddQuestionsFromBankRequest,
    DistributionCreate,
    DistributionResponse,
    DistributionUpdate,
    LaunchSurveyRequest,
    QuestionBankCreate,
    QuestionBankListResponse,
    QuestionBankResponse,
    QuestionBankUpdate,
    RefreshAnalyticsResponse,
    ReorderQuestionsRequest,
    SendRemindersResponse,
    SurveyAnalyticsResponse,
    SurveyCreate,
    SurveyListItem,
    SurveyQuestionCreate,
    SurveyQuestionResponse,
    SurveyQuestionUpdate,
    SurveyResponse,
    SurveySubmitRequest,
    SurveySubmitResponse,
    SurveyUpdate,
    TemplateResponse,
    UseTemplateRequest,
)
from services.Forms_Workflows.survey_service import (
    add_question,
    add_questions_from_bank,
    archive_survey,
    compute_and_refresh_analytics,
    create_bank_question,
    create_or_update_distribution,
    create_survey,
    delete_bank_question,
    delete_question,
    delete_survey,
    get_analytics,
    get_bank_question,
    get_distribution,
    get_survey,
    get_template,
    launch_survey,
    list_bank_questions,
    list_surveys,
    list_templates,
    pause_survey,
    publish_survey,
    reorder_questions,
    resume_survey,
    seed_default_bank_questions,
    seed_default_templates,
    send_reminders,
    submit_response,
    update_bank_question,
    update_question,
    update_survey,
    use_template,
)

router = APIRouter(
    prefix="/surveys",
    tags=["Forms & Workflows – Surveys & Pulse Checks"],
)


@router.post(
    "/question-bank",
    response_model=QuestionBankResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new question to the Question Bank",
)
def create_bank_question_endpoint(
    payload: QuestionBankCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_bank_question(db, payload, created_by=current_user.email)


@router.get(
    "/question-bank",
    response_model=QuestionBankListResponse,
    summary="List / search Question Bank (with filters: category, type, perspective, sort_by)",
)
def list_bank_questions_endpoint(
    category:    Optional[str] = Query(None, description="Filter by category label"),
    q_type:      Optional[str] = Query(None, alias="type", description="Filter by question type"),
    perspective: Optional[str] = Query(None, description="Filter by BSC perspective"),
    sort_by:     str           = Query("times_used", description="times_used | created_at | last_used"),
    search:      Optional[str] = Query(None, description="Keyword search in question text"),
    page:        int           = Query(1, ge=1),
    page_size:   int           = Query(50, ge=1, le=200),
    current_user: User         = Depends(get_current_user),
    db: Session                = Depends(get_db),
):
    skip = (page - 1) * page_size
    items, total = list_bank_questions(
        db,
        category=category,
        q_type=q_type,
        perspective=perspective,
        sort_by=sort_by,
        search=search,
        skip=skip,
        limit=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/question-bank/{qid}",
    response_model=QuestionBankResponse,
    summary="Get a single Question Bank entry",
)
def get_bank_question_endpoint(
    qid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_bank_question(db, qid)


@router.put(
    "/question-bank/{qid}",
    response_model=QuestionBankResponse,
    summary="Update a Question Bank entry",
)
def update_bank_question_endpoint(
    qid: int,
    payload: QuestionBankUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_bank_question(db, qid, payload)


@router.delete(
    "/question-bank/{qid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a Question Bank entry",
)
def delete_bank_question_endpoint(
    qid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_bank_question(db, qid)


@router.get(
    "/templates",
    response_model=List[TemplateResponse],
    summary="List all survey templates (Balanced Scorecard + Standard)",
)
def list_templates_endpoint(
    category: Optional[str] = Query(None, description="balanced_scorecard | standard"),
    db: Session = Depends(get_db),
):
    return list_templates(db, category=category)


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get a single template",
)
def get_template_endpoint(
    template_id: int,
    db: Session = Depends(get_db),
):
    return get_template(db, template_id)


@router.post(
    "/templates/{template_id}/use",
    response_model=SurveyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new survey from a template",
)
def use_template_endpoint(
    template_id: int,
    payload: UseTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return use_template(db, template_id, payload, created_by=current_user.email)

@router.post(
    "/",
    response_model=SurveyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new survey (Draft)",
)
def create_survey_endpoint(
    payload: SurveyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_survey(db, payload, created_by=current_user.email)


@router.get(
    "/",
    response_model=dict,
    summary="List surveys with optional filters",
)
def list_surveys_endpoint(
    status_filter: Optional[str] = Query(None, alias="status"),
    perspective:   Optional[str] = Query(None),
    search:        Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=100),
    current_user:  User          = Depends(get_current_user),
    db:            Session       = Depends(get_db),
):
    skip = (page - 1) * page_size
    surveys, total = list_surveys(
        db,
        status_filter=status_filter,
        perspective=perspective,
        search=search,
        skip=skip,
        limit=page_size,
    )

    from sqlalchemy import select as sa_select, func as sa_func
    from model.Forms_Workflows.survey import SurveyResponse as SurveyResponseModel, SurveyQuestion as SurveyQuestionModel

    items = []
    for s in surveys:
        q_count = len(s.questions) if hasattr(s, "questions") else 0
        r_count = db.execute(
            sa_select(sa_func.count(SurveyResponseModel.id)).where(
                SurveyResponseModel.survey_id == s.id
            )
        ).scalar_one()
        items.append({
            "id":          s.id,
            "title":       s.title,
            "status":      s.status.value if hasattr(s.status, "value") else s.status,
            "perspective": s.bsc_perspective.value if hasattr(s.bsc_perspective, "value") else s.bsc_perspective,
            "questions":   q_count,
            "responses":   r_count,
            "created_at":  s.created_at.isoformat(),
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/{survey_id}",
    response_model=SurveyResponse,
    summary="Get a single survey (with questions)",
)
def get_survey_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_survey(db, survey_id)


@router.put(
    "/{survey_id}",
    response_model=SurveyResponse,
    summary="Update survey metadata / settings",
)
def update_survey_endpoint(
    survey_id: int,
    payload: SurveyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_survey(db, survey_id, payload, updated_by=current_user.email)


@router.delete(
    "/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a survey (must not be active)",
)
def delete_survey_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_survey(db, survey_id)


# Lifecycle actions
@router.post("/{survey_id}/publish", response_model=SurveyResponse, summary="Publish (draft → active)")
def publish_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return publish_survey(db, survey_id, updated_by=current_user.email)


@router.post("/{survey_id}/pause", response_model=SurveyResponse, summary="Pause an active survey")
def pause_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return pause_survey(db, survey_id, updated_by=current_user.email)


@router.post("/{survey_id}/resume", response_model=SurveyResponse, summary="Resume a paused survey")
def resume_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return resume_survey(db, survey_id, updated_by=current_user.email)


@router.post("/{survey_id}/archive", response_model=SurveyResponse, summary="Archive a survey")
def archive_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return archive_survey(db, survey_id, updated_by=current_user.email)


@router.post(
    "/{survey_id}/questions",
    response_model=SurveyQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a question to a survey",
)
def add_question_endpoint(
    survey_id: int,
    payload: SurveyQuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return add_question(db, survey_id, payload)


@router.post(
    "/{survey_id}/questions/from-bank",
    response_model=List[SurveyQuestionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add multiple questions from Question Bank",
)
def add_questions_from_bank_endpoint(
    survey_id: int,
    payload: AddQuestionsFromBankRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return add_questions_from_bank(db, survey_id, payload)


@router.put(
    "/{survey_id}/questions/{question_id}",
    response_model=SurveyQuestionResponse,
    summary="Update a question within a survey",
)
def update_question_endpoint(
    survey_id: int,
    question_id: int,
    payload: SurveyQuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_question(db, survey_id, question_id, payload)


@router.delete(
    "/{survey_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a question from a survey",
)
def delete_question_endpoint(
    survey_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_question(db, survey_id, question_id)


@router.patch(
    "/{survey_id}/questions/reorder",
    response_model=List[SurveyQuestionResponse],
    summary="Reorder questions (drag-and-drop order update)",
)
def reorder_questions_endpoint(
    survey_id: int,
    payload: ReorderQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reorder_questions(db, survey_id, payload)


@router.get(
    "/{survey_id}/distribute",
    response_model=DistributionResponse,
    summary="Get distribution configuration + participation tracking",
)
def get_distribution_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_distribution(db, survey_id)


@router.put(
    "/{survey_id}/distribute",
    response_model=DistributionResponse,
    summary="Create or update distribution settings",
)
def set_distribution_endpoint(
    survey_id: int,
    payload: DistributionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_or_update_distribution(db, survey_id, payload)


@router.post(
    "/{survey_id}/launch",
    response_model=DistributionResponse,
    summary="Launch survey now (sets distribution + activates survey)",
)
def launch_survey_endpoint(
    survey_id: int,
    payload: LaunchSurveyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return launch_survey(db, survey_id, payload, launched_by=current_user.email)


@router.post(
    "/{survey_id}/send-reminders",
    response_model=SendRemindersResponse,
    summary="Send reminder to non-responders",
)
def send_reminders_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return send_reminders(db, survey_id)


@router.post(
    "/{survey_id}/submit",
    response_model=SurveySubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an employee's survey response",
)
def submit_response_endpoint(
    survey_id: int,
    payload: SurveySubmitRequest,
    db: Session = Depends(get_db),
):
    resp = submit_response(db, survey_id, payload)
    return {
        "id":           resp.id,
        "survey_id":    resp.survey_id,
        "employee_id":  resp.employee_id,
        "is_complete":  resp.is_complete,
        "submitted_at": resp.submitted_at,
    }


@router.get(
    "/{survey_id}/analytics",
    response_model=SurveyAnalyticsResponse,
    summary="Get survey analytics dashboard data",
)
def get_analytics_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_analytics(db, survey_id)


@router.post(
    "/{survey_id}/analytics/refresh",
    response_model=RefreshAnalyticsResponse,
    summary="Force-refresh analytics aggregation",
)
def refresh_analytics_endpoint(
    survey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analytics = compute_and_refresh_analytics(db, survey_id)
    return {
        "message":      "Analytics refreshed successfully",
        "refreshed_at": analytics.refreshed_at,
    }


@router.post(
    "/admin/seed-templates",
    status_code=status.HTTP_200_OK,
    summary="Seed default survey templates (run once)",
    include_in_schema=False,
)
def seed_templates_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = seed_default_templates(db)
    return {"inserted": count, "message": f"{count} templates seeded"}


@router.post(
    "/admin/seed-question-bank",
    status_code=status.HTTP_200_OK,
    summary="Seed default Question Bank entries (run once)",
    include_in_schema=False,
)
def seed_bank_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = seed_default_bank_questions(db)
    return {"inserted": count, "message": f"{count} question bank entries seeded"}
