import os

from tautulli import empty_trash


def test_empty_trash():
    """Test that empty_trash removes directory and everything inside."""
    # first, create a directory with mixed contents
    os.mkdir(os.path.join("tests", "trash"))
    with open(os.path.join("tests", "trash", "test_file.txt"), "w") as test_file:
        test_file.write("some data")
    os.mkdir(os.path.join("tests", "trash", "subdir"))
    with open(
        os.path.join("tests", "trash", "subdir", "another_file.txt"), "w"
    ) as another_file:
        another_file.write("some more data")
    os.mkdir(os.path.join("tests", "trash2"))
    with open(os.path.join("tests", "trash2", "dif_dir_file.txt"), "w") as dif_dir_file:
        dif_dir_file.write("text")

    assert os.path.exists(os.path.join("tests", "trash", "test_file.txt"))
    assert os.path.exists(os.path.join("tests", "trash", "subdir", "another_file.txt"))
    assert os.path.exists(os.path.join("tests", "trash2", "dif_dir_file.txt"))

    empty_trash(["tests/trash", "tests/trash2"])

    assert not os.path.exists(os.path.join("tests", "trash"))
    assert not os.path.exists(os.path.join("tests", "trash2"))
