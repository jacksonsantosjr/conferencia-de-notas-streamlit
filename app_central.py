# app_central.py (VERSÃO COM INTERFACE DA ETAPA 3)

import streamlit as st
import os
import json
import time
# import psutil
import pandas as pd
import fitz
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import altair as alt
import itertools
import concurrent.futures
import base64
# import subprocess
# import atexit
# import glob # glob é ótimo para encontrar arquivos com padrões, como "robot_instance_*.py"

# =============================================================================
# FUNÇÃO DE LIMPEZA DE ARQUIVOS TEMPORÁRIOS
# =============================================================================
# def limpar_arquivos_temporarios():
#     """
#     Encontra e deleta arquivos temporários da sessão anterior no diretório
#     onde o executável está rodando.
#     """
#     # Pega o diretório onde o script/executável está rodando
#     diretorio_base = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
    
#     print(f"Verificando arquivos temporários em: {diretorio_base}")
    
#     padroes_para_deletar = [
#         "progress.json",
#         "summary.json",
#         "robot_instance_*.py"
#     ]
    
#     for padrao in padroes_para_deletar:
#         # Constrói o caminho completo para a busca
#         caminho_busca = os.path.join(diretorio_base, padrao)
#         arquivos_encontrados = glob.glob(caminho_busca)
        
#         if not arquivos_encontrados:
#             continue # Pula para o próximo padrão se nada for encontrado

#         for arquivo in arquivos_encontrados:
#             try:
#                 os.remove(arquivo)
#                 print(f"Arquivo antigo removido: {arquivo}")
#             except OSError as e:
#                 print(f"Erro ao remover o arquivo antigo {arquivo}: {e}")

# # =============================================================================
# # REGISTRA A FUNÇÃO DE LIMPEZA
# # =============================================================================
# # Esta é a linha mágica: ela diz ao Python para chamar a função
# # 'limpar_arquivos_temporarios' sempre que o programa estiver prestes a fechar.
# #atexit.register(limpar_arquivos_temporarios)

# ==============================================================================
# CONFIGURAÇÕES GERAIS E ESTADO DA SESSÃO
# ==============================================================================
st.set_page_config(
    layout="wide",
    page_title="Conferência Avançada de Notas Fiscais",
    page_icon="📝"
)

# --- Inicialização do Estado da Sessão ---
# Etapa 1: Download
if 'robot_running' not in st.session_state: st.session_state.robot_running = False
if 'process_finished' not in st.session_state: st.session_state.process_finished = False
if 'summary_data' not in st.session_state: st.session_state.summary_data = None
if 'pause_state' not in st.session_state: st.session_state.pause_state = False
# Etapa 2: Conferência
if 'dados_processados' not in st.session_state: st.session_state.dados_processados = None
if 'id_upload_atual' not in st.session_state: st.session_state.id_upload_atual = ""
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0
if 'tempo_execucao' not in st.session_state: st.session_state.tempo_execucao = ""
if 'pdf_files_map' not in st.session_state: st.session_state.pdf_files_map = {}
# Etapa 3: Movimentação e Login
if 'user_logged_in' not in st.session_state: st.session_state.user_logged_in = None
if 'password_logged_in' not in st.session_state: st.session_state.password_logged_in = None

# ==============================================================================
# FUNÇÕES AUXILIARES GLOBAIS (sem alterações)
# ==============================================================================
# def get_robot_pid():
#     for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
#         try:
#             if proc.info['name'] == 'pythonw.exe' and proc.info['cmdline'] and 'robot_instance' in ' '.join(proc.info['cmdline']):
#                 return proc.info['pid']
#         except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
#     return None

# def force_kill_robot():
#     pid = get_robot_pid()
#     if pid:
#         try: p = psutil.Process(pid); p.kill(); return True
#         except psutil.NoSuchProcess: return False
#     return False

# def generate_robot_script(user, password):
#     with open("template_robot.py", "r", encoding='utf-8') as f: template = f.read()
#     script_content = template.replace("{USER}", user).replace("{PASS}", password)
#     script_name = f"robot_instance_{int(time.time())}.pyw"
#     script_path = os.path.join(os.path.expanduser("~"), "Downloads", script_name)
#     with open(script_path, "w", encoding='utf-8') as f: f.write(script_content)
#     return script_path

# def clean_temp_files():
#     base_path = os.path.join(os.path.expanduser("~"), "Downloads")
#     for item in os.listdir(base_path):
#         if (item.startswith("robot_instance_") and item.endswith(".pyw")) or item in ["progress.json", "control.json", "summary.json"]:
#             try: os.remove(os.path.join(base_path, item))
#             except Exception as e: print(f"Aviso: Não foi possível limpar o arquivo {item}: {e}")

# COLE ESTA NOVA FUNÇÃO NO LUGAR DAS QUE VOCÊ DELETOU

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def run_download_robot(username, password, progress_placeholder):
    """
    Função completa do robô Playwright para fazer login, navegar e baixar arquivos.
    Adaptada para rodar no Streamlit Cloud.
    """
    FLUIG_URL = "http://fluig.censo-nso.com.br:8080/portal/p/1/home"
    CONFERENCIA_URL = "http://fluig.censo-nso.com.br:8080/portal/p/1/conferencia_fiscal"
    
    DOWNLOAD_DIR = "Notas_Fluig_Temporarias"
    if not os.path.exists(DOWNLOAD_DIR ):
        os.makedirs(DOWNLOAD_DIR)

    try:
        with sync_playwright() as p:
            progress_placeholder.info("🤖 Iniciando navegador...")
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            progress_placeholder.info("🔐 Acessando e fazendo login no Fluig...")
            page.goto(FLUIG_URL, timeout=60000)
            with page.expect_navigation(wait_until="load", timeout=60000):
                page.fill('#username', username)
                page.fill('#password', password)
                page.click('#submitLogin')
            
            progress_placeholder.info("🧭 Navegando para a Central de Tarefas...")
            menu_principal_locator = page.locator("a").filter(has_text="Central Controladoria")
            menu_principal_locator.wait_for(state="visible", timeout=30000)
            menu_principal_locator.hover()
            menu_principal_locator.click()
            page.get_by_role("link", name=" Conferência Fiscal").hover()
            page.get_by_role("link", name=" Conferência Fiscal").click()
            page.wait_for_url(CONFERENCIA_URL, timeout=60000)

            progress_placeholder.info("📊 Localizando tarefas na página...")
            page.wait_for_selector("table tbody tr", timeout=60000)
            time.sleep(3)
            
            linhas_tarefa_locator = page.locator("table tbody tr")
            count_tarefas = linhas_tarefa_locator.count()

            if count_tarefas == 0:
                progress_placeholder.warning("✅ Nenhuma tarefa encontrada para download.")
                browser.close()
                return True, 0 # Retorna sucesso e 0 arquivos baixados

            progress_placeholder.info(f"📥 {count_tarefas} tarefas encontradas. Iniciando downloads...")
            
            for i in range(count_tarefas):
                tarefa_atual = linhas_tarefa_locator.nth(i)
                
                id_fluig = "ID_NAO_ENCONTRADO"
                try:
                    link_da_celula = tarefa_atual.locator("td:first-child a")
                    link_da_celula.wait_for(state="visible", timeout=5000)
                    texto_do_link = link_da_celula.inner_text()
                    match = re.search(r'\d+', texto_do_link)
                    if match:
                        id_fluig = match.group(0)
                except Exception:
                    pass

                tarefa_atual.get_by_role("link", name="Anexo").first.click()
                seletor_dentro_do_modal = "#select-toolbar > button"
                page.wait_for_selector(seletor_dentro_do_modal, timeout=30000)
                page.click(seletor_dentro_do_modal)

                with page.expect_download() as download_info:
                    page.click("#select-toolbar > ul > li.download.fs-cursor-pointer > a")
                
                download = download_info.value
                nome_original = download.suggested_filename
                novo_nome_arquivo = f"{id_fluig} - {nome_original}"
                caminho_arquivo = os.path.join(DOWNLOAD_DIR, novo_nome_arquivo)
                download.save_as(caminho_arquivo)
                
                progress_placeholder.info(f"({i+1}/{count_tarefas}) Baixado: {novo_nome_arquivo}")
                
                botao_fechar = page.locator("div.wcm-panel-header-bt-close")
                botao_fechar.wait_for(state="visible", timeout=10000)
                botao_fechar.click()
                page.wait_for_selector(seletor_dentro_do_modal, state='detached', timeout=10000)

            progress_placeholder.success(f"✅ Download de {count_tarefas} arquivos concluído!")
            browser.close()
            return True, count_tarefas

    except PlaywrightTimeoutError as e:
        st.error(f"Ocorreu um erro de Timeout no robô: A página demorou demais para responder. Detalhes: {e}")
        return False, 0
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante a execução do robô: {e}")
        return False, 0

