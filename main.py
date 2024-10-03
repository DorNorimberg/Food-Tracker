import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import sqlite3

# Set page configuration
st.set_page_config(page_title="מעקב תזונה", layout="wide", initial_sidebar_state="expanded")

# Custom CSS to center text, set RTL, and style tables
st.markdown("""
<style>
    .stApp {
        direction: rtl;
    }
    .stTextInput>div>div>input {
        text-align: right;
    }
    .stSelectbox>div>div>div {
        text-align: right;
    }
    .dataframe {
        direction: rtl;
    }
    .dataframe th {
        text-align: right !important;
    }
    .dataframe td {
        text-align: right !important;
    }
    button {
        float: right;
    }
    div[data-testid="stVerticalBlock"] {
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
conn = sqlite3.connect('food_tracker.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS categories
             (name TEXT PRIMARY KEY, max_points INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS foods
             (name TEXT PRIMARY KEY, category TEXT, points REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily_intake
             (date TEXT, food TEXT, category TEXT, points REAL, servings REAL)''')

# Initialize categories if the table is empty
c.execute("SELECT COUNT(*) FROM categories")
if c.fetchone()[0] == 0:
    categories = [
        ("שומנים", 11),
        ("פחמימות", 24),
        ("חלבונים", 28),
        ("ירקות", -1),  # -1 for unlimited
        ("מוצרי חלב", 16),
        ("פירות", 5)
    ]
    c.executemany("INSERT INTO categories VALUES (?, ?)", categories)
    conn.commit()


def get_remaining_points():
    today = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime('%Y-%m-%d')
    remaining_points = {}

    # Fetch all categories first
    c.execute("SELECT name, max_points FROM categories")
    all_categories = c.fetchall()

    for category, max_points in all_categories:
        c.execute("SELECT SUM(points * servings) FROM daily_intake WHERE date = ? AND category = ?", (today, category))
        used_points = c.fetchone()[0] or 0
        if max_points == -1:
            remaining = "ללא הגבלה"
        else:
            remaining = max_points - used_points
        remaining_points[category] = remaining

    return remaining_points


def add_food_item(food_name, category, points, servings):
    today = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime('%Y-%m-%d')
    c.execute("INSERT INTO daily_intake (date, food, category, points, servings) VALUES (?, ?, ?, ?, ?)",
              (today, food_name, category, points, servings))
    conn.commit()

def add_new_food_to_database(food_name, category, points):
    c.execute("INSERT INTO foods (name, category, points) VALUES (?, ?, ?)", (food_name, category, points))
    conn.commit()

def get_daily_intake():
    today = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime('%Y-%m-%d')
    c.execute("SELECT * FROM daily_intake WHERE date = ? ORDER BY category", (today,))
    return c.fetchall()


def delete_food_item(food_name, category, points, servings):
    today = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime('%Y-%m-%d')
    c.execute("""DELETE FROM daily_intake 
                 WHERE date = ? AND food = ? AND category = ? AND points = ? AND servings = ? 
                 AND rowid = (SELECT rowid FROM daily_intake 
                              WHERE date = ? AND food = ? AND category = ? AND points = ? AND servings = ? 
                              LIMIT 1)""",
              (today, food_name, category, points, servings, today, food_name, category, points, servings))
    conn.commit()


def main_page():
    st.title("מעקב תזונה יומי")

    col1, col2 = st.columns([3, 2])

    with col1:
        food_name = st.text_input("שם המזון")
        servings = st.number_input("מספר מנות", min_value=0.1, step=0.1, value=1.0)

        if st.button("הוסף מזון"):
            c.execute("SELECT * FROM foods WHERE name = ?", (food_name,))
            food = c.fetchone()

            if food:
                add_food_item(food[0], food[1], food[2], servings)
                st.success(f"נוסף {servings} מנות של {food_name}")
            else:
                st.warning("מזון לא נמצא במסד הנתונים. אנא הוסף אותו.")
                with st.form("add_new_food"):
                    new_category = st.selectbox("קטגוריה", [cat[0] for cat in c.execute("SELECT name FROM categories")])
                    new_points = st.number_input("נקודות למנה", min_value=0.1, step=0.1)
                    if st.form_submit_button("הוסף מזון חדש"):
                        try:
                            add_new_food_to_database(food_name, new_category, new_points)
                            add_food_item(food_name, new_category, new_points, servings)
                            st.success(f"נוסף {food_name} למסד הנתונים ולצריכה היומית")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"המזון {food_name} כבר קיים במסד הנתונים.")

    with col2:
        st.subheader("נקודות נותרות לכל קטגוריה:")
        remaining_points = get_remaining_points()

        # Create a DataFrame for better display
        df_points = pd.DataFrame(list(remaining_points.items()), columns=['קטגוריה', 'נקודות נותרות'])

        # Display the DataFrame as a table
        st.table(df_points)


def history_page():
    st.title("היסטוריית צריכה יומית")

    daily_intake = get_daily_intake()
    if daily_intake:
        for index, item in enumerate(daily_intake):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"{item[1]} ({item[2]})")
            with col2:
                st.write(f"{item[4]} מנות")
            with col3:
                if st.button("מחק", key=f"delete_{item[1]}_{item[3]}_{item[4]}_{index}"):
                    delete_food_item(*item[1:])
                    st.rerun()
    else:
        st.write("אין נתונים להיום")


def database_page():
    st.title("ניהול מסד נתונים")

    tab1, tab2 = st.tabs(["מזונות", "קטגוריות"])

    with tab1:
        st.subheader("הוסף מזון חדש")
        with st.form("add_food"):
            new_food = st.text_input("שם המזון")
            new_category = st.selectbox("קטגוריה", [cat[0] for cat in c.execute("SELECT name FROM categories")])
            new_points = st.number_input("נקודות למנה", min_value=0.1, step=0.1)
            if st.form_submit_button("הוסף"):
                c.execute("INSERT INTO foods VALUES (?, ?, ?)", (new_food, new_category, new_points))
                conn.commit()
                st.success(f"נוסף {new_food} למסד הנתונים")

        st.subheader("מזונות קיימים")
        foods = pd.read_sql_query("SELECT * FROM foods", conn)
        edited_df = st.data_editor(foods, num_rows="dynamic")

        if st.button("שמור שינויים"):
            c.execute("DELETE FROM foods")
            edited_df.to_sql("foods", conn, if_exists="replace", index=False)
            st.success("השינויים נשמרו בהצלחה")

    with tab2:
        st.subheader("קטגוריות קיימות")
        categories = pd.read_sql_query("SELECT * FROM categories", conn)
        st.dataframe(categories)


def main():
    st.sidebar.title("ניווט")
    page = st.sidebar.radio("עבור ל:", ["דף ראשי", "היסטוריה", "ניהול מסד נתונים"])

    if page == "דף ראשי":
        main_page()
    elif page == "היסטוריה":
        history_page()
    else:
        database_page()


if __name__ == "__main__":
    main()