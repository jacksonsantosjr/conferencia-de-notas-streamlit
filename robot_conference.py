# import streamlit as st
# import pandas as pd
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image, ImageEnhance
# import io
# import re
# import os
# import altair as alt
# import time
# import itertools
# import concurrent.futures
# import base64

# # ==============================================================================
# # 1. CONFIGURAÇÃO DA PÁGINA
# # ==============================================================================
# # O usuário pode alternar o tema no menu (☰) -> Settings.
# # O Streamlit lerá o arquivo .streamlit/config.toml se ele existir.
# st.set_page_config(
#     layout="wide",
#     page_title="Conferência Avançada de Notas Fiscais Fluig x Totvs RM",
#     page_icon="⚡"
# )

# # Paleta de Cores
# COR_VERDE = "#28a745"
# COR_VERMELHA = "#dc3545"

# # CSS customizado
# st.markdown(f"""
# <style>
#     /* Ajusta o fundo dos cards KPI para branco, garantindo visibilidade no tema escuro */
#     .kpi-card {{
#         background-color: #ffffff;
#         border: 1px solid #e0e0e0;
#         border-radius: 8px;
#         padding: 20px;
#         display: flex;
#         flex-direction: column;
#         justify-content: center;
#         height: 120px;
#         box-shadow: 0 2px 4px rgba(0,0,0,0.05);
#         margin-bottom: 15px;
#     }}
#     .kpi-title {{ font-size: 13px; color: #555; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
#     .kpi-value {{ font-size: 34px; color: #222; font-weight: 800; line-height: 1.2; }}
#     .txt-green {{ color: {COR_VERDE}; }}
#     .txt-red {{ color: {COR_VERMELHA}; }}

#     /* Ajusta o fundo e a cor do texto do card de divergência */
#     .div-card {{
#         background-color: #fff5f5;
#         border-left: 5px solid {COR_VERMELHA};
#         padding: 15px;
#         margin-bottom: 10px;
#         border-radius: 5px;
#         color: #444; /* Cor de texto escura para bom contraste no fundo claro */
#     }}
#     .kw-badge {{
#         display: inline-block;
#         background-color: #e9ecef;
#         padding: 3px 8px;
#         border-radius: 4px;
#         font-size: 0.85em;
#         margin-right: 5px;
#         margin-bottom: 5px;
#         border: 1px solid #dee2e6;
#         color: #495057; /* Cor de texto escura */
#     }}
#     button[title="View fullscreen"]{{ visibility: hidden; }}
# </style>
# """, unsafe_allow_html=True)

# # ==============================================================================
# # 🚨 CAMINHO INTELIGENTE DO TESSERACT 🚨
# # ==============================================================================
# def find_tesseract_cmd():
#     if 'tesseract_cmd_path' in st.session_state:
#         return st.session_state.tesseract_cmd_path
#     try:
#         pytesseract.pytesseract.tesseract_cmd = 'tesseract'
#         pytesseract.get_tesseract_version()
#         st.session_state.tesseract_cmd_path = 'tesseract'
#         return 'tesseract'
#     except (pytesseract.TesseractNotFoundError, FileNotFoundError):
#         windows_paths = [
#             r"C:\Program Files\Tesseract-OCR\tesseract.exe",
#             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
#             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")
#         ]
#         for path in windows_paths:
#             if os.path.exists(path):
#                 st.session_state.tesseract_cmd_path = path
#                 return path
#     st.session_state.tesseract_cmd_path = None
#     return None

# tesseract_path = find_tesseract_cmd()
# if tesseract_path:
#     pytesseract.pytesseract.tesseract_cmd = tesseract_path
# else:
#     st.error("Tesseract OCR não foi encontrado. Verifique se ele está instalado e se o caminho de instalação foi adicionado ao PATH do sistema.")

# # ==============================================================================
# # 2. FUNÇÕES TÉCNICAS
# # ==============================================================================
# def limpar_formatacao(valor):
#     if isinstance(valor, (int, float)): return float(valor)
#     if not valor or str(valor).strip() in ['-', '', 'nan']: return 0.0
#     val_str = str(valor).replace('R$', '').strip()
#     val_str = re.sub(r'[^\d.,]', '', val_str)
#     if ',' in val_str and '.' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
#     elif ',' in val_str: val_str = val_str.replace(',', '.')
#     try: return float(val_str)
#     except: return 0.0

# def formatar_moeda(valor):
#     return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# def ler_pdf_ocr(arquivo_bytes):
#     texto_completo = ""
#     try:
#         doc = fitz.open(stream=arquivo_bytes, filetype="pdf")
#         for pagina in doc: texto_completo += pagina.get_text("text", sort=True) + "\n"
#         if len(texto_completo.strip()) < 100:
#             texto_ocr = ""
#             for pagina in doc:
#                 pix = pagina.get_pixmap(dpi=300)
#                 img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
#                 enhancer = ImageEnhance.Contrast(img)
#                 img_enhanced = enhancer.enhance(2.0)
#                 texto_ocr += pytesseract.image_to_string(img_enhanced, lang='por') + "\n"
#             texto_completo += "\n" + texto_ocr
#     except Exception as e:
#         st.warning(f"Não foi possível ler um dos PDFs. Erro: {e}")
#         return None
#     return texto_completo

# def buscar_valor_com_keywords(texto_ocr, valor_erp, keywords, tolerancia=0.05):
#     if valor_erp <= 0.02: return True
#     valor_str_padrao = f"{valor_erp:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#     if valor_str_padrao in texto_ocr: return True
#     padrao_num = r"(\d{1,3}(?:[.,\s]?\d{3})*[.,]\d{2})"
#     for m in re.finditer(padrao_num, texto_ocr):
#         try:
#             val_float = limpar_formatacao(m.group())
#             if abs(val_float - valor_erp) <= tolerancia:
#                 start, end = m.span()
#                 janela = texto_ocr[max(0, start-150):min(len(texto_ocr), end+150)].upper()
#                 if any(kw.upper() in janela for kw in keywords): return True
#         except: continue
#     return False

# def verificar_existencia_valor_absoluto(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     for n in raw_nums:
#         try:
#             if abs(limpar_formatacao(n) - valor_alvo) <= tolerancia: return True
#         except: pass
#     return False

# def verificar_soma_global(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     candidatos = sorted(list(set([limpar_formatacao(n) for n in raw_nums if 0.01 <= limpar_formatacao(n) <= valor_alvo])), reverse=True)[:80]
#     for r in range(2, 5): 
#         for combo in itertools.combinations(candidatos, r):
#             if abs(sum(combo) - valor_alvo) <= tolerancia: return True
#     return False

# def obter_valor_coluna_segura(linha, nomes_possiveis):
#     for nome_alvo in nomes_possiveis:
#         for col_real in linha.index:
#             if nome_alvo.upper() == str(col_real).strip().upper():
#                 return limpar_formatacao(linha[col_real])
#     return 0.0

# @st.cache_data
# def to_excel(df):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, index=False, sheet_name='Resultados')
#         workbook = writer.book
#         worksheet = writer.sheets['Resultados']
#         for i, col in enumerate(df.columns):
#             column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
#             worksheet.set_column(i, i, column_len)
#     processed_data = output.getvalue()
#     return processed_data

# KW_CSRF = ["PIS", "COFINS", "CSLL", "FEDERAL", "RETEN", "CSRF", "PASEP", "DEDUÇÕES", "LEI 10833"]
# KW_IRRF = ["IR", "IRRF", "RENDA", "FONTE"]
# KW_ISS = ["ISS", "ISSQN", "MUNICIPAL"]
# KW_INSS = ["INSS", "PREVIDENCIA"]
# KW_TOTAL = ["TOTAL", "BRUTO", "SERVIÇO", "NOTA", "VALOR", "LIQUIDO", "VALOR DOS SERVIÇOS", "VALOR DO SERVIÇO", "SERVIÇO PRESTADO", "SERVIÇOS PRESTADOS", "VALOR TOTAL DO SERVIÇO"]

# def analisar_nota(file_content, file_name, df_erp, numeros_validos_erp):
#     texto = ler_pdf_ocr(file_content) or ""
#     texto_cabecalho = texto[:3000]
#     padroes = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)", r"DANFE.*?(\d{3,})"]
#     candidato_ocr = next((int(m) for p in padroes for m in re.findall(p, texto_cabecalho, re.IGNORECASE) if int(m) in numeros_validos_erp), 0)
#     candidato_arq = 0
#     if candidato_ocr == 0:
#         candidato_arq = next((int(n) for n in re.findall(r"(\d+)", file_name) if int(n) in numeros_validos_erp), 0)
#     numero_final = candidato_ocr or candidato_arq
#     match_row = df_erp[df_erp['Numero'] == numero_final]
#     linha_dados = {'ID_ARQUIVO': file_name, 'NO_NF': numero_final or "N/A", 'NO_FLUIG': 'N/A', 'STATUS_GERAL': 'Conciliado', 'Dados_Detalhados': {}, 'Meta_Dados': {}, 'Texto_Debug': texto}
#     if match_row.empty:
#         linha_dados['STATUS_GERAL'] = 'Não consta no ERP'
#         return linha_dados
#     linha = match_row.iloc[0]
#     col_fluig = next((c for c in df_erp.columns if "Fluig" in str(c)), None)
#     if col_fluig and pd.notnull(linha[col_fluig]):
#         val = linha[col_fluig]
#         linha_dados['NO_FLUIG'] = str(int(val)) if isinstance(val, (int, float)) and str(val).replace('.','').isdigit() else str(val)
#     v_bruto = obter_valor_coluna_segura(linha, ['Valor Bruto', 'Valor Total'])
#     v_liquido = obter_valor_coluna_segura(linha, ['Valor Liquido'])
#     v_iss = obter_valor_coluna_segura(linha, ['ISS', 'Valor ISS'])
#     v_inss = obter_valor_coluna_segura(linha, ['INSS', 'Valor INSS'])
#     v_csrf_col = obter_valor_coluna_segura(linha, ['CSRF', 'PIS/COFINS'])
#     v_irrf_col = obter_valor_coluna_segura(linha, ['IRRF', 'IRFF', 'IR'])
#     v_federal_calc = max(0.0, (v_bruto - v_liquido) - v_iss - v_inss) if v_liquido > 0 else 0.0
#     linha_dados['Meta_Dados']['Federal_Calc'] = v_federal_calc
#     divergencias = False
#     def validar_campo(campo, valor_erp, keywords, usar_soma_global=False, usar_calculo_federal=False):
#         nonlocal divergencias
#         status, is_calc_warning = 'Divergência', False
#         if buscar_valor_com_keywords(texto, valor_erp, keywords) or \
#            (usar_soma_global and verificar_soma_global(texto, valor_erp)) or \
#            (usar_calculo_federal and v_federal_calc > 0 and buscar_valor_com_keywords(texto, v_federal_calc, keywords)) or \
#            (campo == 'VALOR_TOTAL' and verificar_existencia_valor_absoluto(texto, valor_erp)):
#             status = 'OK'
#         if status != 'OK':
#             divergencias = True
#             if valor_erp == 0 and v_federal_calc > 0 and usar_calculo_federal: is_calc_warning = True
#         linha_dados['Dados_Detalhados'][campo] = {'erp_valor': valor_erp, 'status': status, 'is_calc': is_calc_warning}
#     validar_campo('VALOR_TOTAL', v_bruto, KW_TOTAL)
#     validar_campo('ISS', v_iss, KW_ISS)
#     validar_campo('INSS', v_inss, KW_INSS)
#     validar_campo('CSRF', v_csrf_col, KW_CSRF, usar_soma_global=True, usar_calculo_federal=True)
#     validar_campo('IRRF', v_irrf_col, KW_IRRF, usar_soma_global=True, usar_calculo_federal=True)
#     if divergencias: linha_dados['STATUS_GERAL'] = 'Com Divergência'
#     return linha_dados

