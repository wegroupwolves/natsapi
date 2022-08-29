from natsapi.asyncapi.models import RequestOperation


def test_suggested_timeout_should_generate_timeout():
    expected = {"x-suggested-timeout": 0.5}
    actual = RequestOperation(**expected)
    assert actual.suggestedTimeout == expected["x-suggested-timeout"]
