from app.models import ManualSource, User
from app.services.management_service import create_adjustment, create_manual_playtime, set_absolute_total
from app.services.playtime import total_seconds_for_user_game


def test_historical_automatic_adjustment_total(db_session):
    user = User(guild_id=1, discord_user_id=111, username="john", display_name="John")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Game id 1 is created in each test case for simplicity.
    from app.models import Game, ActivitySession
    from datetime import datetime, timedelta, timezone

    game = Game(normalized_name="minecraft", display_name="Minecraft")
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, user.id, game.id, 1240 * 3600, ManualSource.historical, "initial", 1)

    start = datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc)
    db_session.add(ActivitySession(guild_id=1, user_id=user.id, game_id=game.id, started_at=start, ended_at=start + timedelta(hours=6)))
    db_session.commit()

    create_adjustment(db_session, 1, user.id, game.id, 1800, "missing session", 1)

    assert total_seconds_for_user_game(db_session, 1, user.id, game.id) == (1240 + 6) * 3600 + 1800


def test_prevent_negative_total(db_session):
    from app.models import Game

    user = User(guild_id=1, discord_user_id=222, username="sarah", display_name="Sarah")
    game = Game(normalized_name="valorant", display_name="VALORANT")
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    try:
        create_adjustment(db_session, 1, user.id, game.id, -3600, "bad", 1)
        assert False, "Expected ValueError"
    except ValueError:
        assert True


def test_set_absolute_total(db_session):
    from app.models import Game

    user = User(guild_id=1, discord_user_id=333, username="bob", display_name="Bob")
    game = Game(normalized_name="helldivers 2", display_name="Helldivers 2")
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, user.id, game.id, 100 * 3600, ManualSource.historical, "init", 1)
    set_absolute_total(db_session, 1, user.id, game.id, 120 * 3600, "correction", 1)

    assert total_seconds_for_user_game(db_session, 1, user.id, game.id) == 120 * 3600


def test_spec_scenario_historical_plus_tracked_plus_adjustment(db_session):
    from datetime import datetime, timedelta, timezone

    from app.models import ActivitySession, Game

    user = User(guild_id=1, discord_user_id=444, username="john2", display_name="John")
    game = Game(normalized_name="minecraft2", display_name="Minecraft")
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, user.id, game.id, 1240 * 3600, ManualSource.historical, "initial", 1)

    monday = datetime(2026, 9, 7, 18, 0, tzinfo=timezone.utc)
    tuesday = monday + timedelta(days=1)
    wednesday = monday + timedelta(days=2)
    db_session.add_all(
        [
            ActivitySession(guild_id=1, user_id=user.id, game_id=game.id, started_at=monday, ended_at=monday + timedelta(hours=2)),
            ActivitySession(guild_id=1, user_id=user.id, game_id=game.id, started_at=tuesday, ended_at=tuesday + timedelta(hours=3)),
            ActivitySession(guild_id=1, user_id=user.id, game_id=game.id, started_at=wednesday, ended_at=wednesday + timedelta(hours=1)),
        ]
    )
    db_session.commit()

    create_adjustment(db_session, 1, user.id, game.id, 30 * 60, "missing 30m", 1)

    assert total_seconds_for_user_game(db_session, 1, user.id, game.id) == int((1246.5) * 3600)


def test_spec_scenario_automatic_historical_negative_adjustment(db_session):
    from datetime import datetime, timedelta, timezone

    from app.models import ActivitySession, Game

    user = User(guild_id=1, discord_user_id=555, username="sam", display_name="Sam")
    game = Game(normalized_name="game-x", display_name="Game X")
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, user.id, game.id, 500 * 3600, ManualSource.historical, "initial", 1)

    start = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    db_session.add(ActivitySession(guild_id=1, user_id=user.id, game_id=game.id, started_at=start, ended_at=start + timedelta(hours=100)))
    db_session.commit()

    create_adjustment(db_session, 1, user.id, game.id, -2 * 3600, "remove duplicate", 1)

    assert total_seconds_for_user_game(db_session, 1, user.id, game.id) == 598 * 3600


def _auth_header(client):
    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'password'})
    token = resp.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_csv_import_all_or_nothing_rolls_back_on_error(client, db_session):
    from app.models import AuditLog, Game, ManualPlaytime

    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=991, username='john', display_name='John')
    db_session.add(john)
    db_session.commit()

    payload = {
        'guild_id': 1,
        'all_or_nothing': True,
        'rows': [
            {
                'discord_user': 'John',
                'game': 'Minecraft',
                'hours': 1,
                'minutes': 15,
                'source': 'historical',
                'note': 'valid row',
            },
            {
                'discord_user': 'Missing User',
                'game': 'VALORANT',
                'hours': 2,
                'minutes': 0,
                'source': 'historical',
                'note': 'invalid row',
            },
        ],
    }

    resp = client.post('/api/management/csv/import', json=payload, headers=headers)
    assert resp.status_code == 400

    assert db_session.query(ManualPlaytime).count() == 0
    assert db_session.query(Game).count() == 0
    assert db_session.query(AuditLog).count() == 0


