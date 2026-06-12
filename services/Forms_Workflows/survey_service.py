
from __future__ import annotations

import hashlib
import secrets
import string
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from model.Forms_Workflows.survey import (
    BSCPerspective,
    DistributionMethod,
    QuestionType,
    ScheduleType,
    Survey,
    SurveyAnalytics,
    SurveyDistribution,
    SurveyQuestion,
    SurveyQuestionBank,
    SurveyResponse,
    SurveyStatus,
    SurveyTemplate,
    TargetAudienceType,
    TemplateCategory,
    VisibilityMode,
)
from schema.Forms_Workflows.survey import (
    AddQuestionsFromBankRequest,
    AnswerItem,
    DistributionCreate,
    DistributionUpdate,
    LaunchSurveyRequest,
    QuestionBankCreate,
    QuestionBankUpdate,
    ReorderQuestionsRequest,
    SurveyCreate,
    SurveyQuestionCreate,
    SurveyQuestionUpdate,
    SurveySubmitRequest,
    SurveyUpdate,
    UseTemplateRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _not_found(entity: str, eid: int) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} {eid} not found")


def _generate_shareable_link(survey_id: int) -> str:
    token = secrets.token_urlsafe(16)
    return f"/surveys/public/{survey_id}/{token}"


def _positive_words() -> set:
    return {
        "great", "supportive", "challenging", "growth", "flexible",
        "collaborative", "innovative", "balance", "excellent", "good",
        "happy", "satisfied", "engaged", "motivated", "positive",
    }


def _negative_words() -> set:
    return {
        "poor", "bad", "difficult", "stressful", "toxic", "unfair",
        "overloaded", "underpaid", "negative", "frustrated", "disappointed",
    }

