import streamlit as st
import pandas as pd
import re
import io
import csv

# --- Configuração da Página ---
st.set_page_config(
    page_title="Super Conversor Patrimônio > Domínio",
    page_icon="🚀",
    layout="wide"
)

# ==========================================
# 📘 MANUAIS E INSTRUÇÕES (TEXTO)
# ==========================================

MANUAIS = { 
    "IOB / Folhamatic": {
        "titulo": "Como exportar o arquivo no IOB / Folhamatic",
        "passos": [
            "1. Acesse o módulo **Office Contábil** (ou Ativo Fixo).",
            "2. Vá no menu **Relatórios > Diversos**.",
            "3. Selecione o modelo **Relação Completa dos Bens**.",
            "4. Marque as opções **imprimir bens baixados** e **ordenar pelo código**.",
            "5. Salve o arquivo em .TXT e faça o upload aqui."
        ]
    },
    "Prosoft (Excel/CSV)": {
        "titulo": "Como exportar no Prosoft",
        "passos": [
            "1. Acesse o menu **Contábil > Ativo Fixo > Processamentos > Relatórios > Movimentações**.",
            "2. Informe o código da empresa.",
            "3. Acesse a opção **Depreciações**.",
            "4. Marque as opções **Mostrar valores na tela**, **Imprimir bens sem valores de depreciação**, **imprimir valores p/ bens totalmente depreciados** e **Imprimir valores p/bens mantidos para venda**.",
            "5. Clique em **Processar** e salve em EXCEL. Se o Excel abrir com aviso de erro, clique em 'Sim', vá em **Salvar Como** e escolha **Pasta de Trabalho do Excel (.xlsx)**."
        ]
    },
    "Contmatic (Excel/CSV)": {
        "titulo": "Como exportar no Contmatic (Phoenix)",
        "passos": [
            "1. **Arquivo Principal (Cadastro):** Acesse Ativo Imobilizado > Relatórios > Cadastro de Bens. Gere em Excel/TXT.",
            "2. **Arquivo de Saldo (Opcional):** Se o cadastro não tiver saldo, acesse Relatórios > Mapa de Imobilizado/Depreciação.",
            "3. Salve ambos e utilize os campos de upload abaixo."
        ]
    },
    "Planilha Simplificada / Copiar e Colar": {
        "titulo": "Como usar a Planilha Simplificada",
        "passos": [
            "1. Baixe nosso modelo limpo clicando no botão de download.",
            "2. Preencha as colunas com os dados dos bens no seu Excel.",
            "3. Você tem duas opções para enviar os dados: Upload do arquivo ou Copiar e Colar."
        ]
    }
}

def exibir_manual(sistema_selecionado):
    manual = MANUAIS.get(sistema_selecionado)
    if manual:
        with st.expander(f"📚 Instruções: {manual['titulo']}", expanded=False):
            for passo in manual['passos']:
                st.markdown(passo)

# ==========================================
# 🧠 INTELIGÊNCIA CONTÁBIL
# ==========================================

CONTAS_DOMINIO = {
    "1": "VEICULOS", "2": "MAQUINAS E EQUIPAMENTOS", "3": "MOVEIS E UTENSILIOS",
    "4": "EDIFICIOS", "5": "TERRENOS", "6": "CONSTRUCOES",
    "7": "FERRAMENTAS E ACESSORIOS", "8": "COMPUTADORES E ACESSORIOS",
    "9": "INSTALACOES", "10": "BENF. IMOVEIS DE TERCEIROS", "11": "SOFTWARES"
}

def sugerir_conta_dominio(descricao_origem):
    if not descricao_origem: return "" 
    desc = descricao_origem.upper()
    if "VEIC" in desc or "CARRO" in desc: return "1"
    if "MAQ" in desc: return "2"
    if "MOVEIS" in desc or "MESA" in desc or "CADEIRA" in desc: return "3"
    if "COMPUT" in desc or "NOTEBOOK" in desc or "CPU" in desc: return "8"
    if "INSTALA" in desc: return "9"
    return ""

