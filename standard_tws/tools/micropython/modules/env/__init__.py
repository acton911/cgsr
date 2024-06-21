from .env_checks import socket_check, user_check, init_service, config_check, evb_check, create_qcn_path


def env_check():
    socket_check()
    user_check()
    init_service()
    config_check()
    evb_check()
    create_qcn_path()
