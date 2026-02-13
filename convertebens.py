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
    "IOB": {
        "titulo": "Como exportar o arquivo no IOB",
        "passos": [
            "1. Acesse o módulo **Office Contábil**.",
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
    }
}

def exibir_manual(sistema_selecionado):
    """Renderiza o manual em texto na tela principal."""
    manual = MANUAIS.get(sistema_selecionado)
    if manual:
        with st.expander(f"📚 Instruções: {manual['titulo']}", expanded=False):
            for passo in manual['passos']:
                st.markdown(passo)
            st.info("💡 Dica: Se o arquivo der erro, verifique se não há quebras de linha nas descrições.")

# ==========================================
# 🧠 INTELIGÊNCIA CONTÁBIL
# ==========================================

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
    if not descricao_origem: return "" 
    desc = descricao_origem.upper()
    
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
    
    for cod, nome_dominio in CONTAS_DOMINIO.items():
        nome_clean = nome_dominio.replace("S ", " ").replace("ES ", " ").strip()
        if nome_clean in desc: return cod
            
    return ""

# --- Funções Auxiliares ---

def format_currency_dominio(value_str):
    if not value_str or isinstance(value_str, (int, float)):
        value_str = str(value_str)
    value_str = value_str.strip()
    if not value_str: return "0,00"
    
    value_str = value_str.replace('"', '').replace("'", "").strip()
    
    if '.' in value_str and ',' in value_str: 
        value_str = value_str.replace('.', '')
    if '.' in value_str and ',' not in value_str: 
        value_str = value_str.replace('.', ',')
        
    return value_str

def format_date_dominio(date_str):
    if not date_str: return ""
    s_date = str(date_str).strip()
    if " " in s_date:
        s_date = s_date.split(" ")[0]
    
    if "-" in s_date:
        try:
            parts = s_date.split("-")
            if len(parts[0]) == 4:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except: pass
            
    return s_date

# --- Parsers ---

def parse_iob(file_content):
    lines = file_content.split('\n')
    bens = []
    current_bem = {}
    capturing = False
    codigos_vistos = {} 
    
    re_codigo_desc = re.compile(r"Codigo:\s+([\d-]+)\s+(.+)")
    re_data_aquisicao = re.compile(r"Data Aquisicao\s+(\d{2}/\d{2}/\d{4})")
    re_valor_original = re.compile(r"Valor Original\s+([\d\.]+,\d{2})")
    re_inicio_deprec = re.compile(r"Inicio Depreciacao\s+(\d{2}/\d{4})")
    re_nota_fiscal = re.compile(r"Nota Fiscal\s+(\d+)")
    re_taxa = re.compile(r"%\s*Dep\.\s*(\d{1,3},\d{2})")
    re_taxa_isolada = re.compile(r"^\s*(\d{1,3},\d{2})\s*$") 
    re_saldos_line = re.compile(r"^\s*([\d\.]+,\d{2})\s+([\d\.]+,\d{2})")
    re_conta_contabil = re.compile(r"Conta\s+Contabil\s+[\d\.]+\s+-\s+(.+)")

    expecting_saldos = False

    for line in lines:
        line_clean = line.strip()
        
        if ("Relacao Completa" in line_clean or "Periodo:" in line_clean) and "SALDOS" not in line_clean: continue
        if "-------" in line_clean and "SALDOS" not in line_clean: continue

        match_cod = re_codigo_desc.search(line_clean)
        if match_cod:
            if current_bem: bens.append(current_bem)
            
            raw_cod = match_cod.group(1).strip().replace('-', '')
            if raw_cod in codigos_vistos:
                codigos_vistos[raw_cod] += 1
                final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
            else:
                codigos_vistos[raw_cod] = 0
                final_cod = raw_cod
            
            current_bem = {
                "codigo": final_cod,
                "descricao": match_cod.group(2).strip(),
                "data_aquisicao": "", "valor_original": "0,00",
                "inicio_depreciacao": "", "taxa": "0,00", "nota_fiscal": "",
                "depreciacao_acumulada": "0,00", "baixado": False,
                "conta_origem_desc": "INDEFINIDA",
                "duplicado": True if raw_cod != final_cod else False
            }
            capturing = True
            expecting_saldos = False
            continue
        
        if capturing and current_bem:
            if "BEM BAIXADO" in line_clean: current_bem["baixado"] = True
            m_conta = re_conta_contabil.search(line_clean)
            if m_conta: current_bem["conta_origem_desc"] = m_conta.group(1).strip()
            m_data = re_data_aquisicao.search(line_clean)
            if m_data: current_bem["data_aquisicao"] = m_data.group(1)
            m_nf = re_nota_fiscal.search(line_clean)
            if m_nf: current_bem["nota_fiscal"] = m_nf.group(1)
            m_val = re_valor_original.search(line_clean)
            if m_val: current_bem["valor_original"] = m_val.group(1)
            m_ini = re_inicio_deprec.search(line_clean)
            if m_ini: current_bem["inicio_depreciacao"] = m_ini.group(1)
            m_taxa = re_taxa.search(line_clean)
            if not m_taxa: m_taxa = re_taxa_isolada.search(line_clean)
            if m_taxa:
                try:
                    if 0 < float(m_taxa.group(1).replace(',', '.')) <= 100:
                        current_bem["taxa"] = m_taxa.group(1)
                except: pass
            if "SALDOS" in line_clean: expecting_saldos = True; continue;
            if expecting_saldos:
                m_saldos = re_saldos_line.search(line_clean)
                if m_saldos:
                    current_bem["depreciacao_acumulada"] = m_saldos.group(2)
                    expecting_saldos = False

    if current_bem: bens.append(current_bem)
    return pd.DataFrame(bens)