# # ==============================================================================
# # 4. INTERFACE
# # ==============================================================================

# st.title("⚡ Conferência Avançada de Notas Fiscais - Fluig x Totvs RM")

# if 'dados_processados' not in st.session_state: st.session_state.dados_processados = None
# if 'id_upload_atual' not in st.session_state: st.session_state.id_upload_atual = ""
# if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0
# if 'tempo_execucao' not in st.session_state: st.session_state.tempo_execucao = ""
# if 'pdf_files_map' not in st.session_state: st.session_state.pdf_files_map = {}

# if tesseract_path:
#     with st.expander("📂 Importação de Arquivos", expanded=st.session_state.dados_processados is None):
#         c1, c2 = st.columns(2)
#         pdf_files = c1.file_uploader("1. PDFs", accept_multiple_files=True, type="pdf")
#         excel_file = c2.file_uploader("2. ERP (.xlsx)", type=["xlsx", "xls"])

#     if pdf_files and excel_file:
#         id_novo = str(sorted([f.name for f in pdf_files])) + excel_file.name
#         if st.session_state.id_upload_atual != id_novo:
#             with st.spinner('Analisando documentos...'):
#                 try:
#                     inicio_timer = time.time()
#                     df_erp = pd.read_excel(excel_file, sheet_name=0) 
#                     df_erp.columns = [str(c).strip() for c in df_erp.columns]
#                     if 'Numero' in df_erp.columns:
#                         df_erp['Numero'] = pd.to_numeric(df_erp['Numero'], errors='coerce').fillna(0).astype(int)
#                         numeros_validos_erp = set(df_erp['Numero'].unique())
#                         st.session_state.pdf_files_map = {f.name: f.getvalue() for f in pdf_files}
#                         prog = st.empty()
#                         bar = prog.progress(0, text="Iniciando processamento...")
#                         resultados = []
#                         total = len(pdf_files)
#                         with concurrent.futures.ThreadPoolExecutor() as executor:
#                             futures = {executor.submit(analisar_nota, content, name, df_erp, numeros_validos_erp): name for name, content in st.session_state.pdf_files_map.items()}
#                             for i, future in enumerate(concurrent.futures.as_completed(futures)):
#                                 pdf_name = futures[future]
#                                 try: resultados.append(future.result())
#                                 except Exception as exc: st.error(f"Erro ao processar o arquivo {pdf_name}: {exc}")
#                                 bar.progress((i + 1) / total, text=f"Lendo documento {i+1} de {total}: {pdf_name}")
#                         fim_timer = time.time()
#                         st.session_state.tempo_execucao = f"{int((fim_timer - inicio_timer) // 60)} min e {int((fim_timer - inicio_timer) % 60)} seg"
#                         prog.empty()
#                         st.success(f"✅ Processamento concluído! Tempo total: {st.session_state.tempo_execucao}")
#                         st.session_state.dados_processados = pd.DataFrame(sorted(resultados, key=lambda x: x['ID_ARQUIVO']))
#                         st.session_state.id_upload_atual = id_novo
#                         st.session_state.pagina_atual = 0
#                         st.rerun()
#                     else:
#                         st.error("Erro: Coluna 'Numero' não encontrada na primeira aba.")
#                 except Exception as e:
#                     st.error(f"Erro geral no processamento: {e}")

#     if st.session_state.dados_processados is not None:
#         df_final = st.session_state.dados_processados
        
#         divergentes_df = df_final[~df_final['STATUS_GERAL'].str.startswith('Conciliado')]
#         conciliados = len(df_final) - len(divergentes_df)
#         divergentes = len(divergentes_df)
#         total = len(df_final)

#         st.markdown("### Resumo da Conferência")
#         if st.session_state.tempo_execucao: st.caption(f"⏱️ Tempo: {st.session_state.tempo_execucao}")
        
#         col_kpi, col_vazio, col_chart = st.columns([3, 0.2, 2])
#         with col_kpi:
#             st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Verificado (PDFs)</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
#             k2, k3 = st.columns(2)
#             k2.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERDE};"><div class="kpi-title">Conciliados</div><div class="kpi-value txt-green">{conciliados}</div></div>', unsafe_allow_html=True)
#             k3.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERMELHA};"><div class="kpi-title">Com Divergências</div><div class="kpi-value txt-red">{divergentes}</div></div>', unsafe_allow_html=True)

#         with col_chart:
#             if total > 0:
#                 source = pd.DataFrame({"Status": ["Conciliados", "Divergentes"], "Valor": [conciliados, divergentes]})
#                 source["Percent"] = source["Valor"] / source["Valor"].sum()
#                 base = alt.Chart(source).encode(theta=alt.Theta("Valor:Q", stack=True), order=alt.Order("Status:N", sort="descending"))
#                 pie = base.mark_arc(outerRadius=110).encode(
#                     color=alt.Color("Status:N", scale=alt.Scale(domain=["Conciliados", "Divergentes"], range=[COR_VERDE, COR_VERMELHA]), legend=alt.Legend(title=None, orient='right', labelFontSize=14)),
#                     tooltip=["Status", "Valor", alt.Tooltip("Percent:Q", format=".1%")]
#                 )
#                 text = base.mark_text(radius=135, size=16, fontWeight='bold').encode(text=alt.Text("Percent:Q", format=".1%")) 
#                 chart = (pie + text).properties(height=300).configure_view(strokeWidth=0)
#                 st.altair_chart(chart, use_container_width=True, theme="streamlit")

#         st.markdown("---")
#         st.subheader("Detalhamento por Nota Fiscal")
#         filtro = st.radio("Exibir:", ["Todos", "Apenas Divergentes"], horizontal=True, key="filtro_detalhes")
        
#         df_show = divergentes_df.reset_index(drop=True) if filtro == "Apenas Divergentes" else df_final.copy()

#         ITENS_POR_PAGINA = 10
#         total_pags = max(1, (len(df_show) - 1) // ITENS_POR_PAGINA + 1)
#         st.session_state.pagina_atual = min(st.session_state.pagina_atual, total_pags - 1)
#         inicio, fim = st.session_state.pagina_atual * ITENS_POR_PAGINA, (st.session_state.pagina_atual + 1) * ITENS_POR_PAGINA
#         df_pagina = df_show.iloc[inicio:fim]
        
#         def icon_status(row, campo):
#             status_geral = str(row.get('STATUS_GERAL', ''))
#             if status_geral == 'Não consta no ERP':
#                 return "➖"
#             if status_geral.startswith('Conciliado'):
#                 return "✅"
            
#             detalhes = row.get('Dados_Detalhados', {})
#             if not detalhes or campo not in detalhes or detalhes[campo]['erp_valor'] == 0:
#                 return "✅"
#             return "✅" if detalhes[campo]['status'] == "OK" else "❌"

#         if not df_pagina.empty:
#             df_view = pd.DataFrame({
#                 'Fluig': df_pagina['NO_FLUIG'], 
#                 'Arquivo': df_pagina['ID_ARQUIVO'], 
#                 'NF': df_pagina['NO_NF'], 
#                 'ISS': df_pagina.apply(lambda x: icon_status(x, 'ISS'), axis=1), 
#                 'CSRF': df_pagina.apply(lambda x: icon_status(x, 'CSRF'), axis=1), 
#                 'INSS': df_pagina.apply(lambda x: icon_status(x, 'INSS'), axis=1), 
#                 'IRRF': df_pagina.apply(lambda x: icon_status(x, 'IRRF'), axis=1),
#                 'Total': df_pagina.apply(lambda x: icon_status(x, 'VALOR_TOTAL'), axis=1), 
#                 'Status': df_pagina['STATUS_GERAL']
#             })
#             st.dataframe(df_view, hide_index=True, use_container_width=True)
        
#         c_prev, c_info, c_next, c_export_space, c_export_btn = st.columns([1.5, 1, 1.5, 7, 2])
        
#         with c_prev:
#             if st.button("⬅️ Anterior", use_container_width=True, disabled=(st.session_state.pagina_atual == 0)):
#                 st.session_state.pagina_atual -= 1
#                 st.rerun()
#         with c_info:
#             st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual + 1} de {total_pags}</div>", unsafe_allow_html=True)
#         with c_next:
#             if st.button("Próximo ➡️", use_container_width=True, disabled=(st.session_state.pagina_atual >= total_pags - 1)):
#                 st.session_state.pagina_atual += 1
#                 st.rerun()
#         with c_export_btn:
#             df_export = df_final.drop(columns=['Dados_Detalhados', 'Meta_Dados', 'Texto_Debug'])
#             excel_data = to_excel(df_export)
#             st.download_button(label="📥 Exportar para Excel", data=excel_data, file_name="conciliacao_resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

#         st.markdown("---")
#         if not divergentes_df.empty:
#             st.subheader("🔎 Análise e Conciliação Manual")
#             opts = divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1).tolist()
#             sel = st.selectbox("Selecione uma nota para analisar:", opts, key="select_divergencia", index=None, placeholder="Selecione uma nota com divergência...")
            
#             if sel:
#                 col_diag, col_pdf = st.columns(2)
#                 row_index = divergentes_df[divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1) == sel].index[0]
#                 row = divergentes_df.loc[row_index]
                
#                 with col_diag:
#                     if row['STATUS_GERAL'] == 'Não consta no ERP':
#                         st.error(f"**Nota não encontrada no ERP:** O arquivo `{row['ID_ARQUIVO']}` não corresponde a nenhuma linha no relatório em Excel.")
#                     else:
#                         detalhes = row.get('Dados_Detalhados', {})
#                         meta = row.get('Meta_Dados', {})
#                         campos_erro = {k: v for k, v in detalhes.items() if v['status'] != 'OK' and v['erp_valor'] > 0}
#                         if not campos_erro:
#                             st.info("Todos os valores com divergência no ERP são R$ 0,00 ou não foram encontrados.")
#                         for campo, info in campos_erro.items():
#                             nome, valor = campo.replace("_", " "), formatar_moeda(info['erp_valor'])
#                             msg_extra = ""
#                             if info.get('is_calc'):
#                                  calc_val = formatar_moeda(meta.get('Federal_Calc', 0))
#                                  msg_extra = f" (Obs: ERP zerado, mas um cálculo sugere um valor próximo de **{calc_val}**)"
#                             kws_usadas = globals().get(f"KW_{campo.split(' ')[0]}", [])
#                             kw_html = "".join([f"<span class='kw-badge'>{k}</span>" for k in kws_usadas]) or "N/A"
#                             html_parts = ["<div class='div-card'>", f"<div style='margin-bottom:8px;'><b>{nome}</b>: ERP espera <b>{valor}</b>{msg_extra}</div>", "<div style='font-size:0.9em; color:#666;'>", "<b>Diagnóstico:</b> Valor não localizado no PDF próximo às palavras-chave.", 
# f"<b>Keywords:</b> {kw_html}", "</div>", "</div>"]
#                             html_string = "".join(html_parts)
#                             st.markdown(html_string, unsafe_allow_html=True)

