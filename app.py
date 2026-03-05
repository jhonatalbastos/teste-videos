import streamlit as st
import google.generativeai as genai
import os
import subprocess
import concurrent.futures
import time

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA
# ==========================================
try:
    MINHAS_API_KEYS = st.secrets["api_keys"]
except Exception:
    st.error("Erro: Chaves API não encontradas nos Secrets.")
    MINHAS_API_KEYS = []

class GerenciadorDeCota:
    def __init__(self, keys):
        self.keys = keys
        self.index = 0
    
    def obter_proxima_chave(self):
        if not self.keys: return None
        key = self.keys[self.index]
        self.index = (self.index + 1) % len(self.keys)
        return key

gerenciador = GerenciadorDeCota(MINHAS_API_KEYS)

# ==========================================
# FUNÇÕES DE GERAÇÃO COM AUTO-RETRY
# ==========================================

def gerar_imagem_com_retry(prompt, id_job, tentativas=3):
    for i in range(tentativas):
        chave = gerenciador.obter_proxima_chave()
        try:
            genai.configure(api_key=chave)
            model = genai.GenerativeModel('gemini-2.5-flash-image')
            response = model.generate_content(prompt)
            
            path = f"img_{id_job}.png"
            for chunk in response.candidates[0].content.parts:
                if hasattr(chunk, 'inline_data'):
                    with open(path, "wb") as f:
                        f.write(chunk.inline_data.data)
                    return path
        except Exception as e:
            if "429" in str(e) and i < tentativas - 1:
                time.sleep(2) # Espera 2 segundos e tenta a próxima chave
                continue
            return f"Erro Imagem: {str(e)}"
    return "Erro: Todas as chaves falharam (Limite de Cota)."

def gerar_audio_com_retry(texto, id_job, tentativas=3):
    for i in range(tentativas):
        chave = gerenciador.obter_proxima_chave()
        try:
            genai.configure(api_key=chave)
            # O modelo TTS exige uma configuração específica de geração para AUDIO
            model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
            
            # Mudança importante: Solicitando explicitamente a modalidade de áudio
            response = model.generate_content(texto)
            
            path = f"audio_{id_job}.mp3"
            # Captura o áudio binário diretamente da parte da resposta
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            with open(path, "wb") as f:
                f.write(audio_data)
            return path
        except Exception as e:
            if "429" in str(e) and i < tentativas - 1:
                time.sleep(2)
                continue
            return f"Erro Áudio: {str(e)}"
    return "Erro: Todas as chaves falharam (Limite de Cota)."

# ==========================================
# MONTAGEM DE VÍDEO (FFMPEG)
# ==========================================

def montar_video_ffmpeg(img_path, audio_path, out_path):
    try:
        comando = [
            'ffmpeg', '-y', 
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', out_path
        ]
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode != 0:
            return f"Erro FFmpeg: {resultado.stderr}"
        return out_path
    except Exception as e:
        return f"Erro ao processar vídeo: {str(e)}"

# ==========================================
# INTERFACE
# ==========================================
st.set_page_config(page_title="Evangelho Video Maker", layout="centered")
st.title("🙏 Criador de Vídeos do Evangelho")

prompt_img = st.text_input("Descreva a cena para a imagem")
texto_audio = st.text_area("Texto para a narração")

if st.button("🎬 Gerar e Montar Vídeo"):
    if prompt_img and texto_audio:
        with st.spinner("⏳ Rodando chaves em rotação para evitar limites..."):
            
            # 1. Tenta gerar a Imagem
            res_img = gerar_imagem_com_retry(prompt_img, "final")
            
            # 2. Tenta gerar o Áudio
            res_aud = gerar_audio_com_retry(texto_audio, "final")

            if "Erro" not in res_img and "Erro" not in res_aud:
                video_final = "resultado_evangelho.mp4"
                sucesso_video = montar_video_ffmpeg(res_img, res_aud, video_final)
                
                if "Erro" not in sucesso_video:
                    st.success("Vídeo concluído com sucesso!")
                    st.video(video_final)
                    with open(video_final, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, "video_evangelho.mp4")
                    
                    os.remove(res_img)
                    os.remove(res_aud)
                else:
                    st.error(sucesso_video)
            else:
                st.error(f"Falha na geração:\n\n{res_img}\n\n{res_aud}")
    else:
        st.warning("Preencha os campos.")
