"""Select the project interpreter and press Run in PyCharm."""
import os

# USER SETTINGS
HOST = '127.0.0.1'
PORT = 8001


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TicketSystem.settings')
    from django.core.management import execute_from_command_line
    print(f'CalCloud demo: http://{HOST}:{PORT}/calcloud/', flush=True)
    execute_from_command_line(['manage.py', 'runserver', f'{HOST}:{PORT}'])


if __name__ == '__main__':
    main()
