import type { Materia } from '../services/materias'
import { amostraDaCor } from '../utils/efeitos'

interface SeletorMateriaProps {
  materias: Materia[]
  materiaId: string | null
  onEscolher: (materiaId: string | null) => void
  disabled?: boolean
}

export function SeletorMateria({
  materias,
  materiaId,
  onEscolher,
  disabled = false,
}: SeletorMateriaProps) {
  return (
    <div className="seletor-materia">
      <span className="rotulo-campo" id="rotulo-materia">
        Matéria
      </span>
      <div className="chips" role="radiogroup" aria-labelledby="rotulo-materia">
        {materias.map((materia) => {
          const selecionada = materiaId === materia.id
          return (
            <button
              key={materia.id}
              type="button"
              className={`chip ${selecionada ? 'ativo' : ''}`}
              role="radio"
              aria-checked={selecionada}
              onClick={() => onEscolher(materia.id)}
              disabled={disabled}
            >
              <i {...amostraDaCor(materia.cor, materia.efeito)} aria-hidden="true" />
              {materia.nome}
            </button>
          )
        })}
        <button
          type="button"
          className={`chip ${materiaId === null ? 'ativo' : ''}`}
          role="radio"
          aria-checked={materiaId === null}
          onClick={() => onEscolher(null)}
          disabled={disabled}
        >
          Sem matéria
        </button>
      </div>
    </div>
  )
}
