import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
})

// Canvas não é implementado no jsdom. Mock mínimo para suprimir os avisos
// "Not implemented: HTMLCanvasElement's getContext()" durante os testes.
// O RedeFundo verifica `if (!ctx) return` antes de usar qualquer método.
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(null)