def find_tesseract_cmd():
    if 'tesseract_cmd_path' in st.session_state: return st.session_state.tesseract_cmd_path
    try:
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'; pytesseract.get_tesseract_version()
        st.session_state.tesseract_cmd_path = 'tesseract'; return 'tesseract'
    except (pytesseract.TesseractNotFoundError, FileNotFoundError):
        windows_paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")]
        for path in windows_paths:
            if os.path.exists(path): st.session_state.tesseract_cmd_path = path; return path
    st.session_state.tesseract_cmd_path = None; return None

def limpar_formatacao(valor):
    if isinstance(valor, (int, float)): return float(valor)
    if not valor or str(valor).strip() in ['-', '', 'nan']: return 0.0
    val_str = str(valor).replace('R$', '').strip(); val_str = re.sub(r'[^\d.,]', '', val_str)
    if ',' in val_str and '.' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str: val_str = val_str.replace(',', '.')
    try: return float(val_str)
    except: return 0.0

def formatar_moeda(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def ler_pdf_ocr(arquivo_bytes):
    texto_completo = ""
    try:
        doc = fitz.open(stream=arquivo_bytes, filetype="pdf")
        for pagina in doc: texto_completo += pagina.get_text("text", sort=True) + "\n"
        if len(texto_completo.strip()) < 100:
            texto_ocr = ""
            for pagina in doc:
                pix = pagina.get_pixmap(dpi=300); img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
                enhancer = ImageEnhance.Contrast(img); img_enhanced = enhancer.enhance(2.0)
                texto_ocr += pytesseract.image_to_string(img_enhanced, lang='por') + "\n"
            texto_completo += "\n" + texto_ocr
    except Exception as e: st.warning(f"Não foi possível ler um dos PDFs. Erro: {e}"); return None
    return texto_completo

def buscar_valor_com_keywords(texto_ocr, valor_erp, keywords, tolerancia=0.05):
    if valor_erp <= 0.02: return True
    valor_str_padrao = f"{valor_erp:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if valor_str_padrao in texto_ocr: return True
    padrao_num = r"(\d{1,3}(?:[.,\s]?\d{3})*[.,]\d{2})"
    for m in re.finditer(padrao_num, texto_ocr):
        try:
            val_float = limpar_formatacao(m.group())
            if abs(val_float - valor_erp) <= tolerancia:
                start, end = m.span(); janela = texto_ocr[max(0, start-150):min(len(texto_ocr), end+150)].upper()
                if any(kw.upper() in janela for kw in keywords): return True
        except: continue
    return False

def verificar_existencia_valor_absoluto(texto, valor_alvo, tolerancia=0.05):
    if valor_alvo <= 0.05: return True
    raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
    for n in raw_nums:
        try:
            if abs(limpar_formatacao(n) - valor_alvo) <= tolerancia: return True
        except: pass
    return False

def verificar_soma_global(texto, valor_alvo, tolerancia=0.05):
    if valor_alvo <= 0.05: return True
    raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
    candidatos = sorted(list(set([limpar_formatacao(n) for n in raw_nums if 0.01 <= limpar_formatacao(n) <= valor_alvo])), reverse=True)[:80]
    for r in range(2, 5): 
        for combo in itertools.combinations(candidatos, r):
            if abs(sum(combo) - valor_alvo) <= tolerancia: return True
    return False

def obter_valor_coluna_segura(linha, nomes_possiveis):
    for nome_alvo in nomes_possiveis:
        for col_real in linha.index:
            if nome_alvo.upper() == str(col_real).strip().upper():
                return limpar_formatacao(linha[col_real])
    return 0.0

@st.cache_data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
        workbook = writer.book; worksheet = writer.sheets['Resultados']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    processed_data = output.getvalue(); return processed_data

KW_CSRF = ["PIS", "COFINS", "CSLL", "FEDERAL", "RETEN", "CSRF", "PASEP", "DEDUÇÕES", "LEI 10833"]
KW_IRRF = ["IR", "IRRF", "RENDA", "FONTE"]
KW_ISS = ["ISS", "ISSQN", "MUNICIPAL"]
KW_INSS = ["INSS", "PREVIDENCIA"]
KW_TOTAL = ["TOTAL", "BRUTO", "SERVIÇO", "NOTA", "VALOR", "LIQUIDO", "VALOR DOS SERVIÇOS", "VALOR DO SERVIÇO", "SERVIÇO PRESTADO", "SERVIÇOS PRESTADOS", "VALOR TOTAL DO SERVIÇO"]

def analisar_nota(file_content, file_name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome):
    texto = ler_pdf_ocr(file_content) or ""
    match_row = pd.DataFrame()
    # match_fluig_id_search = re.search(r"FLUIG_(\d{6,})", file_name, re.IGNORECASE)
    # if match_fluig_id_search and col_fluig_nome:
    #     fluig_id_from_name = int(match_fluig_id_search.group(1))
    #     possible_match = df_erp[df_erp[col_fluig_nome] == fluig_id_from_name]
    #     if not possible_match.empty: match_row = possible_match

    match_fluig_id_search = re.match(r"(\d+)\s*-", file_name)
    if match_fluig_id_search and col_fluig_nome:
        fluig_id_from_name = int(match_fluig_id_search.group(1))
        possible_match = df_erp[df_erp[col_fluig_nome] == fluig_id_from_name]
        if not possible_match.empty:
            match_row = possible_match
        
    else:
        texto_cabecalho = texto[:3000]
        padroes_nf = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)", r"DANFE.*?(\d{3,})"]
        candidato_ocr = next((int(m) for p in padroes_nf for m in re.findall(p, texto_cabecalho, re.IGNORECASE) if int(m) in numeros_validos_erp), 0)
        if candidato_ocr > 0:
            possible_match = df_erp[df_erp['Numero'] == candidato_ocr]
            if len(possible_match) == 1: match_row = possible_match
        if match_row.empty:
            candidato_arq = next((int(n) for n in re.findall(r"(\d+)", file_name) if int(n) in numeros_validos_erp), 0)
            if candidato_arq > 0:
                possible_match = df_erp[df_erp['Numero'] == candidato_arq]
                if len(possible_match) == 1: match_row = possible_match
    numero_nf_display = 0; fluig_id_display = "N/A"
    if not match_row.empty:
        linha_temp = match_row.iloc[0]
        numero_nf_display = int(linha_temp.get('Numero', 0))
        if col_fluig_nome and pd.notnull(linha_temp.get(col_fluig_nome)):
            val = linha_temp[col_fluig_nome]
            fluig_id_display = str(int(val)) if isinstance(val, (int, float)) and str(val).replace('.','').isdigit() else str(val)
    else:
        padroes_nf_display = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)"]
        numero_nf_display = next((int(m.group(1)) for p in padroes_nf_display for m in re.finditer(p, texto[:3000], re.IGNORECASE)), 0) or next((int(n) for n in re.findall(r"(\d+)", file_name)), 0)
        if match_fluig_id_search: fluig_id_display = match_fluig_id_search.group(1)
    linha_dados = {'ID_ARQUIVO': file_name, 'NO_NF': numero_nf_display or "N/A", 'NO_FLUIG': fluig_id_display, 'STATUS_GERAL': 'Conciliado', 'Dados_Detalhados': {}, 'Meta_Dados': {}, 'Texto_Debug': texto}
    if match_row.empty:
        linha_dados['STATUS_GERAL'] = 'Não consta no ERP'; return linha_dados
    linha = match_row.iloc[0]
    v_bruto = obter_valor_coluna_segura(linha, ['Valor Bruto', 'Valor Total']); v_liquido = obter_valor_coluna_segura(linha, ['Valor Liquido']); v_iss = obter_valor_coluna_segura(linha, ['ISS', 'Valor ISS']); v_inss = obter_valor_coluna_segura(linha, ['INSS', 'Valor INSS']); v_csrf_col = obter_valor_coluna_segura(linha, ['CSRF', 'PIS/COFINS']); v_irrf_col = obter_valor_coluna_segura(linha, ['IRRF', 'IRFF', 'IR'])
    v_federal_calc = max(0.0, (v_bruto - v_liquido) - v_iss - v_inss) if v_liquido > 0 else 0.0
    linha_dados['Meta_Dados']['Federal_Calc'] = v_federal_calc
    divergencias = False
    def validar_campo(campo, valor_erp, keywords, usar_soma_global=False, usar_calculo_federal=False):
        nonlocal divergencias; status, is_calc_warning = 'Divergência', False
        if buscar_valor_com_keywords(texto, valor_erp, keywords) or (usar_soma_global and verificar_soma_global(texto, valor_erp)) or (usar_calculo_federal and v_federal_calc > 0 and buscar_valor_com_keywords(texto, v_federal_calc, keywords)) or (campo == 'VALOR_TOTAL' and verificar_existencia_valor_absoluto(texto, valor_erp)): status = 'OK'
        if status != 'OK':
            divergencias = True
            if valor_erp == 0 and v_federal_calc > 0 and usar_calculo_federal: is_calc_warning = True
        linha_dados['Dados_Detalhados'][campo] = {'erp_valor': valor_erp, 'status': status, 'is_calc': is_calc_warning}
    validar_campo('VALOR_TOTAL', v_bruto, KW_TOTAL); validar_campo('ISS', v_iss, KW_ISS); validar_campo('INSS', v_inss, KW_INSS); validar_campo('CSRF', v_csrf_col, KW_CSRF, usar_soma_global=True, usar_calculo_federal=True); validar_campo('IRRF', v_irrf_col, KW_IRRF, usar_soma_global=True, usar_calculo_federal=True)
    if divergencias: linha_dados['STATUS_GERAL'] = 'Com Divergência'
    return linha_dados

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.markdown("<div class='main-title'><h1 style='text-align: left;'>📝 Conferência Avançada de Notas Fiscais</h1></div>", unsafe_allow_html=True)

