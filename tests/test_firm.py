from datetime import date

import pytest

from domain.case import Case
from domain.firm import LawFirm
from domain.person import Client, Lawyer, Manager


def make_case(**overrides):
    defaults = dict(
        title="ผิดสัญญาซื้อขาย",
        client=Client(name="สมหญิง", citizen_id="2", phone="081"),
        client_role="โจทก์",
        opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่งกรุงเทพใต้",
        opened_date=date(2026, 1, 1),
    )
    defaults.update(overrides)
    return Case(**defaults)


def test_find_by_case_no_matches_black_or_red_number():
    firm = LawFirm()
    case = make_case(black_case_no="1234/2568", red_case_no="99/2569")
    firm.open_case(case)

    assert firm.find_by_case_no("1234/2568") is case
    assert firm.find_by_case_no("99/2569") is case
    assert firm.find_by_case_no("ไม่มีจริง") is None


def test_search_by_case_no_first():
    firm = LawFirm()
    case = make_case(black_case_no="1234/2568")
    firm.open_case(case)

    assert firm.search("1234/2568") == [case]


def test_search_falls_back_to_title_client_and_opposing_party():
    firm = LawFirm()
    target = make_case(
        title="ฟ้องเรียกค่าเสียหาย",
        client=Client(name="วิชัย ใจดี", citizen_id="9", phone="080"),
        opposing_party="บจก. เอบีซี",
    )
    other = make_case(title="คดีอื่นไม่เกี่ยวข้อง")
    firm.open_case(target)
    firm.open_case(other)

    assert firm.search("วิชัย") == [target]
    assert firm.search("เอบีซี") == [target]
    assert firm.search("เรียกค่าเสียหาย") == [target]


def test_assign_lawyer_supports_three_lawyers_with_lead():
    # BL-14 (many-to-many + 1 lead) หลัง BL-24: lawyers()/lead_lawyer() นับเฉพาะที่ ACCEPTED แล้ว
    firm = LawFirm()
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lead = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    second = Lawyer(name="สมศักดิ์", citizen_id="3", phone="082", license_no="L2")
    third = Lawyer(name="สมหมาย", citizen_id="4", phone="083", license_no="L3")

    firm.assign_lawyer(case, lead, assigned_by=manager, is_lead=True).accept()
    firm.assign_lawyer(case, second, assigned_by=manager).accept()
    firm.assign_lawyer(case, third, assigned_by=manager).accept()

    assert len(case.lawyers()) == 3
    assert case.lead_lawyer() is lead


def test_assign_lawyer_only_counts_accepted_ones():
    firm = LawFirm()
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")

    firm.assign_lawyer(case, lawyer, assigned_by=manager)  # ยังไม่กดรับ

    assert case.lawyers() == []
    assert case.lead_lawyer() is None
