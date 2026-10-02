interface PaginaProvisoriaProps {
  titulo: string
  descricao: string
}

/** Conteúdo temporário das telas que ainda não foram implementadas. */
export function PaginaProvisoria({ titulo, descricao }: PaginaProvisoriaProps) {
  return (
    <section>
      <h1>{titulo}</h1>
      <p>{descricao}</p>
    </section>
  )
}