with st.sidebar:

    # ✅ NOVA LÓGICA COM BOTÕES ESTILIZADOS ✅

    # --- 1. Injetar o CSS para os botões ---
    # Define o estilo para o botão padrão e para o botão "ativo"
    st.markdown("""
    <style>
        
        .sidebar-title {
            margin-top: -3rem; /* Remove o espaçamento superior */
        }
        
        /* ✅ NOVA REGRA PARA O TÍTULO PRINCIPAL ✅ */
        .main-title {
            margin-top: -4rem; /* Puxa o título principal para cima. */
        }
                
        /* ... (outras regras de CSS) ... */

        /* Estilo para o botão ATIVO */
        .stButton.active>button {
            background-color: #0275d8;
            color: white;
            border: 1px solid #0275d8;
        }

        /* ✅ NOVA REGRA DE HOVER MAIS VISÍVEL ✅ */
        /* Aplica-se apenas aos botões que NÃO estão ativos */
        .stButton:not(.active) > button:hover {
            background-color: #e6f1ff; /* Um azul bem claro */
            color: #004085; /* Um azul escuro para o texto */
            border: 1px solid #b8d7ff; /* Uma borda azul clara */
        }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. Lógica dos Botões ---
    # ✅ NOVA LÓGICA (CENTRALIZADO) ✅
    st.markdown("<div class='sidebar-title'><h2 style='text-align: center;'>🤖️ Menu de Robôs</h2></div>", unsafe_allow_html=True)
    
    # Define as opções
    opcoes = {
        "download": "📥 Download das Notas Fiscais",
        "conferencia": "🔍 Conferência Fluig x RM",
        "movimentacao": "🚚 Movimentar Conciliados"
    }

    # Inicializa a página selecionada se ainda não existir
    if 'pagina_selecionada' not in st.session_state:
        st.session_state.pagina_selecionada = "download"

    # Função para criar um botão e atualizar o estado
    def create_nav_button(key, label):
        # Define a classe CSS 'active' se o botão for o selecionado
        active_class = "active" if st.session_state.pagina_selecionada == key else ""
        # Usa st.markdown para envolver o botão em um div com a classe
        st.markdown(f'<div class="stButton {active_class}">', unsafe_allow_html=True)
        if st.button(label, key=f"btn_{key}", disabled=not st.session_state.user_logged_in, use_container_width=True):
            st.session_state.pagina_selecionada = key
            st.rerun()
        # ✅ ENVOLVE OS BOTÕES NO NOVO CONTÊINER ✅
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    create_nav_button("download", opcoes["download"])
    create_nav_button("conferencia", opcoes["conferencia"])
    create_nav_button("movimentacao", opcoes["movimentacao"])
    st.markdown('</div>', unsafe_allow_html=True)
    # ✅ FIM DO CONTÊINER ✅

    # Pega o valor completo da página selecionada para usar no if/elif
    pagina_selecionada = opcoes[st.session_state.pagina_selecionada]

    # ======================================================================
    # ✅ CÓDIGO DO RODAPÉ RESTAURADO ✅
    # ======================================================================
    # Espaçador para empurrar para baixo
    for _ in range(7): # Ajuste o número para o espaçamento desejado
        st.write("")

    # Lógica de exibição do login e botão de sair
    if st.session_state.user_logged_in:
        st.markdown("---")
        st.success(f"Logado como: **{st.session_state.user_logged_in}**")
        if st.button("Sair (Logoff)"):
            # Limpa toda a sessão para um logoff completo
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ==============================================================================
# CABEÇALHO FIXO (STICKY HEADER)
# ==============================================================================
# Define os títulos para cada página
#     titulos_etapas = {
#         "📥 Download das Notas Fiscais": "Etapa 1: Download de Anexos do Fluig",
#         "🔍 Conferência das Notas Fiscais": "Etapa 2: Conferência Fluig x RM",
#         "🚚 Movimentar Conciliados": "Etapa 3: Movimentar Documentos Conciliados"
#     }
#     titulo_etapa_atual = titulos_etapas.get(pagina_selecionada, "")

# #    Cria o contêiner do cabeçalho fixo
#     st.markdown("""
#         <div class="sticky-header">
#             <h1 style='text-align: center; font-size: 2.2rem;'>📝 Conferência Avançada de Notas Fiscais</h1>
#             <h2 style='text-align: center; font-weight: 400;'>{}</h2>
#         </div>
# """.format(titulo_etapa_atual), unsafe_allow_html=True)

#     # --- 3. Lógica do Rodapé (inalterada) ---
#     for _ in range(4): # Ajuste o número para o espaçamento desejado
#         st.write("")

#     if st.session_state.user_logged_in:
#         st.markdown("---")
#         st.success(f"Logado como: **{st.session_state.user_logged_in}**")
#         if st.button("Sair (Logoff)"):
#             for key in list(st.session_state.keys()):
#                 del st.session_state[key]
#             st.rerun()

# # ==============================================================================
# # PÁGINA 1: DOWNLOAD DAS NOTAS FISCAIS
# # ==============================================================================
# if pagina_selecionada == "📥 Download das Notas Fiscais":
#     st.header("Etapa 1: Download de Anexos do Fluig")

#     # Se o usuário já está logado, pula a tela de login e vai direto para o monitoramento/resumo
#     if st.session_state.user_logged_in:
#         if st.session_state.process_finished:
#             st.success("Processo finalizado!")
#             if st.session_state.summary_data:
#                 summary = st.session_state.summary_data
#                 if summary.get("status") == "success":
#                     st.subheader("Resumo do Processamento")
#                     duration = summary.get("duration_seconds")
#                     if duration is not None:
#                         minutes, seconds = divmod(int(duration), 60)
#                         duration_str = f"{minutes} min {seconds} seg"
#                     else:
#                         duration_str = "N/A"

#                     col1, col2, col3 = st.columns(3)
#                     col1.metric("Fluigs Processados", summary.get("total_fluigs", "N/A"))
#                     col2.metric("Arquivos Baixados", summary.get("downloaded_count", "N/A"))
#                     col3.metric("Tempo Total", duration_str) # <--- USA A STRING FORMATADA
#                     # --- FIM DA CORREÇÃO ---
                    
#                     st.info(f"**Anexos sem opção de download:** {summary.get('skipped_count', 0)}")
#                     if summary.get("skipped_list"):
#                         with st.expander("Ver lista de anexos não baixados"): st.code('\n'.join(summary.get('skipped_list', [])))
#                     pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
#                     if st.button("📂 Abrir Pasta de Downloads"):
#                         try: os.startfile(pasta_downloads)
#                         except AttributeError: subprocess.run(['xdg-open', pasta_downloads])
#                 elif summary.get("status") == "cancelled": st.warning("O processo foi cancelado pelo usuário.")
#                 else:
#                     st.error("Ocorreu um erro durante a execução do robô."); st.code(summary.get("message", "Nenhuma mensagem de erro detalhada."))
#             if st.button("⬅️ Voltar para o Início"):
#                 st.session_state.robot_running = False; st.session_state.process_finished = False
#                 st.session_state.summary_data = None; st.session_state.pause_state = False
#                 clean_temp_files(); st.rerun()
        
#         elif st.session_state.robot_running:
#             st.info("🤖 Robô em execução... Acompanhe o progresso abaixo.")
#             progress_bar = st.progress(0, text="Aguardando início...")
#             st.write("")
#             c1, c2, c3, c4 = st.columns([2, 2, 2, 6])
#             if st.session_state.pause_state:
#                 if c1.button("▶️ Continuar", use_container_width=True):
#                     with open(os.path.join(os.path.expanduser("~"), "Downloads", "control.json"), "w", encoding='utf-8') as f: json.dump({"command": "run"}, f)
#                     st.session_state.pause_state = False; st.rerun()
#             else:
#                 if c1.button("⏸️ Pausar", use_container_width=True):
#                     with open(os.path.join(os.path.expanduser("~"), "Downloads", "control.json"), "w", encoding='utf-8') as f: json.dump({"command": "pause"}, f)
#                     st.session_state.pause_state = True; st.rerun()
#             if c2.button("⏹️ Cancelar", use_container_width=True):
#                 st.toast("Comando 'Cancelar' enviado! Encerrando processo...")
#                 force_kill_robot(); clean_temp_files()
#                 st.session_state.robot_running = False; st.session_state.process_finished = True
#                 st.session_state.summary_data = {"status": "cancelled"}; st.rerun()
#             summary_file = os.path.join(os.path.expanduser("~"), "Downloads", "summary.json")
#             while True:
#                 robot_pid = get_robot_pid()
#                 summary_exists = os.path.exists(summary_file)
#                 if robot_pid is None and summary_exists: break
#                 if robot_pid is None and not st.session_state.get('initial_wait_done', False):
#                      time.sleep(2)
#                      if get_robot_pid() is None:
#                          st.session_state.summary_data = {"status": "error", "message": "O processo do robô terminou inesperadamente."}; break
#                 progress_file = os.path.join(os.path.expanduser("~"), "Downloads", "progress.json")
#                 if os.path.exists(progress_file):
#                     try:
#                         with open(progress_file, "r", encoding='utf-8') as f: progress_data = json.load(f)
#                         total = progress_data.get("total", 1); current = progress_data.get("current", 0); message = progress_data.get("message", "...")
#                         percent_complete = current / total if total > 0 else 0
#                         progress_bar.progress(percent_complete, text=message)
#                     except: pass
#                 time.sleep(1)
#             st.session_state.robot_running = False; st.session_state.process_finished = True
#             if os.path.exists(summary_file):
#                 try:
#                     with open(summary_file, "r", encoding='utf-8') as f: st.session_state.summary_data = json.load(f)
#                 except: st.session_state.summary_data = {"status": "error", "message": "Falha ao ler o arquivo de resumo."}
#             st.rerun()
        
#         else:
#             # Se está logado, mas nenhum processo rodando, mostra um botão para iniciar
#             st.info("Você já está logado. Clique abaixo para iniciar o download dos anexos.")
#             if st.button("📥 Iniciar Download", use_container_width=False):
#                 try:
#                     clean_temp_files()
#                     # Usa as credenciais salvas na sessão
#                     script_path = generate_robot_script(st.session_state.user_logged_in, st.session_state.password_logged_in)
#                     os.startfile(script_path)
#                     time.sleep(3)
#                     if get_robot_pid() is not None:
#                         st.session_state.robot_running = True
#                         st.session_state.initial_wait_done = True
#                         st.rerun()
#                     else: st.error("Falha ao iniciar o processo do robô.")
#                 except Exception as e: st.error(f"Ocorreu um erro ao gerar o robô: {e}")

#     # Se o usuário NÃO está logado, mostra o formulário de login
#     else:
#         st.info("Insira suas credenciais do Fluig para iniciar a automação.")
#         with st.form("login_form"):
#             user = st.text_input("Usuário do Fluig")
#             password = st.text_input("Senha do Fluig", type="password")
#             submitted = st.form_submit_button("Entrar") 
            
#             if submitted:
#                 if user and password:
#                     # ✅ NOVA LÓGICA CORRETA (APENAS FAZ LOGIN) ✅
#                     # Salva as credenciais na sessão
#                     st.session_state.user_logged_in = user
#                     st.session_state.password_logged_in = password
#                     # Força o recarregamento da página para refletir o estado de "logado"
#                     st.rerun() 
#                 else:
#                     st.error("Por favor, preencha o usuário e a senha.")

# SUBSTITUA TODA A SEÇÃO DA ETAPA 1 POR ISTO:

if pagina_selecionada == "📥 Download das Notas Fiscais":
    st.header("Etapa 1: Download de Anexos do Fluig")

    # Se o usuário já está logado, mostra o botão para iniciar
    if st.session_state.user_logged_in:
        st.info("Você já está logado. Clique abaixo para iniciar o download dos anexos.")
        if st.button("📥 Iniciar Download", use_container_width=False, type="primary"):
            progress_placeholder = st.empty()
            with st.spinner("Executando robô... Isso pode levar alguns minutos. Por favor, aguarde."):
                success, count = run_download_robot(st.session_state.user_logged_in, st.session_state.password_logged_in, progress_placeholder)
            
            if success:
                if count > 0:
                    st.success(f"Robô finalizado! {count} arquivos baixados. Prossiga para a etapa de conferência.")
                else:
                    st.info("Robô finalizado. Nenhum arquivo novo para baixar.")
                time.sleep(3)
                st.session_state.pagina_selecionada = "conferencia"
                st.rerun()
            else:
                st.error("O robô encontrou um erro. Verifique as mensagens acima e tente novamente.")
    
    # Se o usuário NÃO está logado, mostra o formulário de login
    else:
        st.info("Insira suas credenciais do Fluig para continuar.")
        with st.form("login_form"):
            user = st.text_input("Usuário do Fluig")
            password = st.text_input("Senha do Fluig", type="password")
            submitted = st.form_submit_button("Entrar") 
            
            if submitted:
                if user and password:
                    st.session_state.user_logged_in = user
                    st.session_state.password_logged_in = password
                    st.rerun() 
                else:
                    st.error("Por favor, preencha o usuário e a senha.")

# ==============================================================================
# PÁGINA 2: CONFERÊNCIA DAS NOTAS FISCAIS
# ==============================================================================
elif pagina_selecionada == "🔍 Conferência Fluig x RM":

    # Todo o código da Etapa 2, que já validamos, vai aqui, devidamente indentado.
    # Nenhuma alteração lógica é necessária nesta parte.

    st.header("Etapa 2: Conferência Fluig x RM")

    COR_VERDE = "#28a745"; COR_VERMELHA = "#dc3545"
    st.markdown(f"""<style>
        .kpi-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; justify-content: center; height: 120px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
        .kpi-title {{ font-size: 13px; color: #555; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
        .kpi-value {{ font-size: 34px; color: #222; font-weight: 800; line-height: 1.2; }}
        .txt-green {{ color: {COR_VERDE}; }}; .txt-red {{ color: {COR_VERMELHA}; }}
        .div-card {{ background-color: #fff5f5; border-left: 5px solid {COR_VERMELHA}; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #444; }}
        .kw-badge {{ display: inline-block; background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; margin-right: 5px; margin-bottom: 5px; border: 1px solid #dee2e6; color: #495057; }}
        button[title="View fullscreen"]{{ visibility: hidden; }}
    </style>""", unsafe_allow_html=True)

    tesseract_path = find_tesseract_cmd()
    if not tesseract_path:
        st.error("Tesseract OCR não foi encontrado."); st.stop()

    with st.expander("📂 Arquivos para Conferência", expanded=st.session_state.dados_processados is None):
        pdf_files_prontos = []; arquivos_ignorados = []
        # pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
        pasta_downloads = "Notas_Fluig_Temporarias"
        palavras_chave_filtro = ["boleto", "bol", "orçamento", "fatura", "relatorio", "demonstrativo", "extrato","sabesp", "enel"]
        # if os.path.exists(pasta_downloads):
        #     for filename in os.listdir(pasta_downloads):
        #         if filename.lower().endswith(".pdf"):
        #             if any(keyword in filename.lower() for keyword in palavras_chave_filtro): arquivos_ignorados.append(filename)
        #             else: pdf_files_prontos.append(filename)
        # if pdf_files_prontos:
        #     st.success(f"✅ **{len(pdf_files_prontos)}** arquivos PDF encontrados e prontos para a conferência.")
        #     if arquivos_ignorados:
        #         with st.expander(f"⚠️ **{len(arquivos_ignorados)}** arquivos foram ignorados."): st.code("\n".join(arquivos_ignorados))
        # ✅ NOVA LÓGICA ROBUSTA DE CONTAGEM ✅
        if os.path.exists(pasta_downloads):
            todos_os_arquivos = os.listdir(pasta_downloads)
            total_na_pasta = len(todos_os_arquivos)
            
            # Nova lista para arquivos que não são PDF
            outros_arquivos_ignorados = []

            for filename in todos_os_arquivos:
                # Primeiro, verifica se é um PDF
                if filename.lower().endswith(".pdf"):
                    # Se for PDF, verifica as palavras-chave
                    if any(keyword in filename.lower() for keyword in palavras_chave_filtro):
                        arquivos_ignorados.append(filename) # Ignorado por palavra-chave
                    else:
                        pdf_files_prontos.append(filename) # Válido para conferência
                else:
                    # Se não for PDF, vai para a nova lista de ignorados
                    outros_arquivos_ignorados.append(filename) # Ignorado por não ser PDF
        else:
            total_na_pasta = 0

        # --- Exibição Aprimorada do Resumo ---
        st.info(f"🔎 Total de itens na pasta 'Notas_Fluig': **{total_na_pasta}**")

        if pdf_files_prontos:
            st.success(f"✅ **{len(pdf_files_prontos)}** arquivos PDF prontos para a conferência.")
        
        if arquivos_ignorados:
            with st.expander(f"⚠️ **{len(arquivos_ignorados)}** PDFs ignorados por conterem palavras-chave (ex: boleto, fatura)."):
                st.code("\n".join(arquivos_ignorados))
        
        # Nova seção para exibir os outros arquivos ignorados
        if outros_arquivos_ignorados:
            with st.expander(f"🚫 **{len(outros_arquivos_ignorados)}** itens ignorados por não serem arquivos PDF."):
                st.code("\n".join(outros_arquivos_ignorados))
        else: st.warning("Nenhum arquivo PDF válido encontrado na pasta 'Downloads/Notas_Fluig'.")
        excel_file = st.file_uploader("Anexe o relatório do ERP (.xlsx) para iniciar", type=["xlsx", "xls"], key="excel_uploader_etapa2")

    if pdf_files_prontos and excel_file:
        id_novo = str(sorted(pdf_files_prontos)) + excel_file.name
        if st.session_state.id_upload_atual != id_novo:
            with st.spinner('Analisando documentos...'):
                try:
                    inicio_timer = time.time()
                    df_erp = pd.read_excel(excel_file, sheet_name=0); df_erp.columns = [str(c).strip() for c in df_erp.columns]
                    if 'Numero' not in df_erp.columns: st.error("Erro: Coluna 'Numero' não encontrada."); st.stop()
                    df_erp['Numero'] = pd.to_numeric(df_erp['Numero'], errors='coerce').fillna(0).astype(int)
                    numeros_validos_erp = set(df_erp['Numero'].unique())
                    col_fluig_nome = next((c for c in df_erp.columns if "FLUIG" in str(c).upper()), None)
                    fluigs_validos_erp = set()
                    if col_fluig_nome:
                        df_erp[col_fluig_nome] = pd.to_numeric(df_erp[col_fluig_nome], errors='coerce').fillna(0).astype(int)
                        fluigs_validos_erp = set(df_erp[col_fluig_nome].unique())
                    st.session_state.pdf_files_map = {}
                    for filename in pdf_files_prontos:
                        filepath = os.path.join(pasta_downloads, filename)
                        with open(filepath, "rb") as f: st.session_state.pdf_files_map[filename] = f.read()
                    prog = st.empty(); bar = prog.progress(0, text="Iniciando processamento...")
                    resultados = []; total = len(st.session_state.pdf_files_map)
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {executor.submit(analisar_nota, content, name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome): name for name, content in st.session_state.pdf_files_map.items()}
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            pdf_name = futures[future]
                            try: resultados.append(future.result())
                            except Exception as exc: st.error(f"Erro ao processar o arquivo {pdf_name}: {exc}")
                            bar.progress((i + 1) / total, text=f"Lendo documento {i+1} de {total}: {pdf_name}")
                    fim_timer = time.time()
                    st.session_state.tempo_execucao = f"{int((fim_timer - inicio_timer) // 60)} min e {int((fim_timer - inicio_timer) % 60)} seg"
                    prog.empty(); st.success(f"✅ Processamento concluído! Tempo total: {st.session_state.tempo_execucao}")
                    st.session_state.dados_processados = pd.DataFrame(sorted(resultados, key=lambda x: (x['STATUS_GERAL'] != 'Conciliado', x['ID_ARQUIVO'])))
                    st.session_state.id_upload_atual = id_novo; st.session_state.pagina_atual = 0; st.rerun()
                except Exception as e: st.error(f"Erro geral no processamento: {e}")

    if st.session_state.dados_processados is not None:
        df_final = st.session_state.dados_processados
        divergentes_df = df_final[~df_final['STATUS_GERAL'].str.startswith('Conciliado')]
        conciliados = len(df_final) - len(divergentes_df); divergentes = len(divergentes_df); total = len(df_final)
        st.markdown("### Resumo da Conferência")
        if st.session_state.tempo_execucao: st.caption(f"⏱️ Tempo: {st.session_state.tempo_execucao}")
        col_kpi, col_vazio, col_chart = st.columns([3, 0.2, 2])
        with col_kpi:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Verificado (PDFs)</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
            k2, k3 = st.columns(2)
            k2.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERDE};"><div class="kpi-title">Conciliados</div><div class="kpi-value txt-green">{conciliados}</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERMELHA};"><div class="kpi-title">Com Divergências</div><div class="kpi-value txt-red">{divergentes}</div></div>', unsafe_allow_html=True)
        with col_chart:
            if total > 0:
                source = pd.DataFrame({"Status": ["Conciliados", "Divergentes"], "Valor": [conciliados, divergentes]}); source["Percent"] = source["Valor"] / source["Valor"].sum()
                base = alt.Chart(source).encode(theta=alt.Theta("Valor:Q", stack=True), order=alt.Order("Status:N", sort="descending"))
                pie = base.mark_arc(outerRadius=110).encode(color=alt.Color("Status:N", scale=alt.Scale(domain=["Conciliados", "Divergentes"], range=[COR_VERDE, COR_VERMELHA]), legend=alt.Legend(title=None, orient='right', labelFontSize=14)), tooltip=["Status", "Valor", alt.Tooltip("Percent:Q", format=".1%")])
                text = base.mark_text(radius=135, size=16, fontWeight='bold').encode(text=alt.Text("Percent:Q", format=".1%")) 
                chart = (pie + text).properties(height=300).configure_view(strokeWidth=0)
                st.altair_chart(chart, use_container_width=True, theme="streamlit")

        # ======================================================================
        # 💡 NOVA FUNCIONALIDADE: Botão para Refazer a Conferência 💡
        # ======================================================================
        st.write("") # Adiciona um pequeno espaço
        c1_refazer, c2_refazer = st.columns([3, 1]) # Cria colunas para alinhar o botão
        with c2_refazer: # Usa a coluna da direita
            if st.button("🔄 Refazer Conferência", use_container_width=True):
                # Limpa todas as variáveis de sessão relacionadas à Etapa 2
                st.session_state.dados_processados = None
                st.session_state.id_upload_atual = ""
                st.session_state.pdf_files_map = {}
                st.session_state.tempo_execucao = ""
                st.session_state.pagina_atual = 0
                # Força o recarregamento da página para voltar à tela de upload
                st.rerun()
        # ======================================================================
        st.markdown("---")
        st.subheader("Detalhamento por Nota Fiscal")
        filtro = st.radio("Exibir:", ["Todos", "Com Divergência", "Não consta no ERP", "Conciliados"], horizontal=True, key="filtro_detalhes")
        if filtro == "Com Divergência": df_show = df_final[df_final['STATUS_GERAL'] == 'Com Divergência'].reset_index(drop=True)
        elif filtro == "Não consta no ERP": df_show = df_final[df_final['STATUS_GERAL'] == 'Não consta no ERP'].reset_index(drop=True)
        elif filtro == "Conciliados": df_show = df_final[df_final['STATUS_GERAL'].str.startswith('Conciliado')].reset_index(drop=True)
        else: df_show = df_final.copy()
        ITENS_POR_PAGINA = 10
        total_pags = max(1, (len(df_show) - 1) // ITENS_POR_PAGINA + 1)
        st.session_state.pagina_atual = min(st.session_state.pagina_atual, total_pags - 1)
        inicio, fim = st.session_state.pagina_atual * ITENS_POR_PAGINA, (st.session_state.pagina_atual + 1) * ITENS_POR_PAGINA
        df_pagina = df_show.iloc[inicio:fim]
        def icon_status(row, campo):
            status_geral = str(row.get('STATUS_GERAL', ''));
            if status_geral == 'Não consta no ERP': return "➖"
            if status_geral.startswith('Conciliado'): return "✅"
            detalhes = row.get('Dados_Detalhados', {});
            if not detalhes or campo not in detalhes or detalhes[campo]['erp_valor'] == 0: return "✅"
            return "✅" if detalhes[campo]['status'] == "OK" else "❌"
        if not df_pagina.empty:
            df_view = pd.DataFrame({'Fluig': df_pagina['NO_FLUIG'].astype(str), 'Arquivo': df_pagina['ID_ARQUIVO'].astype(str), 'ISS': df_pagina.apply(lambda x: icon_status(x, 'ISS'), axis=1), 'CSRF': df_pagina.apply(lambda x: icon_status(x, 'CSRF'), axis=1), 'INSS': df_pagina.apply(lambda x: icon_status(x, 'INSS'), axis=1), 'IRRF': df_pagina.apply(lambda x: icon_status(x, 'IRRF'), axis=1), 'Total': df_pagina.apply(lambda x: icon_status(x, 'VALOR_TOTAL'), axis=1), 'Status': df_pagina['STATUS_GERAL'].astype(str)}) #'NF': df_pagina['NO_NF'].astype(str),
            st.dataframe(df_view, hide_index=True, use_container_width=True)
        c_prev, c_info, c_next, c_export_space, c_export_btn = st.columns([2.5, 2, 2.5, 7, 3])
        with c_prev:
            if st.button("⬅️ Anterior", use_container_width=True, disabled=(st.session_state.pagina_atual == 0)): st.session_state.pagina_atual -= 1; st.rerun()
        with c_info: st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual + 1} de {total_pags}</div>", unsafe_allow_html=True)
        with c_next:
            if st.button("Próximo ➡️", use_container_width=True, disabled=(st.session_state.pagina_atual >= total_pags - 1)): st.session_state.pagina_atual += 1; st.rerun()
        with c_export_btn:
            df_export = df_final.drop(columns=['Dados_Detalhados', 'Meta_Dados', 'Texto_Debug'])
            excel_data = to_excel(df_export)
            st.download_button(label="📥 Exportar para Excel", data=excel_data, file_name="conciliacao_resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        st.markdown("---")
        if not divergentes_df.empty:
            st.subheader("🔎 Análise e Conciliação Manual")
            opts = divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1).tolist()
            sel = st.selectbox("Selecione uma nota para analisar:", opts, key="select_divergencia", index=None, placeholder="Selecione uma nota com divergência...")
            if sel:
                col_diag, col_pdf = st.columns(2)
                row_index = divergentes_df[divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1) == sel].index[0]
                row = divergentes_df.loc[row_index]
                with col_diag:
                    if row['STATUS_GERAL'] == 'Não consta no ERP': st.error(f"**Nota não encontrada no ERP:** O arquivo `{row['ID_ARQUIVO']}` não corresponde a nenhuma linha no relatório em Excel.")
                    else:
                        detalhes = row.get('Dados_Detalhados', {}); meta = row.get('Meta_Dados', {})
                        campos_erro = {k: v for k, v in detalhes.items() if v['status'] != 'OK' and v['erp_valor'] > 0}
                        if not campos_erro: st.info("Todos os valores com divergência no ERP são R$ 0,00 ou não foram encontrados.")
                        for campo, info in campos_erro.items():
                            nome, valor = campo.replace("_", " "), formatar_moeda(info['erp_valor'])
                            msg_extra = ""
                            if info.get('is_calc'):
                                 calc_val = formatar_moeda(meta.get('Federal_Calc', 0))
                                 msg_extra = f" (Obs: ERP zerado, mas um cálculo sugere um valor próximo de **{calc_val}**)"
                            kws_usadas = globals().get(f"KW_{campo.split(' ')[0]}", [])
                            kw_html = "".join([f"<span class='kw-badge'>{k}</span>" for k in kws_usadas]) or "N/A"
                            html_parts = ["<div class='div-card'>", f"<div style='margin-bottom:8px;'><b>{nome}</b>: ERP espera <b>{valor}</b>{msg_extra}</div>", "<div style='font-size:0.9em; color:#666;'>", "<b>Diagnóstico:</b> Valor não localizado no PDF próximo às palavras-chave.", f"<b>Keywords:</b> {kw_html}", "</div>", "</div>"]
                            html_string = "".join(html_parts); st.markdown(html_string, unsafe_allow_html=True)
                    st.write("") 
                    col_btn_vazia1, col_btn_centro, col_btn_vazia2 = st.columns([1, 2, 1])
                    with col_btn_centro:
                        if st.button("✅ Conciliar Manualmente", key=f"manual_concile_{row_index}", use_container_width=True):
                            original_index = st.session_state.dados_processados[st.session_state.dados_processados['ID_ARQUIVO'] == row['ID_ARQUIVO']].index[0]
                            st.session_state.dados_processados.loc[original_index, 'STATUS_GERAL'] = 'Conciliado (Manual)'
                            for k in st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados']:
                                st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados'][k]['status'] = 'OK (Manual)'
                            st.success(f"Nota {row['NO_NF']} conciliada manualmente!"); time.sleep(1); st.rerun()
                with col_pdf:
                    pdf_content = st.session_state.pdf_files_map.get(row['ID_ARQUIVO'])
                    if pdf_content:
                        base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    else: st.error("Arquivo PDF não encontrado na memória para exibição.")

