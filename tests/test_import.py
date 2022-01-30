import logging

def test_import_works():
    import typeforce.enforcing
    assert typeforce.enforcing


def test_import_bad_fails():
    import typeforce.enforcing
    assert typeforce.enforcing
    try:
        import bad_test_case
    except ImportError as ex:
        if "No module named" in str(ex):
            raise ex
        pass
    else:
        raise Exception("Should have import error from bad_test_case")


def test_import_good_succeeds():
    import typeforce.enforcing
    assert typeforce.enforcing
    import good_test_case
    assert good_test_case.returns_int(5) == 5
