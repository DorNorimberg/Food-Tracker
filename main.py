import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import os
import io
import math

# Set page configuration
st.set_page_config(page_title="מעקב תזונה", layout="wide", initial_sidebar_state="expanded")

# Custom CSS to set RTL and font
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500&display=swap');

    body {
        direction: rtl;
        text-align: right;
        font-family: 'Rubik', sans-serif;
    }
    .stButton>button {
        float: right;
    }
    .stSelectbox>div>div>select {
        direction: rtl;
    }
    .stTextInput>div>div>input {
        direction: rtl;
    }
    .points-table {
        position: fixed;
        left: 10px;
        top: 60px;
        width: 200px;
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .half-width {
        width: 50%;
    }
    .quarter-width {
        width: 25%;
    }
    .streamlit-table {
        direction: rtl;
    }
    .streamlit-table th {
        text-align: right !important;
    }
    .streamlit-table td {
        text-align: right !important;
    }
    .stDataFrame {
        direction: rtl;
    }
    .stDataFrame th {
        text-align: right !important;
    }
    .stDataFrame td {
        text-align: right !important;
    }
    /* Ensure all tables have RTL text alignment */
    table {
        direction: rtl;
    }
    th, td {
        text-align: right !important;
    }
    /* Override Streamlit's default left alignment for buttons */
    .stButton {
        text-align: right;
    }
    /* Ensure dropdowns are properly aligned */
    .stSelectbox {
        direction: rtl;
        text-align: right;
    }
    /* Adjust input fields for RTL */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        text-align: right;
    }
    /* Ensure date picker is RTL */
    .stDateInput {
        direction: rtl;
    }
    /* Adjust tab labels for RTL */
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl;
    }
    .stTabs [data-baseweb="tab"] {
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'food_data' not in st.session_state:
    st.session_state.food_data = pd.DataFrame({
        'קטגוריה': ['שומנים', 'פחמימות', 'חלבונים', 'ירקות', 'מוצרי חלב', 'פירות'],
        'מקסימום נקודות': [11, 24, 28, math.inf, 16, 5],
        'שם מזון': ['', '', '', '', '', ''],
        'נקודות למנה': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })
if 'consumption_history' not in st.session_state:
    st.session_state.consumption_history = {}

if 'remaining_points' not in st.session_state:
    st.session_state.remaining_points = {
        'שומנים': 11,
        'פחמימות': 24,
        'חלבונים': 28,
        'ירקות': math.inf,
        'מוצרי חלב': 16,
        'פירות': 5
    }

if 'last_reset_date' not in st.session_state:
    st.session_state.last_reset_date = date.today()


# Function to save data
def save_data():
    st.session_state.food_data.to_csv('food_data.csv', index=False)
    with open('consumption_history.json', 'w') as f:
        json.dump(st.session_state.consumption_history, f)
    with open('remaining_points.json', 'w') as f:
        json.dump(st.session_state.remaining_points, f)


# Function to load data
def load_data():
    if os.path.exists('food_data.csv'):
        st.session_state.food_data = pd.read_csv('food_data.csv')
    if os.path.exists('consumption_history.json'):
        with open('consumption_history.json', 'r') as f:
            st.session_state.consumption_history = json.load(f)
    if os.path.exists('remaining_points.json'):
        with open('remaining_points.json', 'r') as f:
            st.session_state.remaining_points = json.load(f)


# Load data at the start of the app
load_data()


# Function to format points
def format_points(value):
    if isinstance(value, (int, float)):
        if math.isinf(value):
            return "∞"
        elif value == int(value):
            return f"{int(value)}"
        else:
            return f"{value:.1f}".rstrip('0').rstrip('.')
    return value


# Function to reset points
def reset_points():
    today = date.today()
    if today > st.session_state.last_reset_date:
        st.session_state.remaining_points = {
            'שומנים': 11,
            'פחמימות': 24,
            'חלבונים': 28,
            'ירקות': math.inf,
            'מוצרי חלב': 16,
            'פירות': 5
        }
        today_str = today.strftime('%Y-%m-%d')
        if today_str in st.session_state.consumption_history:
            del st.session_state.consumption_history[today_str]

        st.session_state.last_reset_date = today
        save_data()


# Function to add food consumption
def add_food_consumption(food_name, servings, date):
    food_item = st.session_state.food_data[st.session_state.food_data['שם מזון'] == food_name]
    if not food_item.empty:
        category = food_item['קטגוריה'].values[0]
        points = food_item['נקודות למנה'].values[0] * servings
        if date not in st.session_state.consumption_history:
            st.session_state.consumption_history[date] = []
        st.session_state.consumption_history[date].append({
            'שם מזון': food_name,
            'קטגוריה': category,
            'מנות': servings,
            'נקודות': points
        })
        if category != 'ירקות':
            st.session_state.remaining_points[category] -= points
        save_data()
        st.success(f'המזון {food_name} נוסף בהצלחה')
        st.rerun()
    else:
        st.error('המזון לא נמצא במאגר. אנא הוסף אותו קודם.')
        st.session_state.show_add_new_food = True


# Function to add new food to database
def add_new_food(name, category, points):
    if name.strip() == '':
        st.error('שם המזון לא יכול להיות ריק')
        return
    if not st.session_state.food_data[(st.session_state.food_data['קטגוריה'] == category) &
                                      (st.session_state.food_data['שם מזון'] == name)].empty:
        st.error('המזון כבר קיים ברשימה')
        return
    new_food = pd.DataFrame({
        'קטגוריה': [category],
        'מקסימום נקודות': [
            st.session_state.food_data[st.session_state.food_data['קטגוריה'] == category]['מקסימום נקודות'].iloc[0]],
        'שם מזון': [name],
        'נקודות למנה': [points]
    })
    st.session_state.food_data = pd.concat([st.session_state.food_data, new_food], ignore_index=True)
    save_data()
    st.success(f'המזון {name} נוסף בהצלחה למאגר')


# Function to edit food consumption
def edit_food_consumption(date, index, new_servings):
    food_item = st.session_state.consumption_history[date][index]
    old_points = food_item['נקודות']
    new_points = (new_servings * old_points) / food_item['מנות']

    if food_item['קטגוריה'] != 'ירקות':
        st.session_state.remaining_points[food_item['קטגוריה']] += old_points
        st.session_state.remaining_points[food_item['קטגוריה']] -= new_points

    st.session_state.consumption_history[date][index]['מנות'] = new_servings
    st.session_state.consumption_history[date][index]['נקודות'] = new_points
    save_data()
    st.success('הצריכה עודכנה בהצלחה')


# Function to delete food consumption
def delete_food_consumption(date, index):
    food_item = st.session_state.consumption_history[date][index]
    if food_item['קטגוריה'] != 'ירקות':
        st.session_state.remaining_points[food_item['קטגוריה']] += food_item['נקודות']
    del st.session_state.consumption_history[date][index]
    if not st.session_state.consumption_history[date]:
        del st.session_state.consumption_history[date]
    save_data()
    st.success('הצריכה נמחקה בהצלחה')


# Function to generate Excel report
def generate_excel_report():
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Get dates for the last week
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=6)

    for i in range(7):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        if date in st.session_state.consumption_history:
            df = pd.DataFrame(st.session_state.consumption_history[date])
            df.to_excel(writer, sheet_name=date, index=False)

    writer.save()
    return output.getvalue()