# ==============================================================================
# PÁGINA 3: MOVIMENTAR CONCILIADOS
# ==============================================================================
elif pagina_selecionada == "🚚 Movimentar Conciliados":
    st.header("Etapa 3: Movimentar Documentos Conciliados")

    # Verifica se a Etapa 2 já foi executada
    if st.session_state.dados_processados is None:
        st.warning("⚠️ Por favor, execute a Etapa 2 (Conferência Fluig x RM) primeiro.")
        st.info("A lista de Fluigs a serem movimentados é gerada a partir do resultado da conferência.")
    # else:
    #     df_resultados = st.session_state.dados_processados
        
    #     # Filtra apenas os Fluigs que foram conciliados (automática ou manualmente)
    #     fluigs_conciliados_df = df_resultados[
    #         df_resultados['STATUS_GERAL'].str.startswith('Conciliado') &
    #         (df_resultados['NO_FLUIG'] != 'N/A')
    #     ]
        
    #     lista_fluigs_para_movimentar = fluigs_conciliados_df['NO_FLUIG'].unique().tolist()

    #     if not lista_fluigs_para_movimentar:
    #         st.info("Nenhum Fluig com status 'Conciliado' foi encontrado no resultado da Etapa 2.")
    #         st.warning("Não há documentos para movimentar.")
    #     else:
    #         st.success(f"✅ **{len(lista_fluigs_para_movimentar)}** Fluigs conciliados estão prontos para serem movimentados.")
            
    #         with st.expander("Ver lista de Fluigs a serem movimentados"):
    #             st.dataframe(pd.DataFrame(lista_fluigs_para_movimentar, columns=["Fluig ID"]), use_container_width=True, hide_index=True)

    #         st.markdown("---")
    #         st.warning("**Atenção:** A ação a seguir irá marcar e movimentar os documentos selecionados no Fluig. Esta ação não pode ser desfeita pelo robô.", icon="⚠️")
            
    #         if st.button("🚀 Iniciar Movimentação dos Documentos", type="primary", use_container_width=True):
    #             st.info("Funcionalidade em desenvolvimento...")
    else:
        df_resultados = st.session_state.dados_processados
        
        # Filtra apenas os Fluigs que foram conciliados (automática ou manualmente)
        fluigs_conciliados_df = df_resultados[
            df_resultados['STATUS_GERAL'].str.startswith('Conciliado') &
            (df_resultados['NO_FLUIG'] != 'N/A')
        ].copy()

        #st.subheader("Detalhamento por Nota Fiscal")
       
        lista_fluigs_para_movimentar = fluigs_conciliados_df['NO_FLUIG'].unique().tolist()

        contagem_correta_de_documentos = len(fluigs_conciliados_df)

        if not lista_fluigs_para_movimentar:
            st.info("Nenhum Fluig com status 'Conciliado' foi encontrado no resultado da Etapa 2.")
            st.warning("Não há documentos para movimentar.")
        else:
            # ✅ NOVA LÓGICA (COM PAGINAÇÃO) ✅
            #st.info(f"A lista abaixo contém os **{len(lista_fluigs_para_movimentar)}** documentos com status 'Conciliado' que serão movimentados.")
            st.info(f"A lista abaixo contém os **{contagem_correta_de_documentos}** documentos com status 'Conciliado' que serão movimentados.")

            # --- INÍCIO DA LÓGICA DE PAGINAÇÃO ---
            ITENS_POR_PAGINA_E3 = 10 # Constante de paginação para a Etapa 3
            
            # Garante que a página atual não seja inválida se a lista diminuir
            total_pags_e3 = max(1, (len(fluigs_conciliados_df) - 1) // ITENS_POR_PAGINA_E3 + 1)
            if 'pagina_atual_e3' not in st.session_state:
                st.session_state.pagina_atual_e3 = 0
            st.session_state.pagina_atual_e3 = min(st.session_state.pagina_atual_e3, total_pags_e3 - 1)

            # Calcula os índices de início e fim para a página atual
            inicio_e3 = st.session_state.pagina_atual_e3 * ITENS_POR_PAGINA_E3
            fim_e3 = (st.session_state.pagina_atual_e3 + 1) * ITENS_POR_PAGINA_E3
            df_pagina_e3 = fluigs_conciliados_df.iloc[inicio_e3:fim_e3]
            # --- FIM DA LÓGICA DE PAGINAÇÃO ---

            # Cria o DataFrame de visualização APENAS com os dados da página atual
            df_view_movimentacao = pd.DataFrame({
                'Fluig': df_pagina_e3['NO_FLUIG'].astype(str), 
                #'Arquivo': df_pagina_e3['ID_ARQUIVO'].astype(str), 
                #'NF': df_pagina_e3['NO_NF'].astype(str), 
                'Status': df_pagina_e3['STATUS_GERAL'].astype(str)
            })
            
            st.dataframe(df_view_movimentacao, hide_index=True, use_container_width=True)

            # --- INÍCIO DOS BOTÕES DE NAVEGAÇÃO ---
            c_prev, c_info, c_next = st.columns([2, 1, 2])
            
            with c_prev:
                if st.button("⬅️ Anterior", key="prev_e3", use_container_width=True, disabled=(st.session_state.pagina_atual_e3 == 0)):
                    st.session_state.pagina_atual_e3 -= 1
                    st.rerun()
            with c_info:
                st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual_e3 + 1} de {total_pags_e3}</div>", unsafe_allow_html=True)
            with c_next:
                if st.button("Próximo ➡️", key="next_e3", use_container_width=True, disabled=(st.session_state.pagina_atual_e3 >= total_pags_e3 - 1)):
                    st.session_state.pagina_atual_e3 += 1
                    st.rerun()
            # --- FIM DOS BOTÕES DE NAVEGAÇÃO ---

            st.markdown("---")
            st.warning("**Atenção:** A ação a seguir irá marcar e movimentar os documentos selecionados no Fluig. Esta ação não pode ser desfeita pelo robô.", icon="⚠️")
            
            if st.button("🚀 Iniciar Movimentação dos Documentos", type="primary", use_container_width=False):
                st.info("Funcionalidade em desenvolvimento...")
                # Aqui entrará a lógica para chamar o robô da Etapa 3,
                # passando st.session_state.user_logged_in, st.session_state.password_logged_in,
                # e a lista_fluigs_para_movimentar.
                #st.balloons()