#                     st.write("") 
#                     col_btn_vazia1, col_btn_centro, col_btn_vazia2 = st.columns([1, 2, 1])
#                     with col_btn_centro:
#                         if st.button("✅ Conciliar Manualmente", key=f"manual_concile_{row_index}", use_container_width=True):
#                             original_index = st.session_state.dados_processados[st.session_state.dados_processados['ID_ARQUIVO'] == row['ID_ARQUIVO']].index[0]
#                             st.session_state.dados_processados.loc[original_index, 'STATUS_GERAL'] = 'Conciliado (Manual)'
#                             for k in st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados']:
#                                 st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados'][k]['status'] = 'OK (Manual)'
#                             st.success(f"Nota {row['NO_NF']} conciliada manualmente!")
#                             time.sleep(1)
#                             st.rerun()

#                 with col_pdf:
#                     pdf_content = st.session_state.pdf_files_map.get(row['ID_ARQUIVO'])
#                     if pdf_content:
#                         base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
#                         pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
#                         st.markdown(pdf_display, unsafe_allow_html=True)
#                     else:
#                         st.error("Arquivo PDF não encontrado na memória para exibição.")
#----------------------------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------------

# # robot_conference.py (VERSÃO COMPLETA COM BUSCA AUTOMÁTICA E FILTRO INTELIGENTE)

# import streamlit as st
# import pandas as pd
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image, ImageEnhance
# import io
# import re
# import os
# import altair as alt
# import time
# import itertools
# import concurrent.futures
# import base64
# import subprocess

# # ==============================================================================
# # 1. CONFIGURAÇÃO DA PÁGINA E FUNÇÕES AUXILIARES
# # ==============================================================================
# st.set_page_config(
#     layout="wide",
#     page_title="Conferência Avançada de Notas Fiscais Fluig x Totvs RM",
#     page_icon="⚡"
# )

# # Paleta de Cores e CSS
# COR_VERDE = "#28a745"
# COR_VERMELHA = "#dc3545"
# st.markdown(f"""
# <style>
#     .kpi-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; justify-content: center; height: 120px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
#     .kpi-title {{ font-size: 13px; color: #555; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
#     .kpi-value {{ font-size: 34px; color: #222; font-weight: 800; line-height: 1.2; }}
#     .txt-green {{ color: {COR_VERDE}; }}
#     .txt-red {{ color: {COR_VERMELHA}; }}
#     .div-card {{ background-color: #fff5f5; border-left: 5px solid {COR_VERMELHA}; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #444; }}
#     .kw-badge {{ display: inline-block; background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; margin-right: 5px; margin-bottom: 5px; border: 1px solid #dee2e6; color: #495057; }}
#     button[title="View fullscreen"]{{ visibility: hidden; }}
# </style>
# """, unsafe_allow_html=True)

# # Caminho do Tesseract
# def find_tesseract_cmd():
#     if 'tesseract_cmd_path' in st.session_state: return st.session_state.tesseract_cmd_path
#     try:
#         pytesseract.pytesseract.tesseract_cmd = 'tesseract'
#         pytesseract.get_tesseract_version()
#         st.session_state.tesseract_cmd_path = 'tesseract'
#         return 'tesseract'
#     except (pytesseract.TesseractNotFoundError, FileNotFoundError):
#         windows_paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")]
#         for path in windows_paths:
#             if os.path.exists(path):
#                 st.session_state.tesseract_cmd_path = path
#                 return path
#     st.session_state.tesseract_cmd_path = None
#     return None
# tesseract_path = find_tesseract_cmd()
# if tesseract_path: pytesseract.pytesseract.tesseract_cmd = tesseract_path
# else: st.error("Tesseract OCR não foi encontrado.")

# # Funções Técnicas
# def limpar_formatacao(valor):
#     if isinstance(valor, (int, float)): return float(valor)
#     if not valor or str(valor).strip() in ['-', '', 'nan']: return 0.0
#     val_str = str(valor).replace('R$', '').strip()
#     val_str = re.sub(r'[^\d.,]', '', val_str)
#     if ',' in val_str and '.' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
#     elif ',' in val_str: val_str = val_str.replace(',', '.')
#     try: return float(val_str)
#     except: return 0.0
# def formatar_moeda(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
# def ler_pdf_ocr(arquivo_bytes):
#     texto_completo = ""
#     try:
#         doc = fitz.open(stream=arquivo_bytes, filetype="pdf")
#         for pagina in doc: texto_completo += pagina.get_text("text", sort=True) + "\n"
#         if len(texto_completo.strip()) < 100:
#             texto_ocr = ""
#             for pagina in doc:
#                 pix = pagina.get_pixmap(dpi=300)
#                 img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
#                 enhancer = ImageEnhance.Contrast(img)
#                 img_enhanced = enhancer.enhance(2.0)
#                 texto_ocr += pytesseract.image_to_string(img_enhanced, lang='por') + "\n"
#             texto_completo += "\n" + texto_ocr
#     except Exception as e:
#         st.warning(f"Não foi possível ler um dos PDFs. Erro: {e}")
#         return None
#     return texto_completo
# def buscar_valor_com_keywords(texto_ocr, valor_erp, keywords, tolerancia=0.05):
#     if valor_erp <= 0.02: return True
#     valor_str_padrao = f"{valor_erp:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#     if valor_str_padrao in texto_ocr: return True
#     padrao_num = r"(\d{1,3}(?:[.,\s]?\d{3})*[.,]\d{2})"
#     for m in re.finditer(padrao_num, texto_ocr):
#         try:
#             val_float = limpar_formatacao(m.group())
#             if abs(val_float - valor_erp) <= tolerancia:
#                 start, end = m.span()
#                 janela = texto_ocr[max(0, start-150):min(len(texto_ocr), end+150)].upper()
#                 if any(kw.upper() in janela for kw in keywords): return True
#         except: continue
#     return False
# def verificar_existencia_valor_absoluto(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     for n in raw_nums:
#         try:
#             if abs(limpar_formatacao(n) - valor_alvo) <= tolerancia: return True
#         except: pass
#     return False
# def verificar_soma_global(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     candidatos = sorted(list(set([limpar_formatacao(n) for n in raw_nums if 0.01 <= limpar_formatacao(n) <= valor_alvo])), reverse=True)[:80]
#     for r in range(2, 5): 
#         for combo in itertools.combinations(candidatos, r):
#             if abs(sum(combo) - valor_alvo) <= tolerancia: return True
#     return False
# def obter_valor_coluna_segura(linha, nomes_possiveis):
#     for nome_alvo in nomes_possiveis:
#         for col_real in linha.index:
#             if nome_alvo.upper() == str(col_real).strip().upper():
#                 return limpar_formatacao(linha[col_real])
#     return 0.0
# @st.cache_data
# def to_excel(df):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, index=False, sheet_name='Resultados')
#         workbook = writer.book
#         worksheet = writer.sheets['Resultados']
#         for i, col in enumerate(df.columns):
#             column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
#             worksheet.set_column(i, i, column_len)
#     processed_data = output.getvalue()
#     return processed_data
# KW_CSRF = ["PIS", "COFINS", "CSLL", "FEDERAL", "RETEN", "CSRF", "PASEP", "DEDUÇÕES", "LEI 10833"]
# KW_IRRF = ["IR", "IRRF", "RENDA", "FONTE"]
# KW_ISS = ["ISS", "ISSQN", "MUNICIPAL"]
# KW_INSS = ["INSS", "PREVIDENCIA"]
# KW_TOTAL = ["TOTAL", "BRUTO", "SERVIÇO", "NOTA", "VALOR", "LIQUIDO", "VALOR DOS SERVIÇOS", "VALOR DO SERVIÇO", "SERVIÇO PRESTADO", "SERVIÇOS PRESTADOS", "VALOR TOTAL DO SERVIÇO"]
# def analisar_nota(file_content, file_name, df_erp, numeros_validos_erp):
#     texto = ler_pdf_ocr(file_content) or ""
#     texto_cabecalho = texto[:3000]
#     padroes = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)", r"DANFE.*?(\d{3,})"]
#     candidato_ocr = next((int(m) for p in padroes for m in re.findall(p, texto_cabecalho, re.IGNORECASE) if int(m) in numeros_validos_erp), 0)
#     candidato_arq = 0
#     if candidato_ocr == 0:
#         candidato_arq = next((int(n) for n in re.findall(r"(\d+)", file_name) if int(n) in numeros_validos_erp), 0)
#     numero_final = candidato_ocr or candidato_arq
#     match_row = df_erp[df_erp['Numero'] == numero_final]
#     linha_dados = {'ID_ARQUIVO': file_name, 'NO_NF': numero_final or "N/A", 'NO_FLUIG': 'N/A', 'STATUS_GERAL': 'Conciliado', 'Dados_Detalhados': {}, 'Meta_Dados': {}, 'Texto_Debug': texto}
#     if match_row.empty:
#         linha_dados['STATUS_GERAL'] = 'Não consta no ERP'
#         return linha_dados
#     linha = match_row.iloc[0]
#     col_fluig = next((c for c in df_erp.columns if "Fluig" in str(c)), None)
#     if col_fluig and pd.notnull(linha[col_fluig]):
#         val = linha[col_fluig]
#         linha_dados['NO_FLUIG'] = str(int(val)) if isinstance(val, (int, float)) and str(val).replace('.','').isdigit() else str(val)
#     v_bruto = obter_valor_coluna_segura(linha, ['Valor Bruto', 'Valor Total'])
#     v_liquido = obter_valor_coluna_segura(linha, ['Valor Liquido'])
#     v_iss = obter_valor_coluna_segura(linha, ['ISS', 'Valor ISS'])
#     v_inss = obter_valor_coluna_segura(linha, ['INSS', 'Valor INSS'])
#     v_csrf_col = obter_valor_coluna_segura(linha, ['CSRF', 'PIS/COFINS'])
#     v_irrf_col = obter_valor_coluna_segura(linha, ['IRRF', 'IRFF', 'IR'])
#     v_federal_calc = max(0.0, (v_bruto - v_liquido) - v_iss - v_inss) if v_liquido > 0 else 0.0
#     linha_dados['Meta_Dados']['Federal_Calc'] = v_federal_calc
#     divergencias = False
#     def validar_campo(campo, valor_erp, keywords, usar_soma_global=False, usar_calculo_federal=False):
#         nonlocal divergencias
#         status, is_calc_warning = 'Divergência', False
#         if buscar_valor_com_keywords(texto, valor_erp, keywords) or \
#            (usar_soma_global and verificar_soma_global(texto, valor_erp)) or \
#            (usar_calculo_federal and v_federal_calc > 0 and buscar_valor_com_keywords(texto, v_federal_calc, keywords)) or \
#            (campo == 'VALOR_TOTAL' and verificar_existencia_valor_absoluto(texto, valor_erp)):
#             status = 'OK'
#         if status != 'OK':
#             divergencias = True
#             if valor_erp == 0 and v_federal_calc > 0 and usar_calculo_federal: is_calc_warning = True
#         linha_dados['Dados_Detalhados'][campo] = {'erp_valor': valor_erp, 'status': status, 'is_calc': is_calc_warning}
#     validar_campo('VALOR_TOTAL', v_bruto, KW_TOTAL)
#     validar_campo('ISS', v_iss, KW_ISS)
#     validar_campo('INSS', v_inss, KW_INSS)
#     validar_campo('CSRF', v_csrf_col, KW_CSRF, usar_soma_global=True, usar_calculo_federal=True)
#     validar_campo('IRRF', v_irrf_col, KW_IRRF, usar_soma_global=True, usar_calculo_federal=True)
#     if divergencias: linha_dados['STATUS_GERAL'] = 'Com Divergência'
#     return linha_dados

