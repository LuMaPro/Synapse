from django.core.management.base import BaseCommand
from django.db import transaction

from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.observadores import AtualizadorRede
from app.infra.repositorios import (
    RepositorioRedeNeuralDjango,
    RepositorioSessaoDjango,
)


class Command(BaseCommand):
    help = (
        "Poda as sessões em andamento há mais de duração + 5 min sem conclusão. "
        "Feito para rodar periodicamente (ex.: cron); a API também expira cada "
        "sessão órfã quando ela é acessada."
    )

    def handle(self, *args, **options):
        # Configura a rede e os observadores
        rede_service = RedeNeuralService(RepositorioRedeNeuralDjango())
        atualizador = AtualizadorRede(rede_service)

        # Configura o publicador e inscreve os observadores
        publicador = PublicadorEventos()
        publicador.inscrever(SessaoConcluida, atualizador)
        publicador.inscrever(SessaoPodada, atualizador)

        # Injeta o publicador no serviço de sessão
        servico = SessaoService(RepositorioSessaoDjango(), publicador)

        # A sessão podada e o neurônio morto que ela deixa na rede são gravados juntos.
        with transaction.atomic():
            podadas = servico.podar_orfas()
        self.stdout.write(
            self.style.SUCCESS(f"{podadas} sessão(ões) órfã(s) podada(s).")
        )
