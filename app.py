import streamlit as st
import google.generativeai as genai
import os
import subprocess
import time

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA (SECRETS)
# ==========================================
try:
    # Suas 5 chaves devem estar no TOML do Streamlit
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
# GERAÇÃO DE IMAGEM (CORRIGIDO)
# ==========================================
def gerar_imagem(prompt, id_job):
    for _ in range(len(MINHAS_API_KEYS)): # Tenta em todas as chaves se necessário
        chave = gerenciador.obter_proxima_chave()
        try:
            genai.configure(api_key=chave)
            # Usando o modelo flash mais estável para geração de imagem
            model = genai.GenerativeModel('gemini-2.5-flash-image')
            response = model.generate_content(prompt)
            
            path = f"img_{id_job}.png"
            # Captura binária correta da imagem
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data'):
                    with open(path, "wb") as f:
                        f.write(part.inline_data.data)
                    return path
        except Exception as e:
            if "429" in str(e):
                continue # Pula para a próxima chave
            return f"Erro Imagem: {str(e)}"
    return "Erro: Todas as chaves atingiram o limite de cota."

# ==========================================
# GERAÇÃO DE ÁUDIO (CORRIGIDO PARA MODALIDADE AUDIO)
# ==========================================
def gerar_audio(texto, id_job):
    for _ in range(len(MINHAS_API_KEYS)):
        chave = gerenciador.obter_proxima_chave()
        try:
            genai.configure(api_key=chave)
            # Chamada específica para modelos nativos de áudio (Speech-to-Speech/TTS)
            model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
            
            # Em 2026, a resposta do TTS vem em um formato de stream binário
            response = model.generate_content(texto)
            
            path = f"audio_{id_job}.mp3"
            # O segredo: extrair os bytes do áudio da primeira parte da resposta
            audio_bytes = response.candidates[0].content.parts[0].inline_data.data
            
            with open(path, "wb") as f:
                f.write(audio_bytes)
            return path
        except Exception as e:
            if "429" in str(e):
                continue
            return f"Erro Áudio: {str(e)}"
    return "Erro: Limite de cota atingido no áudio."

# ==========================================
# MONTAGEM DE VÍDEO (FFMPEG DIRETO)
# ==========================================
def montar_video(img_path, audio_path, out_path):
    try:
        # Comando para criar vídeo de imagem estática + áudio
        comando = [
            'ffmpeg', '-y', 
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', out_path
        ]
        subprocess.run(comando, capture_output=True, check=True)
        return out_path
    except Exception as e:
        return f"Erro FFmpeg: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Evangelho AI", page_icon="🙏")
st.title("🎥 Criador de Vídeos Bíblicos")

with st.form("gerador"):
    prompt = st.text_input("Descreva a imagem (Ex: Batismo de Jesus no Rio Jordão, estilo realista)")
    versiculo = st.text_area("Texto para narração (Versículo)")
    submit = st.form_submit_button("Gerar Vídeo")

if submit:
    if not prompt or not versiculo:
        st.warning("Preencha todos os campos!")
    else:
        with st.spinner("⏳ Processando arte e voz... (Usando rotação de chaves)"):
            path_img = gerar_imagem(prompt, "v1")
            path_aud = gerar_audio(versiculo, "v1")
            
            if "Erro" not in path_img and "Erro" not in path_aud:
                video_file = "video_final.mp4"
                resultado = montar_video(path_img, path_aud, video_file)
                
                if "Erro" not in resultado:
                    st.success("Vídeo gerado com sucesso!")
                    st.video(video_file)
                    with open(video_file, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, file_name="versiculo_video.mp4")
                else:
                    st.error(resultado)
            else:
                st.error(f"Falha na API: {path_img} | {path_aud}")