def test_csv_preview_parses_valid_rows(client):
    headers = _auth_header(client)
    csv_content = (
        "Discord User ID,Discord User,Game,Hours,Minutes,Source,Note\n"
        "746720799582584832,blackkingcj,FIFA 17,823,0,historical,PSN playtime export\n"
    )

    response = client.post(
        '/api/management/csv/preview',
        files={'file': ('blackkingcj_playtime.csv', csv_content, 'text/csv')},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload['valid_rows']) == 1
    assert payload['valid_rows'][0]['discord_user_id'] == 746720799582584832
    assert payload['valid_rows'][0]['game'] == 'FIFA 17'
    assert payload['invalid_rows'] == []


def test_steam_preview_requires_api_key(client, db_session, monkeypatch):
    import app.api.routes.management as management_routes

    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=992, username='john2', display_name='John2')
    db_session.add(john)
    db_session.commit()

    class FakeSettings:
        steam_api_key = ''

    monkeypatch.setattr(management_routes, 'get_settings', lambda: FakeSettings())

    resp = client.post(
        '/api/management/steam/preview',
        json={'guild_id': 1, 'user_id': john.id, 'steam_profile': 'some-profile'},
        headers=headers,
    )
    assert resp.status_code == 400


def test_steam_import_creates_manual_rows(client, db_session, monkeypatch):
    import app.api.routes.management as management_routes
    from app.models import ManualPlaytime
    from app.services.steam_import import SteamImportPreview, SteamOwnedGame

    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=993, username='john3', display_name='John3')
    db_session.add(john)
    db_session.commit()

    class FakeSettings:
        steam_api_key = 'test-key'

    def fake_fetch(_profile: str, _api_key: str):
        return SteamImportPreview(
            steam_id='76561198000000000',
            profile_label='john-steam',
            games=[
                SteamOwnedGame(appid=730, name='Counter-Strike 2', playtime_minutes=120),
                SteamOwnedGame(appid=578080, name='PUBG', playtime_minutes=45),
            ],
        )

    monkeypatch.setattr(management_routes, 'get_settings', lambda: FakeSettings())
    monkeypatch.setattr(management_routes, 'fetch_steam_owned_games', fake_fetch)

    preview = client.post(
        '/api/management/steam/preview',
        json={'guild_id': 1, 'user_id': john.id, 'steam_profile': 'john-steam'},
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.json()['total_games'] == 2

    imported = client.post(
        '/api/management/steam/import',
        json={
            'guild_id': 1,
            'user_id': john.id,
            'steam_profile': 'john-steam',
            'replace_previous': True,
            'max_games': 200,
        },
        headers=headers,
    )
    assert imported.status_code == 200
    assert imported.json()['imported'] == 2

    rows = db_session.query(ManualPlaytime).all()
    assert len(rows) == 2
    assert all(row.source == ManualSource.imported for row in rows)
    assert all((row.note or '').startswith('[steam-import:76561198000000000]') for row in rows)


def test_csv_import_matches_discord_user_id(client, db_session):
    from app.models import ManualPlaytime

    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=994001, username='john4', display_name='John Four')
    db_session.add(john)
    db_session.commit()

    payload = {
        'guild_id': 1,
        'all_or_nothing': True,
        'rows': [
            {
                'discord_user': '',
                'discord_user_id': 994001,
                'game': 'Minecraft',
                'hours': 2,
                'minutes': 30,
                'source': 'historical',
                'note': 'id based import',
            }
        ],
    }

    resp = client.post('/api/management/csv/import', json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['imported'] == 1

    row = db_session.query(ManualPlaytime).first()
    assert row is not None
    assert row.user_id == john.id
    assert row.duration_seconds == (2 * 3600) + (30 * 60)


def test_csv_import_add_mode_accumulates_existing_total(client, db_session):
    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=995001, username='john5', display_name='John Five')
    db_session.add(john)
    db_session.commit()
    db_session.refresh(john)

    from app.models import Game

    game = Game(normalized_name='fifa 17', display_name='FIFA 17')
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, john.id, game.id, 3600, ManualSource.historical, 'seed', 1)

    payload = {
        'guild_id': 1,
        'all_or_nothing': True,
        'import_mode': 'add',
        'rows': [
            {
                'discord_user_id': 995001,
                'discord_user': '',
                'game': 'FIFA 17',
                'hours': 2,
                'minutes': 0,
                'source': 'historical',
                'note': 'csv add',
            }
        ],
    }

    resp = client.post('/api/management/csv/import', json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['imported'] == 1
    assert total_seconds_for_user_game(db_session, 1, john.id, game.id) == 3 * 3600


def test_csv_import_overwrite_mode_sets_absolute_total(client, db_session):
    headers = _auth_header(client)
    john = User(guild_id=1, discord_user_id=995002, username='john6', display_name='John Six')
    db_session.add(john)
    db_session.commit()
    db_session.refresh(john)

    from app.models import Game

    game = Game(normalized_name='fifa 18', display_name='FIFA 18')
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    create_manual_playtime(db_session, 1, john.id, game.id, 5 * 3600, ManualSource.historical, 'seed', 1)

    payload = {
        'guild_id': 1,
        'all_or_nothing': True,
        'import_mode': 'overwrite',
        'rows': [
            {
                'discord_user_id': 995002,
                'discord_user': '',
                'game': 'FIFA 18',
                'hours': 2,
                'minutes': 30,
                'source': 'historical',
                'note': 'csv overwrite',
            }
        ],
    }

    resp = client.post('/api/management/csv/import', json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['imported'] == 1
    assert total_seconds_for_user_game(db_session, 1, john.id, game.id) == (2 * 3600) + (30 * 60)
