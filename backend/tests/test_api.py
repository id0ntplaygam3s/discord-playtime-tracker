from datetime import datetime, timedelta, timezone


def _auth_header(client):
    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'password'})
    token = resp.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def _guest_header(client):
    resp = client.post('/api/auth/guest')
    token = resp.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_health(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


def test_login_and_overview(client):
    headers = _auth_header(client)
    resp = client.get('/api/stats/overview', params={'guild_id': 1}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert 'total_combined_seconds' in body


def test_overview_allows_guild_id_zero_fallback(client):
    headers = _auth_header(client)
    resp = client.get('/api/stats/overview', params={'guild_id': 0}, headers=headers)
    assert resp.status_code == 200


def test_guest_login_and_overview(client):
    headers = _guest_header(client)
    me = client.get('/api/auth/me', headers=headers)
    assert me.status_code == 200
    assert me.json()['role'] == 'viewer'

    resp = client.get('/api/stats/overview', params={'guild_id': 1}, headers=headers)
    assert resp.status_code == 200


def test_guest_cannot_access_admin_endpoint(client):
    headers = _guest_header(client)
    resp = client.get('/api/audit', params={'guild_id': 1}, headers=headers)
    assert resp.status_code == 403


def test_user_profile_is_guild_scoped(client, db_session):
    from app.models import User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=5555, username='john', display_name='John')
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    ok = client.get(f'/api/users/{user.id}', params={'guild_id': 1}, headers=headers)
    assert ok.status_code == 200

    not_found = client.get(f'/api/users/{user.id}', params={'guild_id': 999}, headers=headers)
    assert not_found.status_code == 404


def test_user_games_aggregation_no_overcount(client, db_session):
    from app.models import ActivitySession, Game, ManualPlaytime, ManualSource, PlaytimeAdjustment, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=7777, username='sam', display_name='Sam')
    game = Game(normalized_name='minecraft', display_name='Minecraft')
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    start = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
    db_session.add(
        ActivitySession(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            started_at=start,
            ended_at=start + timedelta(hours=2),
        )
    )
    db_session.add(
        ManualPlaytime(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            duration_seconds=3 * 3600,
            source=ManualSource.historical,
            note='initial',
            created_by=1,
        )
    )
    db_session.add(
        PlaytimeAdjustment(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            adjustment_seconds=1800,
            reason='missing session',
            created_by=1,
        )
    )
    db_session.commit()

    resp = client.get(f'/api/users/{user.id}/games', params={'guild_id': 1}, headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]['total_seconds'] == (2 * 3600) + (3 * 3600) + 1800


def test_game_profile_is_guild_scoped(client, db_session):
    from app.models import ActivitySession, Game, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=8888, username='alex', display_name='Alex')
    game = Game(normalized_name='terraria', display_name='Terraria')
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    start = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    db_session.add(
        ActivitySession(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            started_at=start,
            ended_at=start + timedelta(minutes=30),
        )
    )
    db_session.commit()

    ok = client.get(f'/api/games/{game.id}', params={'guild_id': 1}, headers=headers)
    assert ok.status_code == 200

    not_found = client.get(f'/api/games/{game.id}', params={'guild_id': 999}, headers=headers)
    assert not_found.status_code == 404


def test_game_alias_create_and_list(client, db_session):
    from app.models import ActivitySession, Game, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=9898, username='kai', display_name='Kai')
    game = Game(normalized_name='minecraft-core', display_name='Minecraft')
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    start = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    db_session.add(
        ActivitySession(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            started_at=start,
            ended_at=start + timedelta(minutes=10),
        )
    )
    db_session.commit()

    created = client.post(
        f'/api/games/{game.id}/aliases',
        json={'guild_id': 1, 'alias': 'Minecraft Java Edition'},
        headers=headers,
    )
    assert created.status_code == 200

    listed = client.get(f'/api/games/{game.id}/aliases', params={'guild_id': 1}, headers=headers)
    assert listed.status_code == 200
    assert any(row['alias'] == 'Minecraft Java Edition' for row in listed.json())


