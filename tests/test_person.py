from datetime import date

import pytest

from domain.case import Case
from domain.firm import LawFirm
from domain.person import Admin, Client, Lawyer, Manager, Person, SystemUser


def test_person_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        Person(name="สมชาย", citizen_id="1", phone="080")


def test_display_name_is_polymorphic_without_type_checks():
    people = [
        Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1"),
        Client(name="สมหญิง", citizen_id="2", phone="081"),
        Client(name="ตัวแทนบริษัท", citizen_id="3", phone="082", company="บจก. ทดสอบ"),
    ]

    names = [p.display_name() for p in people]

    assert names == ["ทนายสมชาย", "สมหญิง", "บจก. ทดสอบ"]


def test_contact_info_shared_on_base_class():
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    assert lawyer.contact_info() == "สมชาย (080)"


def test_id_defaults_to_none_until_repository_sets_it():
    client = Client(name="สมหญิง", citizen_id="2", phone="081")
    assert client.id is None


def make_case():
    return Case(
        title="ผิดสัญญาซื้อขาย",
        client=Client(name="สมหญิง", citizen_id="2", phone="081"),
        client_role="โจทก์",
        opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่งกรุงเทพใต้",
        opened_date=date(2026, 1, 1),
    )


def test_system_user_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        SystemUser(name="x", citizen_id="1", phone="080")


def test_can_view_case_is_polymorphic_without_type_checks():
    case = make_case()
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    other_lawyer = Lawyer(name="สมศักดิ์", citizen_id="3", phone="082", license_no="L2")
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="4", phone="083")
    admin = Admin(name="แอดมิน", citizen_id="5", phone="084")

    firm = LawFirm()
    firm.open_case(case)
    firm.assign_lawyer(case, lawyer, assigned_by=manager).accept()

    users = [lawyer, other_lawyer, manager, admin]
    results = [u.can_view_case(case) for u in users]

    assert results == [True, False, True, False]


def test_lawyer_workload_combines_case_and_appointment_counts():
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    assert lawyer.workload(cases=[object(), object()], appointments=[object()]) == 3
