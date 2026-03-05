import os
import concurrent.futures
import streamlit as st
import google.generativeai as genai

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA (STREAMLIT SECRETS)
# ==========================================
# No Streamlit Cloud, você cadastrará assim:
# api_keys = ["sua_chave_1", "sua_chave_2"]
try:
    # Tenta ler a lista de chaves dos Secrets do Streamlit
    MINHAS_API_KEYS = st.secrets["api_keys"]
except Exception:
    st.error("Erro: Chaves API não encontradas nos Secrets do Streamlit.")
    MINHAS_API_KEYS = []

class GerenciadorDeCota:
    def __init__(self, keys):
        self.keys = keys
        self.index = 0

    def obter_proxima_chave(self):
        if not self.keys:
            return None
        key = self.keys[self.index]
        self.index = (self.index + 1) % len(self.keys)
        return key

gerenciador = GerenciadorDeCota(MINHAS_API_KEYS)

# ==========================================
# FUNÇÕES DE GERAÇÃO
# ==========================================

def gerar_imagem(prompt, index):
    try:
        chave = gerenciador.obter_proxima_chave()
        if not chave: return "Erro: Sem chave API"
        
        genai.configure(api_key=chave)
        model = genai.GenerativeModel('gemini-2.5-flash-image')
        
        response = model.generate_content(prompt)
        
        # Salvando em memória para o Streamlit exibir
        for chunk in response.candidates[0].content.parts:
            if hasattr(chunk, 'inline_data'):
                return chunk.inline_data.data
        return None
    except Exception as e:
        return f"Erro: {str(e)}"

def gerar_audio(texto, index):
    try:
        chave = gerenciador.obter_proxima_chave()
        if not chave: return "Erro: Sem chave API"

        genai.configure(api_key=chave)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
        
        response = model.generate_content(texto)
        return response.data # Bytes do áudio
    except Exception as e:
        return f"Erro: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================

st.set_page_config(page_title="Gerador Evangelho AI", layout="wide")
st.title("🙏 Produtor de Conteúdo Cristão")
st.subheader("Geração em massa com múltiplas chaves API")

col1, col2 = st.columns(2)

with col1:
    st.header("🖼️ Prompts de Imagem")
    prompts_input = st.text_area("Um prompt por linha", 
                                 "Jesus caminhando sobre as águas, estilo realista\nA Arca de Noé no dilúvio, arte épica", 
                                 height=200)

with col2:
    st.header("🎙️ Textos para Áudio")
    textos_input = st.text_area("Um texto por linha", 
                                "O Senhor é o meu pastor.\nTudo posso naquele que me fortalece.", 
                                height=200)

if st.button("🚀 Gerar Tudo Simultaneamente"):
    lista_prompts = [p.strip() for p in prompts_input.split('\n') if p.strip()]
    lista_textos = [t.strip() for t in textos_input.split('\n') if t.strip()]
    
    if not MINHAS_API_KEYS:
        st.warning("Configure suas chaves API nos Secrets primeiro!")
    else:
        st.info(f"Processando com {len(MINHAS_API_KEYS)} chaves em rotação...")
        
        # Execução Paralela
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Dispara as tarefas
            img_futures = [executor.submit(gerar_imagem, p, i) for i, p in enumerate(lista_prompts)]
            audio_futures = [executor.submit(gerar_audio, t, i) for i, t in enumerate(lista_textos)]
            
            # Exibe Imagens conforme ficam prontas
            st.divider()
            st.write("### Resultados:")
            
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                for f in concurrent.futures.as_completed(img_futures):
                    res = f.result()
                    if isinstance(res, bytes):
                        st.image(res, caption="Imagem Gerada", use_column_width=True)
                    else:
                        st.error(res)

            with res_col2:
                for f in concurrent.futures.as_completed(audio_futures):
                    res = f.result()
                    if isinstance(res, bytes):
                        st.audio(res, format="audio/mp3")
                    else:
                        st.error(res)
