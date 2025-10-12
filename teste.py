import streamlit as st

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de IMC",
    page_icon="⚖️",
    layout="centered")

# --- Título e Descrição ---
st.title("⚖️ Calculadora de IMC Simples")
st.markdown("Use os sliders abaixo para inserir seu peso e altura e calcular seu Índice de Massa Corporal (IMC).")
st.markdown("---")

# --- Variáveis de Entrada (Usando st.slider para interatividade) ---
with st.container():
    st.subheader("Entrada de Dados")
    
    # Slider para Peso (kg)
    peso = st.slider(
        "Seu Peso (kg)", 
        min_value=30.0, 
        max_value=200.0, 
        value=70.0, 
        step=0.1,
        help="Use a alavanca para ajustar seu peso em quilogramas."
    )

    # Slider para Altura (cm)
    altura_cm = st.slider(
        "Sua Altura (cm)", 
        min_value=100, 
        max_value=250, 
        value=175, 
        step=1,
        help="Use a alavanca para ajustar sua altura em centímetros." )

# --- Lógica e Cálculo ---
if st.button("Calcular IMC", type="primary"):
    
    # Converte altura de cm para metros
    altura_m = altura_cm / 100 
    
    # Cálculo do IMC: peso / (altura * altura)
    imc = peso / (altura_m ** 2)
    
    # Arredonda para 2 casas decimais
    imc_arredondado = round(imc, 2)

    st.markdown("## Seu Resultado")
    
    # --- Determinação da Categoria do IMC e Estilo ---
    if imc < 18.5:
        categoria = "Abaixo do Peso"
        cor = "orange"
        emoji = "⚠️"
    elif 18.5 <= imc < 25:
        categoria = "Peso Normal"
        cor = "green"
        emoji = "✅"
    elif 25 <= imc < 30:
        categoria = "Sobrepeso"
        cor = "orange"
        emoji = "⚠️"
    else:
        categoria = "Obesidade"
        cor = "red"
        emoji = "🚨"

    # --- Exibição do Resultado (Usando st.metric e st.info) ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="Seu IMC é", 
            value=f"{imc_arredondado}"
        )

    with col2:
        st.info(f"{emoji} **Categoria:** {categoria}", icon="🏷️")
        
    st.markdown(f"#### <span style='color:{cor};'>Você se enquadra na categoria: **{categoria}**</span>", unsafe_allow_html=True)
    
    st.divider()

    # --- Tabela de Referência (Para Iniciantes) ---
    st.subheader("Tabela de Classificação do IMC (OMS)")
    st.table({
        'IMC': ['< 18.5', '18.5 - 24.9', '25.0 - 29.9', '>= 30.0'],
        'Categoria': ['Abaixo do Peso', 'Peso Normal', 'Sobrepeso', 'Obesidade']
    })

# --- Sidebar (Para mostrar funcionalidade avançada) ---
st.sidebar.title("Sobre o App")
st.sidebar.info(
    "Meu primeiro app no Streamlit"
