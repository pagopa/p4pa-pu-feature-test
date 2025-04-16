from config.configuration import secrets


def get_user_id(user: str) -> str:
    if user == 'Admin org with GPD':
        return secrets.user_info.admin_org_gpd.user_id
    elif user == 'Admin org with ACA':
        return secrets.user_info.admin_org_aca.user_id
    else:
        raise ValueError
