import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import io
import sys

# ===================== PASSWORD PROTECTION =====================
APP_PASSWORD = "secure123"  # Change this for security

def check_password():
    st.sidebar.title("🔒 Login")
    pwd = st.sidebar.text_input("Enter Password", type="password")
    if pwd == APP_PASSWORD:
        return True
    else:
        if pwd:
            st.sidebar.error("❌ Wrong password!")
        return False

# ===================== LOAD SOURCES =====================
def load_sources():
    try:
        with open("sources.json", "r", encoding="utf-8") as f:
            return json.load(f)["sources"]
    except Exception as e:
        st.error(f"⚠ Error loading sources.json: {e}")
        return []

# ===================== SCRAPER =====================
def scrape_site(url, keywords, exclude_words):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all <a> tags
        articles = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            if text:
                text_lower = text.lower()
                if any(kw.lower() in text_lower for kw in keywords) and not any(
                    ew.lower() in text_lower for ew in exclude_words
                ):
                    full_link = link["href"]
                    if not full_link.startswith("http"):
                        full_link = url.rstrip("/") + "/" + full_link.lstrip("/")
                    articles.append({"title": text, "link": full_link, "source": url})
        return articles
    except Exception as e:
        st.warning(f"❌ Error scraping site {url}: {e}")
        return []

# ===================== GOOGLE NEWS FALLBACK =====================
def scrape_google_news(keywords):
    try:
        base = "https://news.google.com/search?q=" + "%20".join(keywords)
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(base, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for item in soup.select("article h3 a"):
            title = item.get_text(strip=True)
            link = "https://news.google.com" + item["href"][1:]
            results.append({"title": title, "link": link, "source": "Google News"})
        return results
    except Exception as e:
        st.warning(f"❌ Error scraping Google News: {e}")
        return []

# ===================== MAIN APP =====================
def main_app():
    st.title("📰 Polish Local News Scraper")
    st.write("Search **350+ Polish sources** with keyword + exclusion filters.")

    # Load sources
    sources = load_sources()
    st.sidebar.info(f"✅ Loaded {len(sources)} sources")

    # Filters
    keywords = st.text_input("🔍 Keywords (comma separated)", "wypadek,morderstwo")
    exclude_words = st.text_input("🚫 Exclude words (comma separated)", "sport,piłka")

    run_search = st.button("🚀 Run Search")

    if run_search:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        ex_list = [e.strip() for e in exclude_words.split(",") if e.strip()]

        st.write(f"🔎 Searching for **{kw_list}** while excluding **{ex_list}**")

        all_results = []

        progress = st.progress(0)
        for i, site in enumerate(sources):
            site_url = site["url"]
            site_results = scrape_site(site_url, kw_list, ex_list)
            all_results.extend(site_results)
            progress.progress((i + 1) / len(sources))

        # Google News fallback
        google_results = scrape_google_news(kw_list)
        all_results.extend(google_results)

        # Convert to DataFrame
        df = pd.DataFrame(all_results).drop_duplicates()

        if not df.empty:
            st.success(f"✅ Found {len(df)} matching articles")
            st.dataframe(df)

            # Save to Excel in memory
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="News Report", index=False)
            buffer.seek(0)

            # Streamlit download button
            st.download_button(
                label="📥 Download Excel Report",
                data=buffer,
                file_name="polish_news_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠ No matching news found.")

# ===================== STREAMLIT MAIN =====================
def main():
    if check_password():
        main_app()
    else:
        st.stop()

if __name__ == "__main__":
    main()