# # ==============================================================================
# # 4. INTERFACE (SEÇÃO MODIFICADA)
# # ==============================================================================

# st.title("⚡ Conferência Avançada de Notas Fiscais - Fluig x Totvs RM")

# # Inicialização do estado da sessão
# if 'dados_processados' not in st.session_state: st.session_state.dados_processados = None
# if 'id_upload_atual' not in st.session_state: st.session_state.id_upload_atual = ""
# if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0
# if 'tempo_execucao' not in st.session_state: st.session_state.tempo_execucao = ""
# if 'pdf_files_map' not in st.session_state: st.session_state.pdf_files_map = {}

# if tesseract_path:
#     with st.expander("📂 Arquivos para Conferência", expanded=st.session_state.dados_processados is None):
        
#         # ======================================================================
#         # 💡 MELHORIA 1: Busca automática de PDFs na pasta padrão 💡
#         # ======================================================================
#         pdf_files_prontos = []
#         arquivos_ignorados = []
#         pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
#         palavras_chave_filtro = ["boleto", "bol", "orçamento", "fatura", "relatorio", "demonstrativo", "sabesp", "enel"]

#         if os.path.exists(pasta_downloads):
#             for filename in os.listdir(pasta_downloads):
#                 if filename.lower().endswith(".pdf"):
#                     # Filtro inteligente
#                     if any(keyword in filename.lower() for keyword in palavras_chave_filtro):
#                         arquivos_ignorados.append(filename)
#                     else:
#                         pdf_files_prontos.append(filename)
        
#         if pdf_files_prontos:
#             st.success(f"✅ **{len(pdf_files_prontos)}** arquivos PDF encontrados na pasta 'Notas_Fluig' e prontos para a conferência.")
#             if arquivos_ignorados:
#                 with st.expander(f"⚠️ **{len(arquivos_ignorados)}** arquivos foram ignorados (boletos, orçamentos, etc.). Clique para ver a lista."):
#                     st.code("\n".join(arquivos_ignorados))
#         else:
#             st.warning("Nenhum arquivo PDF válido encontrado na pasta 'Downloads/Notas_Fluig'.")
        
#         # Mantém apenas o uploader do Excel
#         excel_file = st.file_uploader("Anexe o relatório do ERP (.xlsx) para iniciar", type=["xlsx", "xls"])
#         # ======================================================================

#     # A lógica de processamento agora é acionada pela presença do arquivo Excel e dos PDFs encontrados
#     if pdf_files_prontos and excel_file:
#         id_novo = str(sorted(pdf_files_prontos)) + excel_file.name
        
#         if st.session_state.id_upload_atual != id_novo:
#             with st.spinner('Analisando documentos...'):
#                 try:
#                     inicio_timer = time.time()
#                     df_erp = pd.read_excel(excel_file, sheet_name=0) 
#                     df_erp.columns = [str(c).strip() for c in df_erp.columns]
#                     if 'Numero' in df_erp.columns:
#                         df_erp['Numero'] = pd.to_numeric(df_erp['Numero'], errors='coerce').fillna(0).astype(int)
#                         numeros_validos_erp = set(df_erp['Numero'].unique())
                        
#                         # ======================================================================
#                         # 💡 MELHORIA 2: Carrega os PDFs encontrados automaticamente 💡
#                         # ======================================================================
#                         st.session_state.pdf_files_map = {}
#                         for filename in pdf_files_prontos:
#                             filepath = os.path.join(pasta_downloads, filename)
#                             with open(filepath, "rb") as f:
#                                 st.session_state.pdf_files_map[filename] = f.read()
#                         # ======================================================================

#                         prog = st.empty()
#                         bar = prog.progress(0, text="Iniciando processamento...")
#                         resultados = []
#                         total = len(st.session_state.pdf_files_map)
                        
#                         with concurrent.futures.ThreadPoolExecutor() as executor:
#                             futures = {executor.submit(analisar_nota, content, name, df_erp, numeros_validos_erp): name for name, content in st.session_state.pdf_files_map.items()}
#                             for i, future in enumerate(concurrent.futures.as_completed(futures)):
#                                 pdf_name = futures[future]
#                                 try: resultados.append(future.result())
#                                 except Exception as exc: st.error(f"Erro ao processar o arquivo {pdf_name}: {exc}")
#                                 bar.progress((i + 1) / total, text=f"Lendo documento {i+1} de {total}: {pdf_name}")
                        
#                         fim_timer = time.time()
#                         st.session_state.tempo_execucao = f"{int((fim_timer - inicio_timer) // 60)} min e {int((fim_timer - inicio_timer) % 60)} seg"
#                         prog.empty()
#                         st.success(f"✅ Processamento concluído! Tempo total: {st.session_state.tempo_execucao}")
#                         st.session_state.dados_processados = pd.DataFrame(sorted(resultados, key=lambda x: x['ID_ARQUIVO']))
#                         st.session_state.id_upload_atual = id_novo
#                         st.session_state.pagina_atual = 0
#                         st.rerun()
#                     else:
#                         st.error("Erro: Coluna 'Numero' não encontrada na primeira aba do arquivo Excel.")
#                 except Exception as e:
#                     st.error(f"Erro geral no processamento: {e}")

#     if st.session_state.dados_processados is not None:
#         df_final = st.session_state.dados_processados
#         divergentes_df = df_final[~df_final['STATUS_GERAL'].str.startswith('Conciliado')]
#         conciliados = len(df_final) - len(divergentes_df)
#         divergentes = len(divergentes_df)
#         total = len(df_final)
#         st.markdown("### Resumo da Conferência")
#         if st.session_state.tempo_execucao: st.caption(f"⏱️ Tempo: {st.session_state.tempo_execucao}")
#         col_kpi, col_vazio, col_chart = st.columns([3, 0.2, 2])
#         with col_kpi:
#             st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Verificado (PDFs)</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
#             k2, k3 = st.columns(2)
#             k2.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERDE};"><div class="kpi-title">Conciliados</div><div class="kpi-value txt-green">{conciliados}</div></div>', unsafe_allow_html=True)
#             k3.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERMELHA};"><div class="kpi-title">Com Divergências</div><div class="kpi-value txt-red">{divergentes}</div></div>', unsafe_allow_html=True)
#         with col_chart:
#             if total > 0:
#                 source = pd.DataFrame({"Status": ["Conciliados", "Divergentes"], "Valor": [conciliados, divergentes]})
#                 source["Percent"] = source["Valor"] / source["Valor"].sum()
#                 base = alt.Chart(source).encode(theta=alt.Theta("Valor:Q", stack=True), order=alt.Order("Status:N", sort="descending"))
#                 pie = base.mark_arc(outerRadius=110).encode(color=alt.Color("Status:N", scale=alt.Scale(domain=["Conciliados", "Divergentes"], range=[COR_VERDE, COR_VERMELHA]), legend=alt.Legend(title=None, orient='right', labelFontSize=14)), tooltip=["Status", "Valor", alt.Tooltip("Percent:Q", format=".1%")])
#                 text = base.mark_text(radius=135, size=16, fontWeight='bold').encode(text=alt.Text("Percent:Q", format=".1%")) 
#                 chart = (pie + text).properties(height=300).configure_view(strokeWidth=0)
#                 st.altair_chart(chart, use_container_width=True, theme="streamlit")
#         st.markdown("---")
#         st.subheader("Detalhamento por Nota Fiscal")
#         filtro = st.radio("Exibir:", ["Todos", "Apenas Divergentes"], horizontal=True, key="filtro_detalhes")
#         df_show = divergentes_df.reset_index(drop=True) if filtro == "Apenas Divergentes" else df_final.copy()
#         ITENS_POR_PAGINA = 10
#         total_pags = max(1, (len(df_show) - 1) // ITENS_POR_PAGINA + 1)
#         st.session_state.pagina_atual = min(st.session_state.pagina_atual, total_pags - 1)
#         inicio, fim = st.session_state.pagina_atual * ITENS_POR_PAGINA, (st.session_state.pagina_atual + 1) * ITENS_POR_PAGINA
#         df_pagina = df_show.iloc[inicio:fim]
#         def icon_status(row, campo):
#             status_geral = str(row.get('STATUS_GERAL', ''))
#             if status_geral == 'Não consta no ERP': return "➖"
#             if status_geral.startswith('Conciliado'): return "✅"
#             detalhes = row.get('Dados_Detalhados', {})
#             if not detalhes or campo not in detalhes or detalhes[campo]['erp_valor'] == 0: return "✅"
#             return "✅" if detalhes[campo]['status'] == "OK" else "❌"
#         if not df_pagina.empty:
#             df_view = pd.DataFrame({'Fluig': df_pagina['NO_FLUIG'], 'Arquivo': df_pagina['ID_ARQUIVO'], 'NF': df_pagina['NO_NF'], 'ISS': df_pagina.apply(lambda x: icon_status(x, 'ISS'), axis=1), 'CSRF': df_pagina.apply(lambda x: icon_status(x, 'CSRF'), axis=1), 'INSS': df_pagina.apply(lambda x: icon_status(x, 'INSS'), axis=1), 'IRRF': df_pagina.apply(lambda x: icon_status(x, 'IRRF'), axis=1), 'Total': df_pagina.apply(lambda x: icon_status(x, 'VALOR_TOTAL'), axis=1), 'Status': df_pagina['STATUS_GERAL']})
#             st.dataframe(df_view, hide_index=True, use_container_width=True)
#         c_prev, c_info, c_next, c_export_space, c_export_btn = st.columns([1.5, 1, 1.5, 7, 2])
#         with c_prev:
#             if st.button("⬅️ Anterior", use_container_width=True, disabled=(st.session_state.pagina_atual == 0)):
#                 st.session_state.pagina_atual -= 1
#                 st.rerun()
#         with c_info: st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual + 1} de {total_pags}</div>", unsafe_allow_html=True)
#         with c_next:
#             if st.button("Próximo ➡️", use_container_width=True, disabled=(st.session_state.pagina_atual >= total_pags - 1)):
#                 st.session_state.pagina_atual += 1
#                 st.rerun()
#         with c_export_btn:
#             df_export = df_final.drop(columns=['Dados_Detalhados', 'Meta_Dados', 'Texto_Debug'])
#             excel_data = to_excel(df_export)
#             st.download_button(label="📥 Exportar para Excel", data=excel_data, file_name="conciliacao_resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
#         st.markdown("---")
#         if not divergentes_df.empty:
#             st.subheader("🔎 Análise e Conciliação Manual")
#             opts = divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1).tolist()
#             sel = st.selectbox("Selecione uma nota para analisar:", opts, key="select_divergencia", index=None, placeholder="Selecione uma nota com divergência...")
#             if sel:
#                 col_diag, col_pdf = st.columns(2)
#                 row_index = divergentes_df[divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1) == sel].index[0]
#                 row = divergentes_df.loc[row_index]
#                 with col_diag:
#                     if row['STATUS_GERAL'] == 'Não consta no ERP': st.error(f"**Nota não encontrada no ERP:** O arquivo `{row['ID_ARQUIVO']}` não corresponde a nenhuma linha no relatório em Excel.")
#                     else:
#                         detalhes = row.get('Dados_Detalhados', {})
#                         meta = row.get('Meta_Dados', {})
#                         campos_erro = {k: v for k, v in detalhes.items() if v['status'] != 'OK' and v['erp_valor'] > 0}
#                         if not campos_erro: st.info("Todos os valores com divergência no ERP são R$ 0,00 ou não foram encontrados.")
#                         for campo, info in campos_erro.items():
#                             nome, valor = campo.replace("_", " "), formatar_moeda(info['erp_valor'])
#                             msg_extra = ""
#                             if info.get('is_calc'):
#                                  calc_val = formatar_moeda(meta.get('Federal_Calc', 0))
#                                  msg_extra = f" (Obs: ERP zerado, mas um cálculo sugere um valor próximo de **{calc_val}**)"
#                             kws_usadas = globals().get(f"KW_{campo.split(' ')[0]}", [])
#                             kw_html = "".join([f"<span class='kw-badge'>{k}</span>" for k in kws_usadas]) or "N/A"
#                             html_parts = ["<div class='div-card'>", f"<div style='margin-bottom:8px;'><b>{nome}</b>: ERP espera <b>{valor}</b>{msg_extra}</div>", "<div style='font-size:0.9em; color:#666;'>", "<b>Diagnóstico:</b> Valor não localizado no PDF próximo às palavras-chave.", f"<b>Keywords:</b> {kw_html}", "</div>", "</div>"]
#                             html_string = "".join(html_parts)
#                             st.markdown(html_string, unsafe_allow_html=True)
#                     st.write("") 
#                     col_btn_vazia1, col_btn_centro, col_btn_vazia2 = st.columns([1, 2, 1])
#                     with col_btn_centro:
#                         if st.button("✅ Conciliar Manualmente", key=f"manual_concile_{row_index}", use_container_width=True):
#                             original_index = st.session_state.dados_processados[st.session_state.dados_processados['ID_ARQUIVO'] == row['ID_ARQUIVO']].index[0]
#                             st.session_state.dados_processados.loc[original_index, 'STATUS_GERAL'] = 'Conciliado (Manual)'
#                             for k in st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados']:
#                                 st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados'][k]['status'] = 'OK (Manual)'
#                             st.success(f"Nota {row['NO_NF']} conciliada manualmente!")
#                             time.sleep(1)
#                             st.rerun()
#                 with col_pdf:
#                     pdf_content = st.session_state.pdf_files_map.get(row['ID_ARQUIVO'])
#                     if pdf_content:
#                         base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
#                         pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
#                         st.markdown(pdf_display, unsafe_allow_html=True)
#                     else:
#                         st.error("Arquivo PDF não encontrado na memória para exibição.")
#-----------------------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------------------

