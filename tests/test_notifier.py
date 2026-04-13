import pytest
from unittest.mock import patch, MagicMock
from cronwatcher.notifier import Notifier, NotifierConfig


@pytest.fixture
def notifier_config():
    return NotifierConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        sender="alerts@example.com",
        recipient="admin@example.com",
        username="alerts@example.com",
        password="secret",
        use_tls=True,
    )


@pytest.fixture
def notifier(notifier_config):
    return Notifier(notifier_config)


@patch("cronwatcher.notifier.smtplib.SMTP")
def test_send_alert_success(mock_smtp, notifier):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = notifier.send_alert("Test Subject", "Test body")

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("alerts@example.com", "secret")
    mock_server.sendmail.assert_called_once()


@patch("cronwatcher.notifier.smtplib.SMTP")
def test_send_alert_smtp_failure(mock_smtp, notifier):
    import smtplib
    mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPException("connection refused")

    result = notifier.send_alert("Test Subject", "Test body")

    assert result is False


@patch.object(Notifier, "send_alert", return_value=True)
def test_notify_failure_calls_send_alert(mock_send, notifier):
    result = notifier.notify_failure("backup-job", error="exit code 1")

    assert result is True
    call_args = mock_send.call_args
    assert "backup-job" in call_args[0][0]
    assert "FAILED" in call_args[0][0]
    assert "exit code 1" in call_args[0][1]


@patch.object(Notifier, "send_alert", return_value=True)
def test_notify_missed_calls_send_alert(mock_send, notifier):
    result = notifier.notify_missed("cleanup-job", "0 2 * * *")

    assert result is True
    call_args = mock_send.call_args
    assert "cleanup-job" in call_args[0][0]
    assert "MISSED" in call_args[0][0]
    assert "0 2 * * *" in call_args[0][1]


@patch("cronwatcher.notifier.smtplib.SMTP")
def test_no_tls_no_login_when_disabled(mock_smtp, notifier_config):
    notifier_config.use_tls = False
    notifier_config.username = None
    notifier_config.password = None
    notifier = Notifier(notifier_config)

    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = notifier.send_alert("Hi", "body")

    assert result is True
    mock_server.starttls.assert_not_called()
    mock_server.login.assert_not_called()
