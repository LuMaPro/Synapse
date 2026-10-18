from django.core.management.base import BaseCommand

from app.application.sessoes import SessaoService
from app.infra.repositorios import RepositorioNeuronioDjango, RepositorioSessaoDjango


class Command(BaseCommand):
    help = (
        "Poda as sessões em andamento há mais de duração + 5 min sem conclusão. "
        "Feito para rodar periodicamente (ex.: cron); a API também expira cada "
        "sessão órfã quando ela é acessada."
    )

    def handle(self, *args, **options):
        servico = SessaoService(RepositorioSessaoDjango(), RepositorioNeuronioDjango())
        podadas = servico.podar_orfas()
        self.stdout.write(
            self.style.SUCCESS(f"{podadas} sessão(ões) órfã(s) podada(s).")
        )