# --- Funções de Formatação ---

def format_currency_dominio(value_str):
    if not value_str or value_str == "nan": return "0,00"
    v = str(value_str).replace('R$', '').replace(' ', '').strip()
    if '.' in v and ',' in v: v = v.replace('.', '')
    elif '.' in v: v = v.replace('.', ',')
    return v if ',' in v else f"{v},00"

def format_date_dominio(date_str):
    if not date_str or date_str == "nan": return ""
    d = str(date_str).split(' ')[0]
    if '-' in d:
        p = d.split('-')
        return f"{p[2]}/{p[1]}/{p[0]}" if len(p[0]) == 4 else d
    return d

# --- Parsers ---

def parse_contmatic_universal(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file).astype(str)
    except: return pd.DataFrame()

    bens = []
    # Busca cabeçalhos dinâmicos
    cols = {c.upper().strip(): i for i, c in enumerate(df.columns)}
    
    for _, row in df.iterrows():
        cod = str(row[0]).strip()
        if not cod or "TOTAL" in cod.upper(): continue
        
        bens.append({
            "codigo": cod,
            "descricao": str(row[1]) if len(row) > 1 else "",
            "data_aquisicao": str(row[6]) if len(row) > 6 else "",
            "valor_original": str(row[7]) if len(row) > 7 else "0,00",
            "depreciacao_acumulada": "0,00",
            "conta_origem_desc": str(row[5]) if len(row) > 5 else "GERAL",
            "taxa": "0,00"
        })
    return pd.DataFrame(bens)