def parse_prosoft_universal(uploaded_file):
    filename = uploaded_file.name.lower()
    rows = []
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)
            rows = df_raw.fillna("").astype(str).values.tolist()
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
            return pd.DataFrame()
    else:
        try: stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        except: stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
        reader = csv.reader(stringio)
        rows = list(reader)

    bens = []
    current_group_desc = "GERAL"
    start_processing = False
    codigos_vistos = {} 
    
    for row in rows:
        if not row: continue
        row_str = "".join(str(x) for x in row)
        
        if "Código do bem" in row_str or "Codigo do bem" in row_str:
            start_processing = True
            continue
            
        if not start_processing: continue
            
        col0 = str(row[0]).strip() if len(row) > 0 else ""
        col2 = str(row[2]).strip() if len(row) > 2 else ""
        
        if "TOTAL" in col2.upper() or "TOTAL" in col0.upper(): continue

        if col0 == "" and col2 != "":
            current_group_desc = col2
            continue
            
        if len(row) > 8 and col0 != "":
            try:
                raw_cod = col0.replace('-', '').replace('/', '')
                if "TOTAL" in str(row[2]).upper(): continue

                if raw_cod in codigos_vistos:
                    codigos_vistos[raw_cod] += 1
                    final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
                else:
                    codigos_vistos[raw_cod] = 0
                    final_cod = raw_cod

                def get_col(idx): return str(row[idx]).strip() if len(row) > idx else ""

                bem = {
                    "codigo": final_cod,
                    "descricao": get_col(2),
                    "data_aquisicao": get_col(3),
                    "valor_original": get_col(8),
                    "inicio_depreciacao": "", 
                    "taxa": get_col(5),
                    "nota_fiscal": "",
                    "depreciacao_acumulada": get_col(12),
                    "baixado": False,
                    "conta_origem_desc": current_group_desc,
                    "duplicado": True if raw_cod != final_cod else False
                }
                bens.append(bem)
            except Exception as e:
                continue
            
    return pd.DataFrame(bens)

# --- Gerador Domínio ---

def generate_dominio_txt(df, configs, de_para_contas):
    output = io.StringIO()
    
    for _, row in df.iterrows():
        campos = [""] * 77
        campos[1] = "0450"
        
        campos[2] = re.sub(r'[^a-zA-Z0-9-]', '', str(row.get('codigo', '')))[:15]
        
        desc_limpa = str(row.get('descricao', ''))
        desc_limpa = desc_limpa.replace("_x000D_", " ")
        desc_limpa = desc_limpa.replace("|", "-").replace("\n", " ").replace("\r", "")
        desc_limpa = re.sub(' +', ' ', desc_limpa).strip()
        
        campos[3] = desc_limpa[:250]
        
        campos[4] = format_date_dominio(row.get('data_aquisicao', ''))
        
        conta_origem = row.get('conta_origem_desc', '')
        conta_final = de_para_contas.get(conta_origem)
        if not conta_final or str(conta_final).strip() == "":
            conta_final = configs['conta_contabil_padrao']
        campos[5] = str(conta_final)
        campos[6] = str(configs['centro_custo_padrao'])
        
        campos[8] = "B"
        campos[9] = "I"
        campos[11] = "N"
        campos[12] = desc_limpa 
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
        
        val_orig = format_currency_dominio(row.get('valor_original', '0,00'))
        campos[42] = val_orig
        campos[49] = val_orig
        campos[50] = "0,00"
        campos[51] = "0,00"
        campos[52] = val_orig
        
        baixado = row.get('baixado', False)
        taxa = format_currency_dominio(row.get('taxa', '0,00'))
        tem_taxa = taxa != "0,00"
        val_acum = format_currency_dominio(row.get('depreciacao_acumulada', '0,00'))
        tem_acumulado = val_acum != "0,00" and val_acum != "0"

        if tem_acumulado: campos[53] = "S"
        elif baixado or not tem_taxa: campos[53] = "N"
        else: campos[53] = "S"
            
        campos[54] = "N"
        campos[55] = taxa
        
        ini_dep = row.get('inicio_depreciacao', '')
        if ini_dep and len(ini_dep) == 7: dt_ini = f"01/{ini_dep}"
        elif campos[4]: dt_ini = campos[4]
        else: dt_ini = ""
        campos[56] = dt_ini
        
        if tem_acumulado:
            campos[57] = "S"
            campos[58] = configs['data_saldo']
            campos[59] = val_acum
        else: campos[57] = "N"

        campos[60] = dt_ini
        if tem_acumulado:
            campos[61] = "S"
            campos[62] = configs['data_saldo']
            campos[63] = val_acum
        else: campos[61] = "N"
            
        campos[64] = taxa
        nf = re.sub(r'\D', '', str(row.get('nota_fiscal', '')))
        campos[65] = nf[:6]

        line = "|".join(campos)
        if not line.startswith("|"): line = "|" + line
        output.write(line + "\n")

    return output.getvalue()

