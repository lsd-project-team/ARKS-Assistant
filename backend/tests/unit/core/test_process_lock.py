import pytest

from app.core.process_lock import service_lock


def test_data_directory_has_single_writer(tmp_path):
    with service_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with service_lock(tmp_path):
                pass
    with service_lock(tmp_path):
        pass
