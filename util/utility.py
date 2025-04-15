from config.configuration import secrets


def get_user_id(user: str) -> str:
    if user == 'Amministratore Globale':
        return secrets.user_info.admin_global.user_id
    elif user == 'Amministratore Ente':
        return secrets.user_info.admin_ente.user_id
    elif user == 'Operatore':
        return secrets.user_info.operator.user_id
    else:
        raise ValueError

