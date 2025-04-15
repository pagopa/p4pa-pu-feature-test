from api.auth import post_auth_token
from util.utility import get_user_id


def get_token_org(context, user):
    res = post_auth_token(get_user_id(user))
    assert res.status_code == 200

    try:
        context.token[user] = res.json()['accessToken']
    except AttributeError:
        context.token = {user: res.json()['accessToken']}

    context.latest_user_authenticated = user