# # robot_conference.py (VERSÃO COMPLETA COM CONEXÃO PRIORITÁRIA POR FLUIG ID)

# import streamlit as st
# import pandas as pd
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image, ImageEnhance
# import io
# import re
# import os
# import altair as alt
# import time
# import itertools
# import concurrent.futures
# import base64
# import subprocess

# # ==============================================================================
# # 1. CONFIGURAÇÃO E FUNÇÕES AUXILIARES
# # ==============================================================================
# st.set_page_config(layout="wide", page_title="Conferência Avançada de Notas Fiscais", page_icon="⚡")
# COR_VERDE = "#28a745"
# COR_VERMELHA = "#dc3545"
# st.markdown(f"""
# <style>
#     .kpi-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; justify-content: center; height: 120px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
#     .kpi-title {{ font-size: 13px; color: #555; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
#     .kpi-value {{ font-size: 34px; color: #222; font-weight: 800; line-height: 1.2; }}
#     .txt-green {{ color: {COR_VERDE}; }}
#     .txt-red {{ color: {COR_VERMELHA}; }}
#     .div-card {{ background-color: #fff5f5; border-left: 5px solid {COR_VERMELHA}; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #444; }}
#     .kw-badge {{ display: inline-block; background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; margin-right: 5px; margin-bottom: 5px; border: 1px solid #dee2e6; color: #495057; }}
#     button[title="View fullscreen"]{{ visibility: hidden; }}
# </style>
# """, unsafe_allow_html=True)

# def find_tesseract_cmd():
#     if 'tesseract_cmd_path' in st.session_state: return st.session_state.tesseract_cmd_path
#     try:
#         pytesseract.pytesseract.tesseract_cmd = 'tesseract'
#         pytesseract.get_tesseract_version()
#         st.session_state.tesseract_cmd_path = 'tesseract'
#         return 'tesseract'
#     except (pytesseract.TesseractNotFoundError, FileNotFoundError):
#         windows_paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")]
#         for path in windows_paths:
#             if os.path.exists(path):
#                 st.session_state.tesseract_cmd_path = path
#                 return path
#     st.session_state.tesseract_cmd_path = None
#     return None
# tesseract_path = find_tesseract_cmd()
# if tesseract_path: pytesseract.pytesseract.tesseract_cmd = tesseract_path
# else: st.error("Tesseract OCR não foi encontrado.")

# def limpar_formatacao(valor):
#     if isinstance(valor, (int, float)): return float(valor)
#     if not valor or str(valor).strip() in ['-', '', 'nan']: return 0.0
#     val_str = str(valor).replace('R$', '').strip()
#     val_str = re.sub(r'[^\d.,]', '', val_str)
#     if ',' in val_str and '.' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
#     elif ',' in val_str: val_str = val_str.replace(',', '.')
#     try: return float(val_str)
#     except: return 0.0

# def formatar_moeda(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# def ler_pdf_ocr(arquivo_bytes):
#     texto_completo = ""
#     try:
#         doc = fitz.open(stream=arquivo_bytes, filetype="pdf")
#         for pagina in doc: texto_completo += pagina.get_text("text", sort=True) + "\n"
#         if len(texto_completo.strip()) < 100:
#             texto_ocr = ""
#             for pagina in doc:
#                 pix = pagina.get_pixmap(dpi=300)
#                 img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
#                 enhancer = ImageEnhance.Contrast(img)
#                 img_enhanced = enhancer.enhance(2.0)
#                 texto_ocr += pytesseract.image_to_string(img_enhanced, lang='por') + "\n"
#             texto_completo += "\n" + texto_ocr
#     except Exception as e:
#         st.warning(f"Não foi possível ler um dos PDFs. Erro: {e}")
#         return None
#     return texto_completo

# def buscar_valor_com_keywords(texto_ocr, valor_erp, keywords, tolerancia=0.05):
#     if valor_erp <= 0.02: return True
#     valor_str_padrao = f"{valor_erp:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#     if valor_str_padrao in texto_ocr: return True
#     padrao_num = r"(\d{1,3}(?:[.,\s]?\d{3})*[.,]\d{2})"
#     for m in re.finditer(padrao_num, texto_ocr):
#         try:
#             val_float = limpar_formatacao(m.group())
#             if abs(val_float - valor_erp) <= tolerancia:
#                 start, end = m.span()
#                 janela = texto_ocr[max(0, start-150):min(len(texto_ocr), end+150)].upper()
#                 if any(kw.upper() in janela for kw in keywords): return True
#         except: continue
#     return False

# def verificar_existencia_valor_absoluto(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     for n in raw_nums:
#         try:
#             if abs(limpar_formatacao(n) - valor_alvo) <= tolerancia: return True
#         except: pass
#     return False

# def verificar_soma_global(texto, valor_alvo, tolerancia=0.05):
#     if valor_alvo <= 0.05: return True
#     raw_nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
#     candidatos = sorted(list(set([limpar_formatacao(n) for n in raw_nums if 0.01 <= limpar_formatacao(n) <= valor_alvo])), reverse=True)[:80]
#     for r in range(2, 5): 
#         for combo in itertools.combinations(candidatos, r):
#             if abs(sum(combo) - valor_alvo) <= tolerancia: return True
#     return False

# def obter_valor_coluna_segura(linha, nomes_possiveis):
#     for nome_alvo in nomes_possiveis:
#         for col_real in linha.index:
#             if nome_alvo.upper() == str(col_real).strip().upper():
#                 return limpar_formatacao(linha[col_real])
#     return 0.0

# @st.cache_data
# def to_excel(df):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, index=False, sheet_name='Resultados')
#         workbook = writer.book
#         worksheet = writer.sheets['Resultados']
#         for i, col in enumerate(df.columns):
#             column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
#             worksheet.set_column(i, i, column_len)
#     processed_data = output.getvalue()
#     return processed_data

# KW_CSRF = ["PIS", "COFINS", "CSLL", "FEDERAL", "RETEN", "CSRF", "PASEP", "DEDUÇÕES", "LEI 10833"]
# KW_IRRF = ["IR", "IRRF", "RENDA", "FONTE"]
# KW_ISS = ["ISS", "ISSQN", "MUNICIPAL"]
# KW_INSS = ["INSS", "PREVIDENCIA"]
# KW_TOTAL = ["TOTAL", "BRUTO", "SERVIÇO", "NOTA", "VALOR", "LIQUIDO", "VALOR DOS SERVIÇOS", "VALOR DO SERVIÇO", "SERVIÇO PRESTADO", "SERVIÇOS PRESTADOS", "VALOR TOTAL DO SERVIÇO"]

# def analisar_nota(file_content, file_name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome):
#     texto = ler_pdf_ocr(file_content) or ""
#     match_row = pd.DataFrame()

#     # --- NOVA FASE 1 CORRIGIDA: A CONEXÃO (Hierarquia de Tentativas ISOLADAS) ---

#     # 1ª TENTATIVA: Usar o FLUIG ID do nome do arquivo (mais confiável)
#     if col_fluig_nome:
#         match_fluig_id_search = re.search(r"FLUIG_(\d{6,})", file_name, re.IGNORECASE)
#         if match_fluig_id_search:
#             fluig_id_from_name = int(match_fluig_id_search.group(1))
#             # Procura a linha no ERP que corresponde EXATAMENTE a este Fluig ID
#             possible_match = df_erp[df_erp[col_fluig_nome] == fluig_id_from_name]
#             if not possible_match.empty:
#                 match_row = possible_match

#     # 2ª TENTATIVA: Usar OCR para ler o NÚMERO DA NF no corpo do PDF
#     if match_row.empty: # Só tenta se a primeira falhou
#         texto_cabecalho = texto[:3000]
#         padroes_nf = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)", r"DANFE.*?(\d{3,})"]
#         candidato_ocr = next((int(m) for p in padroes_nf for m in re.findall(p, texto_cabecalho, re.IGNORECASE) if int(m) in numeros_validos_erp), 0)
#         if candidato_ocr > 0:
#             # Procura a linha no ERP que corresponde EXATAMENTE a este Número de NF
#             possible_match = df_erp[df_erp['Numero'] == candidato_ocr]
#             # Medida de segurança: se encontrar múltiplas linhas para a mesma NF, não faz a conexão para evitar ambiguidade.
#             if len(possible_match) == 1:
#                  match_row = possible_match