# --- Interface Gráfica ---

st.sidebar.header("⚙️ Central de Configuração")
sistema = st.sidebar.selectbox("Selecione o Sistema de Origem", ["IOB", "Prosoft (Excel/CSV)"])

st.sidebar.markdown("---")
st.sidebar.subheader("Parâmetros Domínio")
centro_custo = st.sidebar.text_input("Centro de Custo (Campo 6)", value="1")
data_saldo = st.sidebar.text_input("Data do Saldo Acumulado", value="31/12/2025")
conta_padrao = st.sidebar.text_input("Conta Padrão (Fallback)", value="1")

configs = {'centro_custo_padrao': centro_custo, 'conta_contabil_padrao': conta_padrao, 'data_saldo': data_saldo}

with st.sidebar.expander("📋 Tabela de Contas Domínio"):
    st.table(pd.DataFrame.from_dict(CONTAS_DOMINIO, orient='index', columns=['Descrição']))

st.title("🚀 SUPER CONVERSOR DOMÍNIO PATRIMÔNIO")
st.markdown(f"Importação de Ativo Imobilizado: **{sistema} > Domínio**")

# Exibe Manual (Texto Puro)
exibir_manual(sistema)

if 'df_bens' not in st.session_state: st.session_state.df_bens = pd.DataFrame()

file_types = ["txt"] if sistema == "IOB" else ["csv", "xlsx", "xls"]
uploaded_file = st.file_uploader("Carregue o arquivo", type=file_types)

if uploaded_file:
    if st.session_state.df_bens.empty:
        with st.spinner(f"Processando layout {sistema}..."):
            try:
                if sistema == "IOB":
                    content = uploaded_file.getvalue().decode("latin-1")
                    st.session_state.df_bens = parse_iob(content)
                elif sistema == "Prosoft (Excel/CSV)":
                    st.session_state.df_bens = parse_prosoft_universal(uploaded_file)
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

if not st.session_state.df_bens.empty:
    df = st.session_state.df_bens
    col1, col2, col3 = st.columns(3)
    col1.metric("Bens Identificados", len(df))
    col2.metric("Bens com Saldo", len(df[df['depreciacao_acumulada'] != "0,00"]))
    
    duplicados = df.get('duplicado', pd.Series([False]*len(df)))
    qtd_dup = duplicados.sum()
    col3.metric("Códigos Duplicados (Renomeados)", qtd_dup)
    
    if qtd_dup > 0:
        st.warning("⚠️ Atenção: Foram encontrados códigos duplicados. Eles foram renomeados (ex: 100-1).")
    
    st.markdown("---")
    st.subheader("🤖 De-Para Inteligente de Contas")
    
    contas_origem_unicas = sorted(list(df['conta_origem_desc'].unique()))
    de_para_map = {}
    cols = st.columns(3)
    for i, conta_desc in enumerate(contas_origem_unicas):
        col = cols[i % 3]
        with col:
            sugestao = sugerir_conta_dominio(conta_desc)
            icon = "✅" if sugestao else "⚠️"
            label_text = f"{icon} {conta_desc}"
            if len(label_text) > 40: label_text = label_text[:37] + "..."
            novo_cod = st.text_input(label=label_text, value=sugestao, key=f"conta_{i}", help=f"Original: {conta_desc}", placeholder="Vazio = Padrão")
            de_para_map[conta_desc] = novo_cod

    st.markdown("---")
    if st.button("🚀 Gerar Arquivo de Importação", type="primary"):
        txt_output = generate_dominio_txt(df, configs, de_para_map)
        st.success("Arquivo gerado com sucesso!")
        st.download_button(label="📥 Baixar TXT (Registro 0450)", data=txt_output, file_name="importacao_bens_dominio.txt", mime="text/plain")
    
    with st.expander("🔍 Conferência Detalhada dos Dados"):
        st.dataframe(df)

if st.sidebar.button("Limpar / Novo Arquivo"):
    st.session_state.df_bens = pd.DataFrame()

    st.rerun()
