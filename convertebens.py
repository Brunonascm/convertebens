import streamlit as st
import pandas as pd
import re
import io

# --- Configuração da Página ---
st.set_page_config(
    page_title="Conversor Oficial IOB > Domínio",
    page_icon="🏢",
    layout="wide"
)

# --- Constantes e Inteligência de Contas ---

# Dicionário de Contas Padrão Domínio
CONTAS_DOMINIO = {
    "1": "VEICULOS",
    "2": "MAQUINAS E EQUIPAMENTOS",
    "3": "MOVEIS E UTENSILIOS",
    "4": "EDIFICIOS",
    "5": "TERRENOS",
    "6": "CONSTRUCOES",
    "7": "FERRAMENTAS E ACESSORIOS",
    "8": "COMPUTADORES E ACESSORIOS",
    "9": "INSTALACOES",
    "10": "BENF. IMOVEIS DE TERCEIROS",
    "11": "SOFTWARES"
}

def sugerir_conta_dominio(descricao_origem):
    """
    Tenta identificar o código da conta Domínio com base no nome da conta IOB.
    """
    if not descricao_origem: return "" 
    desc = descricao_origem.upper()
    
    # Regras de Palavras-Chave (Prioridade Manual)
    if "VEIC" in desc or "CAMINH" in desc or "MOTO" in desc or "CARRO" in desc: return "1"
    if "MAQ" in desc or "INDUS" in desc: return "2"
    if "MOVEIS" in desc or "MOBIL" in desc or "CADEIRA" in desc or "MESA" in desc: return "3"
    if "EDIFIC" in desc or "PREDIO" in desc or "SALA" in desc or "GALPAO" in desc: return "4"
    if "TERRENO" in desc or "LOTE" in desc: return "5"
    if "CONSTRUC" in desc or "OBRA" in desc: return "6"
    if "FERRAMENT" in desc: return "7"
    if "COMPUT" in desc or "INFORM" in desc or "PROCESSAMENTO" in desc or "NOTEBOOK" in desc or "MONITOR" in desc or "PC" in desc: return "8"
    if "INSTALA" in desc or "AR COND" in desc: return "9"
    if "BENFEITORIA" in desc: return "10"
    if "SOFT" in desc or "SISTEMA" in desc or "PROGRAMA" in desc: return "11"
    
    # Busca exata nos nomes padrão
    for cod, nome_dominio in CONTAS_DOMINIO.items():
        nome_clean = nome_dominio.replace("S ", " ").replace("ES ", " ").strip()
        if nome_clean in desc: return cod
            
    return ""

# --- Funções Auxiliares de Formatação ---

def format_currency_dominio(value_str):
    """Remove pontos de milhar e garante vírgula decimal."""
    if not value_str or isinstance(value_str, (int, float)):
        value_str = str(value_str)
    value_str = value_str.strip()
    if not value_str: return "0,00"
    
    # Lógica: Se tem ponto e vírgula, o ponto é milhar.
    if '.' in value_str and ',' in value_str: 
        value_str = value_str.replace('.', '')
    # Se só tem ponto, assume que é decimal (formato US) e converte para vírgula
    if '.' in value_str and ',' not in value_str: 
        value_str = value_str.replace('.', ',')
        
    return value_str

def format_date_dominio(date_str):
    if not date_str: return ""
    return date_str.strip()

# --- Parser do Sistema IOB ---