#     # 3ª TENTATIVA: Usar o NÚMERO DA NF do nome do arquivo
#     if match_row.empty: # Só tenta se as duas primeiras falharam
#         # Exclui o Fluig ID da busca para não confundir com o número da NF
#         name_sem_fluig = re.sub(r"FLUIG_\d{6,}", "", file_name)
#         candidato_arq = next((int(n) for n in re.findall(r"(\d+)", name_sem_fluig) if int(n) in numeros_validos_erp), 0)
#         if candidato_arq > 0:
#             # Procura a linha no ERP que corresponde EXATAMENTE a este Número de NF
#             possible_match = df_erp[df_erp['Numero'] == candidato_arq]
#             if len(possible_match) == 1:
#                 match_row = possible_match

#     # --- FIM DA FASE DE CONEXÃO ---

#     # O restante da função permanece idêntico, mas agora opera sobre um 'match_row' confiável ou vazio.
#     numero_nf_display = 0
#     fluig_id_display = "N/A"
    
#     if not match_row.empty:
#         linha_temp = match_row.iloc[0]
#         numero_nf_display = int(linha_temp.get('Numero', 0))
#         if col_fluig_nome and pd.notnull(linha_temp.get(col_fluig_nome)):
#             val = linha_temp[col_fluig_nome]
#             fluig_id_display = str(int(val)) if isinstance(val, (int, float)) and str(val).replace('.','').isdigit() else str(val)
#     else:
#         # Se não houve conexão, tenta extrair qualquer número para exibição (sem conectar)
#         padroes_nf_display = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)"]
#         numero_nf_display = next((int(m.group(1)) for p in padroes_nf_display for m in re.finditer(p, texto[:3000], re.IGNORECASE)), 0) or \
#                             next((int(n) for n in re.findall(r"(\d+)", file_name)), 0)

#     linha_dados = {'ID_ARQUIVO': file_name, 'NO_NF': numero_nf_display or "N/A", 'NO_FLUIG': fluig_id_display, 'STATUS_GERAL': 'Conciliado', 'Dados_Detalhados': {}, 'Meta_Dados': {}, 'Texto_Debug': texto}

#     if match_row.empty:
#         linha_dados['STATUS_GERAL'] = 'Não consta no ERP'
#         return linha_dados

#     linha = match_row.iloc[0]
    
#     v_bruto = obter_valor_coluna_segura(linha, ['Valor Bruto', 'Valor Total'])
#     v_liquido = obter_valor_coluna_segura(linha, ['Valor Liquido'])
#     v_iss = obter_valor_coluna_segura(linha, ['ISS', 'Valor ISS'])
#     v_inss = obter_valor_coluna_segura(linha, ['INSS', 'Valor INSS'])
#     v_csrf_col = obter_valor_coluna_segura(linha, ['CSRF', 'PIS/COFINS'])
#     v_irrf_col = obter_valor_coluna_segura(linha, ['IRRF', 'IRFF', 'IR'])
#     v_federal_calc = max(0.0, (v_bruto - v_liquido) - v_iss - v_inss) if v_liquido > 0 else 0.0
#     linha_dados['Meta_Dados']['Federal_Calc'] = v_federal_calc
#     divergencias = False
#     def validar_campo(campo, valor_erp, keywords, usar_soma_global=False, usar_calculo_federal=False):
#         nonlocal divergencias
#         status, is_calc_warning = 'Divergência', False
#         if buscar_valor_com_keywords(texto, valor_erp, keywords) or \
#            (usar_soma_global and verificar_soma_global(texto, valor_erp)) or \
#            (usar_calculo_federal and v_federal_calc > 0 and buscar_valor_com_keywords(texto, v_federal_calc, keywords)) or \
#            (campo == 'VALOR_TOTAL' and verificar_existencia_valor_absoluto(texto, valor_erp)):
#             status = 'OK'
#         if status != 'OK':
#             divergencias = True
#             if valor_erp == 0 and v_federal_calc > 0 and usar_calculo_federal: is_calc_warning = True
#         linha_dados['Dados_Detalhados'][campo] = {'erp_valor': valor_erp, 'status': status, 'is_calc': is_calc_warning}
#     validar_campo('VALOR_TOTAL', v_bruto, KW_TOTAL)
#     validar_campo('ISS', v_iss, KW_ISS)
#     validar_campo('INSS', v_inss, KW_INSS)
#     validar_campo('CSRF', v_csrf_col, KW_CSRF, usar_soma_global=True, usar_calculo_federal=True)
#     validar_campo('IRRF', v_irrf_col, KW_IRRF, usar_soma_global=True, usar_calculo_federal=True)
#     if divergencias: linha_dados['STATUS_GERAL'] = 'Com Divergência'
#     return linha_dados

# # ==============================================================================
# # 4. INTERFACE
# # ==============================================================================

# st.title("⚡ Conferência Avançada de Notas Fiscais - Fluig x Totvs RM")

# if 'dados_processados' not in st.session_state: st.session_state.dados_processados = None
# if 'id_upload_atual' not in st.session_state: st.session_state.id_upload_atual = ""
# if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0
# if 'tempo_execucao' not in st.session_state: st.session_state.tempo_execucao = ""
# if 'pdf_files_map' not in st.session_state: st.session_state.pdf_files_map = {}

# if tesseract_path:
#     with st.expander("📂 Arquivos para Conferência", expanded=st.session_state.dados_processados is None):
#         pdf_files_prontos = []
#         arquivos_ignorados = []
#         pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
#         palavras_chave_filtro = ["boleto", "bol", "orçamento", "fatura"]
#         if os.path.exists(pasta_downloads):
#             for filename in os.listdir(pasta_downloads):
#                 if filename.lower().endswith(".pdf"):
#                     if any(keyword in filename.lower() for keyword in palavras_chave_filtro):
#                         arquivos_ignorados.append(filename)
#                     else:
#                         pdf_files_prontos.append(filename)
#         if pdf_files_prontos:
#             st.success(f"✅ **{len(pdf_files_prontos)}** arquivos PDF encontrados e prontos para a conferência.")
#             if arquivos_ignorados:
#                 with st.expander(f"⚠️ **{len(arquivos_ignorados)}** arquivos foram ignorados. Clique para ver a lista."):
#                     st.code("\n".join(arquivos_ignorados))
#         else:
#             st.warning("Nenhum arquivo PDF válido encontrado na pasta 'Downloads/Notas_Fluig'.")
#         excel_file = st.file_uploader("Anexe o relatório do ERP (.xlsx) para iniciar", type=["xlsx", "xls"])

#     if pdf_files_prontos and excel_file:
#         id_novo = str(sorted(pdf_files_prontos)) + excel_file.name
#         if st.session_state.id_upload_atual != id_novo:
#             with st.spinner('Analisando documentos...'):
#                 try:
#                     inicio_timer = time.time()
#                     df_erp = pd.read_excel(excel_file, sheet_name=0) 
#                     df_erp.columns = [str(c).strip() for c in df_erp.columns]
                    
#                     if 'Numero' not in df_erp.columns:
#                         st.error("Erro: Coluna 'Numero' não encontrada na primeira aba do arquivo Excel.")
#                         st.stop()
                    
#                     df_erp['Numero'] = pd.to_numeric(df_erp['Numero'], errors='coerce').fillna(0).astype(int)
#                     numeros_validos_erp = set(df_erp['Numero'].unique())
                    
#                     col_fluig_nome = next((c for c in df_erp.columns if "FLUIG" in str(c).upper()), None)
#                     fluigs_validos_erp = set()
#                     if col_fluig_nome:
#                         df_erp[col_fluig_nome] = pd.to_numeric(df_erp[col_fluig_nome], errors='coerce').fillna(0).astype(int)
#                         fluigs_validos_erp = set(df_erp[col_fluig_nome].unique())

#                     st.session_state.pdf_files_map = {}
#                     for filename in pdf_files_prontos:
#                         filepath = os.path.join(pasta_downloads, filename)
#                         with open(filepath, "rb") as f:
#                             st.session_state.pdf_files_map[filename] = f.read()

#                     prog = st.empty()
#                     bar = prog.progress(0, text="Iniciando processamento...")
#                     resultados = []
#                     total = len(st.session_state.pdf_files_map)
                    
#                     with concurrent.futures.ThreadPoolExecutor() as executor:
#                         futures = {executor.submit(analisar_nota, content, name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome): name for name, content in st.session_state.pdf_files_map.items()}
#                         for i, future in enumerate(concurrent.futures.as_completed(futures)):
#                             pdf_name = futures[future]
#                             try: resultados.append(future.result())
#                             except Exception as exc: st.error(f"Erro ao processar o arquivo {pdf_name}: {exc}")
#                             bar.progress((i + 1) / total, text=f"Lendo documento {i+1} de {total}: {pdf_name}")
                    
#                     fim_timer = time.time()
#                     st.session_state.tempo_execucao = f"{int((fim_timer - inicio_timer) // 60)} min e {int((fim_timer - inicio_timer) % 60)} seg"
#                     prog.empty()
#                     st.success(f"✅ Processamento concluído! Tempo total: {st.session_state.tempo_execucao}")
#                     st.session_state.dados_processados = pd.DataFrame(sorted(resultados, key=lambda x: x['ID_ARQUIVO']))
#                     st.session_state.id_upload_atual = id_novo
#                     st.session_state.pagina_atual = 0
#                     st.rerun()

#                 except Exception as e:
#                     st.error(f"Erro geral no processamento: {e}")

