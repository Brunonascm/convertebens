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
    "Exactus (Excel/CSV)": {
        "titulo": "Como exportar no Exactus",
        "passos": [
            "1. Acesse o Relatórios - SGI > Cadastros > Item",
            "2. Exporte o arquivo no formato Excel (.xls/.xlsx) ou CSV.",
            "3. Salve o arquivo e faça o upload abaixo."
        ]
    },
    "Questor (Excel/CSV)": {
        "titulo": "Como exportar no Questor",
        "passos": [
            "1. Acesse o Módulo Controle Patrimonial > Informe o código da empresa > Consultas > Consultas Bens Ativos",
            "2. Marque as opções da tela e clique em 'Executar'",
            "3. Clique com o botão direito sobre os bens > Exportar > Excel"
        ]
    },
    "SCI / Único (Excel/TXT)": {
        "titulo": "Como exportar no SCI / Único",
        "passos": [
            "1. Acesse o sistema SCI Único / Patrimônio.",
            "2. Exporte o arquivo de cadastro de bens em formato TXT (Layout Padrão) ou gere o Relatório de Cadastro de Bens em Excel.",
            "3. Faça o upload do arquivo gerado abaixo."
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
    if "VEIC" in desc or "CARRO" in desc or "MOTO" in desc or "CAMINH" in desc: return "1"
    if "MAQ" in desc or "INDUS" in desc: return "2"
    if "MOVEIS" in desc or "MESA" in desc or "CADEIRA" in desc or "MOBIL" in desc: return "3"
    if "EDIFIC" in desc or "PREDIO" in desc or "SALA" in desc or "GALPAO" in desc: return "4"
    if "TERRENO" in desc or "LOTE" in desc: return "5"
    if "CONSTRUC" in desc or "OBRA" in desc: return "6"
    if "FERRAMENT" in desc: return "7"
    if "COMPUT" in desc or "NOTEBOOK" in desc or "CPU" in desc or "INFORM" in desc or "PC" in desc or "MONITOR" in desc: return "8"
    if "INSTALA" in desc or "AR COND" in desc: return "9"
    if "BENFEITORIA" in desc: return "10"
    if "SOFT" in desc or "SISTEMA" in desc or "PROGRAMA" in desc: return "11"
    
    for cod, nome_dominio in CONTAS_DOMINIO.items():
        nome_clean = nome_dominio.replace("S ", " ").replace("ES ", " ").strip()
        if nome_clean in desc: return cod
            
    return ""

# --- Funções de Formatação ---

def format_currency_dominio(value_str):
    if not value_str or value_str == "nan": return "0,00"
    v = str(value_str).replace('R$', '').replace(' ', '').replace('"', '').replace("'", "").strip()
    if not v: return "0,00"
    if '.' in v and ',' in v: v = v.replace('.', '')
    elif '.' in v: v = v.replace('.', ',')
    return v if ',' in v else f"{v},00"

def format_date_dominio(date_str):
    if not date_str or date_str == "nan": return ""
    d = str(date_str).split(' ')[0].strip()
    if '-' in d:
        try:
            p = d.split('-')
            return f"{p[2]}/{p[1]}/{p[0]}" if len(p[0]) == 4 else d
        except: pass
    return d

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

def parse_contmatic_universal(uploaded_file):
    filename = uploaded_file.name.lower()
    rows = []
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)
            rows = df_raw.fillna("").astype(str).values.tolist()
        except Exception as e:
            st.error(f"Erro ao ler Excel Contmatic: {e}")
            return pd.DataFrame()
    else:
        try: stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        except: stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
        
        try:
            sniffer = csv.Sniffer()
            sample = stringio.read(2048)
            stringio.seek(0)
            dialect = sniffer.sniff(sample)
            reader = csv.reader(stringio, dialect)
        except:
            stringio.seek(0)
            reader = csv.reader(stringio, delimiter=',') 
            
        rows = list(reader)

    bens = []
    header_found = False
    col_map = {}
    codigos_vistos = {}

    for row in rows:
        if not row: continue
        row_str = " ".join(str(x) for x in row).upper()
        
        if not header_found and ("CÓDIGO" in row_str or "CODIGO" in row_str) and "AQUISIÇÃO" in row_str:
            header_found = True
            for i, col_name in enumerate(row):
                col_clean = str(col_name).strip().upper()
                if col_clean == "CÓDIGO" or col_clean == "CODIGO": col_map['codigo'] = i
                elif "DESCRIÇÃO" in col_clean or "DESCRICAO" in col_clean: col_map['descricao'] = i
                elif "GRUPO" in col_clean: col_map['grupo'] = i
                elif "AQUISIÇÃO" in col_clean or "AQUISICAO" in col_clean: col_map['aquisicao'] = i
                elif "COMPRA" in col_clean or "AQUISICAO" in col_clean: col_map['valor'] = i
            continue
            
        if not header_found: continue
        
        def get_col(key):
            if key in col_map and col_map[key] < len(row):
                val = str(row[col_map[key]]).strip()
                if val.upper() == "NAN": return ""
                return val
            return ""

        cod = get_col('codigo')
        if not cod or cod == "" or "TOTAL" in cod.upper(): continue
            
        try:
            raw_cod = cod.replace('-', '').replace('/', '')
            
            if raw_cod in codigos_vistos:
                codigos_vistos[raw_cod] += 1
                final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
            else:
                codigos_vistos[raw_cod] = 0
                final_cod = raw_cod
                
            grupo_nome = get_col('grupo')
            if grupo_nome: grupo_nome = f"GRUPO {grupo_nome}"
            else: grupo_nome = "GERAL"

            bem = {
                "codigo": final_cod,
                "descricao": get_col('descricao'),
                "data_aquisicao": get_col('aquisicao'),
                "valor_original": get_col('valor') or "0,00",
                "depreciacao_acumulada": "0,00", 
                "conta_origem_desc": grupo_nome,
                "taxa": "0,00",
                "duplicado": True if raw_cod != final_cod else False
            }
            bens.append(bem)
        except Exception:
            continue
            
    return pd.DataFrame(bens)

def parse_mapa_saldo_contmatic(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                sniffer = csv.Sniffer()
                stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
                sample = stringio.read(2048)
                stringio.seek(0)
                dialect = sniffer.sniff(sample)
                reader = csv.reader(stringio, dialect)
                rows = list(reader)
            except:
                stringio.seek(0)
                reader = csv.reader(stringio, delimiter=',')
                rows = list(reader)
        else:
            df = pd.read_excel(uploaded_file, header=None)
            rows = df.fillna("").astype(str).values.tolist()
    except: return {}

    saldos = {}
    header_found = False
    col_map = {}

    for row in rows:
        if not row: continue
        row_str = " ".join(str(x) for x in row).upper()
        
        if not header_found and "CÓDIGO" in row_str and ("DEPR.ATUAL" in row_str or "ATUAL" in row_str or "ACUMULADA" in row_str):
            header_found = True
            for i, col_name in enumerate(row):
                col_clean = str(col_name).strip().upper()
                if col_clean == "CÓDIGO" or col_clean == "CODIGO": col_map['codigo'] = i
                elif "DEPR.ATUAL" in col_clean or "DEPR. ATUAL" in col_clean or "ACUMULADA" in col_clean: col_map['acumulada'] = i
            continue
            
        if not header_found: continue
        
        try:
            cod_idx = col_map.get('codigo')
            val_idx = col_map.get('acumulada')
            
            if cod_idx is None or val_idx is None or cod_idx >= len(row) or val_idx >= len(row): continue
            
            cod = str(row[cod_idx]).strip()
            if not cod or "TOTAL" in cod.upper(): continue
            
            cod = cod.replace('-', '').replace('/', '')
            
            val_str = str(row[val_idx]).strip()
            if val_str.upper() == "NAN" or not val_str: val_str = "0"
            
            if '.' in val_str and ',' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
                
            atual = float(val_str)
            saldos[cod] = f"{atual:.2f}".replace('.', ',')
        except: continue
        
    return saldos

def parse_exactus(uploaded_file):
    def clean_numeric_str(v_str):
        if not v_str: return 0.0
        v_str = str(v_str).strip()
        if '.' in v_str and ',' in v_str:
            last_dot = v_str.rfind('.')
            last_comma = v_str.rfind(',')
            if last_comma > last_dot: v_str = v_str.replace('.', '').replace(',', '.')
            else: v_str = v_str.replace(',', '')
        elif ',' in v_str: v_str = v_str.replace(',', '.')
        try: return float(re.sub(r'[^\d.-]', '', v_str))
        except: return 0.0

    try:
        content = uploaded_file.getvalue().decode("latin-1")
        if "<table" in content.lower():
            dfs = pd.read_html(io.StringIO(content))
            rows = dfs[0].fillna("").astype(str).values.tolist() if dfs else []
        elif "\x00" in content[:100]:
            df_raw = pd.read_excel(uploaded_file, header=None)
            rows = df_raw.fillna("").astype(str).values.tolist()
        else:
            stringio = io.StringIO(content)
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(stringio.read(2048))
                stringio.seek(0)
                reader = csv.reader(stringio, dialect)
            except Exception:
                stringio.seek(0)
                reader = csv.reader(stringio, delimiter=',')
            rows = list(reader)
    except Exception:
        return pd.DataFrame()

    bens = []
    current_bem = {}
    current_conta = "GERAL"
    codigos_vistos = {}

    for row in rows:
        if not row: continue
        row_clean = [str(x).strip() for x in row]
        row_str = " | ".join(row_clean).upper()
        
        if "CONTA:" in row_str:
            for i, cell in enumerate(row_clean):
                if "CONTA:" in cell.upper():
                    if len(row_clean) > i + 2 and row_clean[i+2]: current_conta = row_clean[i+2]
                    elif len(row_clean) > i + 1 and row_clean[i+1]: current_conta = row_clean[i+1]
            continue
            
        if "ITEM:" in row_str:
            if current_bem: bens.append(current_bem)
            
            raw_cod = ""
            desc = ""
            parts = [p.strip() for p in re.split(r'[,;\t|]', row_clean[0])] if len(row_clean) == 1 else row_clean
                
            for i, cell in enumerate(parts):
                if "ITEM:" in cell.upper():
                    if len(parts) > i + 2: raw_cod = parts[i+2].replace('-', '').replace('/', '')
                    if len(parts) > i + 4: desc = parts[i+4]
                    break
                    
            if not raw_cod: continue

            if raw_cod in codigos_vistos:
                codigos_vistos[raw_cod] += 1
                final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
            else:
                codigos_vistos[raw_cod] = 0
                final_cod = raw_cod
                
            current_bem = {
                "codigo": final_cod,
                "descricao": desc,
                "conta_origem_desc": current_conta,
                "data_aquisicao": "",
                "valor_original": "0,00",
                "depreciacao_acumulada": "0,00",
                "taxa": "0,00",
                "duplicado": True if raw_cod != final_cod else False
            }
            continue
            
        if not current_bem: continue
        
        parts = row_clean if len(row_clean) > 1 else [p.strip() for p in re.split(r'[,;\t|]', row_clean[0])]
        
        if "DT.AQUISIÇÃO:" in row_str or "DT.AQUISICAO:" in row_str:
            for i, cell in enumerate(parts):
                if "DT.AQUISIÇÃO" in cell.upper() or "DT.AQUISICAO" in cell.upper():
                    if len(parts) > i + 1 and parts[i+1]:
                        current_bem['data_aquisicao'] = parts[i+1]
                    break
                    
        if "VALOR ATUALIZADO:" in row_str:
            nums = [clean_numeric_str(x) for x in parts if clean_numeric_str(x) > 0]
            if nums:
                current_bem['valor_original'] = f"{nums[0]:.2f}".replace('.', ',')
                
        if "RESIDUAL CONTÁBIL:" in row_str or "RESIDUAL CONTABIL:" in row_str:
            nums = [clean_numeric_str(x) for x in parts if clean_numeric_str(x) > 0]
            if len(nums) >= 2:
                v_base = nums[0]
                v_res = nums[1]
                acumulada = v_base - v_res
                if acumulada < 0: acumulada = 0.0
                current_bem['depreciacao_acumulada'] = f"{acumulada:.2f}".replace('.', ',')

    if current_bem: bens.append(current_bem)
    return pd.DataFrame(bens)

def parse_questor_universal(uploaded_file):
    filename = uploaded_file.name.lower()
    rows = []
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)
            rows = df_raw.fillna("").astype(str).values.tolist()
        except Exception as e:
            st.error(f"Erro ao ler Excel Questor: {e}")
            return pd.DataFrame()
    else:
        try: stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        except: stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
        
        try:
            sniffer = csv.Sniffer()
            sample = stringio.read(2048)
            stringio.seek(0)
            dialect = sniffer.sniff(sample)
            reader = csv.reader(stringio, dialect)
        except:
            stringio.seek(0)
            reader = csv.reader(stringio, delimiter=',') 
            
        rows = list(reader)

    bens = []
    header_found = False
    col_map = {}
    codigos_vistos = {}

    for row in rows:
        if not row: continue
        row_str = " ".join(str(x) for x in row).upper()
        
        if not header_found and ("NÚMERO BEM" in row_str or "NUMERO BEM" in row_str) and "DESCRIÇÃO" in row_str:
            header_found = True
            for i, col_name in enumerate(row):
                col_clean = str(col_name).strip().upper()
                if "NÚMERO BEM" in col_clean or "NUMERO BEM" in col_clean: col_map['codigo'] = i
                elif "DESCRIÇÃO" in col_clean or "DESCRICAO" in col_clean: col_map['descricao'] = i
                elif "DATA AQUISIÇÃO" in col_clean or "DATA AQUISICAO" in col_clean: col_map['aquisicao'] = i
                elif col_clean == "VALOR": col_map['valor'] = i
                elif "TOTAL ENCARGOS" in col_clean: 
                    if 'acumulada' not in col_map: col_map['acumulada'] = i
                elif "CONTA CONTÁBIL" in col_clean or "CONTA CONTABIL" in col_clean: col_map['grupo'] = i
                elif "PERCENTUAL ENCARGO" in col_clean: col_map['taxa'] = i
            continue
            
        if not header_found: continue
        
        def get_col(key):
            if key in col_map and col_map[key] < len(row):
                val = str(row[col_map[key]]).strip()
                if val.upper() == "NAN": return ""
                return val
            return ""

        cod_raw = get_col('codigo')
        if not cod_raw or cod_raw == "" or "TOTAL" in cod_raw.upper() or "SITUAÇÃO" in cod_raw.upper(): continue
            
        try:
            cod = cod_raw.split('.')[0] if '.' in cod_raw else cod_raw
            cod = cod.replace('-', '').replace('/', '')
            
            if not cod: continue
            
            if cod in codigos_vistos:
                codigos_vistos[cod] += 1
                final_cod = f"{cod}-{codigos_vistos[cod]}"
            else:
                codigos_vistos[cod] = 0
                final_cod = cod
                
            grupo_raw = get_col('grupo')
            if grupo_raw: 
                grupo_limpo = grupo_raw.split('.')[0] if '.' in grupo_raw else grupo_raw
                grupo_nome = f"CONTA {grupo_limpo}"
            else: 
                grupo_nome = "GERAL"

            bem = {
                "codigo": final_cod,
                "descricao": get_col('descricao'),
                "data_aquisicao": get_col('aquisicao'),
                "valor_original": format_currency_dominio(get_col('valor')),
                "depreciacao_acumulada": format_currency_dominio(get_col('acumulada')), 
                "conta_origem_desc": grupo_nome,
                "taxa": format_currency_dominio(get_col('taxa')),
                "duplicado": True if cod != final_cod else False
            }
            bens.append(bem)
        except Exception:
            continue
            
    return pd.DataFrame(bens)

def parse_sci_unico_universal(uploaded_file):
    filename = uploaded_file.name.lower()
    bens = []
    codigos_vistos = {}
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)
            rows = df_raw.fillna("").astype(str).values.tolist()
            
            current_bem = {}
            for row in rows:
                row_clean = [str(x).strip() for x in row]
                col0 = row_clean[0].upper()
                
                if "DESCRIÇÃO:" in col0 or "DESCRICAO:" in col0:
                    if current_bem:
                        bens.append(current_bem)
                    current_bem = {
                        "codigo": "", "descricao": "", "data_aquisicao": "",
                        "valor_original": "0,00", "depreciacao_acumulada": "0,00",
                        "conta_origem_desc": "GERAL", "taxa": "0,00", "duplicado": False
                    }
                    val = row_clean[1] if len(row_clean) > 1 else ""
                    if " - " in val:
                        parts = val.split(" - ", 1)
                        raw_cod = parts[0].strip().replace('-', '').replace('/', '')
                        current_bem["descricao"] = parts[1].strip()
                    else:
                        raw_cod = str(len(bens) + 1)
                        current_bem["descricao"] = val
                        
                    if raw_cod in codigos_vistos:
                        codigos_vistos[raw_cod] += 1
                        current_bem["codigo"] = f"{raw_cod}-{codigos_vistos[raw_cod]}"
                        current_bem["duplicado"] = True
                    else:
                        codigos_vistos[raw_cod] = 0
                        current_bem["codigo"] = raw_cod
                        
                if not current_bem: continue
                    
                if "DATA AQUISIÇÃO:" in col0 or "DATA AQUISICAO:" in col0:
                    current_bem["data_aquisicao"] = row_clean[1] if len(row_clean) > 1 else ""
                    
                if "CONTA CONTÁBIL:" in col0 or "CONTA CONTABIL:" in col0:
                    current_bem["conta_origem_desc"] = row_clean[1] if len(row_clean) > 1 and row_clean[1] else "GERAL"
                    
                if "VALOR ORIGINAL:" in col0:
                    val_str = row_clean[1] if len(row_clean) > 1 else "0"
                    try:
                        val_float = float(val_str.replace(",", ".")) if "." not in val_str or "," in val_str else float(val_str)
                        current_bem["valor_original"] = f"{val_float:.2f}".replace('.', ',')
                    except: pass
                        
                for i, cell in enumerate(row_clean):
                    if "DEPR. ACUMULADA:" in cell.upper() or "DEPR.ACUMULADA:" in cell.upper() or "DEPR. ACUM." in cell.upper():
                        if len(row_clean) > i + 1 and row_clean[i+1]:
                            val_str = row_clean[i+1]
                            try:
                                val_float = float(val_str.replace(",", ".")) if "." not in val_str or "," in val_str else float(val_str)
                                current_bem["depreciacao_acumulada"] = f"{val_float:.2f}".replace('.', ',')
                            except: pass
                            
            if current_bem: bens.append(current_bem)
        except Exception as e:
            st.error(f"Erro ao ler Excel SCI: {e}")
    else:
        try:
            content = uploaded_file.getvalue().decode("latin-1")
            lines = content.split('\n')
            
            for line in lines:
                line_clean = line.strip()
                if not line_clean.startswith('10|'): continue
                    
                parts = line_clean.split('|')
                if len(parts) < 16: continue
                    
                raw_cod = str(parts[15]).strip()
                if not raw_cod: raw_cod = str(len(bens) + 1)
                raw_cod = raw_cod.replace('-', '').replace('/', '')
                
                if raw_cod in codigos_vistos:
                    codigos_vistos[raw_cod] += 1
                    final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
                    dup = True
                else:
                    codigos_vistos[raw_cod] = 0
                    final_cod = raw_cod
                    dup = False
                    
                def fmt_curr(v):
                    if not v: return "0,00"
                    v = v.replace('R$', '').replace(' ', '').strip()
                    if '.' in v and ',' in v: v = v.replace('.', '')
                    elif '.' in v: v = v.replace('.', ',')
                    return v if ',' in v else f"{v},00"

                bem = {
                    "codigo": final_cod,
                    "descricao": parts[1].strip(),
                    "data_aquisicao": parts[7].strip() if len(parts) > 7 else "",
                    "valor_original": fmt_curr(parts[10]) if len(parts) > 10 else "0,00",
                    "depreciacao_acumulada": "0,00",
                    "conta_origem_desc": parts[14].strip() if len(parts) > 14 and parts[14].strip() else "GERAL",
                    "taxa": "0,00",
                    "duplicado": dup
                }
                bens.append(bem)
        except Exception as e:
            st.error(f"Erro ao ler TXT SCI: {e}")
            
    return pd.DataFrame(bens)

