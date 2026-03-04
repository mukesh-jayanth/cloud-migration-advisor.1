import streamlit as st
from cost_engine import calculate_onprem_tco, calculate_manual_tco

st.set_page_config(page_title="CMDSS", layout="wide")

st.title("Cloud Migration Decision Support System")
st.write("On-Premise Cost Analysis")

st.sidebar.write("Assumptions")
st.sidebar.write("Server Cost: $5000")
st.sidebar.write("Maintenance: 15%")
st.sidebar.write("Power: $500/server/year")
st.sidebar.write("Admin Salary: $80k/year")
st.sidebar.write("Growth Rate: 15%")

st.divider()

# -------------------------------
# Input Method Selection
# -------------------------------

input_method = st.radio(
    "Select Input Method",
    [
        "Upload Infrastructure Dataset",
        "Use Enterprise Preset",
        "Manual Inputs"
    ]
)

st.divider()

# -------------------------------
# Dataset Upload Option
# -------------------------------

if input_method == "Upload Infrastructure Dataset":

    uploaded_file = st.file_uploader(
        "Upload Infrastructure Excel File",
        type=["xlsx"]
    )

    if uploaded_file:

        result = calculate_onprem_tco(file_path=uploaded_file)

        st.success("Cost calculation completed.")

        col1, col2, col3 = st.columns(3)

        col1.metric("Servers", result["servers"])
        col2.metric("Storage (TB)", result["storage_tb"])
        col3.metric("Hardware Cost ($)", f"{result['hardware_cost']:,.0f}")

        st.divider()

        col4, col5 = st.columns(2)

        col4.metric("3-Year TCO ($)", f"{result['tco_3yr']:,.0f}")
        col5.metric("5-Year TCO ($)", f"{result['tco_5yr']:,.0f}")


# -------------------------------
# Enterprise Preset Option
# -------------------------------

elif input_method == "Use Enterprise Preset":

    preset = st.selectbox(
        "Select Enterprise Size",
        ["small", "medium", "large"]
    )

    if st.button("Calculate Cost"):

        result = calculate_onprem_tco(preset=preset)

        st.success("Cost calculation completed.")

        col1, col2, col3 = st.columns(3)

        col1.metric("Servers", result["servers"])
        col2.metric("Storage (TB)", result["storage_tb"])
        col3.metric("Hardware Cost ($)", f"{result['hardware_cost']:,.0f}")

        st.divider()

        col4, col5 = st.columns(2)

        col4.metric("3-Year TCO ($)", f"{result['tco_3yr']:,.0f}")
        col5.metric("5-Year TCO ($)", f"{result['tco_5yr']:,.0f}")


# -------------------------------
# Manual Input Option
# -------------------------------

elif input_method == "Manual Inputs":

    st.subheader("Manual Infrastructure Inputs")

    servers = st.number_input(
        "Number of Servers",
        min_value=1,
        value=20
    )

    storage = st.number_input(
        "Total Storage (TB)",
        min_value=1.0,
        value=10.0
    )

    if st.button("Calculate Cost"):

        result = calculate_manual_tco(
            servers=servers,
            storage_tb=storage
        )

        st.success("Cost calculation completed.")

        col1, col2, col3 = st.columns(3)

        col1.metric("Servers", result["servers"])
        col2.metric("Storage (TB)", result["storage_tb"])
        col3.metric("Hardware Cost ($)", f"{result['hardware_cost']:,.0f}")

        st.divider()

        col4, col5 = st.columns(2)

        col4.metric("3-Year TCO ($)", f"{result['tco_3yr']:,.0f}")
        col5.metric("5-Year TCO ($)", f"{result['tco_5yr']:,.0f}")