#     if st.session_state.dados_processados is not None:
#         df_final = st.session_state.dados_processados
#         divergentes_df = df_final[~df_final['STATUS_GERAL'].str.startswith('Conciliado')]
#         conciliados = len(df_final) - len(divergentes_df)
#         divergentes = len(divergentes_df)
#         total = len(df_final)
#         st.markdown("### Resumo da Conferência")
#         if st.session_state.tempo_execucao: st.caption(f"⏱️ Tempo: {st.session_state.tempo_execucao}")
#         col_kpi, col_vazio, col_chart = st.columns([3, 0.2, 2])
#         with col_kpi:
#             st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Verificado (PDFs)</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
#             k2, k3 = st.columns(2)
#             k2.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERDE};"><div class="kpi-title">Conciliados</div><div class="kpi-value txt-green">{conciliados}</div></div>', unsafe_allow_html=True)
#             k3.markdown(f'<div class="kpi-card" style="border-left: 4px solid {COR_VERMELHA};"><div class="kpi-title">Com Divergências</div><div class="kpi-value txt-red">{divergentes}</div></div>', unsafe_allow_html=True)
#         with col_chart:
#             if total > 0:
#                 source = pd.DataFrame({"Status": ["Conciliados", "Divergentes"], "Valor": [conciliados, divergentes]})
#                 source["Percent"] = source["Valor"] / source["Valor"].sum()
#                 base = alt.Chart(source).encode(theta=alt.Theta("Valor:Q", stack=True), order=alt.Order("Status:N", sort="descending"))
#                 pie = base.mark_arc(outerRadius=110).encode(color=alt.Color("Status:N", scale=alt.Scale(domain=["Conciliados", "Divergentes"], range=[COR_VERDE, COR_VERMELHA]), legend=alt.Legend(title=None, orient='right', labelFontSize=14)), tooltip=["Status", "Valor", alt.Tooltip("Percent:Q", format=".1%")])
#                 text = base.mark_text(radius=135, size=16, fontWeight='bold').encode(text=alt.Text("Percent:Q", format=".1%")) 
#                 chart = (pie + text).properties(height=300).configure_view(strokeWidth=0)
#                 st.altair_chart(chart, use_container_width=True, theme="streamlit")
#         st.markdown("---")
#         st.subheader("Detalhamento por Nota Fiscal")
#         filtro = st.radio("Exibir:", ["Todos", "Com Divergência", "Não consta no ERP", "Conciliados"], horizontal=True, key="filtro_detalhes")
#         if filtro == "Com Divergência":
#     # Seleciona apenas os que têm divergência, mas que constam no ERP.
#             df_show = df_final[df_final['STATUS_GERAL'] == 'Com Divergência'].reset_index(drop=True)
#         elif filtro == "Não consta no ERP":
#             df_show = df_final[df_final['STATUS_GERAL'] == 'Não consta no ERP'].reset_index(drop=True)
#         elif filtro == "Conciliados":
#             df_show = df_final[df_final['STATUS_GERAL'].str.startswith('Conciliado')].reset_index(drop=True)
#         else: # "Todos"
#             df_show = df_final.copy()
#         ITENS_POR_PAGINA = 10
#         total_pags = max(1, (len(df_show) - 1) // ITENS_POR_PAGINA + 1)
#         st.session_state.pagina_atual = min(st.session_state.pagina_atual, total_pags - 1)
#         inicio, fim = st.session_state.pagina_atual * ITENS_POR_PAGINA, (st.session_state.pagina_atual + 1) * ITENS_POR_PAGINA
#         df_pagina = df_show.iloc[inicio:fim]
#         def icon_status(row, campo):
#             status_geral = str(row.get('STATUS_GERAL', ''))
#             if status_geral == 'Não consta no ERP': return "➖"
#             if status_geral.startswith('Conciliado'): return "✅"
#             detalhes = row.get('Dados_Detalhados', {})
#             if not detalhes or campo not in detalhes or detalhes[campo]['erp_valor'] == 0: return "✅"
#             return "✅" if detalhes[campo]['status'] == "OK" else "❌"
#         if not df_pagina.empty:
#             # --- CORREÇÃO ABRANGENTE ---
#             # Garante que as colunas de ID sejam tratadas como texto para evitar erros de tipo.
#             df_view = pd.DataFrame({
#                 'Fluig': df_pagina['NO_FLUIG'].astype(str), 
#                 'Arquivo': df_pagina['ID_ARQUIVO'].astype(str), 
#                 'NF': df_pagina['NO_NF'].astype(str), 
#                 'ISS': df_pagina.apply(lambda x: icon_status(x, 'ISS'), axis=1), 
#                 'CSRF': df_pagina.apply(lambda x: icon_status(x, 'CSRF'), axis=1), 
#                 'INSS': df_pagina.apply(lambda x: icon_status(x, 'INSS'), axis=1), 
#                 'IRRF': df_pagina.apply(lambda x: icon_status(x, 'IRRF'), axis=1),
#                 'Total': df_pagina.apply(lambda x: icon_status(x, 'VALOR_TOTAL'), axis=1), 
#                 'Status': df_pagina['STATUS_GERAL'].astype(str)
#             })
#             # --- FIM DA CORREÇÃO ---
#             st.dataframe(df_view, hide_index=True, use_container_width=True)
#         c_prev, c_info, c_next, c_export_space, c_export_btn = st.columns([1.5, 1, 1.5, 7, 2])
#         with c_prev:
#             if st.button("⬅️ Anterior", use_container_width=True, disabled=(st.session_state.pagina_atual == 0)):
#                 st.session_state.pagina_atual -= 1
#                 st.rerun()
#         with c_info: st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual + 1} de {total_pags}</div>", unsafe_allow_html=True)
#         with c_next:
#             if st.button("Próximo ➡️", use_container_width=True, disabled=(st.session_state.pagina_atual >= total_pags - 1)):
#                 st.session_state.pagina_atual += 1
#                 st.rerun()
#         with c_export_btn:
#             df_export = df_final.drop(columns=['Dados_Detalhados', 'Meta_Dados', 'Texto_Debug'])
#             excel_data = to_excel(df_export)
#             st.download_button(label="📥 Exportar para Excel", data=excel_data, file_name="conciliacao_resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
#         st.markdown("---")
#         if not divergentes_df.empty:
#             st.subheader("🔎 Análise e Conciliação Manual")
#             opts = divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1).tolist()
#             sel = st.selectbox("Selecione uma nota para analisar:", opts, key="select_divergencia", index=None, placeholder="Selecione uma nota com divergência...")
#             if sel:
#                 col_diag, col_pdf = st.columns(2)
#                 row_index = divergentes_df[divergentes_df.apply(lambda x: f"NF {x['NO_NF']} | Fluig: {x['NO_FLUIG']} | Arq: {x['ID_ARQUIVO']}", axis=1) == sel].index[0]
#                 row = divergentes_df.loc[row_index]
#                 with col_diag:
#                     if row['STATUS_GERAL'] == 'Não consta no ERP': st.error(f"**Nota não encontrada no ERP:** O arquivo `{row['ID_ARQUIVO']}` não corresponde a nenhuma linha no relatório em Excel.")
#                     else:
#                         detalhes = row.get('Dados_Detalhados', {})
#                         meta = row.get('Meta_Dados', {})
#                         campos_erro = {k: v for k, v in detalhes.items() if v['status'] != 'OK' and v['erp_valor'] > 0}
#                         if not campos_erro: st.info("Todos os valores com divergência no ERP são R$ 0,00 ou não foram encontrados.")
#                         for campo, info in campos_erro.items():
#                             nome, valor = campo.replace("_", " "), formatar_moeda(info['erp_valor'])
#                             msg_extra = ""
#                             if info.get('is_calc'):
#                                  calc_val = formatar_moeda(meta.get('Federal_Calc', 0))
#                                  msg_extra = f" (Obs: ERP zerado, mas um cálculo sugere um valor próximo de **{calc_val}**)"
#                             kws_usadas = globals().get(f"KW_{campo.split(' ')[0]}", [])
#                             kw_html = "".join([f"<span class='kw-badge'>{k}</span>" for k in kws_usadas]) or "N/A"
#                             html_parts = ["<div class='div-card'>", f"<div style='margin-bottom:8px;'><b>{nome}</b>: ERP espera <b>{valor}</b>{msg_extra}</div>", "<div style='font-size:0.9em; color:#666;'>", "<b>Diagnóstico:</b> Valor não localizado no PDF próximo às palavras-chave.", f"<b>Keywords:</b> {kw_html}", "</div>", "</div>"]
#                             html_string = "".join(html_parts)
#                             st.markdown(html_string, unsafe_allow_html=True)
#                     st.write("") 
#                     col_btn_vazia1, col_btn_centro, col_btn_vazia2 = st.columns([1, 2, 1])
#                     with col_btn_centro:
#                         if st.button("✅ Conciliar Manualmente", key=f"manual_concile_{row_index}", use_container_width=True):
#                             original_index = st.session_state.dados_processados[st.session_state.dados_processados['ID_ARQUIVO'] == row['ID_ARQUIVO']].index[0]
#                             st.session_state.dados_processados.loc[original_index, 'STATUS_GERAL'] = 'Conciliado (Manual)'
#                             for k in st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados']:
#                                 st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados'][k]['status'] = 'OK (Manual)'
#                             st.success(f"Nota {row['NO_NF']} conciliada manualmente!")
#                             time.sleep(1)
#                             st.rerun()
#                 with col_pdf:
#                     pdf_content = st.session_state.pdf_files_map.get(row['ID_ARQUIVO'])
#                     if pdf_content:
#                         base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
#                         pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
#                         st.markdown(pdf_display, unsafe_allow_html=True)
#                     else:
#                         st.error("Arquivo PDF não encontrado na memória para exibição.")
#----------------------------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------------

# robot_conference.py (VERSÃO COM LÓGICA DE CONEXÃO CORRIGIDA)

import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import os
import altair as alt
import time
import itertools
import concurrent.futures
import base64
import subprocess

