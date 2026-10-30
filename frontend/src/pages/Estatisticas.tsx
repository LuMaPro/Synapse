import { useEffect, useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell 
} from 'recharts';
import { buscarEstatisticas, type EstatisticasApi } from '../services/estatisticas'; 

export function Estatisticas() {
  const [periodo, setPeriodo] = useState<'dia' | 'semana' | 'mes'>('semana');
  const [dados, setDados] = useState<EstatisticasApi | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    async function carregar() {
      setCarregando(true);
      try {
        const resultado = await buscarEstatisticas(periodo);
        setDados(resultado);
      } catch (error) {
        console.error("Erro ao buscar estatísticas:", error);
      } finally {
        setCarregando(false);
      }
    }
    carregar();
  }, [periodo]);

  if (carregando && !dados) {
    return <div style={{ padding: '24px', color: '#fff' }}>Carregando estatísticas...</div>;
  }

  // Fallback de segurança 
  const stats = dados || {
    tempo_total_minutos: 0,
    taxa_sucesso: 0,
    melhor_horario: null,
    por_dia: [],
    por_materia: []
  };

  // Prepara dados pro gráfico de barras (converte data para dia da semana)
  const dadosBarras = stats.por_dia.map(dia => {
    const dataObj = new Date(dia.data);
    // Para resolver fuso, adiciona o offset
    dataObj.setMinutes(dataObj.getMinutes() + dataObj.getTimezoneOffset());
    const nomeDia = dataObj.toLocaleDateString('pt-BR', { weekday: 'short' });
    return {
      diaStr: nomeDia.charAt(0).toUpperCase() + nomeDia.slice(1).replace('.', ''),
      horas: Number((dia.minutos / 60).toFixed(1))
    };
  });

  // Prepara dados pro gráfico de rosca (converte minutos pra horas e cuida do fallback de nome/cor)
  const dadosRosca = stats.por_materia.map(m => ({
    nome: m.nome || 'Sem Matéria',
    cor: m.cor || '#8B7BFF', // fallback caso venha null
    horas: Number((m.minutos / 60).toFixed(1))
  }));

  // Converte a taxa_sucesso (ex: 0.6667) para porcentagem (67%)
  const taxaPorcentagem = Math.round(stats.taxa_sucesso * 100);
  
  // Converte minutos totais para horas formatadas (ex: 35.5)
  const horasTotais = (stats.tempo_total_minutos / 60).toFixed(1).replace('.0', '');

  return (
    <div style={{ padding: '24px', fontFamily: 'sans-serif', color: '#fff', backgroundColor: '#121212', minHeight: '100vh', paddingBottom: '100px' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Dashboard de Estatísticas</h2>
        <select 
          value={periodo} 
          onChange={(e) => setPeriodo(e.target.value as 'dia' | 'semana' | 'mes')}
          style={{ padding: '8px', borderRadius: '4px', backgroundColor: '#2c2c2c', color: '#fff', border: '1px solid #444' }}
        >
          <option value="dia">Hoje</option>
          <option value="semana">Última Semana</option>
          <option value="mes">Último Mês</option>
        </select>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '32px' }}>
        <div style={{ flex: 1, padding: '16px', backgroundColor: '#1e1e1e', borderRadius: '8px' }}>
          <p style={{ margin: 0, fontSize: '14px', color: '#aaa' }}>Total de Horas</p>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '24px' }}>{horasTotais}h</h3>
        </div>
        <div style={{ flex: 1, padding: '16px', backgroundColor: '#1e1e1e', borderRadius: '8px' }}>
          <p style={{ margin: 0, fontSize: '14px', color: '#aaa' }}>Taxa de Sucesso</p>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '24px', color: '#7BFF8B' }}>{taxaPorcentagem}%</h3>
        </div>
        <div style={{ flex: 1, padding: '16px', backgroundColor: '#1e1e1e', borderRadius: '8px' }}>
          <p style={{ margin: 0, fontSize: '14px', color: '#aaa' }}>Melhor Horário</p>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '24px', color: '#FFB87B' }}>
            {stats.melhor_horario !== null && stats.melhor_horario !== undefined ? `${stats.melhor_horario}h` : '--'}
          </h3>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        
        <div style={{ flex: 2, minWidth: '400px', backgroundColor: '#1e1e1e', padding: '16px', borderRadius: '8px' }}>
          <h4 style={{ marginTop: 0, marginBottom: '16px' }}>Tempo focado por dia (Horas)</h4>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dadosBarras}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="diaStr" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none', borderRadius: '4px', color: '#fff' }} itemStyle={{color: '#fff'}} />
                <Bar dataKey="horas" fill="#8B7BFF" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '300px', backgroundColor: '#1e1e1e', padding: '16px', borderRadius: '8px' }}>
          <h4 style={{ marginTop: 0, marginBottom: '16px' }}>Foco por matéria</h4>
          <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {dadosRosca.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dadosRosca}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="horas"
                  >
                    {dadosRosca.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.cor} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none', borderRadius: '4px', color: '#fff' }} itemStyle={{color: '#fff'}} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <span style={{ color: '#888' }}>Sem dados</span>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
            {dadosRosca.map(item => (
              <div key={item.nome} style={{ display: 'flex', alignItems: 'center', fontSize: '14px' }}>
                <span style={{ width: '12px', height: '12px', backgroundColor: item.cor, borderRadius: '50%', marginRight: '8px' }}></span>
                <span style={{ flex: 1 }}>{item.nome}</span>
                <span>{item.horas}h</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}