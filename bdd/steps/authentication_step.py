from behave import given

from api.auth import post_auth_password
from util.utility import get_user_id


@given('l\'{user} autenticato')
def step_user_authentication(context, user):
    res = post_auth_password(get_user_id(user))
    assert res.status_code == 200

    try:
        context.token[user] = res.json()['accessToken']
    except AttributeError:
        context.token = {user: res.json()['accessToken']}

    context.latest_user_authenticated = user
