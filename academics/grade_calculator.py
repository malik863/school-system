from collections import OrderedDict
from decimal import Decimal

from assessments.models import Grade
from attendance.models import Attendance
from academics.models import AcademicSchemeRule
from schools.models import Term

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _grades(student, academic_year=None, term=None, subject=None, classroom=None):
    qs = Grade.objects.filter(school=student.school, student=student).select_related(
        "assessment", "assessment__subject", "assessment__term", "assessment__term__academic_year"
    )
    if academic_year is not None:
        qs = qs.filter(assessment__term__academic_year=academic_year)
    if term is not None:
        qs = qs.filter(assessment__term=term)
    if subject is not None:
        qs = qs.filter(assessment__subject=subject)
    if classroom is not None:
        qs = qs.filter(assessment__classroom=classroom)
    return qs


def _attendance_percentage(student, term=None, academic_year=None):
    qs = Attendance.objects.filter(school=student.school, student=student)
    if term is not None:
        qs = qs.filter(term=term)
    elif academic_year is not None:
        qs = qs.filter(term__academic_year=academic_year)
    total = qs.count()
    if not total:
        return None
    # Present and late count as attended. Excused/absent do not earn attendance marks.
    attended = qs.filter(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE, Attendance.Status.EXCUSED]).count()
    return Decimal(attended) / Decimal(total) * HUNDRED



def attendance_percentage(student, term=None, academic_year=None):
    """Public attendance percentage for certificate/report display."""
    return _attendance_percentage(student, term=term, academic_year=academic_year)


def attendance_grade_result(student, classroom, term=None, academic_year=None):
    """Return the attendance contribution defined by the classroom scheme.

    For an academic year, each term is calculated independently so a scheme
    attendance weight of 10 contributes up to 10 marks per term.
    """
    scheme = _scheme_for(classroom)
    if not scheme:
        return {"score": ZERO, "max_score": ZERO, "percentage": None}
    rule = scheme.rules.filter(
        assessment_type=AcademicSchemeRule.AssessmentType.ATTENDANCE
    ).first()
    if not rule:
        return {"score": ZERO, "max_score": ZERO, "percentage": None}

    periods = [term] if term is not None else list(terms_for_year(student.school, academic_year))
    score = ZERO
    maximum = ZERO
    for period in periods:
        pct = _attendance_percentage(student, term=period)
        if pct is None:
            continue
        score += pct * rule.weight / HUNDRED
        maximum += rule.weight
    percentage = score / maximum * HUNDRED if maximum else None
    return {"score": score, "max_score": maximum, "percentage": percentage}

def _scheme_for(classroom):
    return classroom.academic_schemes.first() if classroom else None


def _weighted_term_result(student, term, subject=None, classroom=None):
    scheme = _scheme_for(classroom)
    if not scheme:
        return _raw_totals(_grades(student, term=term, subject=subject, classroom=classroom))

    score = ZERO
    maximum = ZERO
    rules = scheme.rules.all()
    for rule in rules:
        if rule.assessment_type == AcademicSchemeRule.AssessmentType.ATTENDANCE:
            pct = _attendance_percentage(student, term=term)
            if pct is not None:
                score += pct * rule.weight / HUNDRED
                maximum += rule.weight
            continue

        grades = _grades(student, term=term, subject=subject, classroom=classroom).filter(
            assessment__assessment_type=rule.assessment_type
        )
        raw = _raw_totals(grades)
        if raw["max_score"]:
            score += raw["percentage"] * rule.weight / HUNDRED
            maximum += rule.weight

    percentage = score / maximum * HUNDRED if maximum else None
    return {"score": score, "max_score": maximum, "percentage": percentage}


def _raw_totals(grades):
    score = ZERO
    maximum = ZERO
    for grade in grades:
        score += grade.score
        maximum += grade.assessment.max_score
    percentage = score / maximum * HUNDRED if maximum else None
    return {"score": score, "max_score": maximum, "percentage": percentage}


def totals(grades):
    return _raw_totals(grades)


def student_term_result(student, term, subject=None, classroom=None):
    return _weighted_term_result(student, term, subject=subject, classroom=classroom)


def student_year_result(student, academic_year, subject=None, classroom=None):
    score = ZERO
    maximum = ZERO
    for term in terms_for_year(student.school, academic_year):
        result = student_term_result(student, term, subject=subject, classroom=classroom)
        score += result["score"]
        maximum += result["max_score"]
    percentage = score / maximum * HUNDRED if maximum else None
    return {"score": score, "max_score": maximum, "percentage": percentage}


def student_subject_breakdown(student, academic_year, classroom=None):
    grades = _grades(student, academic_year=academic_year, classroom=classroom).order_by(
        "assessment__subject__name", "assessment__term__start_date", "assessment__date", "assessment__id"
    )
    data = OrderedDict()
    for grade in grades:
        subject = grade.assessment.subject
        item = data.setdefault(subject.id, {"subject": subject, "terms": OrderedDict(), "year": None})
        term = grade.assessment.term
        term_item = item["terms"].setdefault(term.id, {"term": term, "grades": [], "result": None})
        term_item["grades"].append(grade)
    for item in data.values():
        for term_item in item["terms"].values():
            term_item["result"] = student_term_result(student, term_item["term"], subject=item["subject"], classroom=classroom)
        item["year"] = student_year_result(student, academic_year, subject=item["subject"], classroom=classroom)
    return list(data.values())


def school_period_average(school, students, academic_year, term=None):
    score = ZERO
    maximum = ZERO
    for student in students:
        result = (student_term_result(student, term, classroom=student.classroom) if term else
                  student_year_result(student, academic_year, classroom=student.classroom))
        score += result["score"]
        maximum += result["max_score"]
    return score / maximum * HUNDRED if maximum else None


def terms_for_year(school, academic_year):
    return Term.objects.filter(school=school, academic_year=academic_year).order_by("start_date", "id")