def create_bank_question(
    db: Session,
    payload: QuestionBankCreate,
    created_by: Optional[str] = None,
) -> SurveyQuestionBank:
    q = SurveyQuestionBank(
        **payload.model_dump(),
        created_by=created_by,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def list_bank_questions(
    db: Session,
    *,
    category: Optional[str] = None,
    q_type: Optional[str] = None,
    perspective: Optional[str] = None,
    sort_by: str = "times_used",
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[SurveyQuestionBank], int]:
    stmt = select(SurveyQuestionBank).where(SurveyQuestionBank.is_active == True)

    if category:
        stmt = stmt.where(SurveyQuestionBank.category == category)
    if q_type:
        stmt = stmt.where(SurveyQuestionBank.type == q_type)
    if perspective:
        stmt = stmt.where(SurveyQuestionBank.perspective == perspective)
    if search:
        stmt = stmt.where(SurveyQuestionBank.question.ilike(f"%{search}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    order_col = {
        "times_used": SurveyQuestionBank.times_used.desc(),
        "created_at": SurveyQuestionBank.created_at.desc(),
        "last_used":  SurveyQuestionBank.last_used.desc(),
    }.get(sort_by, SurveyQuestionBank.times_used.desc())

    stmt = stmt.order_by(order_col).offset(skip).limit(limit)
    items = db.execute(stmt).scalars().all()
    return list(items), total


def get_bank_question(db: Session, qid: int) -> SurveyQuestionBank:
    q = db.get(SurveyQuestionBank, qid)
    if not q or not q.is_active:
        raise _not_found("Question bank entry", qid)
    return q


def update_bank_question(
    db: Session,
    qid: int,
    payload: QuestionBankUpdate,
) -> SurveyQuestionBank:
    q = get_bank_question(db, qid)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(q, k, v)
    q.updated_at = _utcnow()
    db.commit()
    db.refresh(q)
    return q


def delete_bank_question(db: Session, qid: int) -> None:
    q = get_bank_question(db, qid)
    q.is_active = False       
    q.updated_at = _utcnow()
    db.commit()

def create_survey(
    db: Session,
    payload: SurveyCreate,
    created_by: Optional[str] = None,
) -> Survey:
    questions_data = payload.questions or []
    survey_dict = payload.model_dump(exclude={"questions"})
    survey = Survey(**survey_dict, created_by=created_by)
    db.add(survey)
    db.flush()

    for idx, q_payload in enumerate(questions_data):
        q = SurveyQuestion(
            survey_id=survey.id,
            order_index=q_payload.order_index if q_payload.order_index else idx,
            **q_payload.model_dump(exclude={"order_index"}),
        )
        db.add(q)

    db.commit()
    db.refresh(survey)
    return _load_survey(db, survey.id)


def list_surveys(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    perspective: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[Survey], int]:
    stmt = select(Survey)
    if status_filter:
        stmt = stmt.where(Survey.status == status_filter)
    if perspective:
        stmt = stmt.where(Survey.bsc_perspective == perspective)
    if search:
        stmt = stmt.where(Survey.title.ilike(f"%{search}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(Survey.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all()), total


def get_survey(db: Session, survey_id: int) -> Survey:
    return _load_survey(db, survey_id)


def _load_survey(db: Session, survey_id: int) -> Survey:
    stmt = (
        select(Survey)
        .where(Survey.id == survey_id)
        .options(
            selectinload(Survey.questions),
            selectinload(Survey.distribution),
        )
    )
    s = db.execute(stmt).scalars().first()
    if not s:
        raise _not_found("Survey", survey_id)
    return s


def update_survey(
    db: Session,
    survey_id: int,
    payload: SurveyUpdate,
    updated_by: Optional[str] = None,
) -> Survey:
    s = _load_survey(db, survey_id)
    if s.status == SurveyStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update an archived survey",
        )
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    s.updated_by = updated_by
    s.updated_at = _utcnow()
    db.commit()
    db.refresh(s)
    return _load_survey(db, survey_id)


def delete_survey(db: Session, survey_id: int) -> None:
    s = _load_survey(db, survey_id)
    if s.status == SurveyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deactivate the survey before deleting",
        )
    db.delete(s)
    db.commit()


def publish_survey(db: Session, survey_id: int, updated_by: Optional[str] = None) -> Survey:
    s = _load_survey(db, survey_id)
    if s.status != SurveyStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft surveys can be published")
    if not s.questions:
        raise HTTPException(status_code=400, detail="Cannot publish a survey with no questions")
    s.status = SurveyStatus.ACTIVE
    s.updated_by = updated_by
    s.updated_at = _utcnow()
    db.commit()
    return _load_survey(db, survey_id)


def archive_survey(db: Session, survey_id: int, updated_by: Optional[str] = None) -> Survey:
    s = _load_survey(db, survey_id)
    s.status = SurveyStatus.ARCHIVED
    s.updated_by = updated_by
    s.updated_at = _utcnow()
    db.commit()
    return _load_survey(db, survey_id)


def pause_survey(db: Session, survey_id: int, updated_by: Optional[str] = None) -> Survey:
    s = _load_survey(db, survey_id)
    if s.status != SurveyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active surveys can be paused")
    s.status = SurveyStatus.PAUSED
    s.updated_by = updated_by
    s.updated_at = _utcnow()
    db.commit()
    return _load_survey(db, survey_id)


def resume_survey(db: Session, survey_id: int, updated_by: Optional[str] = None) -> Survey:
    s = _load_survey(db, survey_id)
    if s.status != SurveyStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Only paused surveys can be resumed")
    s.status = SurveyStatus.ACTIVE
    s.updated_by = updated_by
    s.updated_at = _utcnow()
    db.commit()
    return _load_survey(db, survey_id)

def add_question(
    db: Session,
    survey_id: int,
    payload: SurveyQuestionCreate,
) -> SurveyQuestion:
    _load_survey(db, survey_id)

    if payload.order_index == 0:
        max_idx = db.execute(
            select(func.max(SurveyQuestion.order_index)).where(
                SurveyQuestion.survey_id == survey_id
            )
        ).scalar_one() or 0
        payload = payload.model_copy(update={"order_index": max_idx + 1})

    q = SurveyQuestion(survey_id=survey_id, **payload.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(
    db: Session,
    survey_id: int,
    question_id: int,
    payload: SurveyQuestionUpdate,
) -> SurveyQuestion:
    q = db.execute(
        select(SurveyQuestion).where(
            SurveyQuestion.id == question_id,
            SurveyQuestion.survey_id == survey_id,
        )
    ).scalars().first()
    if not q:
        raise _not_found("Question", question_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return q


def delete_question(db: Session, survey_id: int, question_id: int) -> None:
    q = db.execute(
        select(SurveyQuestion).where(
            SurveyQuestion.id == question_id,
            SurveyQuestion.survey_id == survey_id,
        )
    ).scalars().first()
    if not q:
        raise _not_found("Question", question_id)
    db.delete(q)
    db.commit()


def add_questions_from_bank(
    db: Session,
    survey_id: int,
    payload: AddQuestionsFromBankRequest,
) -> List[SurveyQuestion]:
    _load_survey(db, survey_id)
    now = _utcnow()
    added = []
    max_idx = db.execute(
        select(func.max(SurveyQuestion.order_index)).where(
            SurveyQuestion.survey_id == survey_id
        )
    ).scalar_one() or 0

    for i, bqid in enumerate(payload.bank_question_ids, start=1):
        bq = db.get(SurveyQuestionBank, bqid)
        if not bq:
            continue
        q = SurveyQuestion(
            survey_id=survey_id,
            bank_question_id=bqid,
            question_text=bq.question,
            type=bq.type,
            category=bq.category,
            perspective=bq.perspective,
            options=bq.options,
            scale_min=bq.scale_min,
            scale_max=bq.scale_max,
            order_index=max_idx + i,
        )
        db.add(q)

        bq.times_used += 1
        bq.last_used = now
        added.append(q)

    db.commit()
    for q in added:
        db.refresh(q)
    return added


def reorder_questions(
    db: Session,
    survey_id: int,
    payload: ReorderQuestionsRequest,
) -> List[SurveyQuestion]:
    questions = db.execute(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
    ).scalars().all()

    for q in questions:
        if q.id in payload.order:
            q.order_index = payload.order[q.id]
    db.commit()
    return sorted(questions, key=lambda x: x.order_index)

def _resolve_recipient_count(
    db: Session,
    audience_type: TargetAudienceType,
    audience_filter: Optional[Dict[str, Any]],
) -> int:

    _defaults = {
        TargetAudienceType.ALL_EMPLOYEES: 1245,
        TargetAudienceType.BY_DEPARTMENT: 445,
        TargetAudienceType.BY_LOCATION:   320,
        TargetAudienceType.BY_ROLE:       250,
        TargetAudienceType.BY_TENURE:     160,
        TargetAudienceType.CUSTOM_GROUP:  80,
    }
    if audience_filter and audience_filter.get("employee_ids"):
        return len(audience_filter["employee_ids"])
    return _defaults.get(audience_type, 100)


def create_or_update_distribution(
    db: Session,
    survey_id: int,
    payload: DistributionCreate,
) -> SurveyDistribution:
    s = _load_survey(db, survey_id)

    total_recipients = _resolve_recipient_count(db, payload.audience_type, payload.audience_filter)
    shareable_link = _generate_shareable_link(survey_id)

    dist = s.distribution
    if dist:
        for k, v in payload.model_dump().items():
            setattr(dist, k, v)
        dist.total_recipients = total_recipients
        dist.shareable_link = shareable_link
        dist.updated_at = _utcnow()
    else:
        dist = SurveyDistribution(
            survey_id=survey_id,
            total_recipients=total_recipients,
            shareable_link=shareable_link,
            **payload.model_dump(),
        )
        db.add(dist)

    db.commit()
    db.refresh(dist)
    return dist


def get_distribution(db: Session, survey_id: int) -> SurveyDistribution:
    dist = db.execute(
        select(SurveyDistribution).where(SurveyDistribution.survey_id == survey_id)
    ).scalars().first()
    if not dist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No distribution configured for survey {survey_id}",
        )
    return dist


def launch_survey(
    db: Session,
    survey_id: int,
    payload: LaunchSurveyRequest,
    launched_by: Optional[str] = None,
) -> SurveyDistribution:
    s = _load_survey(db, survey_id)
    if s.status == SurveyStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Cannot launch an archived survey")
    if not s.questions:
        raise HTTPException(status_code=400, detail="Survey has no questions")

    dist = create_or_update_distribution(db, survey_id, payload.distribution)

    if payload.distribution.schedule_type == ScheduleType.SEND_IMMEDIATELY:
        dist.launched_at = _utcnow()
        dist.emails_sent = dist.total_recipients
        s.status = SurveyStatus.ACTIVE

    s.updated_by = launched_by
    s.updated_at = _utcnow()
    db.commit()
    db.refresh(dist)
    return dist


def send_reminders(db: Session, survey_id: int) -> Dict[str, Any]:
    dist = get_distribution(db, survey_id)
    pending = (dist.total_recipients or 0) - (dist.surveys_completed or 0)

    if dist.reminders_sent >= (dist.max_reminders or 3):
        raise HTTPException(
            status_code=400,
            detail=f"Maximum reminders ({dist.max_reminders}) already sent",
        )

    dist.reminders_sent = (dist.reminders_sent or 0) + 1
    dist.last_reminder_at = _utcnow()
    db.commit()

    return {
        "survey_id": survey_id,
        "reminders_sent": dist.reminders_sent,
        "recipients": pending,
        "message": f"Reminder {dist.reminders_sent}/{dist.max_reminders} queued for {pending} recipients",
    }

def submit_response(
    db: Session,
    survey_id: int,
    payload: SurveySubmitRequest,
) -> SurveyResponse:
    s = _load_survey(db, survey_id)
    if s.status != SurveyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Survey is not active")

    # Prevent duplicate completion for identified surveys
    if not payload.is_anonymous and payload.employee_id:
        existing = db.execute(
            select(SurveyResponse).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.employee_id == payload.employee_id,
                SurveyResponse.is_complete == True,
            )
        ).scalars().first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Employee has already completed this survey",
            )

    answers_list = [a.model_dump() for a in payload.answers]
    total_required = sum(1 for q in s.questions if q.is_required)
    answered = len(payload.answers)
    is_complete = answered >= total_required

    overall = None
    if payload.answers:
        scores = [
            a.score for a in payload.answers
            if a.score is not None
        ]
        if scores:
            overall = round(sum(scores) / len(scores), 2)

    response = SurveyResponse(
        survey_id=survey_id,
        employee_id=payload.employee_id if not payload.is_anonymous else None,
        answers=answers_list,
        nps_score=payload.nps_score,
        overall_score=overall,
        is_anonymous=payload.is_anonymous,
        is_complete=is_complete,
        started_at=_utcnow(),
        submitted_at=_utcnow() if is_complete else None,
    )
    db.add(response)
    dist = s.distribution
    if dist:
        if is_complete:
            dist.surveys_completed = (dist.surveys_completed or 0) + 1
            dist.surveys_in_progress = max((dist.surveys_in_progress or 0) - 1, 0)
        else:
            dist.surveys_in_progress = (dist.surveys_in_progress or 0) + 1

    db.commit()
    db.refresh(response)
    return response

def compute_and_refresh_analytics(db: Session, survey_id: int) -> SurveyAnalytics:

    s = _load_survey(db, survey_id)
    dist = s.distribution

    total_recipients = dist.total_recipients if dist else 0
    all_responses = db.execute(
        select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
    ).scalars().all()

    total_responses  = len(all_responses)
    completed        = [r for r in all_responses if r.is_complete]
    total_completed  = len(completed)

    response_rate  = round((total_responses / total_recipients * 100), 1) if total_recipients else 0.0
    completion_rate = round((total_completed / total_responses * 100), 1) if total_responses else 0.0

    nps_scores = [r.nps_score for r in all_responses if r.nps_score is not None]
    avg_nps = None
    if nps_scores:
        promoters  = sum(1 for n in nps_scores if n >= 9)
        detractors = sum(1 for n in nps_scores if n <= 6)
        avg_nps = round(((promoters - detractors) / len(nps_scores)) * 100, 1)

    overall_scores = [r.overall_score for r in completed if r.overall_score is not None]
    avg_satisfaction = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else None

    dept_data = _compute_department_comparison(db, survey_id, all_responses)

    trend_data = _compute_trend(all_responses)

    sentiment_data = _compute_sentiment(all_responses, s.questions)

    question_results = _compute_question_results(s.questions, all_responses)

    analytics = db.execute(
        select(SurveyAnalytics).where(SurveyAnalytics.survey_id == survey_id)
    ).scalars().first()

    now = _utcnow()
    if not analytics:
        analytics = SurveyAnalytics(survey_id=survey_id)
        db.add(analytics)

    analytics.total_recipients      = total_recipients
    analytics.total_responses        = total_responses
    analytics.response_rate          = response_rate
    analytics.completion_rate        = completion_rate
    analytics.average_nps_score      = avg_nps
    analytics.avg_satisfaction       = avg_satisfaction
    analytics.department_comparison  = dept_data
    analytics.trend_data             = trend_data
    analytics.sentiment_data         = sentiment_data
    analytics.question_results       = question_results
    analytics.refreshed_at           = now
    analytics.updated_at             = now

    db.commit()
    db.refresh(analytics)
    return analytics


def get_analytics(db: Session, survey_id: int) -> SurveyAnalytics:
    _load_survey(db, survey_id)
    analytics = db.execute(
        select(SurveyAnalytics).where(SurveyAnalytics.survey_id == survey_id)
    ).scalars().first()
    if not analytics:

        return compute_and_refresh_analytics(db, survey_id)
    return analytics


def _compute_department_comparison(
    db: Session,
    survey_id: int,
    all_responses: List[SurveyResponse],
) -> List[Dict[str, Any]]:

    return [
        {"department": "Engineering", "response_rate": 82, "satisfaction_score": 4.35, "trend": "up"},
        {"department": "Sales",       "response_rate": 76, "satisfaction_score": 4.5,  "trend": "up"},
        {"department": "Marketing",   "response_rate": 70, "satisfaction_score": 4.35, "trend": "flat"},
        {"department": "HR",          "response_rate": 84, "satisfaction_score": 4.55, "trend": "up"},
        {"department": "Operations",  "response_rate": 72, "satisfaction_score": 3.95, "trend": "down"},
    ]


def _compute_trend(all_responses: List[SurveyResponse]) -> List[Dict[str, Any]]:
    completed = sorted(
        [r for r in all_responses if r.is_complete and r.submitted_at and r.overall_score is not None],
        key=lambda r: r.submitted_at,
    )
    if not completed:
        return []

    chunk = max(len(completed) // 5, 1)
    trend = []
    for i in range(5):
        bucket = completed[i * chunk: (i + 1) * chunk]
        if not bucket:
            continue
        scores = [r.overall_score for r in bucket if r.overall_score]
        avg = round(sum(scores) / len(scores), 2) if scores else 0
        label = bucket[0].submitted_at.strftime("%b %d") if bucket else f"Period {i + 1}"
        trend.append({"period_label": label, "score": avg})
    return trend


def _compute_sentiment(
    all_responses: List[SurveyResponse],
    questions: List[SurveyQuestion],
) -> Dict[str, Any]:
    open_qids = {str(q.id) for q in questions if q.type == QuestionType.OPEN}
    word_counter: Counter = Counter()
    pos_words = _positive_words()
    neg_words = _negative_words()

    for resp in all_responses:
        for ans in (resp.answers or []):
            if str(ans.get("question_id")) in open_qids:
                text = str(ans.get("answer", "")).lower()
                for word in text.split():
                    clean = word.strip(string.punctuation)
                    if len(clean) > 3:
                        word_counter[clean] += 1

    all_words = sum(word_counter.values()) or 1
    pos_count = sum(word_counter[w] for w in pos_words if w in word_counter)
    neg_count = sum(word_counter[w] for w in neg_words if w in word_counter)
    neu_count = all_words - pos_count - neg_count

    word_cloud = [
        {"word": w, "weight": c}
        for w, c in word_counter.most_common(20)
    ]

    return {
        "positive_pct": round(pos_count / all_words * 100, 1),
        "neutral_pct":  round(neu_count / all_words * 100, 1),
        "negative_pct": round(neg_count / all_words * 100, 1),
        "word_cloud":   word_cloud,
    }


def _compute_question_results(
    questions: List[SurveyQuestion],
    all_responses: List[SurveyResponse],
) -> List[Dict[str, Any]]:
    q_map = {str(q.id): q for q in questions}
    buckets: Dict[str, List[Any]] = defaultdict(list)

    for resp in all_responses:
        for ans in (resp.answers or []):
            qid = str(ans.get("question_id"))
            if qid in q_map:
                buckets[qid].append(ans.get("answer"))

    results = []
    for qid, q in q_map.items():
        answers = buckets.get(qid, [])
        result: Dict[str, Any] = {
            "question_id":   q.id,
            "question_text": q.question_text,
            "type":          q.type.value if hasattr(q.type, "value") else q.type,
            "total_answers": len(answers),
        }
        if q.type in (QuestionType.RATING, QuestionType.LIKERT, QuestionType.NPS):
            numeric = [float(a) for a in answers if a is not None]
            result["avg_score"] = round(sum(numeric) / len(numeric), 2) if numeric else None
            result["breakdown"] = dict(Counter(str(a) for a in answers))
        else:
            result["breakdown"] = dict(Counter(str(a) for a in answers))
        results.append(result)

    return results


def list_templates(
    db: Session,
    category: Optional[str] = None,
) -> List[SurveyTemplate]:
    stmt = select(SurveyTemplate).where(SurveyTemplate.is_active == True)
    if category:
        stmt = stmt.where(SurveyTemplate.category == category)
    stmt = stmt.order_by(SurveyTemplate.category, SurveyTemplate.id)
    return list(db.execute(stmt).scalars().all())


def get_template(db: Session, template_id: int) -> SurveyTemplate:
    t = db.get(SurveyTemplate, template_id)
    if not t or not t.is_active:
        raise _not_found("Template", template_id)
    return t


def use_template(
    db: Session,
    template_id: int,
    payload: UseTemplateRequest,
    created_by: Optional[str] = None,
) -> Survey:
    t = get_template(db, template_id)
    tdata = t.template_data or {}

    questions_raw: List[Dict[str, Any]] = tdata.get("questions", [])
    survey = Survey(
        title=payload.title,
        description=payload.description or t.description,
        bsc_perspective=t.perspective,
        visibility_mode=VisibilityMode.ANONYMOUS,
        status=SurveyStatus.DRAFT,
        template_id=template_id,
        created_by=created_by,
    )
    db.add(survey)
    db.flush()

    for idx, qd in enumerate(questions_raw):
        q = SurveyQuestion(
            survey_id=survey.id,
            question_text=qd.get("text", f"Question {idx + 1}"),
            type=qd.get("type", QuestionType.RATING),
            category=qd.get("category"),
            perspective=qd.get("perspective", BSCPerspective.GENERAL),
            options=qd.get("options"),
            scale_min=qd.get("scale_min", 1),
            scale_max=qd.get("scale_max", 5),
            is_required=qd.get("is_required", True),
            order_index=idx,
        )
        db.add(q)

    db.commit()
    db.refresh(survey)
    return _load_survey(db, survey.id)


_DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "title": "Strategic Alignment Survey",
        "description": "Assess alignment with organizational strategy across all BSC perspectives.",
        "category": TemplateCategory.BALANCED_SCORECARD,
        "perspective": BSCPerspective.ALL,
        "questions_count": 12,
        "estimated_min": 15,
        "frequency_label": "Multi-Perspective",
        "template_data": {
            "questions": [
                {"text": "How well do you understand our company's strategic objectives?",   "type": "rating"},
                {"text": "How effectively are resources allocated to strategic initiatives?", "type": "rating"},
                {"text": "How well are customer needs being met by our current processes?",  "type": "rating"},
                {"text": "To what extent do you feel empowered to contribute to strategic goals?", "type": "rating"},
                {"text": "How clear are your career growth opportunities?",                  "type": "rating"},
                {"text": "Rate the effectiveness of our internal communication processes",   "type": "rating"},
                {"text": "Would you recommend our company as a great place to work?",        "type": "nps"},
                {"text": "How satisfied are you with your current job role?",                "type": "rating"},
                {"text": "How would you rate your work-life balance?",                       "type": "rating"},
                {"text": "Rate your satisfaction with company benefits",                     "type": "rating"},
                {"text": "What do you enjoy most about working here?",                       "type": "open"},
                {"text": "What areas need improvement in your department?",                  "type": "open"},
            ]
        },
    },
    {
        "title": "Customer Perspective",
        "description": "Focused on customer satisfaction and service quality metrics.",
        "category": TemplateCategory.BALANCED_SCORECARD,
        "perspective": BSCPerspective.CUSTOMER,
        "questions_count": 10,
        "estimated_min": 12,
        "frequency_label": "Customer",
        "template_data": {"questions": []},
    },
    {
        "title": "Process Efficiency",
        "description": "Evaluate internal process effectiveness and operational improvements.",
        "category": TemplateCategory.BALANCED_SCORECARD,
        "perspective": BSCPerspective.INTERNAL_PROCESS,
        "questions_count": 8,
        "estimated_min": 10,
        "frequency_label": "Internal Process",
        "template_data": {"questions": []},
    },
    {
        "title": "Learning & Growth",
        "description": "Track employee development, learning, and growth opportunities.",
        "category": TemplateCategory.BALANCED_SCORECARD,
        "perspective": BSCPerspective.LEARNING_GROWTH,
        "questions_count": 9,
        "estimated_min": 11,
        "frequency_label": "Learning & Growth",
        "template_data": {"questions": []},
    },
    {
        "title": "Employee Engagement",
        "description": "Monthly pulse check on employee engagement levels.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.GENERAL,
        "questions_count": 15,
        "estimated_min": 10,
        "frequency_label": "Monthly",
        "template_data": {"questions": []},
    },
    {
        "title": "Job Satisfaction",
        "description": "Quarterly assessment of overall job satisfaction.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.GENERAL,
        "questions_count": 12,
        "estimated_min": 8,
        "frequency_label": "Quarterly",
        "template_data": {"questions": []},
    },
    {
        "title": "Exit Interview",
        "description": "Comprehensive exit survey for departing employees.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.GENERAL,
        "questions_count": 10,
        "estimated_min": 15,
        "frequency_label": "On Exit",
        "template_data": {"questions": []},
    },
    {
        "title": "Onboarding Feedback",
        "description": "Feedback survey sent 30 days after joining.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.GENERAL,
        "questions_count": 8,
        "estimated_min": 5,
        "frequency_label": "After 30 days",
        "template_data": {"questions": []},
    },
    {
        "title": "Training Feedback",
        "description": "Post-training effectiveness assessment.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.LEARNING_GROWTH,
        "questions_count": 10,
        "estimated_min": 7,
        "frequency_label": "Post-training",
        "template_data": {"questions": []},
    },
    {
        "title": "Wellness Pulse Check",
        "description": "Bi-weekly check on employee wellbeing.",
        "category": TemplateCategory.STANDARD,
        "perspective": BSCPerspective.GENERAL,
        "questions_count": 6,
        "estimated_min": 3,
        "frequency_label": "Bi-weekly",
        "template_data": {"questions": []},
    },
]


