import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    // Com a cobertura ligada, o código fica mais lento, e no CI (2 núcleos rodando
    // vários arquivos de teste ao mesmo tempo) o primeiro teste de uma tela chegou a
    // levar 8 s. Os 5 s padrão do Vitest derrubavam o teste sem ele ter falhado.
    testTimeout: 20_000,
    // Cobertura (issue #43): `npm run test:coverage`. O relatório HTML fica em coverage/.
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/setupTests.ts', 'src/main.tsx'],
      reporter: ['text', 'html', 'json-summary'],
      thresholds: { statements: 80, branches: 80, functions: 80, lines: 80 },
    },
  },
})
