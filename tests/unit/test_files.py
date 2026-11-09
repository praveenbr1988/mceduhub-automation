from mceduhub.utils.files import DownloadLedger, remove_files, safe_name


def test_safe_name_matches_existing_output_folders():
    assert safe_name("Cambridge Primary English Teacher's Guide 1") == "Cambridge Primary English Teacher_s Guide 1"
    assert safe_name("Science (iframe)") == "Science _iframe_"
    assert safe_name("   ") == "book"


def test_ledger_persists_between_instances(tmp_path):
    ledger = DownloadLedger(tmp_path)
    ledger.add("a.zip")
    ledger.add("a.zip")  # duplicates ignored
    ledger.add("b.zip")

    reloaded = DownloadLedger(tmp_path)
    assert "a.zip" in reloaded and "b.zip" in reloaded
    assert len(reloaded) == 2
    assert (tmp_path / ".downloaded.txt").read_text().splitlines() == ["a.zip", "b.zip"]


def test_remove_files_deletes_matches_and_empty_folder(tmp_path):
    folder = tmp_path / "book"
    folder.mkdir()
    for i in range(3):
        (folder / f"page_{i}.jpg").write_bytes(b"x")
    assert remove_files(folder, "page_*.jpg") == 3
    assert not folder.exists()


def test_remove_files_keeps_folder_with_other_files(tmp_path):
    (tmp_path / "page_1.jpg").write_bytes(b"x")
    (tmp_path / "keep.txt").write_text("x")
    remove_files(tmp_path, "page_*.jpg")
    assert tmp_path.exists() and (tmp_path / "keep.txt").exists()