# Main app
def main():
    reset_points()

    st.title('מעקב תזונה')

    tab1, tab2, tab3 = st.tabs(['צריכת מזון', 'היסטוריה', 'מאגר מזון'])

    with tab1:
        st.header('צריכת מזון')

        # Food consumption section
        st.subheader('הוסף צריכת מזון')
        input_col1, input_col2, input_col3, input_col4 = st.columns(4)
        with input_col1:
            food_name = st.text_input('שם המזון', key='food_name_input')
        with input_col2:
            servings = st.number_input('מספר מנות', min_value=0.1, step=0.1, value=1.0, key='servings_input')
        with input_col3:
            date = st.date_input('תאריך', datetime.now(), key='date_input')

        if st.button('הוסף צריכה', key='add_consumption_button'):
            add_food_consumption(food_name, servings, date.strftime('%Y-%m-%d'))

        # Add new food section
        st.subheader('הוסף מזון חדש')
        input_col1, input_col2, input_col3, input_col4 = st.columns(4)
        with input_col1:
            new_food_name = st.text_input('שם המזון החדש', key='new_food_name')
        with input_col2:
            new_food_category = st.selectbox('קטגוריה', st.session_state.food_data['קטגוריה'].unique(),
                                             key='new_food_category')
        with input_col3:
            new_food_points = st.number_input('נקודות למנה', min_value=0.0, step=0.1, key='new_food_points')

        if st.button('הוסף למאגר', key='add_new_food_button'):
            add_new_food(new_food_name, new_food_category, new_food_points)

        # Remaining points table at the bottom
        st.subheader('נקודות נותרות')
        points_df = pd.DataFrame(list(st.session_state.remaining_points.items()), columns=['קטגוריה', 'נקודות'])
        points_df['נקודות'] = points_df['נקודות'].apply(format_points)
        st.table(points_df.style.set_properties(**{'text-align': 'right'}))

    with tab2:
        st.header('היסטוריית צריכה')

        input_col1, input_col2, input_col3, input_col4 = st.columns(4)
        with input_col1:
            selected_date = st.date_input('בחר תאריך', datetime.now(), key='history_date_input')

        date_str = selected_date.strftime('%Y-%m-%d')

        if date_str in st.session_state.consumption_history and st.session_state.consumption_history[date_str]:
            history_data = pd.DataFrame(st.session_state.consumption_history[date_str])

            if not history_data.empty:
                edited_df = st.data_editor(
                    history_data[['קטגוריה', 'נקודות', 'מנות', 'שם מזון']],
                    column_config={
                        "שם מזון": st.column_config.TextColumn("שם מזון", width="medium"),
                        "מנות": st.column_config.NumberColumn("מנות", width="small", format="%.1f"),
                        "נקודות": st.column_config.NumberColumn("נקודות", width="small", format="%.1f"),
                        "קטגוריה": st.column_config.TextColumn("קטגוריה", width="medium"),
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    key="history_table"
                )

                if st.button('שמור שינויים', key='save_history_changes'):
                    # Update consumption history
                    st.session_state.consumption_history[date_str] = edited_df.to_dict('records')

                    # Update remaining points
                    for category in st.session_state.remaining_points.keys():
                        if category != 'ירקות':
                            old_total = sum(item['נקודות'] for item in
                                            history_data[history_data['קטגוריה'] == category].to_dict('records'))
                            new_total = sum(item['נקודות'] for item in
                                            edited_df[edited_df['קטגוריה'] == category].to_dict('records'))
                            st.session_state.remaining_points[category] += old_total - new_total

                    # Remove the date if all items are deleted
                    if edited_df.empty:
                        del st.session_state.consumption_history[date_str]

                    save_data()
                    st.success('השינויים נשמרו בהצלחה')
                    st.rerun()
            else:
                st.warning('אין היסטוריה עבור היום הזה')
                del st.session_state.consumption_history[date_str]
                save_data()
        else:
            st.warning('אין היסטוריה עבור היום הזה')

    with tab3:
        st.header('מאגר מזון')

        input_col1, input_col2, input_col3, input_col4 = st.columns(4)
        with input_col1:
            selected_category = st.selectbox('בחר קטגוריה', [''] + list(st.session_state.food_data['קטגוריה'].unique()))

        if selected_category:
            category_data = st.session_state.food_data[st.session_state.food_data['קטגוריה'] == selected_category]

            input_col1, input_col2, input_col3, input_col4 = st.columns(4)
            with input_col1:
                new_food_name = st.text_input('שם המזון החדש', key='new_food_name_empty')
            with input_col2:
                new_food_points = st.number_input('נקודות למנה', min_value=0.0, step=0.1, key='new_food_points_empty')

            if st.button('הוסף מזון חדש', key='add_new_food_empty'):
                if new_food_name.strip() != '':
                    new_food = pd.DataFrame({
                        'קטגוריה': [selected_category],
                        'מקסימום נקודות': [
                            st.session_state.food_data[st.session_state.food_data['קטגוריה'] == selected_category][
                                'מקסימום נקודות'].iloc[0]],
                        'שם מזון': [new_food_name],
                        'נקודות למנה': [new_food_points]
                    })
                    st.session_state.food_data = pd.concat([st.session_state.food_data, new_food], ignore_index=True)
                    save_data()
                    st.success(f'המזון {new_food_name} נוסף בהצלחה לקטגוריה {selected_category}')
                    st.rerun()
                else:
                    st.error('שם המזון לא יכול להיות ריק')

            if category_data.empty or category_data['שם מזון'].isnull().all() or (category_data['שם מזון'] == '').all():
                st.warning('הקטגוריה ריקה')
            else:
                edited_df = st.data_editor(
                    category_data[['שם מזון', 'נקודות למנה']],
                    num_rows="dynamic",
                    key=f"data_editor_{selected_category}",
                    column_config={
                        "שם מזון": st.column_config.TextColumn(
                            "שם מזון",
                            width="medium",
                            required=True,
                        ),
                        "נקודות למנה": st.column_config.NumberColumn(
                            "נקודות למנה",
                            width="small",
                            min_value=0,
                            max_value=100,
                            step=0.1,
                            format="%.1f",
                        ),
                    },
                )

                if st.button('שמור שינויים', key='save_changes_button'):
                    # Filter out rows with blank food names or NaN points
                    valid_entries = edited_df[(edited_df['שם מזון'].notna()) & (edited_df['שם מזון'] != '') & (
                        edited_df['נקודות למנה'].notna())]

                    # Update the food_data DataFrame for the selected category
                    max_points = st.session_state.food_data[st.session_state.food_data['קטגוריה'] == selected_category][
                        'מקסימום נקודות'].iloc[0]
                    st.session_state.food_data = st.session_state.food_data[
                        st.session_state.food_data['קטגוריה'] != selected_category]

                    if not valid_entries.empty:
                        new_category_data = pd.DataFrame({
                            'קטגוריה': [selected_category] * len(valid_entries),
                            'מקסימום נקודות': [max_points] * len(valid_entries),
                            'שם מזון': valid_entries['שם מזון'],
                            'נקודות למנה': valid_entries['נקודות למנה']
                        })
                    else:
                        new_category_data = pd.DataFrame({
                            'קטגוריה': [selected_category],
                            'מקסימום נקודות': [max_points],
                            'שם מזון': [''],
                            'נקודות למנה': [0.0]
                        })

                    st.session_state.food_data = pd.concat([st.session_state.food_data, new_category_data],
                                                           ignore_index=True)

                    save_data()
                    st.success('השינויים נשמרו בהצלחה')
                    st.rerun()
        else:
            st.write('בחר קטגוריה כדי לראות או לערוך מזונות')


# Call the main function
if __name__ == "__main__":
    main()
