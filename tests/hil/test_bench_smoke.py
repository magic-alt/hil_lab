import pytest


@pytest.mark.hil
def test_physical_resource_has_fieldbus_interface(hil_resource):
    assert hil_resource.fieldbus_interface
