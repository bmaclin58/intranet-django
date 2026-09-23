"""Local development server: select the project interpreter and press Run in PyCharm."""
import os

# USER SETTINGS
HOST = '127.0.0.1'
PORT = 8000


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', f'{HOST}:{PORT}'])


if __name__ == '__main__':
    main()