def parse_planilha_simplificada(df_input):
    bens = []
    codigos_vistos = {}
    
    for _, row in df_input.iterrows():
        cod = str(row.get('Código', '')).strip()
        if not cod or cod.upper() == "NAN" or cod == "NONE": continue
            
        try:
            raw_cod = cod.replace('-', '').replace('/', '')
            
            if raw_cod in codigos_vistos:
                codigos_vistos[raw_cod] += 1
                final_cod = f"{raw_cod}-{codigos_vistos[raw_cod]}"
            else:
                codigos_vistos[raw_cod] = 0
                final_cod = raw_cod

            def safe_str(val, default=""):
                v = str(val).strip()
                return default if (v.upper() == "NAN" or v.upper() == "NONE" or v == "") else v

            bem = {
                "codigo": final_cod,
                "descricao": safe_str(row.get('Descrição', '')),
                "data_aquisicao": safe_str(row.get('Data Aquisição', '')),
                "valor_original": safe_str(row.get('Valor Original', '0,00'), "0,00"),
                "inicio_depreciacao": "", 
                "taxa": "0,00", 
                "nota_fiscal": "", 
                "depreciacao_acumulada": safe_str(row.get('Depreciação Acumulada', '0,00'), "0,00"),
                "baixado": False,
                "conta_origem_desc": safe_str(row.get('Grupo ou Conta', 'GERAL'), "GERAL"),
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
sistema = st.sidebar.selectbox(
    "Selecione o Sistema de Origem", 
    [
        "IOB / Folhamatic", 
        "Prosoft (Excel/CSV)", 
        "Contmatic (Excel/CSV)", 
        "Exactus (Excel/CSV)", 
        "Questor (Excel/CSV)", 
        "SCI / Único (Excel/TXT)", 
        "Planilha Simplificada / Copiar e Colar"
    ]
)

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

# --- FLUXO DA PLANILHA SIMPLIFICADA ---
if sistema == "Planilha Simplificada / Copiar e Colar":
    colunas_padrao = ["Código", "Descrição", "Data Aquisição", "Valor Original", "Depreciação Acumulada", "Grupo ou Conta"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Passo 1: Baixar Modelo Vazio")
        df_vazio = pd.DataFrame(columns=colunas_padrao)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_vazio.to_excel(writer, index=False, sheet_name='Bens')
        
        st.download_button(
            label="Baixar Planilha Modelo (.xlsx)",
            data=buffer.getvalue(),
            file_name="modelo_bens_simplificado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    with col2:
        st.markdown("### 📤 Passo 2: Upload (Opção A)")
        uploaded_planilha = st.file_uploader("Suba a planilha preenchida", type=["xlsx", "xls"], label_visibility="collapsed")
        
        if uploaded_planilha:
            if st.session_state.df_bens.empty:
                with st.spinner("Processando planilha anexada..."):
                    try:
                        df_upload = pd.read_excel(uploaded_planilha)
                        st.session_state.df_bens = parse_planilha_simplificada(df_upload)
                    except Exception as e:
                        st.error(f"Erro ao ler planilha: {e}")

    st.markdown("---")
    st.markdown("### 📝 Passo 2: Copiar e Colar (Opção B)")
    st.caption("Prefere não subir o arquivo? Copie as linhas do Excel e dê um Ctrl+V diretamente na tabela abaixo.")
    
    if 'edited_df' not in st.session_state:
        df_inicial = pd.DataFrame(columns=colunas_padrao, index=range(5))
        st.session_state.edited_df = df_inicial
        
    edited_data = st.data_editor(st.session_state.edited_df, num_rows="dynamic", width="stretch")
    
    if st.button("🚀 Processar Dados da Tabela", type="primary"):
        with st.spinner("Processando dados colados..."):
            st.session_state.df_bens = parse_planilha_simplificada(edited_data)
        st.rerun()

# --- FLUXO CONTMATIC COM DUPLO UPLOAD ---
elif sistema == "Contmatic (Excel/CSV)":
    col1, col2 = st.columns(2)
    with col1:
        f1 = st.file_uploader("Arquivo de Cadastro (Obrigatório)", type=["xlsx", "csv", "txt"])
    with col2:
        f2 = st.file_uploader("Mapa de Imobilizado (Opcional - Para Saldos)", type=["xlsx", "csv"])
    
    if f1 and st.button("Processar Arquivos Contmatic"):
        with st.spinner("Cruzando dados do Contmatic..."):
            df_main = parse_contmatic_universal(f1)
            if f2:
                saldos_map = parse_mapa_saldo_contmatic(f2)
                df_main['depreciacao_acumulada'] = df_main['codigo'].map(
                    lambda x: str(saldos_map.get(str(x).replace('-', '').replace('/', ''), "0,00"))
                )
            st.session_state.df_bens = df_main
            
            if st.session_state.df_bens.empty:
                st.warning("⚠️ Não foi possível encontrar bens processáveis nos arquivos. Verifique os relatórios.")
            else:
                st.rerun()

# --- FLUXO DOS DEMAIS SISTEMAS ---
else:
    if sistema == "IOB / Folhamatic":
        file_types = ["txt"]
    else:
        file_types = ["csv", "xlsx", "xls", "txt"]
        
    uploaded_file = st.file_uploader("Carregue o arquivo", type=file_types)

    if uploaded_file:
        if st.session_state.df_bens.empty:
            with st.spinner(f"Processando layout {sistema}..."):
                try:
                    if sistema == "IOB / Folhamatic":
                        content = uploaded_file.getvalue().decode("latin-1")
                        st.session_state.df_bens = parse_iob(content)
                    elif sistema == "Prosoft (Excel/CSV)":
                        st.session_state.df_bens = parse_prosoft_universal(uploaded_file)
                    elif sistema == "Exactus (Excel/CSV)":
                        st.session_state.df_bens = parse_exactus(uploaded_file)
                    elif sistema == "Questor (Excel/CSV)":
                        st.session_state.df_bens = parse_questor_universal(uploaded_file)
                    elif sistema == "SCI / Único (Excel/TXT)":
                        st.session_state.df_bens = parse_sci_unico_universal(uploaded_file)
                except Exception as e:
                    st.error(f"Erro inesperado ao ler arquivo: {e}")
                    
                if st.session_state.df_bens.empty:
                    st.warning("⚠️ Não foi possível extrair nenhum bem deste arquivo. Verifique se a exportação está no formato correto.")

# --- TELA DE RESULTADOS E EXPORTAÇÃO (Comum a todos) ---
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
        
        txt_bytes = txt_output.encode('cp1252', errors='replace')
        
        st.success("Arquivo gerado com sucesso!")
        st.download_button(
            label="📥 Baixar TXT (Registro 0450)", 
            data=txt_bytes, 
            file_name="importacao_bens_dominio.txt", 
            mime="text/plain"
        )
        
        st.info(
            "**Passo a passo para importar na Domínio:**\n\n"
            "No módulo **CONTABILIDADE**, acesse o menu **UTILITÁRIOS > IMPORTAÇÃO > IMPORTAÇÃO PADRÃO > LEIAUTE DOMÍNIO SISTEMAS COM SEPARADOR**."
        )
    
    with st.expander("🔍 Conferência Detalhada dos Dados"):
        st.dataframe(df)

if st.sidebar.button("Limpar / Novo Arquivo"):
    st.session_state.df_bens = pd.DataFrame()
    if 'edited_df' in st.session_state:
        del st.session_state['edited_df']
    st.rerun()
