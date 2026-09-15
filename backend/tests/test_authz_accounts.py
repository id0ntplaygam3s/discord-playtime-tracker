from datetime import datetime, timedelta, timezone


def _admin_header(client):
    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'password'})
    token = resp.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def _register_account_for_user(client, db_session, user_name='User A', discord_user_id=6001):
    from app.models import User, UserAccount, AccountStatus

    user = User(guild_id=1, discord_user_id=discord_user_id, username=user_name.lower().replace(' ', ''), display_name=user_name)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    reg = client.post(
        '/api/auth/register',
        json={
            'user_id': user.id,
            'password': 'verysecure1',
            'confirm_password': 'verysecure1',
        },
    )
    assert reg.status_code == 200

    account = db_session.query(UserAccount).filter(UserAccount.user_id == user.id).first()
    assert account is not None
    assert account.status == AccountStatus.pending
    return user, account


def test_registration_requires_known_discord_user(client):
    resp = client.post(
        '/api/auth/register',
        json={'user_id': 999999, 'password': 'verysecure1', 'confirm_password': 'verysecure1'},
    )
    assert resp.status_code == 400


def test_registration_then_admin_approve_then_account_login(client, db_session):
    from app.models import UserAccount, AccountStatus

    user, account = _register_account_for_user(client, db_session, user_name='User B', discord_user_id=6002)

    pending_login = client.post('/api/auth/account-login', json={'user_id': user.id, 'password': 'verysecure1'})
    assert pending_login.status_code == 403

    approved = client.post(f'/api/auth/registrations/{account.id}/approve', headers=_admin_header(client))
    assert approved.status_code == 200

    db_session.refresh(account)
    assert account.status == AccountStatus.active

    ok_login = client.post('/api/auth/account-login', json={'user_id': user.id, 'password': 'verysecure1'})
    assert ok_login.status_code == 200
    token = ok_login.json()['access_token']

    me = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['is_guest'] is False
    assert me.json()['tracked_user_id'] == user.id


def test_duplicate_registration_blocked(client, db_session):
    user, _account = _register_account_for_user(client, db_session, user_name='User C', discord_user_id=6003)

    duplicate = client.post(
        '/api/auth/register',
        json={'user_id': user.id, 'password': 'verysecure1', 'confirm_password': 'verysecure1'},
    )
    assert duplicate.status_code == 409


def test_locked_account_cannot_login(client, db_session):
    from app.models import AccountStatus, UserAccount

    user, account = _register_account_for_user(client, db_session, user_name='User D', discord_user_id=6004)
    account.status = AccountStatus.active
    account.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    account.status = AccountStatus.locked
    db_session.commit()

    resp = client.post('/api/auth/account-login', json={'user_id': user.id, 'password': 'verysecure1'})
    assert resp.status_code == 403


def test_user_can_manage_own_manual_but_not_others(client, db_session):
    from app.models import Game, User, UserAccount, AppRole, AppRoleName, AccountStatus
    from app.services.authz_service import ensure_roles_and_permissions

    owner = User(guild_id=1, discord_user_id=6005, username='owner', display_name='Owner')
    other = User(guild_id=1, discord_user_id=6006, username='other', display_name='Other')
    game = Game(normalized_name='test-game-own', display_name='Test Game Own')
    db_session.add_all([owner, other, game])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other)
    db_session.refresh(game)

    ensure_roles_and_permissions(db_session)
    db_session.commit()
    role = db_session.query(AppRole).filter(AppRole.name == AppRoleName.user).first()

    account = UserAccount(user_id=owner.id, role_id=role.id, password_hash='$argon2id$v=19$m=65536,t=3,p=4$uQJ2qzG4Xj2+U4lTQw0P9g$QnH8n+0y9Q3VnTzN9fyQ3M6pT5v8g4R9O0/3vS8qA4Q', status=AccountStatus.active)
    db_session.add(account)
    db_session.commit()

    # Replace placeholder hash with a real one via endpoint registration flow for compatibility.
    db_session.delete(account)
    db_session.commit()
    reg = client.post('/api/auth/register', json={'user_id': owner.id, 'password': 'verysecure1', 'confirm_password': 'verysecure1'})
    assert reg.status_code == 200
    pending = db_session.query(UserAccount).filter(UserAccount.user_id == owner.id).first()
    pending.status = AccountStatus.active
    db_session.commit()

    login = client.post('/api/auth/account-login', json={'user_id': owner.id, 'password': 'verysecure1'})
    assert login.status_code == 200
    token = login.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    own_create = client.post(
        '/api/management/self/manual-playtime',
        json={
            'guild_id': 1,
            'user_id': owner.id,
            'game_id': game.id,
            'hours': 1,
            'minutes': 0,
            'source': 'historical',
            'note': 'own entry',
        },
        headers=headers,
    )
    assert own_create.status_code == 200

    other_create = client.post(
        '/api/management/self/manual-playtime',
        json={
            'guild_id': 1,
            'user_id': other.id,
            'game_id': game.id,
            'hours': 1,
            'minutes': 0,
            'source': 'historical',
            'note': 'forbidden entry',
        },
        headers=headers,
    )
    assert other_create.status_code == 403


def test_custom_title_requires_override_flag(client, db_session):
    from app.models import User, UserAccount, AppRole, AppRoleName, AccountStatus
    from app.services.authz_service import ensure_roles_and_permissions

    owner = User(guild_id=1, discord_user_id=6010, username='owner2', display_name='Owner Two')
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    ensure_roles_and_permissions(db_session)
    db_session.commit()
    role = db_session.query(AppRole).filter(AppRole.name == AppRoleName.user).first()
    account = UserAccount(user_id=owner.id, role_id=role.id, password_hash='tmp', status=AccountStatus.pending)
    db_session.add(account)
    db_session.commit()
    db_session.delete(account)
    db_session.commit()

    reg = client.post('/api/auth/register', json={'user_id': owner.id, 'password': 'verysecure1', 'confirm_password': 'verysecure1'})
    assert reg.status_code == 200
    pending = db_session.query(UserAccount).filter(UserAccount.user_id == owner.id).first()
    pending.status = AccountStatus.active
    db_session.commit()

    login = client.post('/api/auth/account-login', json={'user_id': owner.id, 'password': 'verysecure1'})
    assert login.status_code == 200
    token = login.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    bad = client.post(
        '/api/management/self/manual-playtime',
        json={
            'guild_id': 1,
            'user_id': owner.id,
            'custom_game_title': 'Only Title',
            'hours': 1,
            'minutes': 0,
            'source': 'historical',
            'note': 'missing override flag',
        },
        headers=headers,
    )
    assert bad.status_code == 400

    ok = client.post(
        '/api/management/self/manual-playtime',
        json={
            'guild_id': 1,
            'user_id': owner.id,
            'use_custom_game_title': True,
            'custom_game_title': 'Only Title',
            'hours': 1,
            'minutes': 0,
            'source': 'historical',
            'note': 'with override',
        },
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json().get('game_id')
