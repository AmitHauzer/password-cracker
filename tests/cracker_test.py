from src.pass_cracker.cracker_core import phone_iter, md5_of, crack_range
import logging

logging.basicConfig(
    level=logging.DEBUG,  # set to INFO in real runs to reduce noise
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def test_phone_iter_first_last():
    it = phone_iter()
    assert next(it) == "0500000000"
    # jump near the end without iterating 100 M times
    last = f"05{99_999_999:08d}"
    assert last == "0599999999"


def test_md5_vector():
    assert md5_of("0500000000") == "06aea034b6c8bedc0bed8c4601af45b3"


def test_crack_success_and_fail():
    target = md5_of("0599999999")
    assert crack_range(target, 99_999_999, 99_999_999) == "0599999999"
    assert crack_range(target, 0, 1_000) is None
