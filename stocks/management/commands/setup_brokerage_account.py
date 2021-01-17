from django.core.management.base import BaseCommand

from stocks.models import Exchange


class Command(BaseCommand):
    EXCHANGE_KEY = 'exchange'
    USER_KEY = 'user'
    PASSWORD_KEY = 'password'
    RETRIEVE_KEY = 'retrieve'

    help = 'Setup brokerage account for an exchange'

    def add_arguments(self, parser):
        exchange_choices = [
            exchange.code for exchange in Exchange.objects.all()
        ]
        parser.add_argument(f'--{self.EXCHANGE_KEY}',
                            required=True, choices=exchange_choices)
        parser.add_argument(f'--{self.USER_KEY}')
        parser.add_argument(f'--{self.PASSWORD_KEY}')
        parser.add_argument(f'--{self.RETRIEVE_KEY}',
                            type=bool, const=True, default=False, nargs='?')

    def handle(self, *args, **options):
        exchange_code = options[self.EXCHANGE_KEY]

        exchange = Exchange.objects.get(code=exchange_code)

        if options.get(self.RETRIEVE_KEY):
            account = exchange.retrieve_brokerage_account()
            user = account['user']
            password = account['password']
            print(f'user: {user}, password: {password}')
        else:
            user = options[self.USER_KEY]
            password = options[self.PASSWORD_KEY]
            exchange.setup_brokerage_account(user, password)