# ==============================================================================
# 1. CONFIGURAÇÃO E FUNÇÕES AUXILIARES (Sem alterações)
# ==============================================================================
st.set_page_config(layout="wide", page_title="Conferência Avançada de Notas Fiscais", page_icon="⚡")
COR_VERDE = "#28a745"
COR_VERMELHA = "#dc3545"
st.markdown(f"""
<style>
    /* Ajusta o fundo dos cards KPI para branco, garantindo visibilidade no tema escuro */
    .kpi-card {{
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 120px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }}
    .kpi-title {{ font-size: 13px; color: #555; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
    .kpi-value {{ font-size: 34px; color: #222; font-weight: 800; line-height: 1.2; }}
    .txt-green {{ color: {COR_VERDE}; }}
    .txt-red {{ color: {COR_VERMELHA}; }}

    /* Ajusta o fundo e a cor do texto do card de divergência */
    .div-card {{
        background-color: #fff5f5;
        border-left: 5px solid {COR_VERMELHA};
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 5px;
        color: #444; /* Cor de texto escura para bom contraste no fundo claro */
    }}
    .kw-badge {{
        display: inline-block;
        background-color: #e9ecef;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        margin-right: 5px;
        margin-bottom: 5px;
        border: 1px solid #dee2e6;
        color: #495057; /* Cor de texto escura */
    }}
    button[title="View fullscreen"]{{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


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
tesseract_path = find_tesseract_cmd()
if tesseract_path: pytesseract.pytesseract.tesseract_cmd = tesseract_path
else: st.error("Tesseract OCR não foi encontrado.")

def limpar_formatacao(valor):
    if isinstance(valor, (int, float)): return float(valor)
    if not valor or str(valor).strip() in ['-', '', 'nan']: return 0.0
    val_str = str(valor).replace('R$', '').strip()
    val_str = re.sub(r'[^\d.,]', '', val_str)
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

# ==============================================================================
# 💡 FUNÇÃO ANALISAR_NOTA (LÓGICA DE CONEXÃO CORRIGIDA) 💡
# ==============================================================================
def analisar_nota(file_content, file_name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome):
    texto = ler_pdf_ocr(file_content) or ""
    match_row = pd.DataFrame()

    # --- FASE 1: A CONEXÃO (Lógica Inequívoca) ---
    
    # Verifica se o nome do arquivo contém um Fluig ID
    match_fluig_id_search = re.search(r"FLUIG_(\d{6,})", file_name, re.IGNORECASE)
    
    if match_fluig_id_search and col_fluig_nome:
        # CASO 1: O arquivo tem um Fluig ID no nome. A conexão SÓ PODE ser por ele.
        fluig_id_from_name = int(match_fluig_id_search.group(1))
        possible_match = df_erp[df_erp[col_fluig_nome] == fluig_id_from_name]
        if not possible_match.empty:
            match_row = possible_match
        # Se não encontrar, 'match_row' permanece vazio e o status será "Não consta no ERP".
        # O sistema NÃO prosseguirá para as tentativas por NF, evitando a conexão errada.

    else:
        # CASO 2: O arquivo NÃO tem um Fluig ID no nome. Usa a hierarquia por NF.
        # 2.1: Tenta por OCR
        texto_cabecalho = texto[:3000]
        padroes_nf = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)", r"DANFE.*?(\d{3,})"]
        candidato_ocr = next((int(m) for p in padroes_nf for m in re.findall(p, texto_cabecalho, re.IGNORECASE) if int(m) in numeros_validos_erp), 0)
        if candidato_ocr > 0:
            possible_match = df_erp[df_erp['Numero'] == candidato_ocr]
            if len(possible_match) == 1:
                 match_row = possible_match
        
        # 2.2: Se OCR falhar, tenta pelo nome do arquivo
        if match_row.empty:
            candidato_arq = next((int(n) for n in re.findall(r"(\d+)", file_name) if int(n) in numeros_validos_erp), 0)
            if candidato_arq > 0:
                possible_match = df_erp[df_erp['Numero'] == candidato_arq]
                if len(possible_match) == 1:
                    match_row = possible_match

    # --- FIM DA FASE DE CONEXÃO ---

    # Lógica de exibição (para preencher as colunas mesmo se não houver conexão)
    numero_nf_display = 0
    fluig_id_display = "N/A"
    if not match_row.empty:
        linha_temp = match_row.iloc[0]
        numero_nf_display = int(linha_temp.get('Numero', 0))
        if col_fluig_nome and pd.notnull(linha_temp.get(col_fluig_nome)):
            val = linha_temp[col_fluig_nome]
            fluig_id_display = str(int(val)) if isinstance(val, (int, float)) and str(val).replace('.','').isdigit() else str(val)
    else:
        padroes_nf_display = [r"N[ºo°]\s*:?\s*(\d{3,})", r"Nota\s*Fiscal\s*:?\s*(\d+)", r"NFS-e\s*:?\s*(\d+)"]
        numero_nf_display = next((int(m.group(1)) for p in padroes_nf_display for m in re.finditer(p, texto[:3000], re.IGNORECASE)), 0) or \
                            next((int(n) for n in re.findall(r"(\d+)", file_name)), 0)
        if match_fluig_id_search:
            fluig_id_display = match_fluig_id_search.group(1)

    linha_dados = {'ID_ARQUIVO': file_name, 'NO_NF': numero_nf_display or "N/A", 'NO_FLUIG': fluig_id_display, 'STATUS_GERAL': 'Conciliado', 'Dados_Detalhados': {}, 'Meta_Dados': {}, 'Texto_Debug': texto}

    if match_row.empty:
        linha_dados['STATUS_GERAL'] = 'Não consta no ERP'
        return linha_dados

    # --- FASE 2 e 3: Validação (sem alterações) ---
    linha = match_row.iloc[0]
    v_bruto = obter_valor_coluna_segura(linha, ['Valor Bruto', 'Valor Total'])
    v_liquido = obter_valor_coluna_segura(linha, ['Valor Liquido'])
    v_iss = obter_valor_coluna_segura(linha, ['ISS', 'Valor ISS'])
    v_inss = obter_valor_coluna_segura(linha, ['INSS', 'Valor INSS'])
    v_csrf_col = obter_valor_coluna_segura(linha, ['CSRF', 'PIS/COFINS'])
    v_irrf_col = obter_valor_coluna_segura(linha, ['IRRF', 'IRFF', 'IR'])
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
# 4. INTERFACE (Sem alterações)
# ==============================================================================
st.title("⚡ Conferência Avançada de Notas Fiscais - Fluig x Totvs RM")
# ... (O restante do código da interface é idêntico ao que você já tem) ...
# ... (Ele já contém as correções de 'astype(str)' e os filtros que adicionamos) ...
if 'dados_processados' not in st.session_state: st.session_state.dados_processados = None
if 'id_upload_atual' not in st.session_state: st.session_state.id_upload_atual = ""
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0
if 'tempo_execucao' not in st.session_state: st.session_state.tempo_execucao = ""
if 'pdf_files_map' not in st.session_state: st.session_state.pdf_files_map = {}

if tesseract_path:
    with st.expander("📂 Arquivos para Conferência", expanded=st.session_state.dados_processados is None):
        pdf_files_prontos = []
        arquivos_ignorados = []
        pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
        palavras_chave_filtro = ["boleto", "bol", "orçamento", "orç", "fatura", "relatorio", "comunicação de venda", "artesp", "demonstrativo", "extrato", "sabesp", "enel"]
        if os.path.exists(pasta_downloads):
            for filename in os.listdir(pasta_downloads):
                if filename.lower().endswith(".pdf"):
                    if any(keyword in filename.lower() for keyword in palavras_chave_filtro):
                        arquivos_ignorados.append(filename)
                    else:
                        pdf_files_prontos.append(filename)
        if pdf_files_prontos:
            st.success(f"✅ **{len(pdf_files_prontos)}** arquivos PDF encontrados e prontos para a conferência.")
            if arquivos_ignorados:
                with st.expander(f"⚠️ **{len(arquivos_ignorados)}** arquivos foram ignorados. Clique para ver a lista."):
                    st.code("\n".join(arquivos_ignorados))
        else:
            st.warning("Nenhum arquivo PDF válido encontrado na pasta 'Downloads/Notas_Fluig'.")
        excel_file = st.file_uploader("Anexe o relatório do ERP (.xlsx) para iniciar", type=["xlsx", "xls"])

    if pdf_files_prontos and excel_file:
        id_novo = str(sorted(pdf_files_prontos)) + excel_file.name
        if st.session_state.id_upload_atual != id_novo:
            with st.spinner('Analisando documentos...'):
                try:
                    inicio_timer = time.time()
                    df_erp = pd.read_excel(excel_file, sheet_name=0) 
                    df_erp.columns = [str(c).strip() for c in df_erp.columns]
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
                    resultados = []
                    total = len(st.session_state.pdf_files_map)
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {executor.submit(analisar_nota, content, name, df_erp, numeros_validos_erp, fluigs_validos_erp, col_fluig_nome): name for name, content in st.session_state.pdf_files_map.items()}
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            pdf_name = futures[future]
                            try: resultados.append(future.result())
                            except Exception as exc: st.error(f"Erro ao processar o arquivo {pdf_name}: {exc}")
                            bar.progress((i + 1) / total, text=f"Lendo documento {i+1} de {total}: {pdf_name}")
                    fim_timer = time.time()
                    st.session_state.tempo_execucao = f"{int((fim_timer - inicio_timer) // 60)} min e {int((fim_timer - inicio_timer) % 60)} seg"
                    prog.empty()
                    st.success(f"✅ Processamento concluído! Tempo total: {st.session_state.tempo_execucao}")
                    st.session_state.dados_processados = pd.DataFrame(sorted(resultados, key=lambda x: (x['STATUS_GERAL'] != 'Conciliado', x['ID_ARQUIVO'])))
                    st.session_state.id_upload_atual = id_novo
                    st.session_state.pagina_atual = 0
                    st.rerun()
                except Exception as e: st.error(f"Erro geral no processamento: {e}")

    if st.session_state.dados_processados is not None:
        df_final = st.session_state.dados_processados
        divergentes_df = df_final[~df_final['STATUS_GERAL'].str.startswith('Conciliado')]
        conciliados = len(df_final) - len(divergentes_df)
        divergentes = len(divergentes_df)
        total = len(df_final)
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
                source = pd.DataFrame({"Status": ["Conciliados", "Divergentes"], "Valor": [conciliados, divergentes]})
                source["Percent"] = source["Valor"] / source["Valor"].sum()
                base = alt.Chart(source).encode(theta=alt.Theta("Valor:Q", stack=True), order=alt.Order("Status:N", sort="descending"))
                pie = base.mark_arc(outerRadius=110).encode(color=alt.Color("Status:N", scale=alt.Scale(domain=["Conciliados", "Divergentes"], range=[COR_VERDE, COR_VERMELHA]), legend=alt.Legend(title=None, orient='right', labelFontSize=14)), tooltip=["Status", "Valor", alt.Tooltip("Percent:Q", format=".1%")])
                text = base.mark_text(radius=135, size=16, fontWeight='bold').encode(text=alt.Text("Percent:Q", format=".1%")) 
                chart = (pie + text).properties(height=300).configure_view(strokeWidth=0)
                st.altair_chart(chart, use_container_width=True, theme="streamlit")
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
            df_view = pd.DataFrame({'Fluig': df_pagina['NO_FLUIG'].astype(str), 'Arquivo': df_pagina['ID_ARQUIVO'].astype(str), 'NF': df_pagina['NO_NF'].astype(str), 'ISS': df_pagina.apply(lambda x: icon_status(x, 'ISS'), axis=1), 'CSRF': df_pagina.apply(lambda x: icon_status(x, 'CSRF'), axis=1), 'INSS': df_pagina.apply(lambda x: icon_status(x, 'INSS'), axis=1), 'IRRF': df_pagina.apply(lambda x: icon_status(x, 'IRRF'), axis=1), 'Total': df_pagina.apply(lambda x: icon_status(x, 'VALOR_TOTAL'), axis=1), 'Status': df_pagina['STATUS_GERAL'].astype(str)})
            st.dataframe(df_view, hide_index=True, use_container_width=True)
        c_prev, c_info, c_next, c_export_space, c_export_btn = st.columns([1.5, 1, 1.5, 7, 2])
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
                        detalhes = row.get('Dados_Detalhados', {})
                        meta = row.get('Meta_Dados', {})
                        campos_erro = {k: v for k, v in detalhes.items() if v['status'] != 'OK' and v['erp_valor'] > 0}
                        if not campos_erro:
                            st.info("Todos os valores com divergência no ERP são R$ 0,00 ou não foram encontrados.")
                        for campo, info in campos_erro.items():
                            nome, valor = campo.replace("_", " "), formatar_moeda(info['erp_valor'])
                            msg_extra = ""
                            if info.get('is_calc'):
                                 calc_val = formatar_moeda(meta.get('Federal_Calc', 0))
                                 msg_extra = f" (Obs: ERP zerado, mas um cálculo sugere um valor próximo de **{calc_val}**)"
                            kws_usadas = globals().get(f"KW_{campo.split(' ')[0]}", [])
                            kw_html = "".join([f"<span class='kw-badge'>{k}</span>" for k in kws_usadas]) or "N/A"
                            html_parts = [
                                "<div class='div-card'>",
                                f"<div style='margin-bottom:8px;'><b>{nome}</b>: ERP espera <b>{valor}</b>{msg_extra}</div>",
                                "<div style='font-size:0.9em; color:#666;'>",
                                "<b>Diagnóstico:</b> Valor não localizado no PDF próximo às palavras-chave.",
                                f"<b>Keywords:</b> {kw_html}",
                                "</div>",
                                "</div>"
                            ]
                            html_string = "".join(html_parts)
                            st.markdown(html_string, unsafe_allow_html=True)
                    
                    st.write("") 
                    col_btn_vazia1, col_btn_centro, col_btn_vazia2 = st.columns([1, 2, 1])
                    with col_btn_centro:
                        if st.button("✅ Conciliar Manualmente", key=f"manual_concile_{row_index}", use_container_width=True):
                            original_index = st.session_state.dados_processados[st.session_state.dados_processados['ID_ARQUIVO'] == row['ID_ARQUIVO']].index[0]
                            st.session_state.dados_processados.loc[original_index, 'STATUS_GERAL'] = 'Conciliado (Manual)'
                            for k in st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados']:
                                st.session_state.dados_processados.loc[original_index, 'Dados_Detalhados'][k]['status'] = 'OK (Manual)'
                            st.success(f"Nota {row['NO_NF']} conciliada manualmente!")
                            time.sleep(1)
                            st.rerun()

                with col_pdf:
                    pdf_content = st.session_state.pdf_files_map.get(row['ID_ARQUIVO'])
                    if pdf_content:
                        base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    else:
                        st.error("Arquivo PDF não encontrado na memória para exibição.")



