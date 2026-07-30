"""Sửa lỗi chất lượng: nhầm tên (false match), guardrail rò, nhận diện help."""
from app.services.guardrails import is_help_request, is_in_scope
from app.services.text_utils import find_staff


# 1) Không false-match khi họ+đệm trùng nhưng TÊN khác
def test_no_false_match_on_family_middle_only():
    # "Phan Minh <tên giả>" không được khớp Phan Minh Hoàng (vì thiếu 'Hoàng')
    assert find_staff("task của Phan Minh Xyzzy") != "Phan Minh Hoàng"


def test_still_matches_when_given_name_present():
    assert find_staff("task của Minh Hoàng") == "Phan Minh Hoàng"
    assert find_staff("task của Phan Minh Hoàng") == "Phan Minh Hoàng"


# 2) Guardrail không lọt câu ngoài phạm vi vì khớp chuỗi con tên người
def test_guardrail_blocks_cooking_question():
    assert is_in_scope("cách nấu phở bò ngon") is False


def test_guardrail_allows_real_task_question():
    assert is_in_scope("task của Phan Minh Hoàng") is True
    assert is_in_scope("Phan Minh Hoàng") is True
    assert is_in_scope("task đang làm") is True


# 3) Nhận diện câu hỏi trợ giúp
def test_help_detection():
    assert is_help_request("bạn giúp được gì") is True
    assert is_help_request("bạn hỗ trợ được gì") is True
