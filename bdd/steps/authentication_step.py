from behave import given

from api.auth import post_auth_password
from util.utility import get_user_info_login


@given('l\'{user} autenticato')
def step_user_authentication(context, user):
    res = post_auth_password(get_user_info_login(user))

    assert res.status_code == 200

    context.token = res.headers.get('Authorization')
