# template_robot_movimentacao.py

import os
import time
from playwright.sync_api import sync_playwright
import json
import ast  # <-- NOVO: Biblioteca nativa para converter string em lista de forma segura

def report_progress(total, current, message):
    try:
        progress_data = {"total": total, "current": current, "message": message}
        progress_file = os.path.join(os.path.expanduser("~"), "Downloads", "progress_movimentacao.json")
        with open(progress_file, "w", encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except: pass

def write_summary(summary_data):
    try:
        summary_file = os.path.join(os.path.expanduser("~"), "Downloads", "summary_movimentacao.json")
        with open(summary_file, "w", encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False)
    except: pass

def check_control_command():
    control_file = os.path.join(os.path.expanduser("~"), "Downloads", "control_movimentacao.json")
    if os.path.exists(control_file):
        try:
            with open(control_file, 'r', encoding='utf-8') as f:
                command = json.load(f).get("command")
            return command
        except: return None
    return None

def run():
    usuario = "{USER}"
    senha = "{PASS}"
    
    # AGORA ENTRE ASPAS: O Pylance lê como uma simples string e não apita erro.
    lista_fluigs_str = "{FLUIGS_LIST}" 

    # # Converte a string injetada de volta para uma Lista Python real
    # try:
    #     lista_fluigs = ast.literal_eval(lista_fluigs_str) if lista_fluigs_str != "{FLUIGS_LIST}" else []
    # except Exception:
    #     lista_fluigs = [
    
    # --- NOVO CONVERSOR À PROVA DE BALAS ---
    try:
        # Apenas verifica se a lista injetada tem colchetes
        if "[" in lista_fluigs_str:
            # Limpa colchetes, aspas, espaços e lixos de memória (nan)
            texto_limpo = lista_fluigs_str.replace("[", "").replace("]", "").replace("'", "").replace('"', "").replace("nan", "")
            # Corta pelas vírgulas e guarda só o que for texto válido
            lista_fluigs = [item.strip() for item in texto_limpo.split(",") if item.strip()]
        else:
            lista_fluigs = []
    except Exception:
        lista_fluigs = []

    if not usuario or not lista_fluigs:
        write_summary({"status": "error", "message": "Usuário ou lista de Fluigs ausente."})
        return

    browser = None
    try:
        report_progress(len(lista_fluigs), 0, "Iniciando automação e fazendo login...")
        with sync_playwright() as p:
            # Rodando silenciosamente (headless=True)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()

            # 1. ACESSO E LOGIN
            page.goto("http://fluig.censo-nso.com.br:8080/portal/home")
            if page.locator('//*[@id="username"]').is_visible():
                page.locator('//*[@id="username"]').fill(usuario)
                time.sleep(0.5)
                page.locator('//*[@id="password"]').fill(senha)
                time.sleep(0.5)
                page.locator('//*[@id="submitLogin"]').click()

            try:
                page.wait_for_url("**/portal/**", timeout=30000)
            except:
                raise Exception("Falha no Login ou tempo excedido.")

            # 2. NAVEGAÇÃO
            report_progress(len(lista_fluigs), 0, "Navegando para Conferência Fiscal...")
            time.sleep(0.5)
            try: page.mouse.move(50, 300)
            except: pass

            navegou = False
            try:
                page.get_by_text("Central Controladoria").first.click(timeout=3000)
                time.sleep(1)
                page.get_by_text("Conferência Fiscal").first.click(timeout=3000)
                navegou = True
            except:
                pass

            if not navegou:
                try:
                    page.locator('//*[@id="liquidMenu_4065176"]').first.hover()
                    page.locator('//*[@id="liquidMenu_4065176"]/div/aside/div[1]/nav/ul/li[14]/a').click(force=True)
                    time.sleep(1)
                    page.locator('//*[@id="liquidMenu_4065176"]/div/aside/div[1]/nav/ul/li[2]/a').click(force=True)
                except:
                    raise Exception("Erro de navegação. Não foi possível acessar a Conferência Fiscal.")

            # 3. IDENTIFICAR O FRAME DA TABELA
            report_progress(len(lista_fluigs), 0, "Buscando tabela de documentos...")
            time.sleep(1)
            frame_alvo = None
            for frame in page.frames:
                try:
                    if frame.locator("input[type='checkbox']").count() > 0:
                        if frame.get_by_text("Fluig").count() > 0 or frame.get_by_text("Nota Fiscal").count() > 0:
                            frame_alvo = frame
                            break
                except: continue

            if not frame_alvo:
                frame_alvo = page.main_frame

            # 4. LOOP DE MARCAÇÃO
            qtd_marcados = 0
            ids_nao_encontrados = []
            total = len(lista_fluigs)

            for i, fluig_id in enumerate(lista_fluigs):
                command = check_control_command()
                if command == "cancel": raise Exception("Cancelado pelo usuário")

                report_progress(total, i, f"Buscando e marcando Fluig {fluig_id} ({i+1}/{total})...")
                try:
                    xpath_linha = f"//tr[.//td[contains(., '{fluig_id}')]]"
                    linha = frame_alvo.locator(xpath_linha).first

                    if linha.is_visible():
                        checkbox = linha.locator("input[type='checkbox']").first
                        if not checkbox.is_checked():
                            checkbox.click()
                            qtd_marcados += 1
                            report_progress(total, i+1, f"Fluig {fluig_id} MARCADO!")
                        else:
                            report_progress(total, i+1, f"Fluig {fluig_id} já estava marcado.")
                    else:
                        ids_nao_encontrados.append(fluig_id)
                except Exception as e:
                    ids_nao_encontrados.append(fluig_id)

            # 5. AÇÃO FINAL: MOVIMENTAR
            if qtd_marcados > 0:
                report_progress(total, total, "Clicando no botão 'Movimentar Documentos'...")
                time.sleep(1)
                btn_texto = "Movimentar Documentos"
                btn = frame_alvo.get_by_text(btn_texto, exact=False).first
                if not btn.is_visible():
                    btn = page.get_by_text(btn_texto, exact=False).first

                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
                    write_summary({
                        "status": "success",
                        "message": f"Sucesso! {qtd_marcados} documentos foram marcados e movimentados.",
                        "qtd_marcados": qtd_marcados,
                        "ids_nao_encontrados": ids_nao_encontrados
                    })
                else:
                    write_summary({
                        "status": "error",
                        "message": f"Itens marcados ({qtd_marcados}), mas o botão 'Movimentar Documentos' não foi encontrado."
                    })
            else:
                write_summary({
                    "status": "warning",
                    "message": "Nenhum Fluig da lista foi encontrado ou marcado na tela."
                })

    except Exception as e:
        if browser and browser.is_connected(): browser.close()
        write_summary({"status": "error", "message": str(e)})
        
    finally:
        try: os.remove(__file__)
        except: pass

if __name__ == "__main__":
    run()