def parse_iob(file_content):
    lines = file_content.split('\n')
    bens = []
    current_bem = {}
    capturing = False
    
    # Regex compilados para performance
    re_codigo_desc = re.compile(r"Codigo:\s+([\d-]+)\s+(.+)")
    re_data_aquisicao = re.compile(r"Data Aquisicao\s+(\d{2}/\d{2}/\d{4})")
    re_valor_original = re.compile(r"Valor Original\s+([\d\.]+,\d{2})")
    re_inicio_deprec = re.compile(r"Inicio Depreciacao\s+(\d{2}/\d{4})")
    re_nota_fiscal = re.compile(r"Nota Fiscal\s+(\d+)")
    
    # Captura taxa: suporta " % Dep. 10,00" ou apenas "10,00" isolado
    re_taxa = re.compile(r"%\s*Dep\.\s*(\d{1,3},\d{2})")
    re_taxa_isolada = re.compile(r"^\s*(\d{1,3},\d{2})\s*$") 
    
    # Captura a linha de saldos monetários
    re_saldos_line = re.compile(r"^\s*([\d\.]+,\d{2})\s+([\d\.]+,\d{2})")
    # Captura a conta contábil e sua descrição
    re_conta_contabil = re.compile(r"Conta\s+Contabil\s+[\d\.]+\s+-\s+(.+)")

    expecting_saldos = False

    for line in lines:
        line_clean = line.strip()
        
        # Filtros para ignorar cabeçalhos repetitivos, mas NUNCA ignorar a linha que contem "SALDOS"
        if ("Relacao Completa" in line_clean or "Periodo:" in line_clean) and "SALDOS" not in line_clean:
            continue
        if "-------" in line_clean and "SALDOS" not in line_clean:
            continue

        # Início de um novo bem
        match_cod = re_codigo_desc.search(line_clean)
        if match_cod:
            if current_bem: bens.append(current_bem) # Salva o anterior
            current_bem = {
                "codigo": match_cod.group(1).strip().replace('-', ''),
                "descricao": match_cod.group(2).strip(),
                "data_aquisicao": "", "valor_original": "0,00",
                "inicio_depreciacao": "", "taxa": "0,00", "nota_fiscal": "",
                "depreciacao_acumulada": "0,00", "baixado": False,
                "conta_origem_desc": "INDEFINIDA" 
            }
            capturing = True
            expecting_saldos = False
            continue
        
        if capturing and current_bem:
            # Verifica status do bem
            if "BEM BAIXADO" in line_clean: current_bem["baixado"] = True
            
            # Conta Contábil
            m_conta = re_conta_contabil.search(line_clean)
            if m_conta: current_bem["conta_origem_desc"] = m_conta.group(1).strip()

            # Dados Gerais
            m_data = re_data_aquisicao.search(line_clean)
            if m_data: current_bem["data_aquisicao"] = m_data.group(1)
            
            m_nf = re_nota_fiscal.search(line_clean)
            if m_nf: current_bem["nota_fiscal"] = m_nf.group(1)

            m_val = re_valor_original.search(line_clean)
            if m_val: current_bem["valor_original"] = m_val.group(1)

            m_ini = re_inicio_deprec.search(line_clean)
            if m_ini: current_bem["inicio_depreciacao"] = m_ini.group(1)

            # Taxa de Depreciação
            m_taxa = re_taxa.search(line_clean)
            if not m_taxa: m_taxa = re_taxa_isolada.search(line_clean)
                
            if m_taxa:
                try:
                    if 0 < float(m_taxa.group(1).replace(',', '.')) <= 100:
                        current_bem["taxa"] = m_taxa.group(1)
                except: pass
            
            # Gatilho para ler saldos na próxima linha
            if "SALDOS" in line_clean: 
                expecting_saldos = True; 
                continue;
            
            # Leitura dos valores acumulados
            if expecting_saldos:
                m_saldos = re_saldos_line.search(line_clean)
                if m_saldos:
                    # O segundo grupo capturado costuma ser o valor da Depreciação Acumulada
                    current_bem["depreciacao_acumulada"] = m_saldos.group(2)
                    expecting_saldos = False

    if current_bem: bens.append(current_bem)
    return pd.DataFrame(bens)

# --- Gerador do Arquivo TXT Domínio (Registro 0450) ---

def generate_dominio_txt(df, configs, de_para_contas):
    output = io.StringIO()
    
    for _, row in df.iterrows():
        # Cria lista de 77 campos vazios (índices 0 a 76)
        campos = [""] * 77
        
        # 1. Identificador
        campos[1] = "0450"
        
        # 2 e 3. Código e Descrição
        campos[2] = str(row.get('codigo', ''))[:10]
        descricao = str(row.get('descricao', ''))[:250]
        campos[3] = descricao
        
        # 4. Data Aquisição
        campos[4] = format_date_dominio(row.get('data_aquisicao', ''))
        
        # 5. Conta Patrimonial (Com De/Para)
        conta_origem = row.get('conta_origem_desc', '')
        conta_final = de_para_contas.get(conta_origem)
        if not conta_final or str(conta_final).strip() == "":
            conta_final = configs['conta_contabil_padrao']
        campos[5] = str(conta_final)
        
        # 6. Centro de Custo
        campos[6] = str(configs['centro_custo_padrao'])
        
        # Campos Fixos de Classificação
        campos[8] = "B"  # Bem
        campos[9] = "I"  # Imobilizado
        campos[11] = "N"
        campos[12] = descricao # Função = Descrição (Regra solicitada)
        campos[13] = "N"
        campos[14] = "N"
        campos[15] = "N"
        campos[17] = "N"
        campos[20] = "99"
        campos[21] = "9"
        campos[26] = "N"
        campos[34] = "N"
        campos[35] = "N"
        campos[36] = "N"
        campos[37] = "N"
        campos[38] = "N"
        campos[40] = "N"
        
        # Valores Originais
        val_orig = format_currency_dominio(row.get('valor_original', '0,00'))
        campos[42] = val_orig
        campos[49] = val_orig
        campos[50] = "0,00"
        campos[51] = "0,00"
        campos[52] = val_orig
        
        # --- Lógica Crítica: Depreciação e Saldos ---
        baixado = row.get('baixado', False)
        taxa = format_currency_dominio(row.get('taxa', '0,00'))
        tem_taxa = taxa != "0,00"
        
        val_acum = format_currency_dominio(row.get('depreciacao_acumulada', '0,00'))
        tem_acumulado = val_acum != "0,00" and val_acum != "0"

        # Se tiver valor acumulado, OBRIGA "Sim" na depreciação para habilitar o campo de saldo
        if tem_acumulado:
            campos[53] = "S"
        elif baixado or not tem_taxa:
            campos[53] = "N"
        else:
            campos[53] = "S"
            
        campos[54] = "N"
        campos[55] = taxa
        
        # Data Início Depreciação
        ini_dep = row.get('inicio_depreciacao', '')
        if ini_dep and len(ini_dep) == 7: dt_ini = f"01/{ini_dep}"
        elif campos[4]: dt_ini = campos[4]
        else: dt_ini = ""
        campos[56] = dt_ini
        
        # Campos de Saldo Acumulado (Fiscal)
        if tem_acumulado:
            campos[57] = "S" # Informar depreciação acumulada = SIM
            campos[58] = configs['data_saldo']
            campos[59] = val_acum
        else:
            campos[57] = "N"

        # Campos de Saldo Acumulado (Societário - Espelho)
        campos[60] = dt_ini
        if tem_acumulado:
            campos[61] = "S"
            campos[62] = configs['data_saldo']
            campos[63] = val_acum
        else:
            campos[61] = "N"
            
        campos[64] = taxa
        
        # Nota Fiscal
        nf = re.sub(r'\D', '', str(row.get('nota_fiscal', '')))
        campos[65] = nf[:6]

        # Montagem da Linha com Pipes
        line = "|".join(campos)
        if not line.startswith("|"): line = "|" + line
        output.write(line + "\n")

    return output.getvalue()

