import pytest

from ptrack.config import ConfigError, Settings, describe, load


def write(tmp_path, text):
    path = tmp_path / "ptrack.toml"
    path.write_text(text)
    return path


def test_defaults_without_a_file(tmp_path):
    assert load(tmp_path / "missing.toml", env={}) == Settings()


def test_reads_sections(tmp_path):
    path = write(tmp_path, """
[server]
host = "0.0.0.0"
port = 9000
[database]
url = "sqlite:////srv/ptrack/ptrack.db"
[accounts]
device_idle_days = 90
login_delay_seconds = 2
""")
    s = load(path, env={})
    assert (s.host, s.port, s.database_url, s.device_idle_days, s.login_delay_seconds) == (
        "0.0.0.0", 9000, "sqlite:////srv/ptrack/ptrack.db", 90, 2)


def test_environment_overrides_the_file(tmp_path):
    path = write(tmp_path, '[database]\nurl = "sqlite:///from-file.db"\n')
    assert load(path, env={"PTRACK_DB": "sqlite:///from-env.db"}).database_url == "sqlite:///from-env.db"


@pytest.mark.parametrize("text", [
    "[server]\nprot = 8000\n",           # typo
    "[srever]\nport = 8000\n",           # unknown section
    "[server]\nport = \"8000\"\n",       # wrong type
    "[accounts]\ndevice_idle_days = -1\n",
    "[server\nport = 1\n",              # not TOML
])
def test_mistakes_are_errors(tmp_path, text):
    with pytest.raises(ConfigError):
        load(write(tmp_path, text), env={})


def test_describe_round_trips(tmp_path):
    s = Settings(host="0.0.0.0", device_idle_days=30)
    assert load(write(tmp_path, describe(s)), env={}) == s
