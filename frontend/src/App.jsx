import React, { useState } from 'react';

export default function App() {
  const [arquivo, setArquivo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!arquivo) return alert("Selecione um arquivo .ofx");

    const formData = new FormData();
    formData.append("file", arquivo);

    setLoading(true);
    setResultado(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/upload-ofx", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setResultado(data);
      } else {
        alert(data.detail || "Erro ao processar arquivo.");
      }
    } catch (error) {
      alert("Erro ao conectar com a API Python.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '40px auto', fontFamily: 'system-ui, sans-serif', padding: '0 20px' }}>
      <h1>Gestão Financeira — Importador OFX</h1>
      <p style={{ color: '#666' }}>Selecione um arquivo de extrato bancário (.ofx) para classificar e gravar no PostgreSQL.</p>
      
      <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #ccc' }} />

      <form onSubmit={handleUpload} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '30px' }}>
        <input 
          type="file" 
          accept=".ofx" 
          onChange={(e) => setArquivo(e.target.files[0])} 
          style={{ padding: '8px' }}
        />
        <button 
          type="submit" 
          disabled={loading}
          style={{ padding: '8px 16px', backgroundColor: '#000', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {loading ? "Processando..." : "Enviar e Classificar"}
        </button>
      </form>

      {resultado && (
        <div>
          <h2>Resumo da Importação</h2>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', background: '#f9f9f9', padding: '15px', borderRadius: '6px' }}>
            <div>Novos Registros: <strong>{resultado.inseridos}</strong></div>
            <div>Duplicados Ignorados: <strong>{resultado.duplicados}</strong></div>
            <div>Entradas: <strong style={{ color: 'green' }}>R$ {resultado.total_entradas.toFixed(2)}</strong></div>
            <div>Saídas: <strong style={{ color: 'red' }}>R$ {resultado.total_saidas.toFixed(2)}</strong></div>
            <div>Saldo: <strong>R$ {resultado.saldo.toFixed(2)}</strong></div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #000' }}>
                <th style={{ padding: '10px' }}>Data</th>
                <th style={{ padding: '10px' }}>Valor</th>
                <th style={{ padding: '10px' }}>Tipo</th>
                <th style={{ padding: '10px' }}>Categoria</th>
                <th style={{ padding: '10px' }}>Descrição</th>
              </tr>
            </thead>
            <tbody>
              {resultado.transacoes.map((t, index) => (
                <tr key={index} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px' }}>{t.data}</td>
                  <td style={{ padding: '10px', color: t.valor > 0 ? 'green' : 'red', fontWeight: 'bold' }}>
                    R$ {t.valor.toFixed(2)}
                  </td>
                  <td style={{ padding: '10px' }}>{t.tipo}</td>
                  <td style={{ padding: '10px' }}><strong>{t.categoria}</strong></td>
                  <td style={{ padding: '10px' }}>{t.descricao}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}