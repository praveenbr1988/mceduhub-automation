from mceduhub.models import ResourceFile
from mceduhub.utils.filters import select_resource_files


def names(files):
    return [f.name for f in files]


def test_default_policy_selects_resource_zips_without_audio(teacher_guide_files):
    selected, excluded = select_resource_files(
        teacher_guide_files, ["Teacher's Resources"], [".zip"], ["audio"]
    )
    assert names(selected) == [
        "1 Cambridge PRI ENG TG4 TG.zip",
        "5 Cambridge PRI ENG SB4 WB4 Suggested Answers.zip",
        "6 Cambridge PRI ENG S4 Exam Papers.zip",
    ]
    assert len(excluded) == 4


def test_empty_filters_select_everything(teacher_guide_files):
    selected, excluded = select_resource_files(teacher_guide_files)
    assert len(selected) == len(teacher_guide_files)
    assert excluded == []


def test_curly_apostrophe_in_section_heading_still_matches():
    files = [ResourceFile(0, "a.zip", "Teacher’s Resources")]
    selected, _ = select_resource_files(files, ["Teacher's Resources"])
    assert names(selected) == ["a.zip"]


def test_exclusion_reasons(teacher_guide_files):
    _, excluded = select_resource_files(teacher_guide_files, ["Teacher's Resources"], [".zip"], ["audio"])
    reasons = {f.name: reason for f, reason in excluded}
    assert reasons["Cambridge PRI ENG SB4 Audio.zip"] == "name filter"
    assert reasons["Cambridge PRI ENG TG4 BLM.pdf"].startswith("section")
