import pytest

from sports_data import StumpsProvider


def test_stumps_provider_parses_public_line_based_scorecard():
    provider = StumpsProvider("-OiyGifAxdcSXcSbbE5m")
    html = """
    <html><body>
      <h1>dark knight</h1>
      <div>Eagles vs Titans</div>
      <div>Score</div><div>142/3</div>
      <div>Overs</div><div>18.4 overs</div>
      <div>Striker</div><div>V. Kohli</div>
      <div>Non-Striker</div><div>R. Sharma</div>
      <div>Bowler</div><div>S. Yadav</div>
      <div>Recent Balls</div><div>1 4 6</div>
      <div>Event</div><div>SIX</div>
    </body></html>
    """
    payload = provider._parse_team_page(html)
    assert payload["team_name"] == "dark knight"
    assert payload["live_data_available"] is True
    match = payload["match"]
    assert match["team_home"] == "Eagles"
    assert match["team_away"] == "Titans"
    assert match["score"] == "142"
    assert match["wickets"] == "3"
    assert match["overs"] == "18.4"
    assert match["striker"] == "V. Kohli"
    assert match["non_striker"] == "R. Sharma"
    assert match["bowler"] == "S. Yadav"
    assert match["recent_balls"] == ["1", "4", "6"]
    assert match["event"] == "SIX"


def test_stumps_provider_uses_embedded_next_data_when_present():
    provider = StumpsProvider("team-1")
    html = """
    <html><head></head><body>
      <script id="__NEXT_DATA__" type="application/json">
      {
        "props": {
          "pageProps": {
            "match": {
              "id": "m123",
              "title": "Eagles vs Titans",
              "score": "142/3",
              "overs": "18.4",
              "striker": "V. Kohli",
              "nonstriker": "R. Sharma",
              "bowler": "S. Yadav",
              "recent_balls": ["1", "4", "6"],
              "event": "SIX"
            }
          }
        }
      }
      </script>
    </body></html>
    """
    payload = provider._parse_team_page(html)
    assert payload["live_data_available"] is True
    assert payload["match"]["match_id"] == "m123"
    assert payload["match"]["team_home"] == "Eagles"
    assert payload["match"]["team_away"] == "Titans"


@pytest.mark.asyncio
async def test_detect_stumps_status_returns_limitation_on_fetch_error(monkeypatch):
    provider = StumpsProvider("team-1")

    async def fail(url: str):
        raise RuntimeError("network down")

    monkeypatch.setattr(provider, "_fetch_text", fail)
    result = await provider.get_status()
    assert result.connected is False
    assert "network down" in str(result.limitation)