# --- Interface Gráfica Streamlit ---

st.sidebar.header("⚙️ Configurações Gerais")

# Seleção de Sistema (Preparado para expansão futura)
sistema = st.sidebar.selectbox("Sistema de Origem", ["IOB"])

st.sidebar.markdown("---")
st.sidebar.subheader("Parâmetros Domínio")
centro_custo = st.sidebar.text_input("Centro de Custo (Campo 6)", value="1")
data_saldo = st.sidebar.text_input("Data do Saldo Acumulado", value="31/12/2025")
conta_padrao = st.sidebar.text_input("Conta Padrão (Fallback)", value="1", help="Código usado se a inteligência não identificar a conta.")

configs = {
    'centro_custo_padrao': centro_custo, 
    'conta_contabil_padrao': conta_padrao, 
    'data_saldo': data_saldo
}

# Tabela de Ajuda
with st.sidebar.expander("📋 Ver Códigos Contábeis Domínio"):
    st.table(pd.DataFrame.from_dict(CONTAS_DOMINIO, orient='index', columns=['Descrição']))

# Corpo Principal
st.title("🔄 Conversor Oficial - IOB para Domínio")
st.markdown(f"Ferramenta oficial para migração de bens do Ativo Imobilizado. Módulo atual: **{sistema}**.")

if 'df_bens' not in st.session_state: 
    st.session_state.df_bens = pd.DataFrame()

uploaded_file = st.file_uploader("Carregue o arquivo de Relatório (.txt)", type=["txt"])

if uploaded_file:
    # Processamento do Arquivo
    if st.session_state.df_bens.empty:
        try: 
            content = uploaded_file.getvalue().decode("latin-1")
        except: 
            content = uploaded_file.getvalue().decode("utf-8")
            
        with st.spinner("Processando arquivo oficial..."):
            if sistema == "IOB": 
                st.session_state.df_bens = parse_iob(content)

if not st.session_state.df_bens.empty:
    df = st.session_state.df_bens
    
    # Métricas Rápidas
    col1, col2 = st.columns(2)
    col1.metric("Bens Identificados", len(df))
    bens_com_saldo = df[df['depreciacao_acumulada'] != "0,00"]
    col2.metric("Bens com Saldo Anterior", len(bens_com_saldo))
    
    st.markdown("---")
    st.subheader("🤖 De-Para Inteligente de Contas")
    
    contas_origem_unicas = sorted(list(df['conta_origem_desc'].unique()))
    de_para_map = {}
    
    # Grid de De-Para
    cols = st.columns(3)
    for i, conta_desc in enumerate(contas_origem_unicas):
        col = cols[i % 3]
        with col:
            sugestao = sugerir_conta_dominio(conta_desc)
            icon = "✅" if sugestao else "⚠️"
            label_text = f"{icon} {conta_desc}"
            
            # Encurtar labels muito longos visualmente
            if len(label_text) > 40: label_text = label_text[:37] + "..."
            
            novo_cod = st.text_input(
                label=label_text, 
                value=sugestao, 
                key=f"conta_{i}", 
                help=f"Conta Original: {conta_desc}", 
                placeholder="Vazio = Padrão"
            )
            de_para_map[conta_desc] = novo_cod

    st.markdown("---")
    
    # Botão de Geração
    if st.button("🚀 Gerar Arquivo de Importação", type="primary"):
        txt_output = generate_dominio_txt(df, configs, de_para_map)
        
        st.success("Arquivo gerado com sucesso! Pronto para importar na Domínio.")
        st.download_button(
            label="📥 Baixar TXT (Registro 0450)", 
            data=txt_output, 
            file_name="importacao_bens_dominio.txt", 
            mime="text/plain"
        )
    
    # Preview de Dados
    with st.expander("🔍 Conferência Detalhada dos Dados"):
        st.dataframe(df)

# Botão de Reset
if st.sidebar.button("Limpar / Novo Arquivo"):
    st.session_state.df_bens = pd.DataFrame()
    st.rerun()