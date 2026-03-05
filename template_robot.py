# template_robot.py (VERSÃO OTIMIZADA + MEDIDOR DE TEMPO)

import os
import time
import ctypes
from playwright.sync_api import sync_playwright
import json
import re
import shutil # Adicione este import

# --- Funções auxiliares (sem alterações) ---
def report_progress(total, current, message):
    try:
        progress_data = {"total": total, "current": current, "message": message}
        progress_file = os.path.join(os.path.expanduser("~"), "Downloads", "progress.json")
        with open(progress_file, "w", encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except: pass

def write_summary(summary_data):
    try:
        summary_file = os.path.join(os.path.expanduser("~"), "Downloads", "summary.json")
        with open(summary_file, "w", encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False)
    except: pass

def check_control_command():
    control_file = os.path.join(os.path.expanduser("~"), "Downloads", "control.json")
    if os.path.exists(control_file):
        try:
            with open(control_file, 'r', encoding='utf-8') as f:
                command = json.load(f).get("command")
            return command
        except: return None
    return None

def run():
    # ======================================================================
    # 💡 MELHORIA 1: Medir o tempo de execução 💡
    # ======================================================================
    start_time = time.time()
    
    usuario = "{USER}"
    senha = "{PASS}"
    
    browser = None
    try:
        report_progress(1, 0, "Iniciando automação e fazendo login...")
        
        #PASTA_DESTINO = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")
        #if not os.path.exists(PASTA_DESTINO): os.makedirs(PASTA_DESTINO)

        # --- INÍCIO DA NOVA IMPLEMENTAÇÃO DE LIMPEZA ---

        # 1. Defina o caminho para a pasta de destino.
        #    (O caminho foi ajustado para corresponder ao seu código original)
        PASTA_DESTINO = os.path.join(os.path.expanduser("~"), "Downloads", "Notas_Fluig")

        try:
            # 2. Verifique se a pasta existe.
            if os.path.exists(PASTA_DESTINO):
                # 3. Se existir, delete a pasta e todo o seu conteúdo.
                print(f"Limpando pasta de destino: {PASTA_DESTINO}")
                report_progress(1, 0, f"Limpando pasta de execuções anteriores...")
                shutil.rmtree(PASTA_DESTINO)
            
            # 4. Crie a pasta novamente, garantindo que ela esteja limpa e pronta.
            os.makedirs(PASTA_DESTINO)
            print(f"Pasta de destino '{PASTA_DESTINO}' pronta para o download.")

        except Exception as e:
            # 5. Se houver um erro na limpeza, registre e pare a execução.
            print(f"ERRO CRÍTICO: Não foi possível limpar a pasta de destino. Erro: {e}")
            report_progress(1, 1, f"ERRO: Não foi possível limpar a pasta de destino. Verifique as permissões.")
            write_summary({"status": "error", "message": f"Falha na limpeza da pasta: {e}"})
            if browser: browser.close()
            return # Interrompe a execução do robô

        # --- FIM DA NOVA IMPLEMENTAÇÃO DE LIMPEZA ---
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            page.goto("http://fluig.censo-nso.com.br:8080/portal/home"  )
            if page.locator('//*[@id="username"]').is_visible():
                page.locator('//*[@id="username"]').fill(usuario)
                page.locator('//*[@id="password"]').fill(senha)
                page.locator('//*[@id="submitLogin"]').click()
            page.wait_for_url("**/portal/**", timeout=60000)
            
            report_progress(1, 0, "Navegando até a página de conferência...")
            page.wait_for_timeout(5000)
            page.locator("a").filter(has_text="Central Controladoria").first.click(timeout=30000)
            page.wait_for_timeout(1000)
            page.get_by_role("link", name="Conferência Fiscal").first.click()
            page.wait_for_timeout(5000)

            frame_alvo = next((f for f in page.frames if f.locator("//tr[.//span[contains(text(),'Anexo')]]").count() > 0), None)
            
            if not frame_alvo:
                ctypes.windll.user32.MessageBoxW(0, "Nenhum Fluig com anexo foi encontrado.", "Aviso", 64)
            else:
                report_progress(1, 0, "Fase A: Mapeando todas as tarefas (Colheita)...")
                tasks_to_process = []
                all_rows = frame_alvo.locator("//tr[.//span[contains(text(),'Anexo')]]").all()
                
                for row in all_rows:
                    match = re.search(r'\b(\d{6})\b', row.inner_text())
                    if match:
                        fluig_id = match.group(1)
                        anexos_locators = row.locator("span", has_text="Anexo").all()
                        tasks_to_process.append({
                            "fluig_id": fluig_id,
                            "anexos": anexos_locators
                        })
                
                if not tasks_to_process:
                    raise Exception("Não foi possível extrair os IDs dos Fluigs da página.")

                total_tasks = len(tasks_to_process)
                downloaded_files_list = []
                skipped_files_list = []
                
                report_progress(total_tasks, 0, "Fase B: Iniciando processamento em lote...")

                for i, task in enumerate(tasks_to_process):
                    fluig_id = task["fluig_id"]
                    
                    command = check_control_command()
                    if command == "cancel": raise Exception("Cancelado pelo usuário")
                    while command == "pause":
                        report_progress(total_tasks, i, f"Pausado em {i+1}/{total_tasks}. Aguardando...")
                        time.sleep(2)
                        command = check_control_command()
                        if command == "cancel": raise Exception("Cancelado pelo usuário")

                    report_progress(total_tasks, i, f"Processando Fluig ID {fluig_id} ({i+1}/{total_tasks}) | Baixados: {len(downloaded_files_list)}")
                    
                    for anexo_span in task["anexos"]:
                        anexo_text = anexo_span.inner_text()
                        anexo_num_match = re.search(r'\d+', anexo_text)
                        anexo_num = anexo_num_match.group(0) if anexo_num_match else "X"

                        try:
                            anexo_span.scroll_into_view_if_needed()
                            anexo_span.click()
                            time.sleep(0.5)

                            btn_acoes = frame_alvo.locator('//button[contains(text(), "Ações do documento")]').first
                            btn_acoes.click()
                            time.sleep(0.5)

                            download_link = frame_alvo.locator('//a[text()="Download"]')
                            
                            if download_link.is_visible(timeout=5000):
                                with page.expect_download(timeout=30000) as dl_info:
                                    download_link.click()
                                
                                dl = dl_info.value
                                original_filename = dl.suggested_filename
                                safe_original_filename = re.sub(r'[\\/*?:"<>|]', "", original_filename)
                                novo_nome_arquivo = f"FLUIG_{fluig_id}_ANEXO_{anexo_num}_{safe_original_filename}"
                                file_path = os.path.join(PASTA_DESTINO, novo_nome_arquivo)
                                dl.save_as(file_path)
                                
                                if os.path.exists(file_path):
                                    downloaded_files_list.append(novo_nome_arquivo)
                            else:
                                skipped_files_list.append(f"Fluig {fluig_id} ({anexo_text})")
                        except Exception as inner_e:
                            print(f"Erro em um anexo no Fluig {fluig_id}, tentando recuperar: {inner_e}")
                        finally:
                            try:
                                close_button = page.locator('//div[contains(@id, "wcm-panel")]//div[contains(@class, "close") or @role="button"]').last
                                if close_button.is_visible(timeout=1000):
                                    close_button.click()
                                else:
                                    page.keyboard.press("Escape")
                            except:
                                page.keyboard.press("Escape")
                            time.sleep(1)

                report_progress(total_tasks, total_tasks, "Processo finalizado, gerando resumo...")
                
                # ======================================================================
                # 💡 MELHORIA 2: Calcular e adicionar o tempo ao resumo 💡
                # ======================================================================
                end_time = time.time()
                total_duration_seconds = end_time - start_time
                
                summary = {
                    "status": "success",
                    "total_fluigs": total_tasks,
                    "downloaded_count": len(downloaded_files_list),
                    "skipped_count": len(skipped_files_list),
                    "skipped_list": skipped_files_list,
                    "duration_seconds": total_duration_seconds # Nova informação
                }
                write_summary(summary)
                ctypes.windll.user32.MessageBoxW(0, "Downloads concluídos! Veja o resumo do processamento.", "Sucesso", 64)

            if browser: browser.close()
    except Exception as e:
        if browser and browser.is_connected(): browser.close()
        end_time = time.time()
        total_duration_seconds = end_time - start_time
        summary = {
            "status": "error",
            "message": str(e),
            "duration_seconds": total_duration_seconds
        }
        write_summary(summary)
        if "Cancelado pelo usuário" not in str(e):
            ctypes.windll.user32.MessageBoxW(0, f"Ocorreu um erro na automação:\n{e}", "Erro", 16)

if __name__ == "__main__":
    run()