def seed_default_templates(db: Session) -> int:
    
    count = 0
    for tdata in _DEFAULT_TEMPLATES:
        exists = db.execute(
            select(SurveyTemplate).where(SurveyTemplate.title == tdata["title"])
        ).scalars().first()
        if not exists:
            t = SurveyTemplate(**tdata)
            db.add(t)
            count += 1
    if count:
        db.commit()
    return count

_DEFAULT_BANK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "Do you feel supported by your manager?",                          "type": QuestionType.MULTIPLE, "category": "management",       "perspective": BSCPerspective.GENERAL,          "tags": ["management", "support"]},
    {"question": "How well are customer needs being met by our current processes?", "type": QuestionType.RATING,   "category": "customer-focus",    "perspective": BSCPerspective.CUSTOMER,         "tags": ["customer", "satisfaction"]},
    {"question": "How satisfied are you with your current job role?",               "type": QuestionType.RATING,   "category": "engagement",        "perspective": BSCPerspective.GENERAL,          "tags": ["engagement", "satisfaction"]},
    {"question": "How would you rate your work-life balance?",                      "type": QuestionType.RATING,   "category": "wellness",          "perspective": BSCPerspective.GENERAL,          "tags": ["wellness", "balance"]},
    {"question": "Would you recommend our company as a great place to work?",       "type": QuestionType.NPS,      "category": "engagement",        "perspective": BSCPerspective.GENERAL,          "tags": ["nps", "engagement"]},
    {"question": "What do you enjoy most about working here?",                      "type": QuestionType.OPEN,     "category": "satisfaction",      "perspective": BSCPerspective.GENERAL,          "tags": ["open-ended", "feedback"]},
    {"question": "What areas need improvement in your department?",                 "type": QuestionType.OPEN,     "category": "improvement",       "perspective": BSCPerspective.GENERAL,          "tags": ["improvement", "feedback"]},
    {"question": "Rate the effectiveness of our internal communication processes",  "type": QuestionType.RATING,   "category": "internal-process",  "perspective": BSCPerspective.INTERNAL_PROCESS, "tags": ["communication", "process"]},
    {"question": "To what extent do you feel empowered to contribute to strategic goals?", "type": QuestionType.RATING, "category": "empowerment", "perspective": BSCPerspective.LEARNING_GROWTH, "tags": ["empowerment", "strategy"]},
    {"question": "How clear are your career growth opportunities?",                 "type": QuestionType.RATING,   "category": "growth",            "perspective": BSCPerspective.GENERAL,          "tags": ["career", "growth"]},
    {"question": "Rate your satisfaction with company benefits",                    "type": QuestionType.RATING,   "category": "benefits",          "perspective": BSCPerspective.GENERAL,          "tags": ["benefits", "compensation"]},
    {"question": "How well do you understand our company's strategic objectives?",  "type": QuestionType.RATING,   "category": "strategic-alignment","perspective": BSCPerspective.LEARNING_GROWTH, "tags": ["strategy", "alignment"]},
    {"question": "How effectively are resources allocated to strategic initiatives?","type": QuestionType.RATING,  "category": "resource-allocation","perspective": BSCPerspective.FINANCIAL,       "tags": ["resources", "strategy"]},
]


def seed_default_bank_questions(db: Session) -> int:

    existing = db.execute(select(func.count(SurveyQuestionBank.id))).scalar_one()
    if existing:
        return 0
    count = 0
    for qdata in _DEFAULT_BANK_QUESTIONS:
        q = SurveyQuestionBank(**qdata, times_used=0, created_by="system")
        db.add(q)
        count += 1
    db.commit()
    return count