def test_game_merge_reassigns_guild_data(client, db_session):
    from app.models import ActivitySession, Game, ManualPlaytime, ManualSource, PlaytimeAdjustment, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=9090, username='merge', display_name='Merge User')
    source_game = Game(normalized_name='minecraft-old', display_name='Minecraft Old')
    target_game = Game(normalized_name='minecraft', display_name='Minecraft')
    db_session.add_all([user, source_game, target_game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(source_game)
    db_session.refresh(target_game)

    start = datetime(2026, 9, 10, 18, 0, tzinfo=timezone.utc)
    db_session.add(
        ActivitySession(
            guild_id=1,
            user_id=user.id,
            game_id=source_game.id,
            started_at=start,
            ended_at=start + timedelta(hours=1),
        )
    )
    db_session.add(
        ManualPlaytime(
            guild_id=1,
            user_id=user.id,
            game_id=source_game.id,
            duration_seconds=3600,
            source=ManualSource.historical,
            note='seed',
            created_by=1,
        )
    )
    db_session.add(
        PlaytimeAdjustment(
            guild_id=1,
            user_id=user.id,
            game_id=source_game.id,
            adjustment_seconds=600,
            reason='seed',
            created_by=1,
        )
    )
    db_session.commit()

    merged = client.post(
        '/api/games/merge',
        json={
            'guild_id': 1,
            'source_game_id': source_game.id,
            'target_game_id': target_game.id,
            'reason': 'duplicate normalized title',
        },
        headers=headers,
    )
    assert merged.status_code == 200

    game_users = client.get(f'/api/games/{target_game.id}/users', params={'guild_id': 1}, headers=headers)
    assert game_users.status_code == 200
    assert any(row['id'] == user.id for row in game_users.json())

    db_session.refresh(source_game)
    assert source_game.canonical_game_id == target_game.id

    source_auto = db_session.query(ActivitySession).filter(ActivitySession.game_id == source_game.id).count()
    target_auto = db_session.query(ActivitySession).filter(ActivitySession.game_id == target_game.id).count()
    assert source_auto == 1
    assert target_auto == 0


def test_merge_suggestion_ignore_hides_pair(client, db_session):
    from app.models import ActivitySession, Game, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=9111, username='merge2', display_name='Merge User 2')
    source = Game(normalized_name='counter strike 2', display_name='Counter-Strike 2')
    target = Game(normalized_name='counterstrike 2', display_name='Counter Strike 2')
    db_session.add_all([user, source, target])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(source)
    db_session.refresh(target)

    start = datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
    db_session.add(ActivitySession(guild_id=1, user_id=user.id, game_id=source.id, started_at=start, ended_at=start + timedelta(minutes=20)))
    db_session.commit()

    before = client.get('/api/games/meta/merge-suggestions', headers=headers)
    assert before.status_code == 200

    ignored = client.post(f'/api/games/meta/merge-suggestions/{source.id}/{target.id}/ignore', json={'guild_id': 1}, headers=headers)
    assert ignored.status_code == 200

    after = client.get('/api/games/meta/merge-suggestions', headers=headers)
    assert after.status_code == 200
    assert not any(row['source_game_id'] == source.id and row['target_game_id'] == target.id for row in after.json())


def test_stats_custom_range_validation(client):
    headers = _auth_header(client)

    missing_to = client.get(
        '/api/stats/overview',
        params={'guild_id': 1, 'range': 'custom', 'from': '2026-01-01T00:00:00Z'},
        headers=headers,
    )
    assert missing_to.status_code == 400

    inverted = client.get(
        '/api/stats/overview',
        params={
            'guild_id': 1,
            'range': 'custom',
            'from': '2026-01-10T00:00:00Z',
            'to': '2026-01-01T00:00:00Z',
        },
        headers=headers,
    )
    assert inverted.status_code == 400


def test_stats_custom_range_valid(client):
    headers = _auth_header(client)
    resp = client.get(
        '/api/stats/overview',
        params={
            'guild_id': 1,
            'range': 'custom',
            'from': '2026-01-01T00:00:00Z',
            'to': '2026-01-10T00:00:00Z',
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_active_sessions_allows_guild_id_zero_fallback(client, db_session):
    from app.models import ActivitySession, Game, User

    headers = _auth_header(client)
    user = User(guild_id=1, discord_user_id=121212, username='active', display_name='Active User')
    game = Game(normalized_name='active-game', display_name='Active Game')
    db_session.add_all([user, game])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(game)

    start = datetime(2026, 9, 10, 19, 0, tzinfo=timezone.utc)
    db_session.add(
        ActivitySession(
            guild_id=1,
            user_id=user.id,
            game_id=game.id,
            started_at=start,
            ended_at=None,
        )
    )
    db_session.commit()

    resp = client.get('/api/activity/active', params={'guild_id': 0}, headers=headers)
    assert resp.status_code == 200
    assert any(row['user_id'] == user.id for row in resp.json())