def parse_mapa_saldo_contmatic(uploaded_file):
    """Lê o arquivo de Mapa de Imobilizado para extrair saldos acumulados"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1', skiprows=1)
        else:
            df = pd.read_excel(uploaded_file, skiprows=1)
    except: return {}

    saldos = {}
    # Mapa de colunas baseado no arquivo enviado (Código, Descrição, Aquisição, Valor Aquisição, Valor Corrigido, Depr.Anterior...)
    for _, row in df.iterrows():
        try:
            cod = str(row.iloc[0]).strip()
            # O saldo acumulado é a soma da Depr.Anterior + Depr.Atual (ou apenas Anterior dependendo da data de corte)
            # Para segurança, somamos o que já foi depreciado até então
            anterior = float(str(row.iloc[5]).replace('.', '').replace(',', '.')) if not pd.isna(row.iloc[5]) else 0
            atual = float(str(row.iloc[7]).replace('.', '').replace(',', '.')) if not pd.isna(row.iloc[7]) else 0
            saldos[cod] = anterior + atual
        except: continue
    return saldos

# --- (Outros Parsers: IOB, Prosoft, Simplificada seguem a lógica anterior) ---
# [As funções parse_iob e parse_prosoft permanecem as mesmas das versões anteriores]

def parse_planilha_simplificada(df_input):
    bens = []
    for _, row in df_input.iterrows():
        cod = str(row.get('Código', '')).strip()
        if not cod or cod == "nan": continue
        bens.append({
            "codigo": cod, "descricao": str(row.get('Descrição', '')),
            "data_aquisicao": str(row.get('Data Aquisição', '')),
            "valor_original": str(row.get('Valor Original', '0,00')),
            "depreciacao_acumulada": str(row.get('Depreciação Acumulada', '0,00')),
            "conta_origem_desc": str(row.get('Grupo ou Conta', 'GERAL')), "taxa": "0,00"
        })
    return pd.DataFrame(bens)

# --- Gerador TXT ---

def generate_dominio_txt(df, configs, de_para):
    output = io.StringIO()
    for _, row in df.iterrows():
        campos = [""] * 78
        campos[1] = "0450"
        campos[2] = str(row['codigo'])[:15]
        campos[3] = str(row['descricao'])[:250]
        campos[4] = format_date_dominio(row['data_aquisicao'])
        campos[5] = de_para.get(row['conta_origem_desc'], configs['conta_contabil_padrao'])
        campos[6] = configs['centro_custo_padrao']
        campos[8], campos[9], campos[11] = "B", "I", "N"
        val = format_currency_dominio(row['valor_original'])
        campos[42], campos[49], campos[52] = val, val, val
        
        # Saldo Acumulado
        acum = format_currency_dominio(row['depreciacao_acumulada'])
        if acum != "0,00":
            campos[53], campos[57], campos[61] = "S", "S", "S"
            campos[58], campos[62] = configs['data_saldo'], configs['data_saldo']
            campos[59], campos[63] = acum, acum
        else:
            campos[53], campos[57], campos[61] = "N", "N", "N"
            
        output.write("|" + "|".join(campos[1:]) + "|\n")
    return output.getvalue()

# --- Interface ---

st.sidebar.header("⚙️ Configurações")
sistema = st.sidebar.selectbox("Sistema de Origem", ["IOB / Folhamatic", "Prosoft (Excel/CSV)", "Contmatic (Excel/CSV)", "Planilha Simplificada"])

configs = {
    'centro_custo_padrao': st.sidebar.text_input("Centro de Custo", "1"),
    'data_saldo': st.sidebar.text_input("Data do Saldo", "31/12/2024"),
    'conta_contabil_padrao': st.sidebar.text_input("Conta Padrão", "1")
}

st.title("🚀 Super Conversor Patrimônio")
exibir_manual(sistema)

if 'df_bens' not in st.session_state: st.session_state.df_bens = pd.DataFrame()

# Lógica de Upload
if sistema == "Contmatic (Excel/CSV)":
    col1, col2 = st.columns(2)
    with col1:
        f1 = st.file_uploader("Arquivo de Cadastro (Obrigatório)", type=["xlsx", "csv", "txt"])
    with col2:
        f2 = st.file_uploader("Mapa de Imobilizado (Opcional - Para Saldos)", type=["xlsx", "csv"])
    
    if f1 and st.button("Processar Contmatic"):
        df_main = parse_contmatic_universal(f1)
        if f2:
            saldos_map = parse_mapa_saldo_contmatic(f2)
            df_main['depreciacao_acumulada'] = df_main['codigo'].map(lambda x: str(saldos_map.get(x, "0,00")))
        st.session_state.df_bens = df_main
        st.rerun()

elif sistema == "Planilha Simplificada":
    # [Lógica anterior de Copiar e Colar]
    st.markdown("### Copie e Cole do Excel abaixo:")
    df_modelo = pd.DataFrame(columns=["Código", "Descrição", "Data Aquisição", "Valor Original", "Depreciação Acumulada", "Grupo ou Conta"], index=range(5))
    edited = st.data_editor(df_modelo, num_rows="dynamic", width="stretch")
    if st.button("Processar Tabela"):
        st.session_state.df_bens = parse_planilha_simplificada(edited)
        st.rerun()

else:
    f = st.file_uploader("Suba o arquivo", type=["txt", "xlsx", "csv"])
    if f and st.button("Processar Arquivo"):
        # Chamada dos parsers IOB/Prosoft aqui
        pass

# De-Para e Exportação
if not st.session_state.df_bens.empty:
    df = st.session_state.df_bens
    st.subheader("🤖 De-Para de Contas")
    grupos = df['conta_origem_desc'].unique()
    de_para = {}
    cols = st.columns(3)
    for i, g in enumerate(grupos):
        with cols[i % 3]:
            de_para[g] = st.text_input(f"De: {g}", value=sugerir_conta_dominio(g))
    
    if st.button("🚀 Gerar TXT para Domínio", type="primary"):
        txt = generate_dominio_txt(df, configs, de_para)
        st.download_button("📥 Baixar Arquivo (ANSI)", data=txt.encode('cp1252', errors='replace'), file_name="import_dominio.txt")
        st.info("Caminho: Contabilidade > Utilitários > Importação > Importação Padrão > Leiaute Domínio com Separador.")

if st.sidebar.button("Limpar Dados"):
    st.session_state.df_bens = pd.DataFrame()
    st.rerun()