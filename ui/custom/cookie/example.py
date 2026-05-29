import streamlit as st

from ui.custom.cookie import CookieManager

st.title("CookieManager test app")

manager = CookieManager()
st.write("Current cookies:", manager.get_all())

cookie_name = st.text_input("Cookie name", value="demo")
cookie_value = st.text_input("Cookie value", value="hello")

col1, col2 = st.columns(2)
with col1:
    if st.button("Set cookie"):
        manager.set(cookie_name, cookie_value, key="set_cookie")
        st.success("Cookie set")
with col2:
    if st.button("Delete cookie"):
        manager.delete(cookie_name, key="delete_cookie")
        st.success("Cookie deleted")

if st.button("Refresh cookie list"):
    st.write("Current cookies:", manager.get_all(key="refresh_cookies"))
