import os
import os.path
import gzip
import threading
import time

import pytest
from smb.base import SMBTimeout

import pyndows
from pyndows.testing import samba_mock, SMBConnectionMock


def test_remaining_files_to_retrieve_when_reset():
    pyndows.testing.SMBConnectionMock.files_to_retrieve["tests"] = "Test"
    with pytest.raises(Exception) as exception_info:
        pyndows.testing.SMBConnectionMock.reset()
    assert (
        str(exception_info.value)
        == "Expected files were not retrieved: {'tests': 'Test'}"
    )


def test_remaining_storeFile_exceptions_when_reset():
    pyndows.testing.SMBConnectionMock.storeFile_exceptions.append(SMBTimeout)
    with pytest.raises(Exception) as exception_info:
        pyndows.testing.SMBConnectionMock.reset()
    assert (
        str(exception_info.value)
        == "storeFile exceptions were not triggered: [<class 'smb.base.SMBTimeout'>]"
    )


def test_remaining_echo_responses_when_reset():
    pyndows.testing.SMBConnectionMock.echo_responses["tests"] = "Test"
    with pytest.raises(Exception) as exception_info:
        pyndows.testing.SMBConnectionMock.reset()
    assert str(exception_info.value) == "Echo were not requested: {'tests': 'Test'}"


def test_connection_can_be_used_as_context_manager(samba_mock: SMBConnectionMock):
    with pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    ):
        pass


def test_non_text_file_can_be_stored(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    with gzip.open(os.path.join(tmpdir, "local_file"), mode="w") as distant_file:
        distant_file.write(b"Test Content Move")

    pyndows.move(
        connection, "TestShare", "TestFilePath", os.path.join(tmpdir, "local_file")
    )

    assert (
        gzip.decompress(samba_mock.stored_files[("TestShare", "TestFilePath")])
        == b"Test Content Move"
    )


def test_async_retrieval(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    with gzip.open(os.path.join(tmpdir, "local_file"), mode="w") as distant_file:
        distant_file.write(b"Test Content Move")

    def add_with_delay(delay: int):
        time.sleep(delay)
        pyndows.move(
            connection, "TestShare", "TestFilePath", os.path.join(tmpdir, "local_file")
        )

    threading.Thread(target=add_with_delay, args=(2,)).start()

    assert (
        gzip.decompress(
            samba_mock.stored_files.try_get(("TestShare", "TestFilePath"), timeout=3)
        )
        == b"Test Content Move"
    )


def test_async_retrieval_timeout(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    with gzip.open(os.path.join(tmpdir, "local_file"), mode="w") as distant_file:
        distant_file.write(b"Test Content Move")

    def add_with_delay(delay: int):
        time.sleep(delay)
        pyndows.move(
            connection, "TestShare", "TestFilePath", os.path.join(tmpdir, "local_file")
        )

    threading.Thread(target=add_with_delay, args=(2,)).start()

    with pytest.raises(TimeoutError) as exception_info:
        samba_mock.stored_files.try_get(("TestShare", "TestFilePath"))
    assert (
        str(exception_info.value)
        == "('TestShare', 'TestFilePath') could not be found within 1 seconds."
    )


def test_file_retrieval_using_path(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    with gzip.open(os.path.join(tmpdir, "local_file"), mode="w") as distant_file:
        distant_file.write(b"Test Content")
    samba_mock.files_to_retrieve[("TestShare", "TestFilePath")] = os.path.join(
        tmpdir, "local_file"
    )

    pyndows.get(
        connection,
        "TestShare",
        "TestFilePath",
        os.path.join(tmpdir, "local_file_retrieved"),
    )
    with gzip.open(os.path.join(tmpdir, "local_file_retrieved")) as local_file:
        assert local_file.read() == b"Test Content"


def test_file_retrieval_using_str_content(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    samba_mock.files_to_retrieve[("TestShare", "TestFilePath")] = "data"

    pyndows.get(
        connection,
        "TestShare",
        "TestFilePath",
        os.path.join(tmpdir, "local_file_retrieved"),
    )
    with open(os.path.join(tmpdir, "local_file_retrieved"), "rt") as local_file:
        assert local_file.read() == "data"


def test_file_retrieval_using_bytes_content(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    bytes_content_file_path = os.path.join(tmpdir, "local_file")
    with gzip.open(bytes_content_file_path, mode="w") as distant_file:
        distant_file.write(b"Test Content")
    samba_mock.files_to_retrieve[("TestShare", "TestFilePath")] = open(
        bytes_content_file_path, "rb"
    ).read()

    pyndows.get(
        connection,
        "TestShare",
        "TestFilePath",
        os.path.join(tmpdir, "local_file_retrieved"),
    )
    with gzip.open(os.path.join(tmpdir, "local_file_retrieved")) as local_file:
        assert local_file.read() == b"Test Content"


def test_retrieval_of_stored_non_text_file(samba_mock: SMBConnectionMock, tmpdir):
    connection = pyndows.connect(
        "TestComputer", "127.0.0.1", 80, "TestDomain", "TestUser", "TestPassword"
    )
    with gzip.open(os.path.join(tmpdir, "local_file"), mode="w") as distant_file:
        distant_file.write(b"Test Content Move")

    pyndows.move(
        connection, "TestShare", "TestFilePath", os.path.join(tmpdir, "local_file")
    )

    pyndows.get(
        connection,
        "TestShare",
        "TestFilePath",
        os.path.join(tmpdir, "local_file_retrieved"),
    )

    with gzip.open(os.path.join(tmpdir, "local_file_retrieved")) as local_file:
        assert local_file.read() == b"Test Content Move"

    assert (
        gzip.decompress(samba_mock.stored_files[("TestShare", "TestFilePath")])
        == b"Test Content Move"
    )
